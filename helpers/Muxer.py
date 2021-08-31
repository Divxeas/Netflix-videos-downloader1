
import re, os, sys, subprocess, contextlib, json, glob
from configs.config import tool
from helpers.ripprocess import ripprocess
from pymediainfo import MediaInfo
import logging


class Muxer(object):
	def __init__(self, **kwargs):
		self.logger = logging.getLogger(__name__)
		self.CurrentName_Original = kwargs.get("CurrentName", None)
		self.CurrentName = kwargs.get("CurrentName", None)
		self.SeasonFolder = kwargs.get("SeasonFolder", None)
		self.CurrentHeigh = kwargs.get("CurrentHeigh", None)
		self.CurrentWidth = kwargs.get("CurrentWidth", None)
		self.source_tag = kwargs.get("Source", None)
		self.AudioProfile = self.get_audio_id()  # kwargs.get("AudioProfile", None)
		self.VideoProfile = self.get_video_id()  # kwargs.get("VideoProfile", None)
		self.mkvmerge = tool().bin()["mkvmerge"]
		self.merge = []
		self.muxer_settings = tool().muxer()

		##############################################################################
		self.packer = kwargs.get("group", None)
		self.extra_output_folder = self.packer["EXTRA_FOLDER"]       
		self.Group = (
			self.packer["GROUP"]
			if self.packer["GROUP"]
			else self.muxer_settings["GROUP"]
		)
		self.muxer_scheme = (
			self.packer["SCHEME"]
			if self.packer["SCHEME"]
			else self.muxer_settings["scheme"]
		)

		self.scheme = self.muxer_settings["schemeslist"][self.muxer_scheme]
		self.Extras = self.muxer_settings["EXTRAS"]
		self.fps24 = True if self.source_tag in self.muxer_settings["FPS24"] else False
		self.default_mux = True if self.muxer_settings["DEFAULT"] else False
		self.PrepareMuxer()

	def is_extra_folder(self):
		extra_folder = None
		if self.extra_output_folder:
			if not os.path.isabs(self.extra_output_folder):
				raise ValueError("Error you should provide full path dir: {}.".format(self.extra_output_folder))
			if not os.path.exists(self.extra_output_folder):
				try:
					os.makedirs(self.extra_output_folder)
				except Exception as e:
					raise ValueError("Error when create folder dir [{}]: {}.".format(e, self.extra_output_folder))
			extra_folder = self.extra_output_folder
			return extra_folder

		if self.muxer_settings["mkv_folder"]:
			if not os.path.isabs(self.muxer_settings["mkv_folder"]):
				raise ValueError("Error you should provide full path dir: {}.".format(self.muxer_settings["mkv_folder"]))
			if not os.path.exists(self.muxer_settings["mkv_folder"]):
				try:
					os.makedirs(self.muxer_settings["mkv_folder"])
				except Exception as e:
					raise ValueError("Error when create folder dir [{}]: {}.".format(e, self.muxer_settings["mkv_folder"]))
			extra_folder = self.muxer_settings["mkv_folder"]
			return extra_folder

		return extra_folder

	def PrepareMuxer(self):
		if self.muxer_settings["noTitle"]:
			self.CurrentName = self.noTitle()

		extra_folder = self.is_extra_folder()

		if extra_folder:
			self.SeasonFolder = extra_folder
		else:       
			if not self.default_mux:
				if self.SeasonFolder:
					self.SeasonFolder = self.setFolder()

		return

	def SortFilesBySize(self):
		file_list = []
		audio_tracks = (
			glob.glob(f"{self.CurrentName_Original}*.eac3")
			+ glob.glob(f"{self.CurrentName_Original}*.ac3")
			+ glob.glob(f"{self.CurrentName_Original}*.aac")
			+ glob.glob(f"{self.CurrentName_Original}*.m4a")
			+ glob.glob(f"{self.CurrentName_Original}*.dts")
		)

		if audio_tracks == []:
			raise FileNotFoundError("no audio files found")

		for file in audio_tracks:
			file_list.append({"file": file, "size": os.path.getsize(file)})

		file_list = sorted(file_list, key=lambda k: int(k["size"]))
		return file_list[-1]["file"]

	def GetVideoFile(self):
		videofiles = [
			"{} [{}p]_Demuxed.mp4",
			"{} [{}p]_Demuxed.mp4",
			"{} [{}p] [UHD]_Demuxed.mp4",
			"{} [{}p] [UHD]_Demuxed.mp4",
			"{} [{}p] [VP9]_Demuxed.mp4",
			"{} [{}p] [HIGH]_Demuxed.mp4",
			"{} [{}p] [VP9]_Demuxed.mp4",
			"{} [{}p] [HEVC]_Demuxed.mp4",
			"{} [{}p] [HDR]_Demuxed.mp4",
			"{} [{}p] [HDR-DV]_Demuxed.mp4",
		]

		for videofile in videofiles:
			filename = videofile.format(self.CurrentName_Original, self.CurrentHeigh)
			if os.path.isfile(filename):
				return filename

		return None

	def get_video_id(self):
		video_file = self.GetVideoFile()
		if not video_file:
			raise ValueError("No Video file in Dir...")

		media_info = MediaInfo.parse(video_file)
		track = [track for track in media_info.tracks if track.track_type == "Video"][0]

		if track.format == "AVC":
			if track.encoding_settings:
				return "x264"
			return "H.264"
		elif track.format == "HEVC":
			if track.commercial_name == "HDR10" and track.color_primaries:
				return "HDR.HEVC"
			if track.commercial_name == "HEVC" and track.color_primaries:
				return "HEVC"

			return "DV.HEVC"

		return None

	def get_audio_id(self):
		audio_id = None
		media_info = MediaInfo.parse(self.SortFilesBySize())
		track = [track for track in media_info.tracks if track.track_type == "Audio"][0]

		if track.format == "E-AC-3":
			audioCodec = "DDP"
		elif track.format == "AC-3":
			audioCodec = "DD"
		elif track.format == "AAC":
			audioCodec = "AAC"
		elif track.format == "DTS":
			audioCodec = "DTS"
		elif "DTS" in track.format:
			audioCodec = "DTS"
		else:
			audioCodec = "DDP"

		if track.channel_s == 8:
			channels = "7.1"
		elif track.channel_s == 6:
			channels = "5.1"
		elif track.channel_s == 2:
			channels = "2.0"
		elif track.channel_s == 1:
			channels = "1.0"
		else:
			channels = "5.1"

		audio_id = (
			f"{audioCodec}{channels}.Atmos"
			if "Atmos" in track.commercial_name
			else f"{audioCodec}{channels}"
		)

		return audio_id

	def Heigh(self):
		try:
			Width = int(self.CurrentWidth)
			Heigh = int(self.CurrentHeigh)
		except Exception:
			return self.CurrentHeigh

		res1080p = "1080p"
		res720p = "720p"
		sd = ""

		if Width >= 3840:
			return "2160p"

		if Width >= 2560:
			return "1440p"

		if Width > 1920:
			if Heigh > 1440:
				return "2160p"
			return "1440p"

		if Width == 1920:
			return res1080p
		elif Width == 1280:
			return res720p

		if Width >= 1400:
			return res1080p

		if Width < 1400 and Width >= 1100:
			return res720p

		if Heigh == 1080:
			return res1080p
		elif Heigh == 720:
			return res720p

		if Heigh >= 900:
			return res1080p

		if Heigh < 900 and Heigh >= 700:
			return res720p

		return sd

	def noTitle(self):
		regex = re.compile("(.*) [S]([0-9]+)[E]([0-9]+)")
		if regex.search(self.CurrentName):
			return regex.search(self.CurrentName).group(0)

		return self.CurrentName

	def Run(self, command):
		self.logger.debug("muxing command: {}".format(command))

		def unbuffered(proc, stream="stdout"):
			newlines = ["\n", "\r\n", "\r"]
			stream = getattr(proc, stream)
			with contextlib.closing(stream):
				while True:
					out = []
					last = stream.read(1)
					# Don't loop forever
					if last == "" and proc.poll() is not None:
						break
					while last not in newlines:
						# Don't loop forever
						if last == "" and proc.poll() is not None:
							break
						out.append(last)
						last = stream.read(1)
					out = "".join(out)
					yield out

		proc = subprocess.Popen(
			command,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			bufsize=1,
			universal_newlines=True,
		)
		self.logger.info("\nStart Muxing...")
		for line in unbuffered(proc):
			if "Progress:" in line:
				sys.stdout.write("\r%s" % (line))
				sys.stdout.flush()
			elif "Multiplexing" in line:
				sys.stdout.write("\r%s" % (line.replace("Multiplexing", "Muxing")))
				sys.stdout.flush()
			elif "Error" in line:
				sys.stdout.write("\r%s" % (line))
				sys.stdout.flush()

		self.logger.info("")

	def setName(self):

		outputVideo = (
			self.scheme.replace(
				"{t}", ripprocess().CleanMyFileNamePlease(self.CurrentName)
			)
			.replace("{r}", self.Heigh())
			.replace("{s}", self.source_tag)
			.replace("{ac}", self.AudioProfile)
			.replace("{vc}", self.VideoProfile)
			.replace("{gr}", self.Group)
		)

		for i in range(10):
			outputVideo = re.sub(r"(\.\.)", ".", outputVideo)

		if self.SeasonFolder:
			outputVideo = os.path.join(os.path.abspath(self.SeasonFolder), outputVideo)
			outputVideo = outputVideo.replace("\\", "/")

		return f"{outputVideo}.mkv"

	def setFolder(self):
		folder = (
			self.scheme.replace(
				"{t}", ripprocess().CleanMyFileNamePlease(self.SeasonFolder)
			)
			.replace("{r}", self.Heigh())
			.replace("{s}", self.source_tag)
			.replace("{ac}", self.AudioProfile)
			.replace("{vc}", self.VideoProfile)
			.replace("{gr}", self.Group)
		)

		for i in range(10):
			folder = re.sub(r"(\.\.)", ".", folder)

		return folder

	def LanguageList(self):
		LanguageList = [
			["Hindi", "hin", "hin", "Hindi"],
			["Tamil", "tam", "tam", "Tamil"],
			["Telugu", "tel", "tel", "Telugu"],
			["English", "eng", "eng", "English"],
			["Afrikaans", "af", "afr", "Afrikaans"],
			["Arabic", "ara", "ara", "Arabic"],
			["Arabic (Syria)", "araSy", "ara", "Arabic Syria"],
			["Arabic (Egypt)", "araEG", "ara", "Arabic Egypt"],
			["Arabic (Kuwait)", "araKW", "ara", "Arabic Kuwait"],
			["Arabic (Lebanon)", "araLB", "ara", "Arabic Lebanon"],
			["Arabic (Algeria)", "araDZ", "ara", "Arabic Algeria"],
			["Arabic (Bahrain)", "araBH", "ara", "Arabic Bahrain"],
			["Arabic (Iraq)", "araIQ", "ara", "Arabic Iraq"],
			["Arabic (Jordan)", "araJO", "ara", "Arabic Jordan"],
			["Arabic (Libya)", "araLY", "ara", "Arabic Libya"],
			["Arabic (Morocco)", "araMA", "ara", "Arabic Morocco"],
			["Arabic (Oman)", "araOM", "ara", "Arabic Oman"],
			["Arabic (Saudi Arabia)", "araSA", "ara", "Arabic Saudi Arabia"],
			["Arabic (Tunisia)", "araTN", "ara", "Arabic Tunisia"],
			[
				"Arabic (United Arab Emirates)",
				"araAE",
				"ara",
				"Arabic United Arab Emirates",
			],
			["Arabic (Yemen)", "araYE", "ara", "Arabic Yemen"],
			["Armenian", "hye", "arm", "Armenian"],
			["Assamese", "asm", "asm", "Assamese"],
			["Bengali", "ben", "ben", "Bengali"],
			["Basque", "eus", "baq", "Basque"],
			["British English", "enGB", "eng", "British English"],
			["Bulgarian", "bul", "bul", "Bulgarian"],
			["Cantonese", "None", "chi", "Cantonese"],
			["Catalan", "cat", "cat", "Catalan"],
			["Simplified Chinese", "zhoS", "chi", "Chinese Simplified"],
			["Traditional Chinese", "zhoT", "chi", "Chinese Traditional"],
			["Croatian", "hrv", "hrv", "Croatian"],
			["Czech", "ces", "cze", "Czech"],
			["Danish", "dan", "dan", "Danish"],
			["Dutch", "nld", "dut", "Dutch"],
			["Estonian", "est", "est", "Estonian"],
			["Filipino", "fil", "fil", "Filipino"],
			["Finnish", "fin", "fin", "Finnish"],
			["Flemish", "nlBE", "dut", "Flemish"],
			["French", "fra", "fre", "French"],
			["French Canadian", "caFra", "fre", "French Canadian"],
			["Canadian French", "caFra", "fre", "Canadian French"],
			["German", "deu", "ger", "German"],
			["Greek", "ell", "gre", "Greek"],
			["Gujarati", "guj", "guj", "Gujarati"],
			["Hebrew", "heb", "heb", "Hebrew"],
			["Hungarian", "hun", "hun", "Hungarian"],
			["Icelandic", "isl", "ice", "Icelandic"],
			["Indonesian", "ind", "ind", "Indonesian"],
			["Italian", "ita", "ita", "Italian"],
			["Japanese", "jpn", "jpn", "Japanese"],
			["Kannada (India)", "kan", "kan", "Kannada (India)"],
			["Khmer", "khm", "khm", "Khmer"],
			["Klingon", "tlh", "tlh", "Klingon"],
			["Korean", "kor", "kor", "Korean"],
			["Lithuanian", "lit", "lit", "Lithuanian"],
			["Latvian", "lav", "lav", "Latvian"],
			["Malay", "msa", "may", "Malay"],
			["Malayalam", "mal", "mal", "Malayalam"],
			["Mandarin", "None", "chi", "Mandarin"],
			["Mandarin Chinese (Simplified)", "zh-Hans", "chi", "Simplified"],
			["Mandarin Chinese (Traditional)", "zh-Hant", "chi", "Traditional"],
			["Yue Chinese", "yue", "chi", "(Yue Chinese)"],
			["Manipuri", "mni", "mni", "Manipuri"],
			["Marathi", "mar", "mar", "Marathi"],
			["No Dialogue", "zxx", "zxx", "No Dialogue"],
			["Norwegian", "nor", "nor", "Norwegian"],
			["Norwegian Bokmal", "nob", "nob", "Norwegian Bokmal"],
			["Persian", "fas", "per", "Persian"],
			["Polish", "pol", "pol", "Polish"],
			["Portuguese", "por", "por", "Portuguese"],
			["Brazilian Portuguese", "brPor", "por", "Brazilian Portuguese"],
			["Punjabi", "pan", "pan", "Punjabi"],
			["Panjabi", "pan", "pan", "Panjabi"],            
			["Romanian", "ron", "rum", "Romanian"],
			["Russian", "rus", "rus", "Russian"],
			["Serbian", "srp", "srp", "Serbian"],
			["Sinhala", "sin", "sin", "Sinhala"],
			["Slovak", "slk", "slo", "Slovak"],
			["Slovenian", "slv", "slv", "Slovenian"],
			["Spanish", "spa", "spa", "Spanish"],
			["European Spanish", "euSpa", "spa", "European Spanish"],
			["Swedish", "swe", "swe", "Swedish"],
			["Thai", "tha", "tha", "Thai"],					
			["Tagalog", "tgl", "tgl", "Tagalog"],
			["Turkish", "tur", "tur", "Turkish"],
			["Ukrainian", "ukr", "ukr", "Ukrainian"],
			["Urdu", "urd", "urd", "Urdu"],
			["Vietnamese", "vie", "vie", "Vietnamese"],
		]

		return LanguageList

	def ExtraLanguageList(self):
		ExtraLanguageList = [
			["Polish - Dubbing", "pol", "pol", "Polish - Dubbing"],
			["Polish - Lektor", "pol", "pol", "Polish - Lektor"],
		]

		return ExtraLanguageList

	def AddChapters(self):
		if os.path.isfile(self.CurrentName_Original + " Chapters.txt"):
			self.merge += [
				"--chapter-charset",
				"UTF-8",
				"--chapters",
				self.CurrentName_Original + " Chapters.txt",
			]

		return

	def AddVideo(self):
		inputVideo = None

		videofiles = [
			"{} [{}p]_Demuxed.mp4",
			"{} [{}p]_Demuxed.mp4",
			"{} [{}p] [UHD]_Demuxed.mp4",
			"{} [{}p] [UHD]_Demuxed.mp4",
			"{} [{}p] [VP9]_Demuxed.mp4",
			"{} [{}p] [HIGH]_Demuxed.mp4",
			"{} [{}p] [VP9]_Demuxed.mp4",
			"{} [{}p] [HEVC]_Demuxed.mp4",
			"{} [{}p] [HDR]_Demuxed.mp4",
			"{} [{}p] [HDR-DV]_Demuxed.mp4",
		]

		for videofile in videofiles:
			filename = videofile.format(self.CurrentName_Original, self.CurrentHeigh)
			if os.path.isfile(filename):
				inputVideo = filename
				break

		if not inputVideo:
			self.logger.info("cannot found video file.")
			exit(-1)

		if self.default_mux:
			outputVideo = (
				re.compile("|".join([".h264", ".h265", ".vp9", ".mp4"])).sub("", inputVideo)
				+ ".mkv"
			)
			if self.SeasonFolder:
				outputVideo = os.path.join(
					os.path.abspath(self.SeasonFolder), outputVideo
				)
				outputVideo = outputVideo.replace("\\", "/")
		else:
			outputVideo = self.setName()

		self.outputVideo = outputVideo

		if self.fps24:
			self.merge += [
				self.mkvmerge,
				"--output",
				outputVideo,
				"--default-duration",
				"0:24000/1001p",
				"--language",
				"0:und",
				"--default-track",
				"0:yes",
				"(",
				inputVideo,
				")",
			]
		else:
			self.merge += [
				self.mkvmerge,
				"--output",
				outputVideo,
				"--title",
				'RAB',
				"(",
				inputVideo,
				")",
			]

		return

	def AddAudio(self):

		audiofiles = [
			"{} {}.ac3",
			"{} {} - Audio Description.ac3",
			"{} {}.eac3",
			"{} {} - Audio Description.eac3",
			"{} {}.aac",
			"{} {} - Audio Description.aac",			
		]

		for (audio_language, subs_language, language_id, language_name,) in (
			self.LanguageList() + self.ExtraLanguageList()
		):
			for audiofile in audiofiles:
				filename = audiofile.format(self.CurrentName_Original, audio_language)
				if os.path.isfile(filename):
					self.merge += [
						"--language",
						f"0:{language_id}",
						"--track-name",
						"0:Audio Description" if 'Audio Description' in filename
						else f"0:{language_name}",
						"--default-track",
						"0:yes"
						if subs_language == self.muxer_settings["AUDIO"]
						else "0:no",
						"(",
						filename,
						")",
					]

		return

	def AddSubtitles(self):

		srts = [
			"{} {}.srt",
		]
		forceds = [
			"{} forced-{}.srt",
		]
		sdhs = [
			"{} sdh-{}.srt",
		]

		for (
			audio_language,
			subs_language,
			language_id,
			language_name,
		) in self.LanguageList():
			for subtitle in srts:
				filename = subtitle.format(self.CurrentName_Original, subs_language)
				if os.path.isfile(filename):
					self.merge += [
						"--language",
						f"0:{language_id}",
						"--track-name",
						f"0:{language_name}",
						"--forced-track",
						"0:no",
						"--default-track",
						"0:yes"
						if subs_language == self.muxer_settings["SUB"]
						else "0:no",
						"--compression",
						"0:none",
						"(",
						filename,
						")",
					]

			for subtitle in forceds:
				filename = subtitle.format(self.CurrentName_Original, subs_language)
				if os.path.isfile(filename):
					self.merge += [
						"--language",
						f"0:{language_id}",
						"--track-name",
						f"0:Forced",
						"--forced-track",
						"0:yes",
						"--default-track",
						"0:no",
						"--compression",
						"0:none",
						"(",
						filename,
						")",
					]

			for subtitle in sdhs:
				filename = subtitle.format(self.CurrentName_Original, subs_language)
				if os.path.isfile(filename):
					self.merge += [
						"--language",
						f"0:{language_id}",
						"--track-name",
						f"0:SDH",
						"--forced-track",
						"0:no",
						"--default-track",
						"0:no",
						"--compression",
						"0:none",
						"(",
						filename,
						")",
					]

		return

	def startMux(self):
		self.AddVideo()
		self.AddAudio()
		self.AddSubtitles()
		self.AddChapters()
		if not os.path.isfile(self.outputVideo):
			self.Run(self.merge + self.Extras)

		return self.outputVideo
