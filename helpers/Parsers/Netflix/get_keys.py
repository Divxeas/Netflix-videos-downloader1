import time, os, json, logging, base64
from helpers.Parsers.Netflix.MSLClient import MSLClient
from configs.config import tool
from pywidevine.decrypt.wvdecryptcustom import WvDecrypt

logger = logging.getLogger(__name__)

'''			"av1-main-L20-dash-cbcs-prk",
			"av1-main-L21-dash-cbcs-prk",
			"av1-main-L30-dash-cbcs-prk",
			"av1-main-L31-dash-cbcs-prk",
			"av1-main-L40-dash-cbcs-prk",
			"av1-main-L41-dash-cbcs-prk",
			"av1-main-L50-dash-cbcs-prk",
			"av1-main-L51-dash-cbcs-prk",'''

'''			"vp9-profile0-L21-dash-cenc",
			"vp9-profile0-L30-dash-cenc",
			"vp9-profile0-L31-dash-cenc",
			"vp9-profile0-L40-dash-cenc",
			"vp9-profile2-L30-dash-cenc-prk",
			"vp9-profile2-L31-dash-cenc-prk",
			"vp9-profile2-L40-dash-cenc-prk",
			"vp9-profile2-L50-dash-cenc-prk",
			"vp9-profile2-L51-dash-cenc-prk"'''
			
def from_kid(kid):
	array_of_bytes = bytearray(b"\x00\x00\x002pssh\x00\x00\x00\x00")
	array_of_bytes.extend(bytes.fromhex("edef8ba979d64acea3c827dcd51d21ed"))
	array_of_bytes.extend(b"\x00\x00\x00\x12\x12\x10")
	array_of_bytes.extend(bytes.fromhex(kid.replace("-", "")))
	pssh = base64.b64encode(bytes.fromhex(array_of_bytes.hex()))
	return pssh.decode()

def __profiles(profile, addHEVCDO=False):

	profiles = [
		"heaac-2-dash",
		"dfxp-ls-sdh",
		"webvtt-lssdh-ios8",
		"BIF240",
		"BIF320",
	]

	if profile == "High KEYS":
		profiles += [
			"playready-h264hpl22-dash",
			"playready-h264hpl30-dash",
			"playready-h264hpl31-dash",
			#'playready-h264hpl40-dash'
		]
	
	elif profile == "Main KEYS":
		profiles += [
			"playready-h264mpl30-dash",
		]

	elif profile == "HEVC KEYS":
		profiles += [
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
			"hevc-main10-L41-dash-cenc-prk"
		]
		if addHEVCDO:
			profiles += [
				"hevc-main10-L31-dash-cenc-prk-do",
				"hevc-main10-L31-dash-cenc-prk-do",
				"hevc-main10-L40-dash-cenc-prk-do",
				"hevc-main10-L41-dash-cenc-prk-do",
			]			

	elif profile == 'HDR-10 KEYS':
		profiles += [
			"hevc-hdr-main10-L30-dash-cenc",
			"hevc-hdr-main10-L30-dash-cenc-prk",
			"hevc-hdr-main10-L31-dash-cenc",
			"hevc-hdr-main10-L31-dash-cenc-prk",
			"hevc-hdr-main10-L40-dash-cenc",
			"hevc-hdr-main10-L41-dash-cenc",
			"hevc-hdr-main10-L40-dash-cenc-prk",
			"hevc-hdr-main10-L41-dash-cenc-prk"
		]	
	else:
		profiles += [
			"playready-h264mpl30-dash",
		]

	return profiles

def GettingKEYS_Netflixv2(nfID, profile): #
	
	KEYS = []

	available_profiles = [
		"High KEYS",
		"HEVC KEYS",
		"HDR-10 KEYS",
		"Main KEYS"
	]

	if not profile in available_profiles:
		logger.info("Error: Unknown profile: {}".format(profile))
		exit(1)

	logger.info(f"\nGetting {profile}...")
	
	profiles = __profiles(profile)
	
	try:
		client = MSLClient(profiles=profiles)
		resp = client.load_playlist(int(nfID))
		if resp is None:
			if profile == 'HEVC KEYS':
				profiles = __profiles(profile, addHEVCDO=True)
				client = MSLClient(profiles=profiles)
				resp = client.load_playlist(int(nfID))
	
	except Exception as e:
		logger.error("Manifest Error: {}".format(e))
		return KEYS
	
	try:
		#init_data_b64 = from_kid('0000000005edabd50000000000000000')
		init_data_b64 = resp["result"]["video_tracks"][0]["drmHeader"]["bytes"]
	except KeyError:
		logger.error("cannot get pssh, {}".format(resp))
		return KEYS

	cert_data_b64 = "CAUSwwUKvQIIAxIQ5US6QAvBDzfTtjb4tU/7QxiH8c+TBSKOAjCCAQoCggEBAObzvlu2hZRsapAPx4Aa4GUZj4/GjxgXUtBH4THSkM40x63wQeyVxlEEo1D/T1FkVM/S+tiKbJiIGaT0Yb5LTAHcJEhODB40TXlwPfcxBjJLfOkF3jP6wIlqbb6OPVkDi6KMTZ3EYL6BEFGfD1ag/LDsPxG6EZIn3k4S3ODcej6YSzG4TnGD0szj5m6uj/2azPZsWAlSNBRUejmP6Tiota7g5u6AWZz0MsgCiEvnxRHmTRee+LO6U4dswzF3Odr2XBPD/hIAtp0RX8JlcGazBS0GABMMo2qNfCiSiGdyl2xZJq4fq99LoVfCLNChkn1N2NIYLrStQHa35pgObvhwi7ECAwEAAToQdGVzdC5uZXRmbGl4LmNvbRKAA4TTLzJbDZaKfozb9vDv5qpW5A/DNL9gbnJJi/AIZB3QOW2veGmKT3xaKNQ4NSvo/EyfVlhc4ujd4QPrFgYztGLNrxeyRF0J8XzGOPsvv9Mc9uLHKfiZQuy21KZYWF7HNedJ4qpAe6gqZ6uq7Se7f2JbelzENX8rsTpppKvkgPRIKLspFwv0EJQLPWD1zjew2PjoGEwJYlKbSbHVcUNygplaGmPkUCBThDh7p/5Lx5ff2d/oPpIlFvhqntmfOfumt4i+ZL3fFaObvkjpQFVAajqmfipY0KAtiUYYJAJSbm2DnrqP7+DmO9hmRMm9uJkXC2MxbmeNtJHAHdbgKsqjLHDiqwk1JplFMoC9KNMp2pUNdX9TkcrtJoEDqIn3zX9p+itdt3a9mVFc7/ZL4xpraYdQvOwP5LmXj9galK3s+eQJ7bkX6cCi+2X+iBmCMx4R0XJ3/1gxiM5LiStibCnfInub1nNgJDojxFA3jH/IuUcblEf/5Y0s1SzokBnR8V0KbA=="

	device = tool().devices()["NETFLIX-LICENSE"]

	wvdecrypt = WvDecrypt(
		init_data_b64=init_data_b64, cert_data_b64=cert_data_b64, device=device
	)
	challenge = wvdecrypt.get_challenge()
	current_sessionId = str(time.time()).replace(".", "")[0:-2]
	data = client.get_license(challenge, current_sessionId)

	try:
		license_b64 = data["result"][0]["licenseResponseBase64"]
	except Exception:
		logger.error("MSL LICENSE Error Message: {}".format(data))
		return KEYS

	wvdecrypt.update_license(license_b64)
	Correct, keyswvdecrypt = wvdecrypt.start_process()
	KEYS = keyswvdecrypt

	return KEYS