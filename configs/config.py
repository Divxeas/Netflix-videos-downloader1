import sys, os, random, string, platform
from os.path import dirname
from os.path import join
from pywidevine.cdm import cdm, deviceconfig

dirPath = dirname(dirname(__file__)).replace("\\", "/")

class utils:
	def __init__(self):
		self.dir = dirPath

	def random_hex(self, length: int) -> str:
		"""return {length} of random string"""
		return "".join(random.choice("0123456789ABCDEF") for _ in range(length))

utils_ = utils()

#####################################(DEVICES)#####################################

devices_dict = {
	"android_general": deviceconfig.device_android_general,
}

DEVICES = {
	"NETFLIX-MANIFEST": devices_dict["android_general"],
	"NETFLIX-LICENSE": devices_dict["android_general"],
}

#####################################(MUXER)#####################################

MUXER = {
	"muxer_file": f"{dirPath}/bin/muxer.json",
	"mkv_folder": None,
	"DEFAULT": False,  # to use the normal renaming. EX: Stranger Things S01E01 [1080p].mkv
	"AUDIO": "hin",  # default audio language.
	"SUB": "None",  # default subtitle language. EX: "eng" or "spa"
	"GROUP": "Tandav",  # to change the group name!. it's also possible to use this "--gr LOL", on the ripping commands.
	"noTitle": False,  # this will remove titles from the episodes EX: (The Witcher S01E01). insstead of (The Witcher S01E01 The End's Beginning).
	"scheme": "p2p",  # add/change any needed scheme naming. it's also possible to use this "--muxscheme repack", on the ripping commands.
	"schemeslist": {
		"p2p": "{t}.{r}.{s}.WEB-DL.{ac}.{vc}-{gr}",
		"test": "{t}.{r}.{s}.WEB-DL-{gr}",
	},
	"EXTRAS": [],  # extra mkvmerge.exe commands.
	"FPS24": [],
}

#####################################(PATHS)#####################################

PATHS = {
	"DL_FOLDER": "E:/#rips", #
	"DIR_PATH": f"{dirPath}",
	"BINARY_PATH": f"{dirPath}/bin",
	"COOKIES_PATH": f"{dirPath}/configs/Cookies",
	"KEYS_PATH": f"{dirPath}/configs/KEYS",
	"TOKENS_PATH": f"{dirPath}/configs/Tokens",
	"JSON_PATH": f"{dirPath}/json",
	"LOGA_PATH": f"{dirPath}/bin/tools/aria2c",
}

ARIA2C = {
	"enable_logging": False,  # True
}

SETTINGS = {
	"skip_video_demux": [],
}

#####################################(VPN)#####################################

VPN = {
	"proxies": None, # "http://151.253.165.70:8080",
	"nordvpn": {
		"port": "80",
		"email": "xxx",
		"passwd": "xxx",
		"http": "http://{email}:{passwd}@{ip}:{port}",
	},
	"private": {
		"port": "8080",
		"email": "abdalhmohmd8@gmail.com",  
		"passwd": "123456", 
		"http": "http://{email}:{passwd}@{ip}:{port}",
	},
}

#####################################(BIN)#####################################

BIN = {
		"mp4decrypt_moded": f"{dirPath}/bin/tools/mp4decrypt.exe",
		"mp4dump": f"{dirPath}/bin/tools/mp4dump.exe",
		"ffmpeg": f"{dirPath}/bin/tools/ffmpeg.exe",
		"ffprobe": f"{dirPath}/bin/tools/ffprobe.exe",
		"MediaInfo": f"{dirPath}/bin/tools/MediaInfo.exe",
		"mkvmerge": f"{dirPath}/bin/tools/mkvmerge.exe",
		"aria2c": f"{dirPath}/bin/tools/aria2c.exe",
	}

#####################################(Config)#####################################

Config = {}

Config["NETFLIX"] = {
	"cookies_file": f"{dirPath}/configs/Cookies/cookies_nf.txt",
	"cookies_txt": f"{dirPath}/configs/Cookies/cookies.txt",
	"keys_file": f"{dirPath}/configs/KEYS/netflix.keys",
	"token_file": f"{dirPath}/configs/Tokens/netflix_token.json",
	"email": "Cfklop@max07.club",
	"password": "1111",
	"manifest_language": "en-US",
	"metada_language": "en",
	"manifestEsn": "NFCDIE-03-{}".format(utils().random_hex(30)),
	"androidEsn": "NFANDROID1-PRV-P-GOOGLEPIXEL=4=XL-8162-" + utils_.random_hex(64),
}

#####################################(DIRS & FILES)##############################

def make_dirs():
	FILES = []

	DIRS = [
		f"{dirPath}/configs/Cookies",
		f"{dirPath}/configs/Tokens",
		f"{dirPath}/bin/tools/aria2c",
	]

	for dirs in DIRS:
		if not os.path.exists(dirs):
			os.makedirs(dirs)

	for files in FILES:
		if not os.path.isfile(files):
			with open(files, "w") as f:
				f.write("\n")

make_dirs()

#####################################(tool)#####################################

class tool:
	def config(self, service):
		return Config[service]

	def bin(self):
		return BIN

	def vpn(self):
		return VPN

	def paths(self):
		return PATHS

	def muxer(self):
		return MUXER

	def devices(self):
		return DEVICES

	def aria2c(self):
		return ARIA2C

	def video_settings(self):
		return SETTINGS
