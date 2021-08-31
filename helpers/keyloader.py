import os, json, sys
from helpers.ripprocess import ripprocess


class keysaver:
    def __init__(self, **kwargs):
        self.keys_file = kwargs.get("keys_file", None)
        self.stored = self.get_stored()

    def read_(self):
        with open(self.keys_file, "r") as fr:
            return json.load(fr)

    def write_(self, data):
        with open(self.keys_file, "w") as fr:
            fr.write(json.dumps(data, indent=4))

    def get_stored(self):
        stored = []
        if os.path.isfile(self.keys_file):
            return self.read_()
        return stored

    def formatting(self, keys_list, pssh, name):
        return [
            {
                "NAME": name,
                "PSSH": pssh,
                "ID": idx,
                "KID": key.split(":")[0],
                "KEY": key.split(":")[1],
            }
            for idx, key in enumerate(keys_list, start=1)
        ]

    def dump_keys(self, keys, pssh=None, name=None):
        old_keys = list(self.stored)
        new_keys = list(self.formatting(keys, pssh, name))
        self.write_(old_keys + new_keys)
        self.stored = self.get_stored()  # to update stored keys

        return new_keys

    def get_key_by_pssh(self, pssh):
        keys = []
        added = set()
        for key in self.get_stored():  # read file again...
            if key["PSSH"]:
                if not key["KEY"] in added and pssh in key["PSSH"]:
                    keys.append(key)
                    added.add(key["KEY"])

        return keys

    def get_key_by_kid(self, kid):
        keys = []
        added = set()
        for key in self.get_stored():  # read file again...
            if not key["KEY"] in added and key["KID"] == kid:
                keys.append(key)
                added.add(key["KEY"])

        return keys

    def generate_kid(self, encrypted_file):
        return ripprocess().getKeyId(encrypted_file)

    def set_keys(self, keys, no_kid=False):
        command_keys = []
        for key in keys:
            command_keys.append("--key")
            command_keys.append(
                "{}:{}".format(key["ID"] if no_kid else key["KID"], key["KEY"])
            )

        return command_keys
