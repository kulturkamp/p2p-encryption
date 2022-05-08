import logging
from crypto.RSA import RSA, oaep_unpad
from crypto.AES import AES, get_iv
from crypto.sha256 import sha256
import os

"""UTILITY FUNCTIONS"""

def list_to_bytes(lst):
    srt = ','.join(str(num) for num in lst)
    return srt.encode('utf-8')


def bytes_to_list(bts):
    srt = bts.decode('utf-8')
    return [int(s) for s in srt.split(',')]


def generate_sessionkey(l=32):
    return os.urandom(l)

def serialize_tuple(tup):
    return str(tup)[1:-1].replace(', ', '##')

def deserialize_tuple(ser_tup):
    tup = ser_tup.split('##')
    return (int(tup[0]), int(tup[1]))


"""CRYPTOGRAPHY INTERFACE"""

class crypto():
    def __init__(self, chatApp, session_key):
        self.chatApp = chatApp
        self.session_key = session_key
        self.rsa_obj = RSA(chatApp, 512)
        self.aes_obj = AES(session_key)
        self.serialised_public_ley = serialize_tuple(self.rsa_obj.public_key)
        #self.iv = get_iv()

    def encrypt_bytes(self, bts):
        iv = get_iv()
        enc_bts = self.aes_obj.encrypt(bts, iv)
        enc_skey = self.rsa_obj.oaep_encrypt(self.session_key, self.chatApp.peerPubKey)
        bts_hash = sha256(bts).hash()
        enc_hash = self.rsa_obj.oaep_encrypt(bts_hash, self.rsa_obj.private_key)

        return [iv, list_to_bytes(enc_skey), enc_bts, list_to_bytes(enc_hash)]

    def decrypt_bytes(self, bts):

        splitted = bts.split(b' ')
        iv, enc_skey, enc_bts, enc_hash = splitted
        enc_skey = bytes_to_list(enc_skey)
        enc_hash = bytes_to_list(enc_hash)

        dec_skey = oaep_unpad(self.rsa_obj.oaep_decrypt(enc_skey, self.rsa_obj.private_key))
        _aes = AES(dec_skey)
        dec_bts = _aes.decrypt(enc_bts, iv)
        dec_hash = oaep_unpad(self.rsa_obj.oaep_decrypt(enc_hash, self.chatApp.peerPubKey))


        my_hash = sha256(dec_bts).hash()

        if my_hash == dec_hash:
            return dec_bts
        else:
           # self.chatApp.sysMsg(f'no integryty but msg was: {dec_bts.decode()}')
            return b'Integrity is not secured!'


