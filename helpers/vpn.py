import os
import requests
import sys
import random
import logging

class connect(object):
    def __init__(self, code):
        self.code = code.lower()
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36"
        }

    def nordVPN(self):
        nordvpn_codes = {
            "al": "2",
            "ar": "10",
            "au": "13",
            "at": "14",
            "be": "21",
            "ba": "27",
            "br": "30",
            "bg": "33",
            "ca": "38",
            "cl": "43",
            "cr": "52",
            "hr": "54",
            "cy": "56",
            "cz": "57",
            "dk": "58",
            "eg": "64",
            "ee": "68",
            "fi": "73",
            "fr": "74",
            "ge": "80",
            "de": "81",
            "gr": "84",
            "hk": "97",
            "hu": "98",
            "is": "99",
            "in": "100",
            "id": "101",
            "ie": "104",
            "il": "105",
            "it": "106",
            "jp": "108",
            "lv": "119",
            "lu": "126",
            "my": "131",
            "mx": "140",
            "md": "142",
            "nl": "153",
            "nz": "156",
            "mk": "128",
            "no": "163",
            "ro": "179",
            "pl": "174",
            "si": "197",
            "za": "200",
            "kr": "114",
            "rs": "192",
            "sg": "195",
            "sk": "196",
            "es": "202",
            "se": "208",
            "ch": "209",
            "tw": "211",
            "th": "214",
            "tr": "220",
            "ua": "225",
            "ae": "226",
            "gb": "227",
            "us": "228",
            "vn": "234",
            "uk": "227",
        }
        nord_proxy = {}
        if nordvpn_codes.get(self.code):
            resp = requests.get(
                url="https://nordvpn.com/wp-admin/admin-ajax.php?action=servers_recommendations&filters={%22country_id%22:"
                + nordvpn_codes.get(self.code)
                + "}",
                headers=self.headers,
            )
            nord_proxy = resp.json()[0]["hostname"]
        else:
            self.logger.info(
                self.code
                + " : not listed in country codes, read country.doc for more info"
            )

        return nord_proxy

    def load_privatevpn(self):
        html_file = "html.html"
        hosts = []
        resp = requests.get(
            "https://privatevpn.com/serverlist/", stream=True, headers=self.headers
        )
        resp = str(resp.text)
        resp = resp.replace("<br>", "")

        with open(html_file, "w", encoding="utf8") as file:
            file.write(resp)

        with open(html_file, "r") as file:
            text = file.readlines()

        if os.path.exists(html_file):
            os.remove(html_file)

        for p in text:
            if ".pvdata.host" in p:
                hosts.append(p.strip())

        return hosts

    def privateVPN(self):
        private_proxy = {}
        private_hosts = self.load_privatevpn()
        self.logger.debug("private_hosts: {}".format(private_hosts))
        search_host = [host for host in private_hosts if host[:2] == self.code]
        if not search_host == []:
            self.logger.info(f"Founded {str(len(search_host))} Proxies")
            for n, p in enumerate(search_host):
                self.logger.info(f"[{str(n+1)}] {p}")
            inp = input("\nEnter Proxy Number, or Hit Enter for random one: ").strip()
            if inp == "":
                return random.choice(search_host)
            private_proxy = search_host[int(inp) - 1]
        else:
            self.logger.info(f"no Proxies Found, you may entered wrong code, or search failed!...")

        return private_proxy
