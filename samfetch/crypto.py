# Copyright (C) 2022 ysfchn
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

__all__ = [
    "decrypt_iterator",
    "Crypto"
]

import base64
from typing import Any, AsyncIterator, Generator, Optional, Tuple
from Crypto.Cipher import AES


# has_next() function
# https://stackoverflow.com/a/67428657
# Licensed with CC BY-SA 4.0
async def has_next(it) -> Generator[Tuple[bool, Any], None, None]:
    first = True
    async for e in it:
        if not first:
            yield True, prev
        else:
            first = False
        prev = e
    if not first:
        yield False, prev


async def decrypt_iterator(iterator : AsyncIterator, key : Optional[bytes] = None) -> Generator[bytes, None, None]:
    if key:
        cipher = AES.new(key, AES.MODE_ECB)
        async for continues, chunk in has_next(iterator):
            # Decrypt chunk
            data = cipher.decrypt(chunk)
            if continues:
                yield data
            else:
                yield Crypto.unpad(data)
    else:
        async for i in iterator:
            yield i


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