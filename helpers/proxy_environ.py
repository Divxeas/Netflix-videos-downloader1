import os
import requests
import sys, json
import random
from configs.config import tool
from helpers.vpn import connect
import logging


class hold_proxy(object):
    def __init__(self):
        self.proxy = os.environ.get("http_proxy")
        self.logger = logging.getLogger(__name__)

    def disable(self):
        os.environ["http_proxy"] = ""
        os.environ["HTTP_PROXY"] = ""
        os.environ["https_proxy"] = ""
        os.environ["HTTPS_PROXY"] = ""

    def enable(self):
        if self.proxy:
            os.environ["http_proxy"] = self.proxy
            os.environ["HTTP_PROXY"] = self.proxy
            os.environ["https_proxy"] = self.proxy
            os.environ["HTTPS_PROXY"] = self.proxy


class proxy_env(object):
    def __init__(self, args):
        self.logger = logging.getLogger(__name__)
        self.args = args
        self.vpn = tool().vpn()

    def Load(self):
        proxies = None
        proxy = {}
        aria2c_proxy = []

        if self.vpn["proxies"]:
            proxies = self.vpn["proxies"]

        if not self.vpn["proxies"]:
            if self.args.privtvpn:
                self.logger.info("Proxy Status: Activated-PrivateVpn")
                proxy.update({"port": self.vpn["private"]["port"]})
                proxy.update({"user": self.vpn["private"]["email"]})
                proxy.update({"pass": self.vpn["private"]["passwd"]})

                if "pvdata.host" in self.args.privtvpn:
                    proxy.update({"host": self.args.privtvpn})
                else:
                    proxy.update(
                        {"host": connect(code=self.args.privtvpn).privateVPN()}
                    )

                proxies = self.vpn["private"]["http"].format(
                    email=proxy["user"],
                    passwd=proxy["pass"],
                    ip=proxy["host"],
                    port=proxy["port"],
                )
            else:
                if self.args.nordvpn:
                    self.logger.info("Proxy Status: Activated-NordVpn")
                    proxy.update({"port": self.vpn["nordvpn"]["port"]})
                    proxy.update({"user": self.vpn["nordvpn"]["email"]})
                    proxy.update({"pass": self.vpn["nordvpn"]["passwd"]})

                    if "nordvpn.com" in self.args.nordvpn:
                        proxy.update({"host": self.args.nordvpn})
                    else:
                        proxy.update(
                            {"host": connect(code=self.args.nordvpn).nordVPN()}
                        )

                    proxies = self.vpn["nordvpn"]["http"].format(
                        email=proxy["user"],
                        passwd=proxy["pass"],
                        ip=proxy["host"],
                        port=proxy["port"],
                    )
                else:
                    self.logger.info("Proxy Status: Off")

            if proxy.get("host"):
                aria2c_proxy.append(
                    "--https-proxy={}:{}".format(proxy.get("host"), proxy.get("port"))
                )
            if proxy.get("user"):
                aria2c_proxy.append("--https-proxy-user={}".format(proxy.get("user")))
            if proxy.get("pass"):
                aria2c_proxy.append("--https-proxy-passwd={}".format(proxy.get("pass")))

        if proxies:
            os.environ["http_proxy"] = proxies
            os.environ["HTTP_PROXY"] = proxies
            os.environ["https_proxy"] = proxies
            os.environ["HTTPS_PROXY"] = proxies

        ip = None

        try:
            self.logger.info("Getting IP...")
            r = requests.get("https://ipinfo.io/json", timeout=5)
            data = r.json()
            ip = f'{data["ip"]} ({data["country"]})'
        except Exception as e:
            self.logger.info(f"({e.__class__.__name__}: {e})")
            sys.exit(1)

        return aria2c_proxy, ip
