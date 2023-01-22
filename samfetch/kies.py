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
import httpx
import string
from samfetch.session import Session


class KiesFirmwareList:
    """
    Parses firmware list.
    """
    def __init__(self, data : Dict) -> None:
        self._data = data
        self._versions = None if ("versioninfo" not in self._data) else self._data["versioninfo"]["firmware"]["version"]

    def __bool__(self):
        return self.exists

    @classmethod
    def from_xml(cls, xml : str) -> "KiesFirmwareList":
        return cls(xmltodict.parse(xml, dict_constructor = dict))

    @property
    def exists(self) -> bool:
        return bool(self.latest)

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

    # GET_TEST_FIRMWARE_URL = "http://fota-secure-dn.ospserver.net/firmware/{0}/{1}/nspx/{2}.bin"
    #
    # It is still unknown that how to download test firmwares, but several search results got me to find this URL.
    # However, looks like it requires some type of authorization with query parameters instead of nonce.
    # - https://forum.xda-developers.com/t/oneui-4-0-public-beta-download-and-install-in-here-exynos.4333281/page-4

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
        raise ValueError("Invalid firmware format.")

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

    # Joins strings together that includes slashes.
    @staticmethod
    def join_path(*args, prefix = "/") -> str:
        paths = []
        for p in args:
            if p:
                paths.append(p.strip().replace("/", " ").replace("\\", " ").strip().replace(" ", "/"))
        return (prefix or "") + "/".join(paths)

    # Gets basic information from a firmware string.
    # Resources:
    # - https://android.stackexchange.com/questions/183326/what-do-all-these-letters-numbers-in-early-samsung-rom-file-name-mean/183328#183328
    # - https://forum.xda-developers.com/t/ref-samsung-firmware-naming-convention-and-explanation.1356325/
    # - https://r1.community.samsung.com/t5/galaxy-s/how-to-read-build-versions/td-p/581424
    @staticmethod
    def read_firmware(firmware : str) -> Tuple[Optional[str], Optional[int], int, int, int]:
        if firmware.count("/") == 3:
            # Get last 6 character from PDA.
            pda = firmware.split("/")[0][-6:]
            result = [None, None, None, None, None]
            # 0 - Bootloader
            # 1 - Major version
            # 2 - Year
            # 3 - Month
            # 4 - Minor version
            # Make sure the bootloader column exists.
            if (pda[0] in ["U", "S"]):
                # Bootloader version (U = Upgrade, S = Security)
                result[0] = pda[0:2]
                # Major version iteration (A = 0, B = 1, ... Z = Public Beta)
                result[1] = ord(pda[2]) - ord("A")
                # Year (... R = 2018, S = 2019, T = 2020 ...)
                result[2] = (ord(pda[3]) - ord("R")) + 2018
                # Month (A = 01, B = 02, ... L = 12)
                result[3] = ord(pda[4]) - ord("A")
                # Minor version iteration (1 = 1, ... A = 10 ...)
                result[4] = (string.digits + string.ascii_uppercase).index(pda[5])
            else:
                # Year (... R = 2018, S = 2019, T = 2020 ...)
                result[2] = (ord(pda[-3]) - ord("R")) + 2018
                # Month (A = 01, B = 02, ... L = 12)
                result[3] = ord(pda[-2]) - ord("A")
                # Minor version iteration (1 = 1, ... A = 10 ...)
                result[4] = (string.digits + string.ascii_uppercase).index(pda[-1])
            return result
        raise ValueError("Invalid firmware format.")

    @staticmethod
    def read_firmware_dict(firmware : str) -> dict:
        ff = KiesUtils.read_firmware(firmware)
        return {
            "bl": ff[0],
            "date": f"{ff[2]}.{ff[3]}",
            "it": f"{ff[1]}.{ff[4]}"
        }