import os
import shutil
import subprocess
import sys
import re
import logging
from configs.config import tool
from helpers.ripprocess import ripprocess


class aria2Error(Exception):
    pass


class aria2_moded:
    def __init__(self, aria2_download_command):
        self.logger = logging.getLogger(__name__)
        self.aria2_download_command = aria2_download_command
        self.env = self.aria2DisableProxies()
        self.ripprocess = ripprocess()
        self.tool = tool()
        self.LOGA_PATH = self.tool.paths()["LOGA_PATH"]
        self.bin = self.tool.bin()
        self.aria2c_exe = self.bin["aria2c"]
        self.last_message_printed = 0
        self.speed_radar = "0kbps"

    def aria2DisableProxies(self):
        env = os.environ.copy()

        if env.get("http_proxy"):
            del env["http_proxy"]

        if env.get("HTTP_PROXY"):
            del env["HTTP_PROXY"]

        if env.get("https_proxy"):
            del env["https_proxy"]

        if env.get("HTTPS_PROXY"):
            del env["HTTPS_PROXY"]

        return env

    def read_stdout(self, line):
        speed = re.search(r"DL:(.+?)ETA", line)
        eta = re.search(r"ETA:(.+?)]", line)
        connection = re.search(r"CN:(.+?)DL", line)
        percent = re.search(r"\((.*?)\)", line)
        size = re.search(r" (.*?)/(.*?)\(", line)

        if speed and eta and connection and percent and size:
            percent = percent.group().strip().replace(")", "").replace("(", "")
            size = size.group().strip().replace(")", "").replace("(", "")
            complete, total = size.split("/")
            connection = connection.group(1).strip()
            eta = eta.group(1).strip()
            speed = speed.group(1).strip()
            self.speed_radar = speed

            stdout_data = {
                "percent": str(percent),
                "size": str(total),
                "complete": str(complete),
                "total": str(total),
                "connection": str(connection),
                "eta": str(eta),
                "speed": str(speed),
            }

            return stdout_data

        return None

    def if_errors(self, line):
        if "exception" in str(line).lower() or "errorcode" in str(line).lower():
            return line
        return None

    def delete_last_message_printed(self):
        print(" " * len(str(self.last_message_printed)), end="\r")

    def get_status(self, stdout_data: dict):
        return "Aria2c_Status; Size: {Size} | Speed: {Speed} | ETA: {ETA} | Progress: {Complete} -> {Total} ({Percent})".format(
            Size=stdout_data.get("size"),
            Speed=stdout_data.get("speed"),
            ETA=stdout_data.get("eta"),
            Complete=stdout_data.get("complete"),
            Total=stdout_data.get("total"),
            Percent=stdout_data.get("percent"),
        )

    def is_download_completed(self, line):
        if "(ok):download completed." in str(line).lower():
            return "Download completed: (OK) ({}\\s)".format(self.speed_radar)
        return None

    def start_download(self):
        proc = subprocess.Popen(
            self.aria2_download_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            env=self.env,
        )

        check_errors = True
        for line in getattr(proc, "stdout"):
            if check_errors:
                if self.if_errors(line):
                    raise aria2Error("Aria2c Error {}".format(self.if_errors(line)))
            check_errors = False
            stdout_data = self.read_stdout(line)
            if stdout_data:
                status_text = self.get_status(stdout_data)
                self.delete_last_message_printed()
                print(status_text, end="\r", flush=True)
                self.last_message_printed = status_text
            else:
                download_finished = self.is_download_completed(line)
                if download_finished:
                    self.delete_last_message_printed()
                    print(download_finished, end="\r", flush=True)
                    self.last_message_printed = download_finished
        self.logger.info("")
        return


class aria2:
    def __init__(self,):
        self.env = self.aria2DisableProxies()
        self.ripprocess = ripprocess()
        self.tool = tool()
        self.bin = self.tool.bin()
        self.LOGA_PATH = self.tool.paths()["LOGA_PATH"]
        self.config = self.tool.aria2c()
        self.aria2c_exe = self.bin["aria2c"]
        self.logger = logging.getLogger(__name__)

    def convert_args(self, arg):
        if arg is True:
            return "true"
        elif arg is False:
            return "false"
        elif arg is None:
            return "none"
        else:
            return str(arg)

    def append_commands(self, command, option_define, option):
        if option == "skip":
            return []

        return ["{}{}".format(option_define, option)]

    def append_two_commands(self, command, cmd1, cmd2):
        if cmd2 == "skip":
            return []

        return [cmd1] + [cmd2]

    def aria2Options(
        self,
        allow_overwrite=True,
        file_allocation=None,
        auto_file_renaming=False,
        async_dns=False,
        retry_wait=5,
        summary_interval=0,
        enable_color=False,
        connection=16,
        concurrent_downloads=16,
        split=16,
        header="skip",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36",
        uri_selector="inorder",
        console_log_level="skip",
        download_result="hide",
        quiet="false",
        extra_commands=[],
    ):

        options = [] + extra_commands
        allow_overwrite = self.convert_args(allow_overwrite)
        quiet = self.convert_args(quiet)
        file_allocation = self.convert_args(file_allocation)
        auto_file_renaming = self.convert_args(auto_file_renaming)
        async_dns = self.convert_args(async_dns)
        retry_wait = self.convert_args(retry_wait)
        enable_color = self.convert_args(enable_color)
        connection = self.convert_args(connection)
        concurrent_downloads = self.convert_args(concurrent_downloads)
        split = self.convert_args(split)
        header = self.convert_args(header)
        uri_selector = self.convert_args(uri_selector)
        console_log_level = self.convert_args(console_log_level)
        download_result = self.convert_args(download_result)

        ##############################################################################

        options += self.append_commands(options, "--allow-overwrite=", allow_overwrite)
        options += self.append_commands(options, "--quiet=", quiet)
        options += self.append_commands(options, "--file-allocation=", file_allocation)
        options += self.append_commands(
            options, "--auto-file-renaming=", auto_file_renaming
        )
        options += self.append_commands(options, "--async-dns=", async_dns)
        options += self.append_commands(options, "--retry-wait=", retry_wait)
        options += self.append_commands(options, "--enable-color=", enable_color)

        options += self.append_commands(
            options, "--max-connection-per-server=", connection
        )

        options += self.append_commands(
            options, "--max-concurrent-downloads=", concurrent_downloads
        )
        options += self.append_commands(options, "--split=", split)
        options += self.append_commands(options, "--header=", header)
        options += self.append_commands(options, "--uri-selector=", uri_selector)
        options += self.append_commands(
            options, "--console-log-level=", console_log_level
        )
        options += self.append_commands(options, "--download-result=", download_result)

        return options

    def aria2DisableProxies(self):
        env = os.environ.copy()

        if env.get("http_proxy"):
            del env["http_proxy"]

        if env.get("HTTP_PROXY"):
            del env["HTTP_PROXY"]

        if env.get("https_proxy"):
            del env["https_proxy"]

        if env.get("HTTPS_PROXY"):
            del env["HTTPS_PROXY"]

        return env

    def aria2DownloadUrl(self, url, output, options, debug=False, moded=False):
        self.debug = debug
        aria2_download_command = [self.aria2c_exe] + options

        if self.config["enable_logging"]:
            LogFile = os.path.join(self.LOGA_PATH, output.replace(".mp4", ".log"))
            if os.path.isfile(LogFile):
                os.remove(LogFile)
            aria2_download_command.append("--log={}".format(LogFile))

        if not url.startswith("http"):
            raise aria2Error("Url does not start with http/https: {}".format(url))

        aria2_download_command.append(url)
        aria2_download_command += self.append_two_commands(
            aria2_download_command, "-o", output
        )

        self.aria2Debug("Sending Commands to aria2c...")
        self.aria2Debug(aria2_download_command)
        self.logger.debug("aria2_download_command: {}".format(aria2_download_command))

        if moded:
            aria2_moded_download = aria2_moded(aria2_download_command)
            aria2_moded_download.start_download()
        else:
            try:
                aria = subprocess.call(aria2_download_command, env=self.env)
            except FileNotFoundError:
                self.logger.info("UNABLE TO FIND {}".format(self.aria2c_exe))
                exit(-1)
            if aria != 0:
                raise aria2Error("Aria2c exited with code {}".format(aria))

        return

    def aria2DownloadDash(
        self, segments, output, options, debug=False, moded=False, fixbytes=False
    ):
        self.debug = debug
        aria2_download_command = [self.aria2c_exe] + options

        if self.config["enable_logging"]:
            LogFile = os.path.join(self.LOGA_PATH, output.replace(".mp4", ".log"))
            if os.path.isfile(LogFile):
                os.remove(LogFile)
            aria2_download_command.append("--log={}".format(LogFile))

        if not isinstance(segments, list) or segments == []:
            raise aria2Error("invalid list of urls: {}".format(segments))

        if moded:
            raise aria2Error("moded version not supported for dash downloads atm...")

        txt = output.replace(".mp4", ".txt")
        folder = output.replace(".mp4", "")
        segments = list(dict.fromkeys(segments))

        if os.path.exists(folder):
            shutil.rmtree(folder)
        if not os.path.exists(folder):
            os.makedirs(folder)

        segments_location = []

        opened_txt = open(txt, "w+")
        for num, url in enumerate(segments, start=1):
            segment_name = str(num).zfill(5) + ".mp4"
            segments_location.append(os.path.join(*[os.getcwd(), folder, segment_name]))
            opened_txt.write(url + f"\n out={segment_name}" + f"\n dir={folder}" + "\n")
        opened_txt.close()

        aria2_download_command += self.append_commands(
            aria2_download_command, "--input-file=", txt
        )

        try:
            aria = subprocess.call(aria2_download_command, env=self.env)
        except FileNotFoundError:
            self.logger.info("UNABLE TO FIND {}".format(self.aria2c_exe))
            exit(-1)
        if aria != 0:
            raise aria2Error("Aria2c exited with code {}".format(aria))

        self.logger.info("\nJoining files...")
        openfile = open(output, "wb")
        total = int(len(segments_location))
        for current, fragment in enumerate(segments_location):
            if os.path.isfile(fragment):
                if fixbytes:
                    with open(fragment, "rb") as f:
                        wvdll = f.read()
                    if (
                        re.search(
                            b"tfhd\x00\x02\x00\x1a\x00\x00\x00\x01\x00\x00\x00\x02",
                            wvdll,
                            re.MULTILINE | re.DOTALL,
                        )
                        is not None
                    ):
                        fw = open(fragment, "wb")
                        m = re.search(
                            b"tfhd\x00\x02\x00\x1a\x00\x00\x00\x01\x00\x00\x00",
                            wvdll,
                            re.MULTILINE | re.DOTALL,
                        )
                        segment_fixed = (
                            wvdll[: m.end()] + b"\x01" + wvdll[m.end() + 1 :]
                        )
                        fw.write(segment_fixed)
                        fw.close()
                shutil.copyfileobj(open(fragment, "rb"), openfile)
                os.remove(fragment)
                self.ripprocess.updt(total, current + 1)
        openfile.close()

        if os.path.isfile(txt):
            os.remove(txt)
        if os.path.exists(folder):
            shutil.rmtree(folder)

    def aria2Debug(self, txt):
        if self.debug:
            self.logger.info(txt)
