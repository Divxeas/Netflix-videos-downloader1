from utils.modules.pymp4.parser import Box
from io import BytesIO
import base64
import requests
import uuid
import binascii
import subprocess
import logging
import json


class pssh_generator(object):
    def __init__(self, init, **kwargs):
        self.init = init
        self.logger = logging.getLogger(__name__)
        self.proxies = kwargs.get("proxies", None)
        self.mp4dumpexe = kwargs.get("mp4dumpexe", None)

    def from_kid(self):
        array_of_bytes = bytearray(b"\x00\x00\x002pssh\x00\x00\x00\x00")
        array_of_bytes.extend(bytes.fromhex("edef8ba979d64acea3c827dcd51d21ed"))
        array_of_bytes.extend(b"\x00\x00\x00\x12\x12\x10")
        array_of_bytes.extend(bytes.fromhex(self.init.replace("-", "")))
        pssh = base64.b64encode(bytes.fromhex(array_of_bytes.hex()))
        return pssh.decode()

    def Get_PSSH(self):
        WV_SYSTEM_ID = "[ed ef 8b a9 79 d6 4a ce a3 c8 27 dc d5 1d 21 ed]"
        pssh = None
        data = subprocess.check_output(
            [self.mp4dumpexe, "--format", "json", "--verbosity", "1", self.init]
        )
        data = json.loads(data)
        for atom in data:
            if atom["name"] == "moov":
                for child in atom["children"]:
                    if child["name"] == "pssh":
                        if child["system_id"] == WV_SYSTEM_ID:
                            pssh = child["data"][1:-1].replace(" ", "")
                            pssh = binascii.unhexlify(pssh)
                            if pssh.startswith(b"\x08\x01"):
                                pssh = pssh[0:]
                            pssh = base64.b64encode(pssh).decode("utf-8")
                            return pssh

        if not pssh:
            self.logger.error("Error while generate pssh from file.")
            return pssh

    def get_moov_pssh(self, moov):
        while True:
            x = Box.parse_stream(moov)
            if x.type == b"moov":
                for y in x.children:
                    if y.type == b"pssh" and y.system_ID == uuid.UUID(
                        "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
                    ):
                        data = base64.b64encode(y.init_data)
                        return data

    def build_init_segment_mp4(self, bytes_):
        moov = BytesIO(bytes_)
        data = self.get_moov_pssh(moov)
        pssh = data.decode("utf-8")

        return pssh

    def getInitWithRange2(self, headers):

        initbytes = requests.get(url=self.init, proxies=self.proxies, headers=headers,)

        try:
            pssh = self.build_init_segment_mp4(initbytes.content)
            return pssh
        except Exception as e:
            self.logger.info("Error: " + str(e))

        return None

    def getInitWithRange(self, start: int, end: int):

        initbytes = requests.get(
            url=self.init,
            proxies=self.proxies,
            headers={"Range": "bytes={}-{}".format(start, end)},
        )

        try:
            pssh = self.build_init_segment_mp4(initbytes.content)
            return pssh
        except Exception as e:
            self.logger.info("Error: " + str(e))

        return None

    def loads(self):
        req = requests.get(url=self.init, proxies=self.proxies)

        initbytes = req.content

        try:
            pssh = self.build_init_segment_mp4(initbytes)
            return pssh
        except Exception as e:
            self.logger.error("Error: " + str(e))

        return None

    def load(self):

        with open(self.init, "rb") as f:
            initbytes = f.read()

        try:
            pssh = self.build_init_segment_mp4(initbytes)
            return pssh
        except Exception as e:
            self.logger.error("Error: " + str(e))

        return None

    def from_str(self):

        initbytes = self.init

        try:
            pssh = self.build_init_segment_mp4(initbytes)
            return pssh
        except Exception as e:
            self.logger.info("Error: " + str(e))

        return None
