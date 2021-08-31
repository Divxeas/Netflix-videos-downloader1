import base64, binascii, json, os, re, random, requests, string, time, traceback, logging
from datetime import datetime
from Cryptodome.Cipher import AES, PKCS1_OAEP
from Cryptodome.Util import Padding
from Cryptodome.Hash import HMAC, SHA256
from Cryptodome.PublicKey import RSA
from pywidevine.cdm import cdm, deviceconfig
from configs.config import tool

class MSLClient:
	def __init__(self, profiles=None, wv_keyexchange=True, proxies=None):

		self.session = requests.session()
		self.logger = logging.getLogger(__name__)
		if proxies:
			self.session.proxies.update(proxies)

		self.nf_endpoints = {
			"manifest": "https://www.netflix.com/nq/msl_v1/cadmium/pbo_manifests/^1.0.0/router",
			"license": "https://www.netflix.com/nq/msl_v1/cadmium/pbo_licenses/^1.0.0/router",
		}

		######################################################################

		self.config = tool().config("NETFLIX")
		self.email = self.config["email"]
		self.password = self.config["password"]
		self.device = tool().devices()["NETFLIX-MANIFEST"]
		self.save_rsa_location = self.config["token_file"]
		self.languages = self.config["manifest_language"]
		self.license_path = None

		######################################################################

		if os.path.isfile(self.save_rsa_location):
			self.generatePrivateKey = RSA.importKey(
				json.loads(open(self.save_rsa_location, "r").read())["RSA_KEY"]
			)
		else:
			self.generatePrivateKey = RSA.generate(2048)
		
		if wv_keyexchange:
			self.wv_keyexchange = True
			self.cdm = cdm.Cdm()
			self.cdm_session = None
		else:
			self.wv_keyexchange = False
			self.cdm = None
			self.cdm_session = None

		self.manifest_challenge = '' # set desired wv data to overide wvexchange data
		
		self.profiles = profiles

		self.logger.debug("Using profiles: {}".format(self.profiles))		

		esn = self.config["androidEsn"]
		if esn is None:
			self.logger.error(
				'\nandroid esn not found, set esn with cdm systemID in config.py'
			)
		else:
			self.esn = esn

		self.logger.debug("Using esn: " + self.esn)
		
		self.messageid = random.randint(0, 2 ** 52)
		self.session_keys = {} #~
		self.header = {
			"sender": self.esn,
			"handshake": True,
			"nonreplayable": 2,
			"capabilities": {"languages": [], "compressionalgos": []},
			"recipient": "Netflix",
			"renewable": True,
			"messageid": self.messageid,
			"timestamp": time.time(),
		}

		self.setRSA()

	def get_header_extra(self):
		
		if self.wv_keyexchange:
			self.cdm_session = self.cdm.open_session(
				None,
				deviceconfig.DeviceConfig(self.device),
				b"\x0A\x7A\x00\x6C\x38\x2B",
				True,
			)
			wv_request = base64.b64encode(
				self.cdm.get_license_request(self.cdm_session)
			).decode("utf-8")

			self.header["keyrequestdata"] = [
				{
					"scheme": "WIDEVINE", 
					"keydata": {
						"keyrequest": wv_request
					}
				}
			]
		
		else:
			self.header["keyrequestdata"] = [
				{
					"scheme": "ASYMMETRIC_WRAPPED",
					"keydata": {
						"publickey": base64.b64encode(
							self.generatePrivateKey.publickey().exportKey("DER")
						).decode("utf8"),
						"mechanism": "JWK_RSA",
						"keypairid": "rsaKeypairId",
					},
				}
			]
		
		return self.header

	def setRSA(self):
		if os.path.isfile(self.save_rsa_location):
			master_token = self.load_tokens()
			expires = master_token["expiration"]
			valid_until = datetime.utcfromtimestamp(int(expires))
			present_time = datetime.now()

			difference = valid_until - present_time
			difference = difference.total_seconds() / 60 / 60
			if difference < 10:
				self.logger.debug("rsa file found. expired soon")
				self.session_keys["session_keys"] = self.generate_handshake()
			else:
				self.logger.debug("rsa file found")
				self.session_keys["session_keys"] = {
					"mastertoken": master_token["mastertoken"],
					"sequence_number": master_token["sequence_number"],
					"encryption_key": master_token["encryption_key"],
					"sign_key": master_token["sign_key"],
				}
		else:
			self.logger.debug("rsa file not found")
			self.session_keys["session_keys"] = self.generate_handshake()

	def load_playlist(self, viewable_id):
		
		payload = {
			"version": 2,
			"url": "/manifest", #"/licensedManifest"
			"id": int(time.time()),
			"languages": self.languages,
			"params": {
				#"challenge": self.manifest_challenge,
				"type": "standard",
				"viewableId": viewable_id,
				"profiles": self.profiles,
				"flavor": "STANDARD", #'PRE_FETCH'
				"drmType": "widevine",
				"usePsshBox": True,
				"useHttpsStreams": True,
				"supportsPreReleasePin": True,
				"supportsWatermark": True,	
				'supportsUnequalizedDownloadables': True,
				'requestEligibleABTests': True,											
				"isBranching": False,
				'isNonMember': False,
				'isUIAutoPlay': False,				
				"imageSubtitleHeight": 1080,
				"uiVersion": "shakti-v4bf615c3",
				'uiPlatform': 'SHAKTI',
				"clientVersion": "6.0026.291.011",
				'desiredVmaf': 'plus_lts', # phone_plus_exp
				"showAllSubDubTracks": True,
				#"preferredTextLocale": "ar",
				#"preferredAudioLocale": "ar",
				#"maxSupportedLanguages": 2,				
				"preferAssistiveAudio": False,
				"deviceSecurityLevel": "3000",
				'licenseType': 'standard',
				'titleSpecificData': {
					str(viewable_id): {
						'unletterboxed': True
					}
				},				
				"videoOutputInfo": [
					{
						"type": "DigitalVideoOutputDescriptor",
						"outputType": "unknown",
						"supportedHdcpVersions": ['2.2'],
						"isHdcpEngaged": True,
					}
				],
			},
		}

		request_data = self.msl_request(payload)
		response = self.session.post(self.nf_endpoints["manifest"], data=request_data)
		manifest = json.loads(json.dumps(self.decrypt_response(response.text)))

		if manifest.get("result"): 
			#with open('videoTraks.json', 'w', encoding='utf-8') as d: 
				#["result"]["video_tracks"]
			#	d.write(json.dumps(manifest, indent=2))
			self.license_path = manifest["result"]["links"]["license"]["href"]
			return manifest

		if manifest.get("errormsg"):
			self.logger.info(manifest["errormsg"])
			return None
		else:
			self.logger.info(manifest)
			return None

	def decrypt_response(self, payload):
		errored = False
		try:
			p = json.loads(payload)
			if p.get("errordata"):
				return json.loads(base64.b64decode(p["errordata"]).decode())
		except:
			payloads = re.split(
				r',"signature":"[0-9A-Za-z/+=]+"}', payload.split("}}")[1]
			)
			payloads = [x + "}" for x in payloads]
			new_payload = payloads[:-1]

			chunks = []
			for chunk in new_payload:
				try:
					payloadchunk = json.loads(chunk)["payload"]
					encryption_envelope = payloadchunk
					cipher = AES.new(
						self.session_keys["session_keys"]["encryption_key"],
						AES.MODE_CBC,
						base64.b64decode(
							json.loads(
								base64.b64decode(encryption_envelope).decode("utf8")
							)["iv"]
						),
					)

					plaintext = cipher.decrypt(
						base64.b64decode(
							json.loads(
								base64.b64decode(encryption_envelope).decode("utf8")
							)["ciphertext"]
						)
					)

					plaintext = json.loads(Padding.unpad(plaintext, 16).decode("utf8"))

					data = plaintext["data"]
					data = base64.b64decode(data).decode("utf8")
					chunks.append(data)
				except:
					continue

			decrypted_payload = "".join(chunks)
			try:
				return json.loads(decrypted_payload)
			except:
				traceback.print_exc()
				self.logger.info("Unable to decrypt payloads...exiting")
				exit(-1)

	def generate_handshake(self):
		self.logger.debug("generate_handshake")
		header = self.get_header_extra()

		request = {
			"entityauthdata": {
				"scheme": "NONE",
				"authdata": {"identity": self.esn,}
			},
			"signature": "",
			"headerdata": base64.b64encode(json.dumps(header).encode("utf8")).decode("utf8"),
		}
		response = self.session.post(
			url=self.nf_endpoints["manifest"],
			json=request,
		)
		try:
			if response.json().get("errordata"):
				self.logger.info("ERROR")
				self.logger.info(
					base64.b64decode(response.json()["errordata"]).decode()
				)
				exit(-1)
			handshake = self.parse_handshake(response=response.json())
			return handshake
		except:
			traceback.print_exc()
			self.logger.info(response.text)
			exit(-1)

	def load_tokens(self):

		with open(self.save_rsa_location, "r", encoding='utf-8') as f:
			tokens_data = json.loads(f.read())

		data = {
			"mastertoken": tokens_data["mastertoken"],
			"sequence_number": tokens_data["sequence_number"],
			"encryption_key": base64.standard_b64decode(tokens_data["encryption_key"]),
			"sign_key": base64.standard_b64decode(tokens_data["sign_key"]),
			"RSA_KEY": tokens_data["RSA_KEY"],
			"expiration": tokens_data["expiration"],
		}

		return data

	def save_tokens(self, tokens_data):

		data = {
			"mastertoken": tokens_data["mastertoken"],
			"sequence_number": tokens_data["sequence_number"],
			"encryption_key": base64.standard_b64encode(
				tokens_data["encryption_key"]
			).decode("utf-8"),
			"sign_key": base64.standard_b64encode(tokens_data["sign_key"]).decode(
				"utf-8"
			),
			"RSA_KEY": tokens_data["RSA_KEY"],
			"expiration": tokens_data["expiration"],
		}

		with open(self.save_rsa_location, 'w', encoding='utf-8') as f:
			f.write(json.dumps(data, indent=2))

	def parse_handshake(self, response):
		headerdata = json.loads(base64.b64decode(response["headerdata"]).decode("utf8"))

		keyresponsedata = headerdata["keyresponsedata"]
		mastertoken = headerdata["keyresponsedata"]["mastertoken"]
		sequence_number = json.loads(
			base64.b64decode(mastertoken["tokendata"]).decode("utf8")
		)["sequencenumber"]

		if self.wv_keyexchange:
			expected_scheme = "WIDEVINE"
		else:
			expected_scheme = "ASYMMETRIC_WRAPPED"

		scheme = keyresponsedata["scheme"]

		if scheme != expected_scheme:
			self.logger.info("Key Exchange failed:")
			return False

		keydata = keyresponsedata["keydata"]

		if self.wv_keyexchange:
			encryption_key, sign_key = self.__process_wv_keydata(keydata)
		else:
			encryption_key, sign_key = self.__parse_rsa_wrapped_crypto_keys(keydata)

		tokens_data = {
			"mastertoken": mastertoken,
			"sequence_number": sequence_number,
			"encryption_key": encryption_key,
			"sign_key": sign_key,
		}

		tokens_data_save = tokens_data
		tokens_data_save.update(
			{"RSA_KEY": self.generatePrivateKey.exportKey().decode()}
		)
		tokens_data_save.update(
			{
				"expiration": json.loads(
					base64.b64decode(
						json.loads(base64.b64decode(response["headerdata"]))[
							"keyresponsedata"
						]["mastertoken"]["tokendata"]
					)
				)["expiration"]
			}
		)
		self.save_tokens(tokens_data_save)
		return tokens_data

	def __process_wv_keydata(self, keydata):

		wv_response_b64 = keydata["cdmkeyresponse"]  # pass as b64
		encryptionkeyid = base64.standard_b64decode(keydata["encryptionkeyid"])
		hmackeyid = base64.standard_b64decode(keydata["hmackeyid"])
		self.cdm.provide_license(self.cdm_session, wv_response_b64)
		keys = self.cdm.get_keys(self.cdm_session)
		self.logger.debug("wv key exchange: obtained wv key exchange keys %s" % keys)
		return (
			self.__find_wv_key(encryptionkeyid, keys, ["AllowEncrypt", "AllowDecrypt"]),
			self.__find_wv_key(hmackeyid, keys, ["AllowSign", "AllowSignatureVerify"]),
		)

	def __find_wv_key(self, kid, keys, permissions):
		for key in keys:
			if key.kid != kid:
				continue
			if key.type != "OPERATOR_SESSION":
				self.logger.debug(
					"wv key exchange: Wrong key type (not operator session) key %s"
					% key
				)
				continue

			if not set(permissions) <= set(key.permissions):
				self.logger.debug(
					"wv key exchange: Incorrect permissions, key %s, needed perms %s"
					% (key, permissions)
				)
				continue
			return key.key

		return None

	def __parse_rsa_wrapped_crypto_keys(self, keydata):
		# Init Decryption
		encrypted_encryption_key = base64.b64decode(keydata["encryptionkey"])

		encrypted_sign_key = base64.b64decode(keydata["hmackey"])

		oaep_cipher = PKCS1_OAEP.new(self.generatePrivateKey)
		encryption_key_data = json.loads(
			oaep_cipher.decrypt(encrypted_encryption_key).decode("utf8")
		)

		encryption_key = self.base64_check(encryption_key_data["k"])

		sign_key_data = json.loads(
			oaep_cipher.decrypt(encrypted_sign_key).decode("utf8")
		)

		sign_key = self.base64_check(sign_key_data["k"])
		return (encryption_key, sign_key)

	def base64key_decode(self, payload):
		l = len(payload) % 4
		if l == 2:
			payload += "=="
		elif l == 3:
			payload += "="
		elif l != 0:
			raise ValueError("Invalid base64 string")
		return base64.urlsafe_b64decode(payload.encode("utf-8"))

	def base64_check(self, string):

		while len(string) % 4 != 0:
			string = string + "="
		return base64.urlsafe_b64decode(string.encode())

	def msl_request(self, data, is_handshake=False):
		
		header = self.header.copy()
		header["handshake"] = is_handshake
		header["userauthdata"] = {
			"scheme": "EMAIL_PASSWORD",
			"authdata": {"email": self.email, "password": self.password},
		}

		header_envelope = self.msl_encrypt(self.session_keys, json.dumps(header))

		header_signature = HMAC.new(
			self.session_keys["session_keys"]["sign_key"], header_envelope, SHA256
		).digest()

		encrypted_header = {
			"headerdata": base64.b64encode(header_envelope).decode("utf8"),
			"signature": base64.b64encode(header_signature).decode("utf8"),
			"mastertoken": self.session_keys["session_keys"]["mastertoken"],
		}

		payload = {
			"messageid": self.messageid,
			"data": base64.b64encode(json.dumps(data).encode()).decode("utf8"),
			"sequencenumber": 1,
			"endofmsg": True,
		}

		payload_envelope = self.msl_encrypt(self.session_keys, json.dumps(payload))

		payload_signature = HMAC.new(
			self.session_keys["session_keys"]["sign_key"], payload_envelope, SHA256
		).digest()

		payload_chunk = {
			"payload": base64.b64encode(payload_envelope).decode("utf8"),
			"signature": base64.b64encode(payload_signature).decode("utf8"),
		}
		return json.dumps(encrypted_header) + json.dumps(payload_chunk)

	def msl_encrypt(self, msl_session, plaintext):

		cbc_iv = os.urandom(16)
		encryption_envelope = {
			"keyid": "%s_%s"
			% (self.esn, msl_session["session_keys"]["sequence_number"]),
			"sha256": "AA==",
			"iv": base64.b64encode(cbc_iv).decode("utf8"),
		}

		plaintext = Padding.pad(plaintext.encode("utf8"), 16)
		cipher = AES.new(
			msl_session["session_keys"]["encryption_key"], AES.MODE_CBC, cbc_iv
		)

		ciphertext = cipher.encrypt(plaintext)

		encryption_envelope["ciphertext"] = base64.b64encode(ciphertext).decode("utf8")

		return json.dumps(encryption_envelope).encode("utf8")

	def get_license(self, challenge, session_id):

		if not isinstance(challenge, bytes):
			raise TypeError("challenge must be of type bytes")

		if not isinstance(session_id, str):
			raise TypeError("session_id must be of type string")

		timestamp = int(time.time() * 10000)

		license_request_data = {
			"version": 2,
			"url": self.license_path,
			"id": timestamp,
			"languages": "en_US",
			"echo": "drmsessionId",	
			"params": [
				{
					"drmSessionId": session_id,
					"clientTime": int(timestamp / 10000),
					"challengeBase64": base64.b64encode(challenge).decode("utf8"),
					"xid": str(timestamp + 1610),
				}
			]
		}

		request_data = self.msl_request(license_request_data)

		resp = self.session.post(url=self.nf_endpoints["license"],data=request_data)

		try:
			resp.json()

		except ValueError:
			msl_license_data = json.loads(json.dumps(self.decrypt_response(resp.text)))
			if msl_license_data.get("result"):
				return msl_license_data
			if msl_license_data.get("errormsg"):
				raise ValueError(msl_license_data["errormsg"])
		raise ValueError(msl_license_data)
