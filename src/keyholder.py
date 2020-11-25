from typing import Any
import hashlib

from src.crypto import Crypto
from fastapi import HTTPException
from requests import Response

class Keyholder:
    def __init__(self, encrypted_nonce : str, session_id : str = "") -> None:
        self.session_id = session_id
        self.encrypted_nonce = encrypted_nonce
        self.nonce = ""
        self.auth = ""
        if self.encrypted_nonce:
            self.nonce = Crypto.decrypt_nonce(self.encrypted_nonce)
            self.auth = Crypto.get_auth(self.nonce)
        else:
            raise HTTPException(401, "Something went wrong with authorization. This is related to Kies servers, not you.")

    @staticmethod
    def from_dict(keyholder : dict) -> Any:
        k = Keyholder(keyholder.get("encrypted_nonce", ""), keyholder.get("session_id"))
        return k

    @staticmethod
    def from_response(response : Response) -> Any:
        k = Keyholder(response.headers.get("NONCE"), response.cookies.get("JSESSIONID"))
        return k

    def logic_check(self, firmware : str, custom_nonce : str = None) -> str:
        if len(firmware) < 16:
            raise HTTPException(412, "Logic check has failed, firmware text must be longer than 16.")
        out = ""
        for c in custom_nonce if custom_nonce else self.nonce:
            out += firmware[ord(c) & 0xf]
        return out

    def refresh_keyholder(self, response : Response) -> None:
        if response.headers.get("NONCE", None):
            self.encrypted_nonce = response.headers.get("NONCE")
            self.nonce = Crypto.decrypt_nonce(self.encrypted_nonce)
            self.auth = Crypto.get_auth(self.nonce)
        if "JSESSIONID" in response.cookies:
            self.session_id = response.cookies["JSESSIONID"]

    def to_dict(self) -> dict:
        keyholder = {
            "encrypted_nonce": self.encrypted_nonce,
            "session_id": self.session_id
        }
        return keyholder

    def getv4key(self, fw_ver, logic_value) -> bytes:
        deckey = self.logic_check(fw_ver, logic_value)
        return hashlib.md5(deckey.encode()).digest()

    def getv2key(self, version, model, region) -> bytes:
        deckey = region + ":" + model + ":" + version
        return hashlib.md5(deckey.encode()).digest()