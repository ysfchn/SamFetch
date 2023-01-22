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

from typing import AsyncGenerator, List, Literal, Optional, Tuple
from samfetch.crypto import decrypt_iterator
from samfetch.kies import KiesData, KiesFirmwareList, KiesRequest, KiesUtils, KiesDict
from samfetch.session import Session
import httpx


class ServerException(Exception):
    pass

class PayloadException(Exception):
    pass

class DeviceNotFoundException(Exception):
    pass

class FirmwareNotAvailableException(Exception):
    pass


class Device:
    __slots__ = ("region", "model", )

    def __init__(self, region : str, model : str) -> None:
        self.region = region
        self.model = model

    async def list_firmware(self) -> List["Firmware"]:
        """
        List available firmwares for this Device and return a list of Firmware object.
        """
        data = []
        async with httpx.AsyncClient() as client:
            # Send request to list firmware.
            resp = await client.send(KiesRequest.list_firmware(region = self.region, model = self.model))
            if resp.status_code != 200:
                raise DeviceNotFoundException("Device has not found.")
            # Parse firmware list and create Firmware object for each firmware.
            firmlist = KiesFirmwareList.from_xml(resp.text)
            if not firmlist:
                raise FirmwareNotAvailableException("Device exists; but there is no latest firmware available.")
            data.append(Firmware(firmlist.latest, self))
            for i in firmlist.alternate:
                data.append(Firmware(i, self))
            return data


class FirmwareStreamInfo:
    def __init__(self, file_size : int, range_header : Optional[str] = None) -> None:
        self.file_size = file_size
        self.range_header = range_header


class Firmware:
    def __init__(self, value : str, device : "Device") -> None:
        self.value = value
        self.device = device
        self.info : Optional["FirmwareDetail"] = None

    @property
    def pda(self) -> dict:
        return KiesUtils.read_firmware_dict(self.firmware.value)

    async def fetch(self, skip_exists : bool = False) -> "FirmwareDetail":
        """
        Fetch this firmware from Kies servers to get FirmwareDetail object 
        that contains related information about this firmware. If skip_exists is
        True, then the cached FirmwareDetail object (if any) will be returned instead.
        """
        if skip_exists and self.info:
            return self.info
        async with httpx.AsyncClient() as client:
            # Send nonce request.
            nonce = await client.send(KiesRequest.get_nonce())
            session = Session.from_response(nonce)
            # Send request to get firmware.
            binary_info = await client.send(
                KiesRequest.get_binary(region = self.device.region, model = self.device.model, firmware = self.firmware, session = session)
            )
            if binary_info.status_code != 200:
                raise ServerException(f"Kies returned {binary_info.status_code}; are their servers down?")
            # Parse firmware info.
            kies = KiesData.from_xml(binary_info.text)
            if kies.status_code != 200:
                raise PayloadException(f"Kies returned {kies.status_code}; does firmware exists?")
            # Return error if binary is not downloadable.
            # https://github.com/nlscc/samloader/issues/54
            if kies.body.get("BINARY_NAME") == None:
                raise FirmwareNotAvailableException(f"Sadly, Samsung no longer serves this firmware.")
            self.info = FirmwareDetail(kies.body, self, session)
            return self.info

    @staticmethod
    async def get_session() -> Session:
        """
        A function that requests a new Session. An Session is used for
        authenticating with Kies servers, and same Session can't be used for multiple
        requests. (it gets invalidated by server)
        This is automatically called when needed, so you won't probably need that.
        """
        async with httpx.AsyncClient() as client:
            nonce = await client.send(KiesRequest.get_nonce())
            return Session.from_response(nonce)

    @staticmethod
    async def download_generator(
        path : str, session : Session, key : Optional[str] = None, 
        chunk_size : int = 1024, range_header : Optional[str] = None
    ) -> Tuple[AsyncGenerator[bytes], FirmwareStreamInfo]:
        """
        Same as download() but doesn't bound an instance.
        """
        async with httpx.AsyncClient() as client:
            # Send request to get download info.
            download_info = await client.send(
                KiesRequest.get_download(path = path, session = session)
            )
            session.refresh_session(download_info)
            if download_info.status_code != 200:
                raise ServerException(f"Kies returned {download_info.status_code}; are their servers down?")
            # Parse download info.
            kies = KiesData.from_xml(download_info.text)
            if kies.status_code != 200:
                raise PayloadException(f"Kies returned {kies.status_code}; does firmware exists?")
            # Another request for streaming the firmware.
            download_file = await client.send(
                KiesRequest.start_download(
                    path = path, 
                    session = session,
                    custom_range = range_header
                ),
                stream = True
            )
            # Check if status code is not 200 or 206.
            if download_file.status_code not in [200, 206]:
                raise ServerException(f"Kies returned {download_file.status_code}; does firmware exists?")
            return (
                decrypt_iterator(
                    iterator = download_file.aiter_raw(chunk_size = chunk_size),
                    key = None if not key else bytes.fromhex(key)
                ), FirmwareStreamInfo(
                    file_size = download_file["Content-Length"],
                    range_header = download_file.headers.get("Content-Range", None)
                ), )


    async def download(
        self, decrypt : bool = True, chunk_size : int = 1024, 
        range_header : Optional[str] = None
    ) -> Tuple[AsyncGenerator[bytes], FirmwareStreamInfo]:
        """
        A function that returns a two-item tuple; an async generator that iterates 
        HTTP firmware download in chunks and a FirmwareStreamInfo object that stored
        useful information for the download such as encrypted file size.
        If decrypt is True, the generator will decrypt chunk in each iteration automatically.
        """
        await self.fetch(skip_exists = True)
        stream, stream_info = await self.download_generator(
            path = self.info.path + self.info.filename, 
            session = Session.copy(self.info._session),
            key = None if not decrypt else self.info.decryption_key(),
            range_header = range_header,
            chunk_size = chunk_size
        )
        # Consume info
        self.info = None
        return stream, stream_info, 


class FirmwareDetail:
    __slots__ = ("_body", "_session", "firmware")

    def __init__(self, body : KiesDict, firmware : "Firmware", session : Session) -> None:
        self._body = body
        self._session = session
        self.firmware = firmware

    @property
    def display_name(self) -> str : return self._body["DEVICE_MODEL_DISPLAYNAME"]
    @property
    def size(self) -> str : return int(self._body["BINARY_BYTE_SIZE"])
    @property
    def filename(self) -> str : return self._body["BINARY_NAME"]
    @property
    def path(self) -> str : return self._body["MODEL_PATH"]
    @property
    def version(self) -> str: return self._body["CURRENT_OS_VERSION"].replace("(", " (")
    @property
    def last_modified(self) -> str : return int(self._body["LAST_MODIFIED"])
    @property
    def platform(self) -> str : return self._body["DEVICE_PLATFORM"]
    @property
    def crc(self) -> str: return self._body["BINARY_CRC"]
    @property
    def firmware_changelog_url(self) -> str : return self._body.get_first("DESCRIPTION", "ADD_DESCRIPTION")
    @property
    def encrypt_version(self) -> Literal[2, 4] : return 4 if str(self._body["BINARY_NAME"]).endswith("4") else 2
    @property
    def size_readable(self) -> str : return "{:.2f} GB".format(float(self._body["BINARY_BYTE_SIZE"]) / 1024 / 1024 / 1024)
    @property
    def pda(self) -> dict : return self.firmware.pda

    def decryption_key(self) -> str:
        return \
            self._session.getv2key(self.firmware.value, self.firmware.device.model, self.firmware.device.region).hex() if self.encrypt_version == 2 else \
            self._session.getv4key(self._body.get_first("LATEST_FW_VERSION", "ADD_LATEST_FW_VERSION"), self._body["LOGIC_VALUE_FACTORY"]).hex()

    def to_dict(self) -> dict:
        return {
            "display_name": self.display_name,
            "size": self.size,
            "size_readable": self.size_readable,
            "filename": self.filename,
            "path": self.path,
            "version": self.version,
            "encrypt_version": self.encrypt_version,
            "last_modified": self.last_modified,
            "decrypt_key": self.decryption_key(),
            "firmware_changelog_url": self.firmware_changelog_url,
            "platform": self.platform,
            "crc": self.crc,
            "pda": self.pda
        }