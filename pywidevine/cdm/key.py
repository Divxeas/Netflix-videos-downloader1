# uncompyle6 version 3.3.2
# Python bytecode 3.6 (3379)
# Decompiled from: Python 3.7.3 (v3.7.3:ef4ec6ed12, Mar 25 2019, 22:22:05) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: pywidevine\cdm\key.py
import binascii

class Key:

    def __init__(self, kid, type, key, permissions=[]):
        self.kid = kid
        self.type = type
        self.key = key
        self.permissions = permissions

    def __repr__(self):
        if self.type == 'OPERATOR_SESSION':
            return ('key(kid={}, type={}, key={}, permissions={})').format(self.kid, self.type, binascii.hexlify(self.key), self.permissions)
        else:
            return ('key(kid={}, type={}, key={})').format(self.kid, self.type, binascii.hexlify(self.key))