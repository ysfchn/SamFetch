from typing import Iterator, Tuple
import dicttoxml
from src.crypto import Crypto
from Crypto.Cipher import AES
import xmltodict
import re


class KiesData:
    """
    A class that handles Kies data.
    """
    def __init__(self, data : str) -> None:
        self.data = xmltodict.parse(data, dict_constructor = dict)
        self.session_id : str = self.data["FUSMsg"]["FUSHdr"]["SessionID"]
        self.status_code : str = self.data["FUSMsg"]["FUSBody"]["Results"]["Status"]
        self.body : dict = {x : y if type(y) is not dict else y.get("Data", y) for x, y in self.data["FUSMsg"]["FUSBody"].get("Put", {}).items()}
        # Add data from FUSBody/Results too.
        for k, v in self.data["FUSMsg"]["FUSBody"]["Results"].items():
            if k not in ["CmdRef", "Status"]:
                self.body[k] = v if type(v) is not dict else v.get("Data", v)


class Constants:
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
    HEADERS = lambda nonce = "", signature = "": \
        {
            "Authorization": f'FUS nonce="{nonce}", signature="{signature}", nc="", type="", realm="", newauth="1"',
            "User-Agent": "Kies2.0_FUS"
        }

    COOKIES = lambda session_id = "": \
        {
            "JSESSIONID": session_id
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

    # Parses firmware version.
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
    # Returns -2 if range is invalid.
    def parse_range_header(header: str) -> Tuple[int, int]:
        _match = re.findall(r"^bytes=(\d+)-(\d*)?$", header, flags = re.MULTILINE)
        if len(_match) != 1:
            return -1, -1
        return int(_match[0][0]), 0 if not _match[0][1] else int(_match[0][1])

    def make_range_header(start : int, end : int) -> str:
        return (str(start) if start else "0") + "-" + (str(end) if end else "")


# A custom iterator to decrypt the bytes without writing the whole file to the disk
# for downloading firmwares.
class Decryptor:
    """
    A custom iterator to decrypt the bytes without writing the whole file to the disk 
    for downloading firmwares.
    """

    def __init__(self, response, key: bytes):
        self.iterator : Iterator = response.iter_content(chunk_size = 0x10000)
        # We need to unpad (basically modify) the last chunk,
        # so we need to learn when will the iterator end.
        # Because of that, we hold next chunks and return the previous chunk to user.
        self.chunks = [next(self.iterator), None]
        # [ X, Y ]
        # X - The future chunk
        # Y - Will be sent to user (always comes from 1 step behind)
        self.cipher = AES.new(key, AES.MODE_ECB)

    def __iter__(self):
        return self

    def move(self):
        chunk = next(self.iterator, None)
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

    def __next__(self):
        # Get the current chunk.
        current = self.chunks[1]
        returned = None
        # Check if ending point exceed.
        if self.is_end_exceed:
            raise StopIteration
        # Check if the chunk is starting point.
        if self.is_start:
            returned = b""
        # Check if the chunk is ending point.
        elif self.is_end:
            returned = Crypto.unpad(self.cipher.decrypt(current))
        else:
            returned = self.cipher.decrypt(current)
        # Shift to the next chunk and keep the previous one.
        self.move()
        return returned