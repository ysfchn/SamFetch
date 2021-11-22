__all__ = [
    "KiesDict",
    "KiesData",
    "KiesConstants",
    "KiesRequest",
    "KiesUtils",
    "KiesFirmwareList"
]

from collections import UserDict
from typing import List, Tuple, Dict, Any, Optional
import dicttoxml
import xmltodict
import re
import httpx
from samfetch.session import Session


class KiesFirmwareList:
    """
    Parses firmware list.
    """
    def __init__(self, data : Dict) -> None:
        self._data = data
        self._versions = None if ("versioninfo" not in self._data) else self._data["versioninfo"]["firmware"]["version"]

    @classmethod
    def from_xml(cls, xml : str) -> "KiesFirmwareList":
        return cls(xmltodict.parse(xml, dict_constructor = dict))

    @property
    def exists(self) -> bool:
        if (self._versions == None) or (self.latest == None):
            return False
        return True

    @property
    def latest(self) -> Optional[str]:
        # The are cases that "latest" key may return a dictionary or just a string in different regions and models.
        # If the "latest" field is dictionary, get the inner text, otherwise get its value directly.
        if "latest" not in self._versions:
            return None
        elif isinstance(self._versions["latest"], str):
            return KiesUtils.parse_firmware(self._versions["latest"])
        elif isinstance(self._versions["latest"], dict):
            return KiesUtils.parse_firmware(self._versions["latest"]["#text"])
        return None

    @property
    def alternate(self) -> List[str]:
        # Some devices may contain alternate/older versions too, so include them with the response.
        upgrade = self._versions["upgrade"]["value"]
        # No alternate versions.
        if upgrade == None:
            return []
        # Multiple alternate versions.
        elif isinstance(upgrade, list):
            return [KiesUtils.parse_firmware(x["#text"]) for x in upgrade if x["#text"].count("/") > 1]
        # Single alternate version.
        elif isinstance(upgrade, dict):
            return [KiesUtils.parse_firmware(upgrade["#text"])] if upgrade["#text"].count("/") > 1 else []
        return []


class KiesDict(UserDict):
    """
    A dictionary object for reading values in KiesData.
    """

    def __getitem__(self, key) -> Any:
        d = super().__getitem__(key)
        if type(d) is not dict:
            return d
        else:
            return d.get("Data", d)

    def get_first(self, *keys) -> Any:
        for key in keys:
            d = self.get(key, None)
            if d != None:
                return d


class KiesData:
    """
    A class that holds Kies server responses.
    """

    def __init__(self, data : Dict) -> None:
        self._data = data

    @classmethod
    def from_xml(cls, xml : str) -> "KiesData":
        return cls(xmltodict.parse(xml, dict_constructor = dict))

    @property
    def body(self) -> "KiesDict":
        return KiesDict(self._data["FUSMsg"]["FUSBody"].get("Put", {}))

    @property
    def results(self) -> "KiesDict":
        return KiesDict(self._data["FUSMsg"]["FUSBody"]["Results"])

    @property
    def status_code(self) -> int:
        return int(self._data["FUSMsg"]["FUSBody"]["Results"]["Status"])

    @property
    def session_id(self) -> str:
        return self._data["FUSMsg"]["FUSHdr"]["SessionID"]


class KiesConstants:

    # Get firmware information url
    GET_FIRMWARE_URL = "http://fota-cloud-dn.ospserver.net/firmware/{0}/{1}/version.xml"

    # Generate nonce url
    NONCE_URL = "https://neofussvr.sslcs.cdngc.net/NF_DownloadGenerateNonce.do"

    # Binary information url
    BINARY_INFO_URL = "https://neofussvr.sslcs.cdngc.net/NF_DownloadBinaryInform.do"

    # Binary file url
    BINARY_FILE_URL = "https://neofussvr.sslcs.cdngc.net/NF_DownloadBinaryInitForMass.do"

    # Binary download url
    BINARY_DOWNLOAD_URL = "http://cloud-neofussvr.sslcs.cdngc.net/NF_DownloadBinaryForMass.do"

    # Build custom headers so Kies servers will think the
    # request is coming from the Kies client.
    HEADERS = lambda nonce = None, signature = None: \
        {
            "Authorization": f'FUS nonce="{nonce or ""}", signature="{signature or ""}", nc="", type="", realm="", newauth="1"',
            "User-Agent": "Kies2.0_FUS"
        }

    COOKIES = lambda session_id = None: \
        {
            "JSESSIONID": session_id or ""
        }
    
    # Creates data for sending to BINARY_INFO_URL
    BINARY_INFO = lambda firmware_version, region, model, logic_check: \
        dicttoxml.dicttoxml({
            "FUSMsg": {
                "FUSHdr": {"ProtoVer": "1.0"}, 
                "FUSBody": {
                    "Put": {
                        "ACCESS_MODE": {"Data": "2"},
                        "BINARY_NATURE": {"Data": "1"},
                        "CLIENT_PRODUCT": {"Data": "Smart Switch"},
                        "DEVICE_FW_VERSION": {"Data": firmware_version},
                        "DEVICE_LOCAL_CODE": {"Data": region},
                        "DEVICE_MODEL_NAME": {"Data": model},
                        "LOGIC_CHECK": {"Data": logic_check}
                    }
                }
            }
        }, attr_type = False, root = False)

    # Creates data for sending to BINARY_FILE_URL
    BINARY_FILE = lambda filename, logic_check: \
        dicttoxml.dicttoxml({
            "FUSMsg": {
                "FUSHdr": {"ProtoVer": "1.0"}, 
                "FUSBody": {
                    "Put": {
                        "BINARY_FILE_NAME": {"Data": filename},
                        "LOGIC_CHECK": {"Data": logic_check}
                    }
                }
            }
        }, attr_type = False, root = False)


class KiesRequest:
    """
    Builds prebuilt requests for getting data from Kies servers.
    """

    @staticmethod
    def get_nonce() -> httpx.Request:
        return httpx.Request(
            "POST",
            KiesConstants.NONCE_URL,
            headers = KiesConstants.HEADERS()
        )

    @staticmethod
    def list_firmware(region : str, model : str) -> httpx.Request:
        return httpx.Request(
            "GET",
            KiesConstants.GET_FIRMWARE_URL.format(region, model)
        )

    @staticmethod
    def get_binary(region : str, model : str, firmware : str, session : Session) -> httpx.Request:
        return httpx.Request(
            "POST",
            KiesConstants.BINARY_INFO_URL,
            content = KiesConstants.BINARY_INFO(firmware, region, model, session.logic_check(firmware)),
            headers = KiesConstants.HEADERS(session.encrypted_nonce, session.auth),
            cookies = KiesConstants.COOKIES(session.session_id)
        )

    @staticmethod
    def get_download(path : str, session : Session) -> httpx.Request:
        # Extract firmware from path.
        filename = path.split("/")[-1]
        return httpx.Request(
            "POST",
            KiesConstants.BINARY_FILE_URL,
            content = KiesConstants.BINARY_FILE(filename, session.logic_check(filename.split(".")[0][-16:])),
            headers = KiesConstants.HEADERS(session.encrypted_nonce, session.auth),
            cookies = KiesConstants.COOKIES(session.session_id)
        )

    @staticmethod
    def start_download(path : str, session : Session, custom_range : str = None) -> httpx.Request:
        headers = KiesConstants.HEADERS(session.encrypted_nonce, session.auth)
        if custom_range:
            headers["Range"] = custom_range
        return httpx.Request(
            "GET",
            KiesConstants.BINARY_DOWNLOAD_URL + "?file=" + path,
            headers = headers,
            cookies = KiesConstants.COOKIES(session.session_id)
        )


class KiesUtils:

    # Parses firmware version.
    @staticmethod
    def parse_firmware(firmware: str) -> str:
        if firmware:
            l = firmware.split("/")
            if len(l) == 3:
                l.append(l[0])
            if l[2] == "":
                l[2] = l[0]
            return "/".join(l)
        else:
            return None

    # Parse range header.
    # Returns two sized tuples, first one is start and second one is end. (-1 if invalid)
    @staticmethod
    def parse_range_header(header: str) -> Tuple[int, int]:
        # Remove "bytes=" prefix.
        ran = header.strip().removeprefix("bytes=").split("-", maxsplit = 1)
        # Get range.
        if len(ran) != 2:
            return -1, -1
        return int(ran[0] or 0), int(ran[1] or 0)

    # Creates new range string.
    @staticmethod
    def make_range_header(start : int, end : int) -> str:
        return f"bytes={start or 0}-{end or ''}"

    # Joins strings together that includes slashes.
    @staticmethod
    def join_path(*args, prefix = "/") -> str:
        paths = []
        for p in args:
            if p:
                paths.append(p.strip().replace("/", " ").replace("\\", " ").strip().replace(" ", "/"))
        return (prefix or "") + "/".join(paths)