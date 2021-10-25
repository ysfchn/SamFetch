__all__ = [
    "Session"
]

import hashlib
from samfetch.crypto import Crypto
from httpx import Response

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
            raise Exception(
                "Something went wrong with authorization. " + \
                "This is probably related to Kies servers or Samfetch itself, " + \
                "you can try creating an issue on the repository."
            )

    @property
    def nonce(self) -> str:
        return Crypto.decrypt_nonce(self.encrypted_nonce)

    @property
    def auth(self) -> str:
        return Crypto.get_auth(self.nonce)

    @classmethod
    def from_response(cls, response : Response) -> "Session":
        return cls(response.headers.get("NONCE"), response.cookies.get("JSESSIONID"))

    @staticmethod
    def custom_logic_check(firmware : str, nonce : str) -> str:
        if len(firmware) < 16:
            raise Exception("Logic check has failed, firmware text must be longer than 16.")
        out = ""
        for c in nonce:
            out += firmware[ord(c) & 0xf]
        return out

    def logic_check(self, firmware : str) -> str:
        return Session.custom_logic_check(firmware, self.nonce)

    def refresh_session(self, response : Response) -> None:
        """
        Update session object from a Response object.
        """
        if response.headers.get("NONCE", None):
            self.encrypted_nonce = response.headers.get("NONCE")
        if "JSESSIONID" in response.cookies:
            self.session_id = response.cookies["JSESSIONID"]

    def getv4key(self, fw_ver, logic_value) -> bytes:
        return hashlib.md5(Session.custom_logic_check(fw_ver, logic_value).encode()).digest()

    def getv2key(self, version, model, region) -> bytes:
        return hashlib.md5(f"{region}:{model}:{version}".encode()).digest()