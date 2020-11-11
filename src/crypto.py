import base64
from Crypto.Cipher import AES

class Crypto:
    # Crypto keys
    KEY_1 = "hqzdurufm2c8mf6bsjezu1qgveouv7c7"
    KEY_2 = "w13r4cvf4hctaujv"

    unpad = lambda d: d[:-d[-1]]
    pad = lambda d: d + bytes([16 - (len(d) % 16)]) * (16 - (len(d) % 16))

    @staticmethod   
    def aes_encrypt(inp, key):
        cipher = AES.new(key, AES.MODE_CBC, key[:16])
        return cipher.encrypt(Crypto.pad(inp))

    @staticmethod
    def aes_decrypt(inp, key):
        cipher = AES.new(key, AES.MODE_CBC, key[:16])
        return Crypto.unpad(cipher.decrypt(inp))

    @staticmethod
    def get_fkey(inp):
        key = ""
        for i in range(16):
            key += Crypto.KEY_1[inp[i]]
        key += Crypto.KEY_2
        return key.encode()

    @staticmethod
    def get_auth(nonce : str) -> str:
        keydata = [ord(c) % 16 for c in nonce]
        fkey = Crypto.get_fkey(keydata)
        return base64.b64encode(Crypto.aes_encrypt(nonce.encode(), fkey)).decode()

    @staticmethod
    def decrypt_nonce(inp):
        nonce = Crypto.aes_decrypt(base64.b64decode(inp), Crypto.KEY_1.encode()).decode()
        return nonce