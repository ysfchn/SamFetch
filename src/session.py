from typing import Any
import hashlib

from src.crypto import Crypto
from fastapi import HTTPException
from requests import Response

class Session:
    """
    A custom session object that holds the session ID and nonce that came from Kies servers.
    """

    def __init__(
        self, 
        encrypted_nonce : str, 
        session_id : str = None
    ) -> None:
        self.session_id = session_id
        self.encrypted_nonce = encrypted_nonce
        if not self.encrypted_nonce:
            raise HTTPException(401, "Something went wrong with authorization. This is related to Kies servers, not you.")


    @property
    def nonce(self) -> str:
        return Crypto.decrypt_nonce(self.encrypted_nonce)

    
    @property
    def auth(self) -> str:
        return Crypto.get_auth(self.nonce)


    @classmethod
    def from_dict(cls, data : dict) -> "Session":
        return cls(data.get("encrypted_nonce"), data.get("session_id"))
    
    
    @classmethod
    def from_response(cls, response : Response) -> "Session":
        return cls(response.headers.get("NONCE"), response.cookies.get("JSESSIONID"))

    
    def to_dict(self) -> dict:
        return {
            "encrypted_nonce": self.encrypted_nonce,
            "session_id": self.session_id
        }

    
    def logic_check(self, firmware : str) -> str:
        return Session.custom_logic_check(firmware, self.nonce)


    @staticmethod
    def custom_logic_check(firmware : str, nonce : str) -> str:
        if len(firmware) < 16:
            raise HTTPException(412, "Logic check has failed, firmware text must be longer than 16.")
        out = ""
        for c in nonce:
            out += firmware[ord(c) & 0xf]
        return out


    def refresh_session(self, response : Response) -> None:
        if response.headers.get("NONCE", None):
            self.encrypted_nonce = response.headers.get("NONCE")
        if "JSESSIONID" in response.cookies:
            self.session_id = response.cookies["JSESSIONID"]


    def getv4key(self, fw_ver, logic_value) -> bytes:
        return hashlib.md5(Session.custom_logic_check(fw_ver, logic_value).encode()).digest()


    def getv2key(self, version, model, region) -> bytes:
        return hashlib.md5(f"{region}:{model}:{version}".encode()).digest()