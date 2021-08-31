# uncompyle6 version 3.3.2
# Python bytecode 3.6 (3379)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: pywidevine\cdm\session.py


class Session:

    def __init__(self, session_id, init_data, device_config, offline):
        self.session_id = session_id
        self.init_data = init_data
        self.offline = offline
        self.device_config = device_config
        self.device_key = None
        self.session_key = None
        self.derived_keys = {'enc':None, 
         'auth_1':None, 
         'auth_2':None}
        self.license_request = None
        self.license = None
        self.service_certificate = None
        self.privacy_mode = False
        self.keys = []