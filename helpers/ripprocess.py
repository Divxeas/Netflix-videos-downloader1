import ffmpy, json, os, sys, unidecode, requests, subprocess, time, pycountry, html, tqdm, re, glob, base64, binascii
from titlecase import titlecase
from configs.config import tool
from helpers.proxy_environ import hold_proxy
import tldextract
from collections import namedtuple
from collections.abc import Sequence
from natsort import natsorted
import logging
import unicodedata, string


class EpisodesNumbersHandler:
    def __init__(self):
        return

    def numberRange(self, start: int, end: int):
        if list(range(start, end + 1)) != []:
            return list(range(start, end + 1))

        if list(range(end, start + 1)) != []:
            return list(range(end, start + 1))

        return [start]

    def ListNumber(self, Number: str):
        if Number.isdigit():
            return [int(Number)]

        if Number.strip() == "~" or Number.strip() == "":
            return self.numberRange(1, 999)

        if "-" in Number:
            start, end = Number.split("-")
            if start.strip() == "" or end.strip() == "":
                raise ValueError("wrong Number: {}".format(Number))
            return self.numberRange(int(start), int(end))

        if "~" in Number:
            start, _ = Number.split("~")
            if start.strip() == "":
                raise ValueError("wrong Number: {}".format(Number))
            return self.numberRange(int(start), 999)

        return

    def sortNumbers(self, Numbers):
        SortedNumbers = []
        for Number in Numbers.split(","):
            SortedNumbers += self.ListNumber(Number.strip())

        return natsorted(list(set(SortedNumbers)))


class ripprocess(object):
    def __init__(self):
        self.tool = tool()
        self.logger = logging.getLogger(__name__)
        self.bin = self.tool.bin()

    def sort_list(self, media_list, keyword1=None, keyword2=None):
        if keyword1:
            if keyword2:
                return sorted(
                    media_list, key=lambda k: (int(k[keyword1]), int(k[keyword2]))
                )
            else:
                sorted(media_list, key=lambda k: int(k[keyword1]))

        return media_list

    def yt2json(self, url, proxies=None):
        jsonfile = "info.info.json"

        yt_cmd = [
            self.bin["youtube"],
            "--skip-download",
            "--write-info-json",
            "--quiet",
            "--no-warnings",
            "-o",
            "info",
            url,
        ]

        if proxies:
            yt_cmd += ["--proxy", proxies.get("https")]

        subprocess.call(yt_cmd)

        while not os.path.isfile(jsonfile):
            time.sleep(0.2)
        with open(jsonfile) as js:
            data = json.load(js)
        if os.path.isfile(jsonfile):
            os.remove(jsonfile)

        return data

    def getKeyId(self, mp4_file):
        data = subprocess.check_output(
            [self.bin["mp4dump"], "--format", "json", "--verbosity", "1", mp4_file]
        )
        try:
            return re.sub(
                " ",
                "",
                re.compile(r"default_KID.*\[(.*)\]").search(data.decode()).group(1),
            )
        except AttributeError:
            return None

    def flatten(self, l):
        return list(self.flatten_g(l))

    def flatten_g(self, l):
        basestring = (str, bytes)
        for el in l:
            if isinstance(el, Sequence) and not isinstance(el, basestring):
                for sub in self.flatten_g(el):
                    yield sub
            else:
                yield el

    def removeExtentsion(self, string: str):
        if "." in string:
            return ".".join(string.split(".")[:-1])
        else:
            raise ValueError("string has no extentsion: {}".format(string))

    def replaceExtentsion(self, string: str, ext: str):
        if "." in string:
            return ".".join(string.split(".")[:-1]) + f".{ext}"
        else:
            raise ValueError("string has no extentsion: {}".format(string))

    def domain(self, url):
        return "{0.domain}.{0.suffix}".format(tldextract.extract(url))

    def remove_dups(self, List, keyword=""):
        Added_ = set()
        Proper_ = []
        for L in List:
            if L[keyword] not in Added_:
                Proper_.append(L)
                Added_.add(L[keyword])

        return Proper_

    def find_str(self, s, char):
        index = 0

        if char in s:
            c = char[0]
            for ch in s:
                if ch == c:
                    if s[index : index + len(char)] == char:
                        return index

                index += 1

        return -1

    def updt(self, total, progress):
        barLength, status = 80, ""
        progress = float(progress) / float(total)
        if progress >= 1.0:
            progress, status = 1, "\r\n"
        block = int(round(barLength * progress))
        text = "\rProgress: {} | {:.0f}% {}".format(
            "█" * block + "" * (barLength - block), round(progress * 100, 0), status,
        )
        sys.stdout.write(text)
        sys.stdout.flush()

    def Get_PSSH(self, mp4_file):
        WV_SYSTEM_ID = "[ed ef 8b a9 79 d6 4a ce a3 c8 27 dc d5 1d 21 ed]"
        pssh = None
        data = subprocess.check_output(
            [self.bin["mp4dump"], "--format", "json", "--verbosity", "1", mp4_file]
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

        return None

    def SubtitleEdit(
        self, contain=None, file=None, removeSDH=False, silent=True, extra_commands=[]
    ):
        if file:
            subtitle_command = [
                self.bin["SubtitleEdit"],
                "/convert",
                file,
                "srt",
                "/overwrite",
                "/multiplereplace:.",
                "/MergeShortLines",
                "/FixCommonErrors",
            ]

            subtitle_command += extra_commands

            if removeSDH:
                subtitle_command.append("/RemoveTextForHI")

            subprocess.call(
                subtitle_command, stdout=open(os.devnull, "wb")
            ) if silent else subprocess.call(subtitle_command)

        if contain:
            subtitle_command = [
                self.bin["SubtitleEdit"],
                "/convert",
                "{}*.srt".format(contain),
                "srt",
                "/overwrite",
                "/multiplereplace:.",
                "/MergeShortLines",
                "/FixCommonErrors",
            ]

            subtitle_command += extra_commands

            if removeSDH:
                subtitle_command.append("/removetextforhi")

            subprocess.call(
                subtitle_command, stdout=open(os.devnull, "wb")
            ) if silent else subprocess.call(subtitle_command)

        return

    def parseCookieFile(self, cookiesfile):
        cookies = {}
        with open(cookiesfile, "r") as fp:
            for line in fp:
                if not re.match(r"^\#", line):
                    lineFields = line.strip().split("\t")
                    try:
                        cookies[lineFields[5]] = lineFields[6]
                    except Exception:
                        pass
        return cookies

    def ReplaceCodeLanguages(self, X):
        X = X.lower()
        X = (
            X.replace("_subtitle_dialog_0", "")
            .replace("_narrative_dialog_0", "")
            .replace("_caption_dialog_0", "")
            .replace("_dialog_0", "")
            .replace("_descriptive_0", "_descriptive")
            .replace("_descriptive", "_descriptive")
            .replace("_sdh", "-sdh")
            .replace("es-es", "es")
            .replace("en-es", "es")
            .replace("kn-in", "kn")
            .replace("gu-in", "gu")
            .replace("ja-jp", "ja")
            .replace("mni-in", "mni")
            .replace("si-in", "si")
            .replace("as-in", "as")
            .replace("ml-in", "ml")
            .replace("sv-se", "sv")
            .replace("hy-hy", "hy")
            .replace("sv-sv", "sv")
            .replace("da-da", "da")
            .replace("fi-fi", "fi")
            .replace("nb-nb", "nb")
            .replace("is-is", "is")
            .replace("uk-uk", "uk")
            .replace("hu-hu", "hu")
            .replace("bg-bg", "bg")
            .replace("hr-hr", "hr")
            .replace("lt-lt", "lt")
            .replace("et-et", "et")
            .replace("el-el", "el")
            .replace("he-he", "he")
            .replace("ar-ar", "ar")
            .replace("fa-fa", "fa")
            .replace("ro-ro", "ro")
            .replace("sr-sr", "sr")
            .replace("cs-cs", "cs")
            .replace("sk-sk", "sk")
            .replace("mk-mk", "mk")
            .replace("hi-hi", "hi")
            .replace("bn-bn", "bn")
            .replace("ur-ur", "ur")
            .replace("pa-pa", "pa")
            .replace("ta-ta", "ta")
            .replace("te-te", "te")
            .replace("mr-mr", "mr")
            .replace("kn-kn", "kn")
            .replace("gu-gu", "gu")
            .replace("ml-ml", "ml")
            .replace("si-si", "si")
            .replace("as-as", "as")
            .replace("mni-mni", "mni")
            .replace("tl-tl", "tl")
            .replace("id-id", "id")
            .replace("ms-ms", "ms")
            .replace("vi-vi", "vi")
            .replace("th-th", "th")
            .replace("km-km", "km")
            .replace("ko-ko", "ko")
            .replace("zh-zh", "zh")
            .replace("ja-ja", "ja")
            .replace("ru-ru", "ru")
            .replace("tr-tr", "tr")
            .replace("it-it", "it")
            .replace("es-mx", "es-la")
            .replace("ar-sa", "ar")
            .replace("zh-cn", "zh")
            .replace("nl-nl", "nl")
            .replace("pl-pl", "pl")
            .replace("pt-pt", "pt")
            .replace("hi-in", "hi")
            .replace("mr-in", "mr")
            .replace("bn-in", "bn")
            .replace("te-in", "te")
            .replace("cmn-hans", "zh-hans")
            .replace("cmn-hant", "zh-hant")
            .replace("ko-kr", "ko")
            .replace("en-au", "en")
            .replace("es-419", "es-la")
            .replace("es-us", "es-la")
            .replace("en-us", "en")
            .replace("en-gb", "en")
            .replace("fr-fr", "fr")
            .replace("de-de", "de")
            .replace("las-419", "es-la")
            .replace("ar-ae", "ar")
            .replace("da-dk", "da")
            .replace("yue-hant", "yue")
            .replace("bn-in", "bn")
            .replace("ur-in", "ur")
            .replace("ta-in", "ta")
            .replace("sl-si", "sl")
            .replace("cs-cz", "cs")
            .replace("hi-jp", "hi")
            .replace("-001", "")
            .replace("en-US", "en")
            .replace("deu", "de")
            .replace("eng", "en")
            .replace("ca-es", "cat")
            .replace("fil-ph", "fil")
            .replace("en-ca", "en")
            .replace("eu-es", "eu")
            .replace("ar-eg", "ar")
            .replace("he-il", "he")
            .replace("el-gr", "he")
            .replace("nb-no", "nb")
            .replace("es-ar", "es-la")
            .replace("en-ph", "en")
            .replace("sq-al", "sq")
            .replace("bs-ba", "bs")
        )

        return X

    def countrycode(self, code, site_domain="None"):
        languageCodes = {
            "zh-Hans": "zhoS",
            "zh-Hant": "zhoT",
            "pt-BR": "brPor",
            "es-ES": "euSpa",
            "en-GB": "enGB",
            "en-PH": "enPH",
            "nl-BE": "nlBE",
            "fil": "enPH",
            "yue": "zhoS",
            "fr-CA": "caFra",
        }

        if code == "cmn-Hans":
            return "Mandarin Chinese (Simplified)", "zh-Hans"
        elif code == "cmn-Hant":
            return "Mandarin Chinese (Traditional)", "zh-Hant"
        elif code == "es-419":
            return "Spanish", "spa"
        elif code == "es-ES":
            return "European Spanish", "euSpa"
        elif code == "pt-BR":
            return "Brazilian Portuguese", "brPor"
        elif code == "pt-PT":
            return "Portuguese", "por"
        elif code == "fr-CA":
            return "French Canadian", "caFra"
        elif code == "fr-FR":
            return "French", "fra"
        elif code == "iw":
            return "Modern Hebrew", "heb"
        elif code == "es" and site_domain == "google":
            return "European Spanish", "euSpa"

        lang_code = code[: code.index("-")] if "-" in code else code
        lang = pycountry.languages.get(alpha_2=lang_code)
        if lang is None:
            lang = pycountry.languages.get(alpha_3=lang_code)

        try:
            languagecode = languageCodes[code]
        except KeyError:
            languagecode = lang.alpha_3

        return lang.name, languagecode

    def tqdm_downloader(self, url, file_name, proxies=None):
        # self.logger.info(file_name)
        r = requests.get(url, stream=True)
        file_size = int(r.headers["Content-Length"])
        chunk = 1
        chunk_size = 1024
        num_bars = int(file_size / chunk_size)

        with open(file_name, "wb") as fp:
            for chunk in tqdm.tqdm(
                r.iter_content(chunk_size=chunk_size),
                total=num_bars,
                unit="KB",
                desc=file_name,
                leave=True,  # progressbar stays
            ):
                fp.write(chunk)

        return

    def silent_aria2c_download(self, url, file_name, disable_proxy=True):
        holder = hold_proxy()

        if disable_proxy:
            holder.disable()

        commands = [
            self.bin["aria2c"],
            url,
            '--user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36"',
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
            "--retry-wait=5",
            "-x16",
            "-j16",
            "-s16",
            "-o",
            file_name,
        ]

        try:
            aria = subprocess.call(commands, stdout=open(os.devnull, "wb"),)
        except FileNotFoundError:
            self.logger.info("UNABLE TO FIND {}".format("aria2c.exe"))
            exit(-1)
        if aria != 0:
            raise ValueError("Aria2c exited with code {}".format(aria))

        if disable_proxy:
            holder.enable()

    def aria2c_download(self, commands, extra_commands, disable_proxy=False):
        LogFile = self.bin["aria2c"].replace("exe", "log")

        if os.path.isfile(LogFile):
            os.remove(LogFile)

        aria2_commands = []
        aria2_commands.append(self.bin["aria2c"])
        aria2_commands.append("--log={}".format(LogFile))
        aria2_commands += commands + extra_commands

        holder = hold_proxy()

        if disable_proxy:
            holder.disable()

        try:
            aria = subprocess.call(aria2_commands)
        except FileNotFoundError:
            self.logger.info("UNABLE TO FIND {}".format("aria2c.exe"))
            exit(-1)
        if aria != 0:
            self.logger.info("Aria2c exited with code {}".format(aria))
            exit(-1)

        if disable_proxy:
            holder.enable()

        self.logger.info()

    def isduplelist(self, a, b):
        return set(a) == set(b) and len(a) == len(b)

    def readfile(self, file, lines=False):
        read = ""
        if os.path.isfile(file):
            with open(file, "r") as f:
                if lines:
                    read = f.readlines()
                    return read
            read = f.read()
        else:
            self.logger.info("File: %s, is not found" % file)
            return None

        return read

    def strip(self, inputint, left=True, right=False):
        if left:
            return str(inputint.lstrip("0"))
        if right:
            return str(inputint.rstrip("0"))

        return

    def CleanMyFileNamePlease(self, filename):
        # edit here...
        filename = filename.replace("666", "666")

        ################################################################################################################################
        # dont edit here...
        filename = (
            filename.replace(" ", ".")
            .replace("'", "")
            .replace(",", "")
            .replace("-", "")
            .replace("-.", ".")
            .replace(".-.", ".")
        )
        filename = re.sub(" +", ".", filename)
        for i in range(10):
            filename = re.sub(r"(\.\.)", ".", filename)

        return filename

    def RemoveExtraWords(self, name):
        if re.search("[eE]pisode [0-9]+", name):
            name = name.replace((re.search("[eE]pisode [0-9]+", name)).group(0), "")

        if re.search(r"(\(.+?)\)", name):
            name = name.replace(re.search(r"(\(.+?)\)", name).group(), "")

        name = re.sub(" +", " ", name)
        name = name.strip()
        name = (
            name.replace(" : ", " - ")
            .replace(": ", " - ")
            .replace(":", " - ")
            .replace("&", "and")
            .replace("ÃƒÂ³", "o")
            .replace("*", "x")
        )

        return name

    def DecodeString(self, text):
        for encoding in ("utf-8-sig", "utf-8", "utf-16"):
            try:
                return text.decode(encoding)
            except UnicodeDecodeError:
                continue

        return text.decode("latin-1")

    def EncodeString(self, text):
        for encoding in ("utf-8-sig", "utf-8", "utf-16"):
            try:
                return text.encode(encoding)
            except UnicodeDecodeError:
                continue

        return text.encode("latin-1")

    def clean_text(self, text):
        whitelist = (
            "-_.() %s%s" % (string.ascii_letters, string.digits) + "',&#$%@`~!^&+=[]{}"
        )

        cleaned_text = (
            unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode()
        )

        return "".join(c for c in cleaned_text if c in whitelist)

    def RemoveCharcters(self, text):
        text = self.EncodeString(text)
        text = self.DecodeString(text)
        text = self.RemoveExtraWords(text)
        text = self.clean_text(text)
        text = unidecode.unidecode(titlecase(text))

        return text

    def do_clean(self, contain, exclude=[], added=[]):
        """contain= string name in the file/files you want to delete.
           exclude= the files that has a specified extension you do not want to delete. send by list like ['.sfv', '.whatever']
           added= another extensions not in the default extension. send by list like ['.sfv', '.whatever']"""

        error = []
        extensions = [
            ".mp4",
            ".h265",
            ".h264",
            ".eac3",
            ".m4a",
            ".ac3",
            ".srt",
            ".vtt",
            ".txt",
            ".aac",
            ".m3u8",
            ".mpd",
        ]

        extensions += added

        erased_files = []

        for ext in extensions:
            if ext not in exclude:
                erased_files += glob.glob(contain + f"*{ext}")

        if not erased_files == []:
            for files in erased_files:
                try:
                    os.remove(files)
                except Exception:
                    error.append(files)

        if not error == []:
            self.logger.info(
                f"some files not deleted with extensions: "
                + ", ".join(str(x) for x in error)
                + "."
            )

        return

    def mediainfo_(self, file):
        mediainfo_output = subprocess.Popen(
            [self.bin["MediaInfo"], "--Output=JSON", "-f", file],
            stdout=subprocess.PIPE,
        )
        mediainfo_json = json.load(mediainfo_output.stdout)
        return mediainfo_json

    def DemuxAudio(self, inputName, replace_str):
        if os.path.isfile(inputName):
            self.logger.info("\nDemuxing audio...")
            mediainfo = self.mediainfo_(inputName)
            for m in mediainfo["media"]["track"]:
                if m["@type"] == "Audio":
                    codec_name = m["Format"]

            ext = ".ac3"
            if codec_name == "AAC":
                ext = ".m4a"
            else:
                if codec_name == "E-AC-3":
                    ext = ".eac3"
                else:
                    if codec_name == "AC-3":
                        ext = ".ac3"
                    if codec_name == "DTS":
                        ext = ".dts"

            outputName = inputName.replace(replace_str, ext)
            self.logger.info(("{} -> {}").format(inputName, outputName))
            ff = ffmpy.FFmpeg(
                executable=self.bin["ffmpeg"],
                inputs={inputName: None},
                outputs={outputName: "-c:a copy"},
                global_options="-vn -sn -y -hide_banner -loglevel panic",
            )
            ff.run()
            time.sleep(0.05)
            if os.path.isfile(outputName) and os.path.getsize(outputName) > 1024 * 1024:
                os.remove(inputName)
            self.logger.info("Done!")

        return

    def shaka_decrypt(self, encrypted, decrypted, keys, stream):
        self.logger.info("\nDecrypting: {}".format(encrypted))
        decrypt_command = [
            self.bin["shaka-packager"],
            "--enable_raw_key_decryption",
            "-quiet",
            "input={},stream={},output={}".format(encrypted, stream, decrypted),
        ]

        for key in keys:
            decrypt_command.append("--keys")
            decrypt_command.append(
                "key={}:key_id={}".format(
                    key["KEY"], "00000000000000000000000000000000"
                )
            )

        self.logger.info("\nDecrypting KEYS: ")
        for key in keys:
            self.logger.info(("{}:{}".format(key["KID"], key["KEY"])))

        wvdecrypt_process = subprocess.Popen(decrypt_command)
        stdoutdata, stderrdata = wvdecrypt_process.communicate()
        wvdecrypt_process.wait()
        self.logger.info("Done!")

        return True

    def mp4_decrypt(
        self,
        encrypted,
        decrypted,
        keys,
        moded_decrypter=True,
        no_kid=True,
        silent=False,
    ):
        self.logger.info("\nDecrypting: {}".format(encrypted))
        decrypt_command = [
            self.bin["mp4decrypt"]
            if not moded_decrypter
            else self.bin["mp4decrypt_moded"]
        ]
        decrypt_command += ["--show-progress", encrypted, decrypted]

        for key in keys:
            decrypt_command.append("--key")
            decrypt_command.append(
                "{}:{}".format(key["ID"] if no_kid else key["KID"], key["KEY"])
            )

        self.logger.info("\nDecrypting KEYS: ")
        for key in keys:
            self.logger.info(
                ("{}:{}".format(key["ID"] if no_kid else key["KID"], key["KEY"]))
            )

        if silent:
            wvdecrypt_process = subprocess.Popen(
                decrypt_command, stdout=open(os.devnull, "wb")
            )
        else:
            wvdecrypt_process = subprocess.Popen(decrypt_command)

        stdoutdata, stderrdata = wvdecrypt_process.communicate()
        wvdecrypt_process.wait()
        if wvdecrypt_process.returncode == 0:
            self.logger.info("Done!")
            return True

        return False

    def DemuxVideo(
        self,
        outputVideoTemp,
        outputVideo,
        ffmpeg=False,
        mp4box=False,
        ffmpeg_version="ffmpeg",
    ):
        if ffmpeg:
            self.logger.info("\nRemuxing video...")
            # if not outputVideo.endswith(".h264"):
            #     os.rename(outputVideoTemp, outputVideo)
            #     self.logger.info("Done!")
            #     return True

            ff = ffmpy.FFmpeg(
                executable=self.bin[ffmpeg_version],
                inputs={outputVideoTemp: None},
                outputs={outputVideo: "-c copy"},
                global_options="-y -hide_banner -loglevel panic",
            ).run()
            time.sleep(0.05)
            if (
                os.path.isfile(outputVideo)
                and os.path.getsize(outputVideo) > 1024 * 1024
            ):
                os.remove(outputVideoTemp)
            self.logger.info("Done!")
            return True

        if mp4box:
            self.logger.info("\nRemuxing video...")
            if not outputVideo.endswith(".h264"):
                os.rename(outputVideoTemp, outputVideo)
                self.logger.info("Done!")
                return True

            subprocess.call(
                [
                    self.bin["mp4box"],
                    "-quiet",
                    "-raw",
                    "1",
                    "-out",
                    outputVideo,
                    outputVideoTemp,
                ]
            )
            if (
                os.path.isfile(outputVideo)
                and os.path.getsize(outputVideo) > 1024 * 1024
            ):
                os.remove(outputVideoTemp)
            self.logger.info("Done!")
            return True

        return False
