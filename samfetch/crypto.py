__all__ = [
    "Decryptor",
    "Crypto"
]

import base64
from typing import AsyncIterator
from Crypto.Cipher import AES
import httpx


class Decryptor:
    """
    A custom iterator to decrypt the bytes without writing the whole file to the disk 
    for downloading firmwares.
    """

    def __init__(self, iterator : AsyncIterator, key : bytes):
        self.iterator : AsyncIterator = iterator
        # We need to unpad (basically, do extra operation) the last chunk,
        # so we need to learn when will the iterator end. As 
        # Because of that, we hold next chunks and return the previous chunk to user.
        self.chunks = [None, None]
        # [ X, Y ]
        # X - The future chunk
        # Y - Will be sent to user (always comes from 1 step behind)
        self.cipher = AES.new(key, AES.MODE_ECB)

    async def __aiter__(self):
        return self

    async def move(self):
        chunk = await self.iterator.__anext__()
        self.chunks = [chunk, self.chunks[0]]

    @property
    def is_end(self) -> bool:
        return self.chunks[0] == None 

    @property
    def is_start(self) -> bool:
        return self.chunks[1] == None

    @property
    def is_end_exceed(self) -> bool:
        return self.chunks[0] == None and self.chunks[1] == None

    async def __anext__(self):
        # Get the current chunk.
        current = self.chunks[1]
        returned = None
        # Check if ending point exceed.
        if self.is_end_exceed:
            raise StopAsyncIteration
        # Check if the chunk is starting point.
        if self.is_start:
            self.chunks = [await self.iterator.__anext__(), None]
            returned = bytes(0)
        # Check if the chunk is ending point.
        elif self.is_end:
            returned = Crypto.unpad(self.cipher.decrypt(current)) + bytes([0] * 10)
        else:
            returned = self.cipher.decrypt(current)
        # Shift to the next chunk and keep the previous one.
        await self.move()
        return returned


# Source:
# https://github.com/nlscc/samloader/blob/2dffa310a144eebe579032e213469d7595277432/samloader/auth.py
class Crypto:
    """
    Provides functions for decrypting Kies data.
    """

    # Crypto keys
    KEY_1 = "hqzdurufm2c8mf6bsjezu1qgveouv7c7"
    KEY_2 = "w13r4cvf4hctaujv"

    @staticmethod
    def unpad(inp):
        return inp[:-inp[-1]]

    @staticmethod
    def pad(inp):
        return inp + bytes([16 - (len(inp) % 16)]) * (16 - (len(inp) % 16))

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
    def get_auth(nonce: str) -> str:
        keydata = [ord(c) % 16 for c in nonce]
        fkey = Crypto.get_fkey(keydata)
        return base64.b64encode(Crypto.aes_encrypt(nonce.encode(), fkey)).decode()

    @staticmethod
    def decrypt_nonce(inp: str):
        nonce = Crypto.aes_decrypt(base64.b64decode(inp), Crypto.KEY_1.encode()).decode()
        return nonce