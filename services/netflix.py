import argparse, configparser,  glob, json, logging, os, re, shutil, subprocess, sys, time, ffmpy, pycountry, requests, tqdm
from bs4 import BeautifulSoup
from threading import Thread
from urllib.parse import urlsplit
import utils.modules.pycaption as pycaption
from http.cookiejar import MozillaCookieJar
from configs.config import tool
from helpers.aria2 import aria2
from helpers.dfxp_to_srt import dfxp_to_srt
from helpers.keyloader import keysaver
from helpers.Muxer import Muxer
from helpers.Parsers.Netflix import get_keys
from helpers.Parsers.Netflix.get_manifest import get_manifest
from helpers.ripprocess import EpisodesNumbersHandler, ripprocess
from helpers.vpn import connect
from pywidevine.cdm import cdm, deviceconfig
from pywidevine.decrypt.wvdecryptcustom import WvDecrypt

class netflix:
	def __init__(self, args, commands):
		self.logger = logging.getLogger(__name__)
		self.args = args
		self.tool = tool()
		self.config = self.tool.config("NETFLIX")
		self.bin = self.tool.bin()
		self.ripprocess = ripprocess()
		self.EpisodesNumbersHandler = EpisodesNumbersHandler()
		self.commands = commands
		self.keysaver = keysaver(keys_file=self.config["keys_file"])
		self.logdata = {}  # to save title data for debug or use later
		self.source_tag = "NF"
		self.dfxp_to_srt = dfxp_to_srt()
		self.aria2 = aria2()
		self.video_settings = self.tool.video_settings()
		self.checkList = list()

	def DumpStoredData(self, nfid):
		if nfid:
			return
		name = "NETFLIX-{}.json".format(nfid)
		nfid_json = os.path.join(self.config["jsonpath"], name)
		with open(nfid_json, "w", encoding="utf-8") as file_:
			file_.write(json.dumps(self.logdata, indent=4))
			file_.flush()
			file_.close()

	def store(self, data, keyword):
		self.logdata.update({keyword: data})
		return

	def get_build(self, cookies): #
		BUILD_REGEX = r'"BUILD_IDENTIFIER":"([a-z0-9]+)"'

		session = requests.Session()
		session.headers = {
			"Connection": "keep-alive",
			"Upgrade-Insecure-Requests": "1",
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36",
			"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
			"Sec-Fetch-Site": "none",
			"Sec-Fetch-Mode": "navigate",
			"Sec-Fetch-Dest": "document",
			"Accept-Language": "en,en-US;q=0.9",
		}

		r = session.get("https://www.netflix.com/browse", cookies=cookies)

		if not re.search(BUILD_REGEX, r.text):
			print(
				"cannot get BUILD_IDENTIFIER from the cookies you saved from the browser..."
			)
			sys.exit()

		return re.search(BUILD_REGEX, r.text).group(1)

	def save(self, cookies, build): #
		cookie_data = {}
		for name, value in cookies.items():
			cookie_data[name] = [value, 0]
		logindata = {"BUILD_IDENTIFIER": build, "cookies": cookie_data}
		with open(self.config["cookies_file"], "w", encoding="utf8") as f:
			f.write(json.dumps(logindata, indent=4))
			f.close()
		os.remove(self.config["cookies_txt"])

	def read_userdata(self): #
		cookies = None
		build = None

		if not os.path.isfile(self.config["cookies_file"]):
			try:
				cj = MozillaCookieJar(self.config["cookies_txt"])
				cj.load()
			except Exception:
				print("invalid netscape format cookies file")
				sys.exit()

			cookies = dict()

			for cookie in cj:
				cookies[cookie.name] = cookie.value

			build = self.get_build(cookies)
			self.save(cookies, build)

		with open(self.config["cookies_file"], "rb") as f:
			content = f.read().decode("utf-8")

		if "NetflixId" not in content:
			self.logger.warning("(Some) cookies expired, renew...")
			return cookies, build

		jso = json.loads(content)
		build = jso["BUILD_IDENTIFIER"]
		cookies = jso["cookies"]
		for cookie in cookies:
			cookie_data = cookies[cookie]
			value = cookie_data[0]
			if cookie != "flwssn":
				cookies[cookie] = value
		if cookies.get("flwssn"):
			del cookies["flwssn"]

		return cookies, build

	def shakti_api(self, nfid): #
		url = f"https://www.netflix.com/api/shakti/{self.build}/metadata"
		headers = {
			"Accept": "*/*",
			"Accept-Encoding": "gzip, deflate, br",
			"Accept-Language": "es,ca;q=0.9,en;q=0.8",
			"Cache-Control": "no-cache",
			"Connection": "keep-alive",
			"Host": "www.netflix.com",
			"Pragma": "no-cache",
			"Sec-Fetch-Mode": "cors",
			"Sec-Fetch-Site": "same-origin",
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36",
			"X-Netflix.browserName": "Chrome",
			"X-Netflix.browserVersion": "79",
			"X-Netflix.clientType": "akira",
			"X-Netflix.esnPrefix": "NFCDCH-02-",
			"X-Netflix.osFullName": "Windows 10",
			"X-Netflix.osName": "Windows",
			"X-Netflix.osVersion": "10.0",
			"X-Netflix.playerThroughput": "1706",
			"X-Netflix.uiVersion": self.build,
		}

		params = {
			"movieid": nfid,
			"drmSystem": "widevine",
			"isWatchlistEnabled": "false",
			"isShortformEnabled": "false",
			"isVolatileBillboardsEnabled": "false",
			"languages": self.config["metada_language"],
		}

		while True:
			resp = requests.get(
				url=url, headers=headers, params=params, cookies=self.cookies
			)

			if resp.status_code == 401:
				self.logger.warning("401 Unauthorized, cookies is invalid.")
			elif resp.text.strip() == "":
				self.logger.error("title is not available in your Netflix region.")
				exit(-1)

			try:
				t = resp.json()["video"]["type"]
				return resp.json()
			except Exception:
				os.remove(self.config["cookies_file"])
				self.logger.warning(
					"Error getting metadata: Cookies expired\nplease fetch new cookies.txt"
				)
				exit(-1)

	def Search(self, query):
		session = requests.Session()
		session.headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"
		}
		# select profile
		'''profiles = list()
		resp = session.get("https://www.netflix.com/browse", cookies=self.cookies)
		bs = BeautifulSoup(resp.text, "html.parser")
		profiles_ = bs.find_all("a", {"class": "profile-link"})

		for profile in profiles_:
			profiles.append(
				(profile.find("span", {"class": "profile-name"}).text, profile["href"])
			)

		if profiles == []:
			self.logger.warning(
				"Cannot select user profile, maybe cookies is invalid or the account has no profies."
			)
			return None

		# request page with the profile
		session.get("https://www.netflix.com" + profiles[0][1], cookies=self.cookies)'''
		# search for title
		resp = session.get(
			"https://www.netflix.com/search?q=" + query, cookies=self.cookies
		)

		if not resp.status_code == 200:
			self.logger.error("error searching, maybe invalid cookies.")
			return None

		# add all search itmes
		itmes = []
		bs = BeautifulSoup(resp.text, "html.parser")
		titles = bs.find_all("div", {"class": "title-card-container"})

		for title in titles:
			itmes.append(
				{
					"name": title.find(
						"div", {"class": "fallback-text-container"}
					).text,
					"id": title.find("a", href=True)["href"]
					.split("?")[0]
					.split("/")[2],
				}
			)

		if itmes == []:
			self.logger.error(
				f'Your search for "{query}" did not have any matches, try different keywords.'
			)
			return None

		# usually first item is the right items
		self.logger.info("Founded: {} items".format(str(len(itmes))))
		self.logger.info("id: {} - name: {}".format(itmes[0]["id"], itmes[0]["name"]))
		isRightItem = input("if this what you looking: Enter yes or no: ").strip()
		if isRightItem.lower() == "y" or isRightItem.lower() == "yes":
			return int(itmes[0]["id"])

		# first item is wrong

		self.logger.info("The available items is: ")
		for idx, item in enumerate(itmes, start=1):
			self.logger.info(
				"[{}] - id: {} - name: {}".format(idx, item["id"], item["name"])
			)

		item_number = input("\nChoose item number: ").strip()
		if item_number.isdigit():
			item = itmes[item_number - 1]["id"]
			return int(item)

		return None

	def get_nfid(self, content_id): #
		if content_id.isdigit():
			return int(content_id)

		validUrl = re.compile(
			r'https?://(?:www\.)?netflix\.com/(\w+)?/?(?:title|watch|browse?jbv=)/?(?P<id>\d+)'
		)

		nfID = validUrl.match(content_id)
		
		if nfID:
			return int(nfID.group('id'))

		else:
			nfID = re.search(r'[0-9]{8}$', content_id)
			
			if nfID:
				return int(nfID[0])

			else:
				self.logger.error('Detection of NF ID from the given url: Failed.')
				sys.exit()

	def CleanSubtitleVTT(self, file_content):
		file_content = re.sub(r"{.*?}", "", file_content)
		file_content = re.sub(
			r"(.*\bposition:50.00%.*\bline:10.00%)\s*(.*)",
			r"\1\n{\\an8}\2",
			file_content,
		)

		file_content = re.sub(r"&rlm;", "\u202B", file_content)
		file_content = re.sub(r"&lrm;", "\u202A", file_content)
		file_content = re.sub(r"&amp;", "&", file_content)
		file_content = re.sub(r"([\d]+)\.([\d]+)", r"\1,\2", file_content)
		file_content = re.sub(r"WEBVTT\n\n", "", file_content)
		file_content = re.sub(r"NOTE.*\n", "", file_content)
		file_content = re.sub(r"\n\s+\n", "", file_content)
		file_content = re.sub(r" position:.+%", "", file_content)
		file_content = re.sub(r"</?c.+?>", "", file_content)
		return file_content

	def downloadFile2(self, url, file_name):
		with open(file_name, "wb") as f:
			response = requests.get(url, stream=True)
			#response.encoding = 'UTF-8'
			f.write(response.content)

		return

	def downloadFile(self, url, file_name, silent=False):
		self.logger.info("\n" + file_name)

		if self.args.noaria2c:
			self.ripprocess.tqdm_downloader(url, file_name)
			return

		options = self.aria2.aria2Options(
			allow_overwrite=True,
			quiet=silent,
			file_allocation=None,
			auto_file_renaming=False,
			async_dns="skip",
			retry_wait=5,
			summary_interval=0,
			enable_color=True,
			connection=16,
			concurrent_downloads=16,
			split=16,
			uri_selector="inorder",
			console_log_level="warn",
			download_result="hide",
			extra_commands=[]
			if self.args.no_download_proxy
			else self.commands["aria2c_extra_commands"],
		)

		self.aria2.aria2DownloadUrl(
			url=url, output=file_name, options=options, debug=False, moded=False
		)

		return

	def GetKeys(self, IDNet, profilename):
		video_keys = []
		available_profiles = [
			"High KEYS",
			"HEVC KEYS",
			"HDR-10 KEYS",
			"Main KEYS"
		]

		if not profilename in available_profiles:
			self.logger.error("Error: Unknown profile: {}".format(profilename))
			sys.exit(1)

		try:
			video_keys = get_keys.GettingKEYS_Netflixv2(IDNet, profilename)
			if not video_keys == []:
				video_keys = list(set(video_keys))
				video_keys = [profilename] + video_keys
				self.logger.info("Done!")
			else:
				self.logger.error("Error!")
		except Exception as e:
			self.logger.error("Error!: {}".format(e))

		return video_keys

	def GetAudioCocedName(self, audioList):
		codecs = {
			"ddplus-atmos-dash": "DDP5.1.Atmos",
			"ddplus-5.1hq-dash": "DDP5.1",
			"ddplus-5.1-dash": "DDP5.1",
			"dd-5.1-dash": "DD5.1",
			"ddplus-2.0-dash": "DDP2.0",
			"heaac-5.1hq-dash": "AAC5.1",
			"heaac-5.1-dash": "AAC5.1",
			"heaac-2-dash": "AAC2.0",
			"heaac-2hq-dash": "AAC2.0",
			"playready-oggvorbis-2-dash": "OGG2.0",
		}

		profiles = [x["Profile"] for x in audioList]
		if not profiles == []:
			for profile in profiles:
				try:
					return codecs[profile]
				except KeyError:
					pass

		return "DDP5.1"

	def RemuxVideo(self, outputVideoTemp, outputVideo, Name):
		self.logger.info("\nRemuxing video...")
		ff = ffmpy.FFmpeg(
			executable=self.bin["ffmpeg"],
			inputs={outputVideoTemp: None},
			outputs={outputVideo: "-c copy"},
			global_options="-y -hide_banner -loglevel warning",
		)

		ff.run()
		time.sleep(50.0 / 1000.0)
		os.remove(outputVideoTemp)
		self.logger.info("Done!")
		return True

	def DecryptVideo_withtxtkeys(self, inputVideo, outputVideoTemp, outputVideo, kid, Name):
		with open(self.config["keys_file"] + "NETFLIX.keys", "r") as keys_file_netflix:
			keys_video = keys_file_netflix.readlines()

		keys_video = [x.strip() for x in keys_video if ":" in x]
		if not keys_video == []:
			for key in keys_video:
				if key[0:32] == kid:
					self.logger.info("\nDecrypting video...")
					self.logger.info("Using KEY: " + key)
					subprocess.call(
						[
							self.bin["mp4decrypt"],
							"--show-progress",
							"--key",
							key,
							inputVideo,
							outputVideoTemp,
						]
					)
					self.RemuxVideo(outputVideoTemp, outputVideo, Name)
					return True
		self.logger.warning("\nKEY for " + inputVideo + " is not in txt.")
		return False

	def DecryptVideo(self, inputVideo, outputVideoTemp, outputVideo, IDNet, Name, Profile, silent=False):
		KID = self.keysaver.generate_kid(inputVideo)
		KEYS = self.keysaver.get_key_by_kid(KID)

		if KEYS == []:
			self.logger.info("\nKEY for {} not saved before.".format(inputVideo))
			self.logger.info("\nGetting Video KEYS...")

			if self.args.video_high:
				KEYS = self.GetKeys(IDNet, "High KEYS")
			else:
				if self.args.hevc:
					KEYS = self.GetKeys(IDNet, "HEVC KEYS")
				else:
					if self.args.hdr:
						KEYS = self.GetKeys(IDNet, "HDR-10 KEYS")
					else:
						if "playready-h264hpl" in Profile:
								KEYS = self.GetKeys(IDNet, "High KEYS")
						else:
							KEYS = self.GetKeys(IDNet, "Main KEYS")
			# ~
			if KEYS == []:
				return False

			KEYS = self.keysaver.dump_keys(
				keys=[key for key in KEYS if ":" in key], pssh=None, name=Name
			)

		only1key = [x for x in KEYS if x["KID"] == KID]
		if not only1key == []:
			KEYS = only1key

		self.ripprocess.mp4_decrypt(
			encrypted=inputVideo,
			decrypted=outputVideoTemp,
			keys=KEYS,
			moded_decrypter=True,
			no_kid=False,
			silent=silent,
		)

		if not "NETFLIX".lower() in list(
			map(lambda x: x.lower(), self.video_settings["skip_video_demux"])
		):
			self.ripprocess.DemuxVideo(
				outputVideoTemp=outputVideoTemp,
				outputVideo=outputVideo,
				ffmpeg=True,
				mp4box=False,
			)
		else:
			os.rename(outputVideoTemp, outputVideo)

		return True

	def SubtitleThreader(self, subtitlesList, name):
		for z in subtitlesList:
			if str(dict(z)["isForced"]) == "YES":
				langAbbrev = "forced-" + str(dict(z)["langAbbrev"])
			elif str(dict(z)["isForced"]) == "SDH":
				langAbbrev = "sdh-" + str(dict(z)["langAbbrev"])
			else:
				langAbbrev = str(dict(z)["langAbbrev"])

			ext = "dfxp" if str(dict(z)["Profile"]) == "dfxp-ls-sdh" else "vtt"
			inputSubtitleDFXP = f"{name} {langAbbrev}.{ext}"
			inputSubtitleSrt = f"{name} {langAbbrev}.srt"
			if os.path.isfile(inputSubtitleDFXP) or os.path.isfile(inputSubtitleSrt):
				pass
			else:
				self.downloadFile2(str(dict(z)["Url"]), inputSubtitleDFXP)

		dfxp = glob.glob(name + "*.dfxp")
		vtt = glob.glob(name + "*.vtt")
		if not dfxp == []:
			for f in dfxp:
				self.dfxp_to_srt.convert(f, f.replace(".dfxp", ".srt"))
				os.remove(f)

		if not vtt == []:
			for f in vtt:
				with open(f, "r+", encoding="utf-8") as x:
					old = x.read()
				with open(f.replace(".vtt", ".srt"), "w+", encoding="utf-8") as x:
					x.write(self.CleanSubtitleVTT(old))
				os.remove(f)

	def downloadItem(self, item):

		TitleName = item["TitleName"]
		FolderName = item["FolderName"]

		try:
			CurrentHeigh = str(item["video"]["Height"])
			CurrentWidth = str(item["video"]["Width"])
		except Exception:
			CurrentHeigh = "None"
			CurrentWidth = "None"

		if not self.args.nosubs:
			SubsThread = Thread(
				target=self.SubtitleThreader,
				args=(item["subtitle"] + item["forced"], TitleName,),
			)
			SubsThread.start()
			self.logger.info("\nSubtitle Thread download started.")

		if not self.args.novideo:
			self.logger.info("\nDownloading video...")
			if self.args.hevc:
				inputVideo = f"{TitleName} [{CurrentHeigh}p] [HEVC].mp4"
				outputVideoTemp = (
					f"{TitleName} [{CurrentHeigh}p] [HEVC]_DecryptTemp.mp4"
				)
				inputVideo_demuxed = f"{TitleName} [{CurrentHeigh}p] [HEVC]_Demuxed.mp4"
			elif self.args.hdr:
				inputVideo = f"{TitleName} [{CurrentHeigh}p] [HDR].mp4"
				outputVideoTemp = f"{TitleName} [{CurrentHeigh}p] [HDR]_DecryptTemp.mp4"
				inputVideo_demuxed = f"{TitleName} [{CurrentHeigh}p] [HDR]_Demuxed.mp4"
			else:
				if "playready-h264hpl" in str(
					item["video"]["Profile"]
				) or "playready-h264shpl" in str(item["video"]["Profile"]):
					inputVideo = f"{TitleName} [{CurrentHeigh}p] [HIGH].mp4"
					outputVideoTemp = (
						f"{TitleName} [{CurrentHeigh}p] [HIGH]_DecryptTemp.mp4"
					)
					inputVideo_demuxed = (
						f"{TitleName} [{CurrentHeigh}p] [HIGH]_Demuxed.mp4"
					)
				else:
					inputVideo = f"{TitleName} [{CurrentHeigh}p].mp4"
					outputVideoTemp = f"{TitleName} [{CurrentHeigh}p]_DecryptTemp.mp4"
					inputVideo_demuxed = f"{TitleName} [{CurrentHeigh}p]_Demuxed.mp4"

			if (
				os.path.isfile(inputVideo)
				and not os.path.isfile(inputVideo + ".aria2")
				or os.path.isfile(inputVideo_demuxed)
			):
				self.logger.info(
					"\n"
					+ inputVideo
					+ "\nFile has already been successfully downloaded previously."
				)
			else:
				self.downloadFile(item["video"]["Url"], inputVideo)

		#################################################################################

		if not self.args.noaudio:
			self.logger.info("\nDownloading audio...")
			for audio in item["audio"]:
				langAbbrev = dict(audio)["Language"]
				inputAudio = f"{TitleName} {langAbbrev}-audio.mp4"
				inputAudio2 = f"{TitleName} {langAbbrev}.ac3"
				inputAudio3 = f"{TitleName} {langAbbrev}.eac3"
				inputAudio4 = f"{TitleName} {langAbbrev}.m4a"
				inputAudio5 = f"{TitleName} {langAbbrev}.oga"
				if (
					os.path.isfile(inputAudio)
					and not os.path.isfile(inputAudio + ".aria2")
					or os.path.isfile(inputAudio2)
					or os.path.isfile(inputAudio3)
					or os.path.isfile(inputAudio4)
					or os.path.isfile(inputAudio5)
				):
					self.logger.info(
						"\n"
						+ inputAudio
						+ "\nFile has already been successfully downloaded previously."
					)
				else:
					self.downloadFile(str(dict(audio)["Url"]), inputAudio)

		#################################################################################

		IDNet = item["NetflixID"]
		self.CorrectDecryptVideo = False

		if not self.args.novideo:
			if not os.path.isfile(inputVideo_demuxed):
				self.CorrectDecryptVideo = self.DecryptVideo(
					inputVideo=inputVideo,
					outputVideoTemp=outputVideoTemp,
					outputVideo=inputVideo_demuxed,
					IDNet=IDNet,
					Name=TitleName,
					Profile=str(item["video"]["Profile"]),
				)
			else:
				self.CorrectDecryptVideo = True

		if not self.args.noaudio:
			for audio in item["audio"]:
				langAbbrev = dict(audio)["Language"]
				inputAudio = f"{TitleName} {langAbbrev}-audio.mp4"
				inputAudio2 = f"{TitleName} {langAbbrev}.ac3"
				inputAudio3 = f"{TitleName} {langAbbrev}.eac3"
				inputAudio4 = f"{TitleName} {langAbbrev}.m4a"
				inputAudio5 = f"{TitleName} {langAbbrev}.oga"
				if (
					os.path.isfile(inputAudio2)
					or os.path.isfile(inputAudio3)
					or os.path.isfile(inputAudio4)
					or os.path.isfile(inputAudio5)
				):
					pass
				else:
					self.ripprocess.DemuxAudio(inputAudio, "-audio.mp4")

		#################################################################################

		if not self.args.nosubs:
			SubsThread.join()

		muxedFile = None

		if (
			not self.args.novideo
			and not self.args.noaudio
			and self.CorrectDecryptVideo is True
		):
			mkvmuxer = Muxer(
				CurrentName=TitleName,
				SeasonFolder=FolderName,
				CurrentHeigh=CurrentHeigh,
				CurrentWidth=CurrentWidth,
				mkvmerge=self.bin["mkvmerge"],
				Source=self.source_tag,
				group=self.commands["group"],
			)
			muxedFile = mkvmuxer.startMux()

		if not self.args.keep:
			self.ripprocess.do_clean(
				TitleName, exclude=self.args.clean_exclude, added=self.args.clean_add
			)

		self.store(item, "item_info")
		self.DumpStoredData(item["NetflixID"])
		self.logger.info("Done!")

		return

	def getItem(self, NetflixID, TitleName, FolderName):

		self.FilesInFolder = []
		if FolderName:
			GlobFiles = glob.glob(f"{FolderName}/*.*", recursive=True)
			if not GlobFiles == []:
				for files in GlobFiles:
					self.FilesInFolder.append(os.path.basename(files))

		if self.args.license:
			KEYS = []

			self.logger.info("\nGetting KEYS...")

			if self.args.hevc:
				KEYS += self.GetKeys(NetflixID, "HEVC KEYS")
			
			elif self.args.hdr:
				KEYS += self.GetKeys(NetflixID, "HDR-10 KEYS")
			
			else: 
				for profile in ["Main KEYS", "High KEYS"]:
					KEYS += self.GetKeys(NetflixID, profile)

			self.logger.info("\n" + TitleName + "\n")
			self.logger.info("\n".join(KEYS))
			KEYS = [x for x in KEYS if ":" in x]
			if not KEYS == []:
				KEYS = self.keysaver.dump_keys(keys=KEYS, pssh=None, name=TitleName)
			return

		VideoList, AudioList, SubtitleList, ForcedList, checkerinfo = get_manifest(
			self.args, NetflixID
		).LoadManifest()

		if self.args.check:
			itemdata = [
				{
					'title': re.search(r'S\d+E\d+', TitleName)[0]
					if self.netflixType == 'show'
					else TitleName, 
					'checkinfo': checkerinfo, 
					'videolist': VideoList
				}
			]
			self.checkList.extend(itemdata)
			return

		if not self.args.novideo:
			self.logger.info(checkerinfo)
			self.logger.info(
				"VIDEO - Bitrate: {}kbps | Profile: {} | Size: {} | Fps: {} | Vmaf: {} | Drm: {} | Resolution: {}x{}".format(
					str(dict(VideoList[-1])["Bitrate"]),
					str(dict(VideoList[-1])["Profile"]),
					str(dict(VideoList[-1])["Size"]),
					str(dict(VideoList[-1])["FrameRate"]),
					str(dict(VideoList[-1])["vmaf"]),
					dict(VideoList[-1])["Drm"],
					str(dict(VideoList[-1])["Width"]),
					str(dict(VideoList[-1])["Height"]),
				)
			)

		if not self.args.noaudio:
			self.logger.info("\n")
			for Audio in AudioList:
				self.logger.info(
					"AUDIO - Bitrate: {}kbps | Profile: {} | Size: {} | Original: {} | Drm: {} | Channels: {}ch | Language: {}".format(
						str(dict(Audio)["Bitrate"]),
						str(dict(Audio)["Profile"]),
						str(dict(Audio)["Size"]),
						str(dict(Audio)["Original"]),
						dict(Audio)["Drm"],
						str(dict(Audio)["channels"]),
						str(dict(Audio)["Language"]),
					)
				)

		if not self.args.nosubs:
			self.logger.info("\n")
			for Subtitle in SubtitleList + ForcedList:
				self.logger.info(
					"SUBTITLE -  Profile: {} | Type: {} | isForced: {} | Language: {}".format(
						str(dict(Subtitle)["Profile"]),
						str(dict(Subtitle)["rawTrackType"]),
						str(dict(Subtitle)["isForced"]),
						str(dict(Subtitle)["Language"]),
					)
				)

		self.logger.info(f"\n{TitleName}\n")

		downloaddict = {
			"NetflixID": NetflixID,
			"TitleName": TitleName,
			"FolderName": FolderName,
			"video": VideoList[-1] if not VideoList == [] else VideoList,
			"audio": AudioList,
			"subtitle": SubtitleList,
			"forced": ForcedList,
		}

		self.logger.debug("downloaddict: {}".format(downloaddict))

		if not self.args.prompt:
			choice = "y"
		else:
			choice = input("\nDoes this look right? Answer yes to download. (y/n): ")

		if choice.lower() == "y" or choice.lower() == "yes":
			self.downloadItem(downloaddict)
		elif choice.lower() == "n" or choice.lower() == "no":
			self.logger.info("Quitting...")

		return

	def main_netflix(self):
		self.cookies, self.build = self.read_userdata()
		self.nfID = None
		if self.args.content:
			self.nfID = self.get_nfid(self.args.content)
			if not self.nfID:
				self.logger.error(
					"Cannot detect netflix id: {}".format(self.args.content)
				)
				exit(-1)
		elif self.args.search:
			self.logger.info("\nSearching NetFlix For: {}".format(self.args.search))
			SearchItem = self.Search(str(self.args.search))
			if not SearchItem:
				self.logger.error("Search Failed: {}".format(self.args.search))
				exit(-1)

			self.nfID = int(SearchItem)
		else:
			self.nfID = self.get_nfid(
				input("Netflix viewable ID / watch URL: ").strip()
			)

		self.logger.info("Getting Metadata...")
		data = self.shakti_api(str(self.nfID))
		self.logger.debug("Metadata: {}".format(data))

		if data["video"]["type"] == "movie":
			self.netflixType = "movie"
		else:
			if data["video"]["type"] == "show":
				self.netflixType = "show"
			else:
				if data["video"]["type"] == "supplemental":
					self.netflixType = "supplemental"
				else:
					self.logger.info(data["video"]["type"] + " is a unrecognized type!")
					sys.exit(0)

		######################################
		if self.args.output:
			dl_location = self.args.output
			if not os.path.exists(dl_location):
				os.makedirs(dl_location)
		else:
			try:
				temp_download = "{}/{}".format(
					tool().paths()["DL_FOLDER"], "downloads/netflix"
				)
				if not os.path.exists(temp_download):
					os.makedirs(temp_download)
				dl_location = temp_download
			except Exception:
				temp_download = "downloads/netflix"
				if not os.path.exists(temp_download):
					os.makedirs(temp_download)
				dl_location = temp_download

		os.chdir(dl_location)
		######################################

		self.items = []
		isAEpisode = False

		if self.netflixType == "movie" or self.netflixType == "supplemental":
			mainTitle = "{} {}".format(
				self.ripprocess.RemoveCharcters(data["video"]["title"]),
				self.ripprocess.RemoveCharcters(str(data["video"]["year"])),
			)
		else:
			mainTitle = self.ripprocess.RemoveCharcters(data["video"]["title"])

		try:
			if (
				str(data["video"]["currentEpisode"]) == str(self.nfID)
				and self.netflixType == "show"
			):
				isAEpisode = True
		except Exception:
			pass

		if self.netflixType == "movie" or self.netflixType == "supplemental":
			self.getItem(
				self.nfID,
				self.args.titlecustom[0] if self.args.titlecustom else mainTitle,
				None,
			)

		elif self.netflixType == "show":
			if isAEpisode:
				self.logger.info("\nID or URL belongs to episode...")
				for season in data["video"]["seasons"]:
					for episode in season["episodes"]:
						if int(episode["id"]) == int(self.nfID):
							self.items.append(
								{
									"TitleName": "{} S{}E{} {}".format(
										self.args.titlecustom[0]
										if self.args.titlecustom
										else mainTitle,
										str(season["seq"]).zfill(2),
										str(episode["seq"]).zfill(2),
										self.ripprocess.RemoveCharcters(
											episode["title"]
										),
									),
									"FolderName": "{} S{}".format(
										self.args.titlecustom[0]
										if self.args.titlecustom
										else mainTitle,
										str(season["seq"]).zfill(2),
									),
									"NetflixID": episode["episodeId"],
								}
							)
			else:
				seasonMatchNumber = (
					str(self.args.season).lstrip("0")
					if self.args.season
					else str(input("ENTER Season Number: ").strip()).lstrip("0")
				)

				AllowedEpisodesNumbers = (
					self.EpisodesNumbersHandler.sortNumbers(
						str(self.args.episodeStart).lstrip("0")
					)
					if self.args.episodeStart
					else self.EpisodesNumbersHandler.sortNumbers("~")
				)

				for season in data["video"]["seasons"]:
					if int(season["seq"]) == int(seasonMatchNumber):
						for episode in season["episodes"]:
							if int(episode["seq"]) in AllowedEpisodesNumbers:
								self.items.append(
									{
										"TitleName": "{} S{}E{} {}".format(
											self.args.titlecustom[0]
											if self.args.titlecustom
											else mainTitle,
											str(season["seq"]).zfill(2),
											str(episode["seq"]).zfill(2),
											self.ripprocess.RemoveCharcters(
												episode["title"]
											),
										),
										"FolderName": "{} S{}".format(
											self.args.titlecustom[0]
											if self.args.titlecustom
											else mainTitle,
											str(season["seq"]).zfill(2),
										),
										"NetflixID": episode["episodeId"],
									}
								)

			self.logger.info("\nTotal items will be downloaded: {}".format(len(self.items)))
			for idx, epsiode in enumerate(self.items, start=1):
				self.logger.info(
					"downloading: {} of {}".format(
						str(idx).zfill(2), str(len(self.items)).zfill(2)
					)
				)
				self.getItem(
					epsiode["NetflixID"],
					self.ripprocess.RemoveCharcters(epsiode["TitleName"]),
					epsiode["FolderName"],
				)	

		if self.args.check:
			self.logger.info('\nCheck Result')
			for item in self.checkList:
				if "MAIN is Better" in item['checkinfo']:
					self.logger.info(item['title'] + ' : MAIN')
				else:
					L3 = str(dict(item['videolist'][-1])["L3"])
					self.logger.info(item['title'] + ' : HIGH ' + L3)