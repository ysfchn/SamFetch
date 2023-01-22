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

__all__ = ["bp"]

from typing import Optional
from sanic import Blueprint
from sanic.request import Request
from sanic.response import json, redirect
from sanic.exceptions import NotFound
from samfetch.kies import KiesUtils
from samfetch.classes import Device, DeviceNotFoundException, FirmwareNotAvailableException, Firmware, FirmwareDetail, PayloadException, ServerException
from web.exceptions import make_error, SamfetchError
import re

bp = Blueprint(name = "Routes")


@bp.get("/<region:str>/<model:str>/list")
async def get_firmware_list(request : Request, region : str, model : str):
    """
    List the available firmware versions of a specified model and region.
    """
    device = Device(region, model)
    result = []
    try:
        for i, f in enumerate(await device.list_firmware()):
            res = {"firmware": f.value}
            if i == 0:
                res["is_latest"] = True
            res["pda"] = f.pda
            result.append(res)
        return json(result)
    except DeviceNotFoundException:
        raise make_error(SamfetchError.DEVICE_NOT_FOUND, 404)
    except FirmwareNotAvailableException:
        raise make_error(SamfetchError.FIRMWARE_LIST_EMPTY, 404)


@bp.get("/<region:str>/<model:str>/<mode:(latest|latest/download)>")
async def get_firmware_latest(request : Request, region : str, model : str, mode : str):
    """
    Gets the latest firmware version for the device and redirects to its information.
    """
    device = Device(region, model)
    try:
        res = await device.list_firmware()
        return redirect(f"/{region}/{model}/{res[0].value}" + ("/download" if "/download" in mode else ""))
    except DeviceNotFoundException:
        raise make_error(SamfetchError.DEVICE_NOT_FOUND, 404)
    except FirmwareNotAvailableException:
        raise make_error(SamfetchError.FIRMWARE_LIST_EMPTY, 404)


# Gets the binary details such as filename and decrypt key.
@bp.get("/<region:str>/<model:str>/<firmware_path:([A-Z0-9]*/[A-Z0-9]*/[A-Z0-9]*/[A-Z0-9]*[/download]*)>")
async def get_binary_details(request : Request, region: str, model: str, firmware_path: str):
    """
    Gets the firmware details such as path, filename and decrypt key. 
    Use these values to start downloading the firmware file.
    """
    # Check if "/download" path has appended to firmware value.
    is_download = firmware_path.removesuffix("/").endswith("/download")
    firmware = firmware_path.removesuffix("/").removesuffix("/download")
    if not re.match(r"^[A-Z0-9]*/[A-Z0-9]*/[A-Z0-9]*/[A-Z0-9]*$", firmware):
        raise NotFound(f"Requested URL {request.path} not found")
    firm = Firmware(firmware, Device(region, model))
    details : FirmwareDetail = None
    try:
        details = await firm.fetch()
    except PayloadException:
        raise make_error(SamfetchError.FIRMWARE_NOT_FOUND, 404)
    except ServerException:
        raise make_error(SamfetchError.KIES_SERVER_OUTER_ERROR, 404)
    except FirmwareNotAvailableException:
        raise make_error(SamfetchError.FIRMWARE_LOST, 404)
    decrypt_key = details.decryption_key()
    # If auto downloading has enabled, redirect to downloading the firmware.
    download_path = f'/file{details.path}{details.filename}'
    if is_download:
        return redirect(download_path + "?decrypt=" + decrypt_key)
    server_path = f"{request.scheme}://{request.server_name}{'' if request.server_port in [80, 443] else ':' + str(request.server_port)}"
    # Create response
    response = details.to_dict()
    response["download_path"] = server_path + download_path
    response["download_path_decrypt"] = server_path + download_path + "?decrypt=" + decrypt_key
    response["pda"] = response.pop("pda")
    return json(response)


@bp.get("/file/<path:path>/<filename:str>")
async def download_binary(request : Request, path: str, filename: str):
    """
    Downloads the firmware with given path and filename.
    To enable decrypting, insert "decrypt" query parameter with decryption key. If this parameter is not provided,
    the encrypted binary will be downloaded. Path, filename and decryption key can be obtained on `/firmware` endpoint.
    """
    args = request.get_args()
    decrypt_key = args.get("decrypt", None)
    DECRYPT_ENABLED : bool = decrypt_key != None
    CUSTOM_FILENAME : Optional[str] = None if "filename" not in args else str(args.get("filename")).removesuffix(".zip") + ".zip"
    # Check if range is invalid.
    START_RANGE, END_RANGE = KiesUtils.parse_range_header(request.headers.get("Range", "bytes=0-"))
    if (START_RANGE == -1) or (END_RANGE == -1) or (DECRYPT_ENABLED and (END_RANGE != 0)):
        raise make_error(SamfetchError.RANGE_HEADER_INVALID, 416)
    # Start streaming firmware.
    try:
        stream, stream_info = await Firmware.download_generator(
            path = KiesUtils.join_path(path, filename),
            session = (await Firmware.get_session()),
            key = decrypt_key,
            chunk_size = request.app.config.SAMFETCH_CHUNK_SIZE,
            range_header = request.headers.get("Range", None)
        )
        # Create headers.
        headers = { 
            "Content-Disposition": 'attachment; filename="' + \
                (CUSTOM_FILENAME or (filename if not DECRYPT_ENABLED else filename.replace(".enc4", "").replace(".enc2", ""))) + '"',
            # Get the total size of binary.
            "Content-Length": stream_info.file_size,
            "Accept-Ranges": "bytes",
            "Connection": "keep-alive"
        }
        if stream_info.range_header:
            headers["Content-Range"] = stream_info.range_header
        # If decryption is enabled, remove Content-Length.
        # Because when we decrypt the firmware, it becomes slightly bigger or smaller
        # so this causes exceptions as Content-Length is not same as sent file size.
        if DECRYPT_ENABLED:
            del headers["Content-Length"]
        # Decrypt bytes while downloading the file.
        # So this way, we can directly serve the bytes to the client without downloading to the disk.
        response = await request.respond(
            headers = headers,
            content_type = "application/zip" if DECRYPT_ENABLED else "application/octet-stream",
            status = 206 if (START_RANGE or END_RANGE) else 200
        )
        async for i in stream:
            await response.send(i)
        await response.eof()
    except PayloadException:
        raise make_error(SamfetchError.KIES_SERVER_ERROR, 404)
    except ServerException:
        raise make_error(SamfetchError.KIES_SERVER_OUTER_ERROR, 404)