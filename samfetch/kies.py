__all__ = [
    "KiesDict",
    "KiesData",
    "KiesConstants",
    "KiesRequest",
    "KiesUtils"
]

from collections import UserDict
from typing import Tuple, Dict, Any
import dicttoxml
import xmltodict
import re
import httpx
from samfetch.session import Session


class KiesDict(UserDict):
    """
    A dictionary object for reading values in KiesData.
    """

    def __getitem__(self, key) -> Any:
        d = super().__getitem__(key)
        return d if type(d) is not dict else d.get("Data", d)


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
        return httpx.Request(
            "POST",
            KiesConstants.BINARY_FILE_URL,
            content = KiesConstants.BINARY_FILE(path, session.logic_check(path.split(".")[0][-16:])),
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
            # params = f"file={path}",
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
        _match = re.findall(r"^bytes=(\d+)-(\d*)?$", header, flags = re.MULTILINE)
        if len(_match) != 1:
            return -1, -1
        return int(_match[0][0]), int(_match[0][1] or "0")

    # Joins strings together that includes slashes.
    @staticmethod
    def join_path(*args) -> str:
        paths = []
        for p in args:
            if p:
                paths.append(p.strip().replace("/", " ").replace("\\", " ").strip().replace(" ", "/"))
        return "/".join(paths)

    # Creates new range string.
    @staticmethod
    def make_range_header(start : int, end : int) -> str:
        return f"bytes={start or 0}-{end or ''}"