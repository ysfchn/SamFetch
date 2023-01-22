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
    """
    Represents a Samsung device.
    """

    __slots__ = ("region", "model", )

    def __init__(self, region : str, model : str) -> None:
        self.region = region
        self.model = model

    async def list_firmware(self) -> List["Firmware"]:
        """
        Fetch a list of firmwares for this Device from Kies servers,
        and return a list containing Firmware object for each 
        firmware version.

        Returns:
            List of Firmware object bound to this Device.
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

    def get_firmware(self, firmware : str) -> "Firmware":
        """
        Return a Firmware object from given firmware version string. 
        The format for firmware version must be one of:
        - "ABCDEF/ABCDEF/" (note the trailing slash)
        - "ABCDEF/ABCDEF/ABCDEF"
        - "ABCDEF/ABCDEF/ABCDEF/ABCDEF"

        Returns:
            A Firmware object bound to this Device and given firmware version.
        """
        return Firmware(KiesUtils.parse_firmware(firmware), self)


class FirmwareStreamInfo:
    """
    Holds useful information for firmware downloads.
    """

    __slots__ = ("file_size", "range_header", )

    def __init__(self, file_size : int, range_header : Optional[str] = None) -> None:
        self.file_size = file_size
        self.range_header = range_header


class Firmware:
    """
    A firmware version for a specific Device.
    """

    __slots__ = ("value", "device", "info", )

    def __init__(self, value : str, device : "Device") -> None:
        self.value = value
        self.device = device
        self.info : Optional["FirmwareDetail"] = None


    @property
    def pda(self) -> dict:
        """
        Returns a dictionary which contains bootloader version,
        firmware date, and iteration count which parsed from 
        firmware version string.
        """
        return KiesUtils.read_firmware_dict(self.firmware.value)


    async def fetch(self, skip_exists : bool = False) -> "FirmwareDetail":
        """
        Fetch this firmware from Kies servers to get FirmwareDetail object 
        that contains related information about this firmware. If skip_exists is
        True, then the cached FirmwareDetail object (if any) will be returned instead.

        Parameters:
            skip_exists:
                When fetch() has called, the returning object will be stored in
                the instance for later use. Set to True for allowing getting from
                cache (if stored). If False (default), cache will be skipped and
                every fetch() will make a HTTP request.
        
        Returns:
            A FirmwareDetail object that contains related information about this firmware.
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
            self.info = FirmwareDetail(kies.body, self)
            return self.info


    @staticmethod
    async def get_session() -> Session:
        """
        A function that requests a new Session. An Session is used for
        authenticating with Kies servers, and same Session can't be used for multiple
        requests. (it gets invalidated by server)
        This is automatically called when needed, so you won't probably need that.

        Returns:
            A Session object that holds nonce fetched from Kies servers.
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
        Same as download() but doesn't bound to an instance.
        See download() method for more details.
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
        range_header : Optional[str] = None, refetch : bool = False
    ) -> Tuple[AsyncGenerator[bytes], FirmwareStreamInfo]:
        """
        A function that returns a two-item tuple; an async generator that iterates 
        HTTP firmware download in chunks and a FirmwareStreamInfo object that stored
        useful information for the download such as encrypted file size.
        If decrypt is True, the generator will decrypt chunk in each iteration automatically.

        Parameters:
            decrypt:
                If True, the returned generator will return decrypted firmware bytes
                for each iteration instead of returning plain encrypted bytes.
            chunk_size:
                Number of bytes to be returned on each iteration for generator.
            range_header:
                A valid "Range" HTTP value if you want to get the part of the firmware
                instead of downloading whole. This can be useful for resuming/pausing
                downloads.
            refetch:
                Setting to True will fetch firmware details again with fetch() and refresh
                the session (more HTTP requests). If set to False (default), then the 
                cached session will be used instead. However, if a long time has passed 
                between fetch() and download() calls, Kies servers may invalidate the session, 
                thus making the download impossible. Set to True if you are having problems.

        Returns:
            Two item tuple. First item is the async generator which returns bytes for 
            the firmware which is downloading in each iteration, and second item is 
            FirmwareStreamInfo which gives basic information about currently 
            downloading file.
        """
        await self.fetch(skip_exists = not refetch)
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
    """
    Fetched details for a firmware of a device.
    """

    __slots__ = ("_body", "firmware")

    def __init__(self, body : KiesDict, firmware : "Firmware") -> None:
        self._body = body
        self.firmware = firmware

    @property
    def display_name(self) -> str:
        """
        Display name of the device.
        """
        return self._body["DEVICE_MODEL_DISPLAYNAME"]

    @property
    def size(self) -> str:
        """
        Download size for the ENCRYPTED firmware file in bytes.
        """
        return int(self._body["BINARY_BYTE_SIZE"])

    @property
    def filename(self) -> str:
        """
        File name of the firmware in Kies server.
        """
        return self._body["BINARY_NAME"]

    @property
    def path(self) -> str:
        """
        File path (no file name) of the firmware in Kies server.
        """
        return self._body["MODEL_PATH"]

    @property
    def version(self) -> str:
        """
        Android version of the firmware.
        """
        return self._body["CURRENT_OS_VERSION"].replace("(", " (")

    @property
    def last_modified(self) -> int:
        """
        Last modified date of the firmware in integer.
        """
        return int(self._body["LAST_MODIFIED"])

    @property
    def platform(self) -> str:
        """
        Platform of the firmware.
        """
        return self._body["DEVICE_PLATFORM"]

    @property
    def crc(self) -> str:
        """
        CRC value for the ENCRYPTED firmware file.
        """
        return self._body["BINARY_CRC"]

    @property
    def firmware_changelog_url(self) -> Optional[str]:
        """
        An URL that points to Samsung's website which contains a changelog
        for this firmware of this device. Not available for every device
        and firmware.
        """
        return self._body.get_first("DESCRIPTION", "ADD_DESCRIPTION")

    @property
    def encrypt_version(self) -> Literal[2, 4]:
        """
        Encrypt version of the firmware file. If firmware file name
        ends with "4", then the version is 4, otherwise it is 2.
        You won't need this value as decryption_key() already handles
        encryption version.
        """
        return 4 if str(self._body["BINARY_NAME"]).endswith("4") else 2

    @property
    def size_readable(self) -> str:
        """
        Firmware size represented in GiB.
        """
        return "{:.2f} GB".format(float(self._body["BINARY_BYTE_SIZE"]) / 1024 / 1024 / 1024)

    @property
    def pda(self) -> dict:
        """
        A dictionary which contains bootloader version,
        firmware date, and iteration count which parsed from 
        firmware version string.
        """
        return self.firmware.pda

    def decryption_key(self) -> str:
        """
        AES (ECB mode) key encoded as hex, which is used for decrypting the
        plain/encrypted firmware file. You won't need this if decrypting has enabled
        in download() method, only if you are downloading the encrypted file.
        """
        if self.encrypt_version == 2:
            return Session.getv2key(
                self.firmware.value, self.firmware.device.model, self.firmware.device.region
            ).hex()
        else:
            return Session.getv4key(
                self._body.get_first("LATEST_FW_VERSION", "ADD_LATEST_FW_VERSION"), 
                self._body["LOGIC_VALUE_FACTORY"]
            ).hex()

    def to_dict(self) -> dict:
        """
        Returns a dictionary (JSON-compatible) containing related
        information for this firmware. 
        """
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