from helpers.ripprocess import ripprocess
from helpers.Parsers.Netflix.MSLClient import MSLClient
from configs.config import tool
import re, os, json, logging

def MSLprofiles():
	PROFILES = {
		"BASICS": ["BIF240", "BIF320", "webvtt-lssdh-ios8", "dfxp-ls-sdh"],
		"MAIN": {
			"SD": [
				"playready-h264bpl30-dash",
				"playready-h264mpl22-dash",
				"playready-h264mpl30-dash",
			],
			"HD": [
				"playready-h264bpl30-dash",
				"playready-h264mpl22-dash",
				"playready-h264mpl30-dash",
				"playready-h264mpl31-dash",
			],
			"FHD": [
				"playready-h264bpl30-dash",
				"playready-h264mpl22-dash",
				"playready-h264mpl30-dash",
				"playready-h264mpl31-dash",
				"playready-h264mpl40-dash",
			],
			"ALL": [
				"playready-h264bpl30-dash",
				"playready-h264mpl22-dash",
				"playready-h264mpl30-dash",
				"playready-h264mpl31-dash",
				"playready-h264mpl40-dash",
			],
		},
		"HIGH": {
			"SD": [
				"playready-h264hpl22-dash",
				"playready-h264hpl30-dash",
			],
			"HD": [
				"playready-h264hpl22-dash",
				"playready-h264hpl30-dash",
				"playready-h264hpl31-dash",
			],
			"FHD": [
				"playready-h264hpl22-dash",
				"playready-h264hpl30-dash",
				"playready-h264hpl31-dash",
				"playready-h264hpl40-dash",
			],
			"ALL": [
				"playready-h264hpl22-dash",
				"playready-h264hpl30-dash",
				"playready-h264hpl31-dash",
				"playready-h264hpl40-dash",
			],
		},
		"HEVC": {
			"SD": [
				"hevc-main-L30-dash-cenc",
				"hevc-main10-L30-dash-cenc",
				"hevc-main10-L30-dash-cenc-prk",
			],
			"HD": [
				"hevc-main-L30-dash-cenc",
				"hevc-main10-L30-dash-cenc",
				"hevc-main10-L30-dash-cenc-prk",
				"hevc-main-L31-dash-cenc",
				"hevc-main10-L31-dash-cenc",
				"hevc-main10-L31-dash-cenc-prk",
			],
			"FHD": [
				"hevc-main-L30-dash-cenc",
				"hevc-main10-L30-dash-cenc",
				"hevc-main10-L30-dash-cenc-prk",
				"hevc-main-L31-dash-cenc"
				"hevc-main10-L31-dash-cenc",
				"hevc-main10-L31-dash-cenc-prk",
				"hevc-main-L40-dash-cenc",				
				"hevc-main10-L40-dash-cenc",
				"hevc-main10-L40-dash-cenc-prk",
				"hevc-main-L41-dash-cenc",				
				"hevc-main10-L41-dash-cenc",
				"hevc-main10-L41-dash-cenc-prk",
			],
			"ALL": [
				"hevc-main-L30-dash-cenc",
				"hevc-main10-L30-dash-cenc",
				"hevc-main10-L30-dash-cenc-prk",
				"hevc-main-L31-dash-cenc"
				"hevc-main10-L31-dash-cenc",
				"hevc-main10-L31-dash-cenc-prk",
				"hevc-main-L40-dash-cenc",				
				"hevc-main10-L40-dash-cenc",
				"hevc-main10-L40-dash-cenc-prk",				
				"hevc-main-L41-dash-cenc",				
				"hevc-main10-L41-dash-cenc",
				"hevc-main10-L41-dash-cenc-prk",
			],
		},
		"HEVCDO": {
			"SD": [
				"hevc-main10-L30-dash-cenc-prk-do",
			],
			"HD": [
				"hevc-main10-L30-dash-cenc-prk-do",
				"hevc-main10-L31-dash-cenc-prk-do"
			],
			"FHD": [
				"hevc-main10-L31-dash-cenc-prk-do",
				"hevc-main10-L31-dash-cenc-prk-do",
				"hevc-main10-L40-dash-cenc-prk-do",
				"hevc-main10-L41-dash-cenc-prk-do",
			],
			"ALL": [
				"hevc-main10-L31-dash-cenc-prk-do",
				"hevc-main10-L31-dash-cenc-prk-do",
				"hevc-main10-L40-dash-cenc-prk-do",
				"hevc-main10-L41-dash-cenc-prk-do",
			],
		},				
		"HDR": {
			"SD": [
				"hevc-hdr-main10-L30-dash-cenc",
				"hevc-hdr-main10-L30-dash-cenc-prk",
			],
			"HD": [
				"hevc-hdr-main10-L30-dash-cenc",
				"hevc-hdr-main10-L30-dash-cenc-prk",
				"hevc-hdr-main10-L31-dash-cenc",
				"hevc-hdr-main10-L31-dash-cenc-prk",
			],
			"FHD": [
				"hevc-hdr-main10-L30-dash-cenc",
				"hevc-hdr-main10-L30-dash-cenc-prk",
				"hevc-hdr-main10-L31-dash-cenc",
				"hevc-hdr-main10-L31-dash-cenc-prk",
				"hevc-hdr-main10-L40-dash-cenc",
				"hevc-hdr-main10-L41-dash-cenc",
				"hevc-hdr-main10-L40-dash-cenc-prk",
				"hevc-hdr-main10-L41-dash-cenc-prk",
			],
			"ALL": [
				"hevc-hdr-main10-L30-dash-cenc",
				"hevc-hdr-main10-L30-dash-cenc-prk",
				"hevc-hdr-main10-L31-dash-cenc",
				"hevc-hdr-main10-L31-dash-cenc-prk",
				"hevc-hdr-main10-L40-dash-cenc",
				"hevc-hdr-main10-L41-dash-cenc",
				"hevc-hdr-main10-L40-dash-cenc-prk",
				"hevc-hdr-main10-L41-dash-cenc-prk",
			],
		},
	}

	return PROFILES

class get_manifest:
	
	def __init__(self, args, nfid):
		self.logger = logging.getLogger(__name__)
		self.args = args
		self.nfid = nfid
		self.ripprocess = ripprocess()
		self.profiles = MSLprofiles()
		self.config = tool().config("NETFLIX")

	def LoadProfies(self, addHEVCDO=False):
		getHigh = False
		profiles = self.profiles["BASICS"]

		if self.args.video_main:
			if self.args.customquality:
				if int(self.args.customquality[0]) == 1080:
					profiles += self.profiles["MAIN"]["FHD"]
				elif (
					int(self.args.customquality[0]) < 1080
					and int(self.args.customquality[0]) >= 720
				):
					profiles += self.profiles["MAIN"]["HD"]
				elif int(self.args.customquality[0]) < 720:
					profiles += self.profiles["MAIN"]["SD"]
			else:
				profiles += self.profiles["MAIN"]["ALL"]
		else:
			if self.args.video_high:
				if self.args.customquality:
					if int(self.args.customquality[0]) == 1080:
						profiles += self.profiles["HIGH"]["FHD"]
					elif (
						int(self.args.customquality[0]) < 1080
						and int(self.args.customquality[0]) >= 720
					):
						profiles += self.profiles["HIGH"]["HD"]
					elif int(self.args.customquality[0]) < 720:
						profiles += self.profiles["HIGH"]["SD"]
				else:
					profiles += self.profiles["HIGH"]["ALL"]
			else:
				if self.args.hdr:
					if self.args.customquality:
						if int(self.args.customquality[0]) == 1080:
							profiles += self.profiles["HDR"]["FHD"]
						elif (
							int(self.args.customquality[0]) < 1080
							and int(self.args.customquality[0]) >= 720
						):
							profiles += self.profiles["HDR"]["HD"]
						elif int(self.args.customquality[0]) < 720:
							profiles += self.profiles["HDR"]["SD"]
					else:
						profiles += self.profiles["HDR"]["ALL"]
				
				elif self.args.hevc:
					if self.args.customquality:
						if int(self.args.customquality[0]) == 1080:
							profiles += self.profiles["HEVC"]["FHD"]
							if addHEVCDO:
								profiles += self.profiles['HEVCDO']['FHD']
						elif (
							int(self.args.customquality[0]) < 1080
							and int(self.args.customquality[0]) >= 720
						):
							profiles += self.profiles["HEVC"]["HD"]
							if addHEVCDO:
								profiles += self.profiles['HEVCDO']['HD']		
						elif int(self.args.customquality[0]) < 720:
							profiles += self.profiles["HEVC"]["SD"]
							if addHEVCDO:
								profiles += self.profiles['HEVCDO']['SD']		
					else:
						profiles += self.profiles["HEVC"]["ALL"]
						if addHEVCDO:
							profiles += self.profiles['HEVCDO']['ALL']
				
				else:
					getHigh = True
					if self.args.customquality:
						if int(self.args.customquality[0]) == 1080:
							profiles += self.profiles["MAIN"]["FHD"]
						elif (
							int(self.args.customquality[0]) < 1080
							and int(self.args.customquality[0]) >= 720
						):
							profiles += self.profiles["MAIN"]["HD"]
						elif int(self.args.customquality[0]) < 720:
							profiles += self.profiles["MAIN"]["SD"]
					else:
						profiles += self.profiles["MAIN"]["ALL"]

		if self.args.aformat_2ch:
			if str(self.args.aformat_2ch[0]) == "aac":
				profiles.append("heaac-2-dash")
				profiles.append("heaac-2hq-dash")
			elif str(self.args.aformat_2ch[0]) == "eac3":
				profiles.append("ddplus-2.0-dash")
			elif str(self.args.aformat_2ch[0]) == "ogg":
				profiles.append("playready-oggvorbis-2-dash")
		else:
			if self.args.only_2ch_audio:
				profiles.append("ddplus-2.0-dash")
			else:
				if self.args.aformat_51ch:
					if str(self.args.aformat_51ch[0]) == "aac":
						profiles.append("heaac-5.1-dash")
						profiles.append("heaac-5.1hq-dash")
					elif str(self.args.aformat_51ch[0]) == "eac3":
						profiles.append("ddplus-5.1-dash")
						profiles.append("ddplus-5.1hq-dash")
					elif str(self.args.aformat_51ch[0]) == "ac3":
						profiles.append("dd-5.1-dash")
					elif str(self.args.aformat_51ch[0]) == "atmos":
						profiles.append("dd-5.1-dash")
						profiles.append("ddplus-atmos-dash")
					else:
						profiles.append("dd-5.1-dash")
						profiles.append("ddplus-5.1-dash")
						profiles.append("ddplus-5.1hq-dash")
				else:
					profiles.append("ddplus-2.0-dash")
					profiles.append("dd-5.1-dash")
					profiles.append("ddplus-5.1-dash")
					profiles.append("ddplus-5.1hq-dash")
					profiles.append("ddplus-atmos-dash")

		return list(set(profiles)), getHigh

	def PyMSL(self, profiles):

		client = MSLClient(profiles=profiles)

		try:
			resp = client.load_playlist(int(self.nfid))
			return resp
		
		except Exception as e:
			self.logger.error("Manifest Error: {}".format(e))
		
		return None

	def HighVideoMSL(self): 
		# for bitrate compare with main ~
		
		self.logger.info("Getting High Profile Manifest...")
		
		profiles = self.profiles["BASICS"]
		
		if self.args.customquality:
			if int(self.args.customquality[0]) == 1080:
				profiles += self.profiles["HIGH"]["FHD"]
			elif (
				int(self.args.customquality[0]) < 1080
				and int(self.args.customquality[0]) >= 720
			):
				profiles += self.profiles["HIGH"]["HD"]
			elif int(self.args.customquality[0]) < 720:
				profiles += self.profiles["HIGH"]["SD"]
		else:
			profiles += self.profiles["HIGH"]["ALL"]

		resp = self.PyMSL(profiles=profiles)

		VideoList = list()

		manifest = resp["result"]

		for video_track in manifest["video_tracks"]:
			for downloadable in video_track["streams"]:
				size_in_bytes = int(float(downloadable["size"]))
				vid_size = (
					f"{size_in_bytes/1048576:0.2f} MiB"
					if size_in_bytes < 1073741824
					else f"{size_in_bytes/1073741824:0.2f} GiB"
				)
				vid_url = downloadable["urls"][0]["url"]
				L3 = 'L3' if 'SEGMENT_MAP_2KEY' in str(downloadable['tags']) else '' #

				VideoList.append(
					{
						"Type": "video",
						"Drm": downloadable["isDrm"],
						"vmaf": downloadable["vmaf"],
						"FrameRate": downloadable["framerate_value"],
						"Height": downloadable["res_h"],
						"Width": downloadable["res_w"],
						"Size": vid_size,
						"Url": vid_url,
						"Bitrate": str(downloadable["bitrate"]),
						"Profile": downloadable["content_profile"],
						"L3": L3 #
					}
				)

		VideoList = sorted(VideoList, key=lambda k: int(k["Bitrate"]))

		if self.args.customquality:
			inp_height = int(self.args.customquality[0])
			top_height = sorted(VideoList, key=lambda k: int(k["Height"]))[-1]["Height"]

			if top_height >= inp_height:
				height = [x for x in VideoList if int(x["Height"]) >= inp_height]
				if not height == []:
					VideoList = height

		return VideoList

	def ParseVideo(self, resp, getHigh):
		manifest = resp["result"]
		VideoList = []
		checkerinfo = ""

		for video_track in manifest["video_tracks"]:
			for downloadable in video_track["streams"]:
				size_in_bytes = int(float(downloadable["size"]))
				vid_size = (
					f"{size_in_bytes/1048576:0.2f} MiB"
					if size_in_bytes < 1073741824
					else f"{size_in_bytes/1073741824:0.2f} GiB"
				)
				vid_url = downloadable["urls"][0]["url"]

				VideoList.append(
					{
						"Type": "video",
						"Drm": downloadable["isDrm"],
						"vmaf": downloadable["vmaf"],
						"FrameRate": downloadable["framerate_value"],
						"Height": downloadable["res_h"],
						"Width": downloadable["res_w"],
						"Size": vid_size,
						"Url": vid_url,
						"Bitrate": str(downloadable["bitrate"]),
						"Profile": downloadable["content_profile"],
					}
				)

		VideoList = sorted(VideoList, key=lambda k: int(k["Bitrate"]))
		self.logger.debug("VideoList: {}".format(VideoList))

		if self.args.customquality:
			inp_height = int(self.args.customquality[0])
			top_height = sorted(VideoList, key=lambda k: int(k["Height"]))[-1]["Height"]

			if top_height >= inp_height:
				height = [x for x in VideoList if int(x["Height"]) >= inp_height]
				if not height == []:
					VideoList = height

		if getHigh:
			HighVideoList = self.HighVideoMSL()
			if not HighVideoList == []:
				checkerinfo = "\nNetflix Profile Checker v1.0\nMAIN: {}kbps | {}\nHIGH: {}kbps | {}\n\n{}\n"
				checkerinfo = checkerinfo.format(
					str(dict(VideoList[-1])["Bitrate"]),
					str(dict(VideoList[-1])["Profile"]),
					str(dict(HighVideoList[-1])["Bitrate"]),
					str(dict(HighVideoList[-1])["Profile"]),
					"result: MAIN is Better"
					if int(dict(VideoList[-1])["Bitrate"])
					>= int(dict(HighVideoList[-1])["Bitrate"])
					else "result: HIGH is Better",
				)

				VideoList += HighVideoList
				self.logger.debug("HighVideoList: {}".format(HighVideoList))

		VideoList = sorted(VideoList, key=lambda k: int(k["Bitrate"]))

		return VideoList, checkerinfo

	def ParseAudioSubs(self, resp):
		
		def remove_dups(List, keyword=""): 
			# function to remove all dups based on list items ~
			Added_ = set()
			Proper_ = []
			for L in List:
				if L[keyword] not in Added_:
					Proper_.append(L)
					Added_.add(L[keyword])

			return Proper_	

		def isOriginal(language_text):
			# function to detect the original audio ~
			if "Original" in language_text:
				return True

			brackets = re.search(r"\[(.*)\]", language_text)
			if brackets:
				return True

			return False

		def noOriginal(language_text): 
			# function to remove (original) from audio language to be detected in --alang ~
			brackets = re.search(r"\[(.*)\]", language_text)
			if brackets:
				return language_text.replace(brackets[0], "").strip()

			return language_text

		# start audio, subs parsing ~ 
		
		manifest = resp["result"]
		
		AudioList, SubtitleList, ForcedList = list(), list(), list()

		# parse audios and return all (AD, non AD) as a list
		for audio_track in manifest["audio_tracks"]:
			AudioDescription = 'Audio Description' if "audio description" in \
			audio_track["languageDescription"].lower() else 'Audio'
			Original = isOriginal(audio_track["languageDescription"])
			LanguageName, LanguageCode = self.ripprocess.countrycode(
				audio_track["language"]
			)
			LanguageName = noOriginal(audio_track["languageDescription"])
			
			for downloadable in audio_track["streams"]:
				aud_url = downloadable["urls"][0]["url"]
				size = (
					str(format(float(int(downloadable["size"])) / 1058816, ".2f"))
					+ " MiB"
				)

				audioDict = {
					"Type": AudioDescription,
					"Drm": downloadable["isDrm"],
					"Original": Original,
					"Language": LanguageName,
					"langAbbrev": LanguageCode,
					"Size": size,
					"Url": aud_url,
					"channels": str(downloadable["channels"]),
					"Bitrate": str(downloadable["bitrate"]),
					"Profile": downloadable["content_profile"],
				}		
					
				if self.args.custom_audio_bitrate:
					# only append the audio langs with the given bitrate
					if int(downloadable["bitrate"]) <= \
					int(self.args.custom_audio_bitrate[0]):
						AudioList.append(audioDict)	
				else:					
					AudioList.append(audioDict)

		AudioList = sorted(AudioList, key=lambda k: int(k["Bitrate"]), reverse=True)
		
		self.logger.debug("AudioList: {}".format(AudioList))
		
		#################################################################################

		AudioList = sorted( # keep only highest bitrate for every language
			remove_dups(AudioList, keyword="Language"),
			key=lambda k: int(k["Bitrate"]),
			reverse=True,
		)

		OriginalAudioList = ( # for detect automatically forced subs ~
			AudioList
			if len(AudioList) == 1
			else [x for x in AudioList if x["Original"]]
		)		
 
		#################################################################################
		
		# now parser AudioList based on user input to
		# --alang X X --AD X X or original if none
		
		if self.args.AD:
			ADlist = list()
			UserLanguagesLower = list(map(lambda x: x.lower(), self.args.AD))
			for aud in AudioList:
				if aud['Type'] == 'Audio':
					if self.args.allaudios:
						ADlist.append(aud)
					else:
						if aud["Original"]:
							ADlist.append(aud)
				
				if aud['Type'] == 'Audio Description':
					if (
						aud["Language"].lower() in UserLanguagesLower
						or aud["langAbbrev"].lower() in UserLanguagesLower
					):
						ADlist.append(aud)
			
			AudioList = ADlist
		
		if self.args.audiolang:
			NewAudioList = list()
			UserLanguagesLower = list(map(lambda x: x.lower(), self.args.audiolang))
			for aud in AudioList:
				if self.args.AD:
					# I already have AD langs parsed
					if aud['Type'] == 'Audio Description':
						NewAudioList.append(aud)					
				if aud['Type'] == 'Audio':
					if (
						aud["Language"].lower() in UserLanguagesLower
						or aud["langAbbrev"].lower() in UserLanguagesLower
					):
						NewAudioList.append(aud)
			
			AudioList = NewAudioList

		else:
			# so I know have the complete Audiolist
			if self.args.allaudios: # remove AD tracks if not --AD X X 
				AllaudiosList = list()
				if self.args.AD:
					for aud in AudioList:
						AllaudiosList.append(aud)
					AudioList = AllaudiosList	
				else:
					for aud in AudioList:
						if aud['Type'] == 'Audio':
							AllaudiosList.append(aud)
					AudioList.clear()
					AudioList = AllaudiosList

			else:
				if self.args.AD:
					AudioList = AudioList # I mean the ADlist
				else:
					# I mean no audio options are given, so we go with the original
					AudioList = [x for x in AudioList if x["Original"] or len(AudioList) == 1]

		#####################################(Subtitles)#####################################

		for text_track in manifest["timedtexttracks"]:
			if (
				not text_track["languageDescription"] == "Off"
				and text_track["language"] is not None
			):
				Language, langAbbrev = self.ripprocess.countrycode(
					text_track["language"]
				)
				Language = text_track["languageDescription"]
				Type = text_track["trackType"]
				rawTrackType = (
					text_track["rawTrackType"]
					.replace("closedcaptions", "CC")
					.replace("subtitles", "SUB")
				)
				isForced = "NO"

				if (
					"CC" in rawTrackType
					and langAbbrev != "ara"
					and "dfxp-ls-sdh" in str(text_track["ttDownloadables"])
				):
					Profile = "dfxp-ls-sdh"
					Url = next(
						iter(
							text_track["ttDownloadables"]["dfxp-ls-sdh"][
								"downloadUrls"
							].values()
						)
					)
				else:
					Profile = "webvtt-lssdh-ios8"
					Url = next(
						iter(
							text_track["ttDownloadables"]["webvtt-lssdh-ios8"][
								"downloadUrls"
							].values()
						)
					)

				SubtitleList.append(
					{
						"Type": Type,
						"rawTrackType": rawTrackType,
						"Language": Language,
						"isForced": isForced,
						"langAbbrev": langAbbrev,
						"Url": Url,
						"Profile": Profile,
					}
				)

		self.logger.debug("SubtitleList: {}".format(SubtitleList))
		SubtitleList = remove_dups(SubtitleList, keyword="Language")

		if self.args.sublang:
			NewSubtitleList = list()
			UserLanguagesLower = list(map(lambda x: x.lower(), self.args.sublang))
			for sub in SubtitleList:
				if (
					sub["Language"].lower() in UserLanguagesLower
					or sub["langAbbrev"].lower() in UserLanguagesLower
				):
					NewSubtitleList.append(sub)
			SubtitleList = remove_dups(NewSubtitleList, keyword="Language")

		#####################################(Forced Subtitles)###############################

		for text_track in manifest["timedtexttracks"]:
			if text_track["isForcedNarrative"] and text_track["language"] is not None:
				LanguageName, LanguageCode = self.ripprocess.countrycode(
					text_track["language"]
				)
				# LanguageName = text_track["languageDescription"] # no i will use pycountry instead bcs it's off dude.
				ForcedList.append(
					{
						"Type": text_track["trackType"],
						"rawTrackType": text_track["rawTrackType"]
						.replace("closedcaptions", "CC ")
						.replace("subtitles", "SUB"),
						"Language": LanguageName,
						"isForced": "YES",
						"langAbbrev": LanguageCode,
						"Url": next(
							iter(
								text_track["ttDownloadables"]["webvtt-lssdh-ios8"][
									"downloadUrls"
								].values()
							)
						),
						"Profile": "webvtt-lssdh-ios8",
					}
				)

		ForcedList = remove_dups(ForcedList, keyword="Language")

		if self.args.forcedlang:
			NewForcedList = []
			UserLanguagesLower = list(map(lambda x: x.lower(), self.args.forcedlang))
			for sub in ForcedList:
				if (
					sub["Language"].lower() in UserLanguagesLower
					or sub["langAbbrev"].lower() in UserLanguagesLower
				):
					NewForcedList.append(sub)
			ForcedList = remove_dups(NewForcedList, keyword="Language")
		else:
			if not self.args.allforcedlang:
				if len(OriginalAudioList) != 0:
					OriginalLanguage = OriginalAudioList[0]["langAbbrev"]
					ForcedList = [
						x for x in ForcedList if x["langAbbrev"] == OriginalLanguage
					]

		return AudioList, SubtitleList, ForcedList

	def LoadManifest(self):
		
		profiles, getHigh = self.LoadProfies()

		if self.args.hevc:
			self.logger.info("Getting HEVC Manifest...")
		elif self.args.hdr:
			self.logger.info("Getting HDR-10 Manifest...")
		elif self.args.video_high:
			self.logger.info("Getting High Profile Manifest...")			
		else:
			self.logger.info("Getting Main Profile Manifest...")

		resp = self.PyMSL(profiles=profiles)

		if not resp:
			if self.args.hevc:
				profiles, getHigh = self.LoadProfies(addHEVCDO=True)
				self.logger.info('\nGetting HEVC DO Manifest...')
				resp = self.PyMSL(profiles=profiles)			

		if not resp:
			self.logger.info("Failed getting Manifest")
			exit(-1)

		VideoList, checkerinfo = self.ParseVideo(resp, getHigh)
		AudioList, SubtitleList, ForcedList = self.ParseAudioSubs(resp)

		return VideoList, AudioList, SubtitleList, ForcedList, checkerinfo
