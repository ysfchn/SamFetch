__all__ = ["bp"]

from typing import Optional
from sanic import Blueprint
from sanic.request import Request
from json import loads
from sanic.response import json, redirect
from samfetch.kies import KiesData, KiesFirmwareList, KiesRequest, KiesUtils
from samfetch.session import Session
from samfetch.crypto import start_decryptor
from web.exceptions import make_error, SamfetchError
import httpx

bp = Blueprint(name = "Routes")


@bp.get("/firmware/<region:str>/<model:str>")
async def get_firmware_list(request : Request, region : str, model : str):
    """
    List the available firmware versions of a specified model and region.
    """
    client = httpx.AsyncClient()
    response = await client.send(
        KiesRequest.list_firmware(region = region, model = model)
    )
    # Close client.
    await client.aclose()
    # Raise exception when firmware list couldn't be fetched.
    if response.status_code != 200:
        raise make_error(SamfetchError.DEVICE_NOT_FOUND, response.status_code)
    # Parse XML
    firmwares = KiesFirmwareList.from_xml(response.text)
    # Check if model is correct by checking the "versioninfo" key.
    if firmwares.exists:
        # Return the firmware data.
        ff = KiesUtils.read_firmware(firmwares.latest)
        f = [{ 
            "firmware": firmwares.latest,
            "pda": {
                "bootloader": ff[0],
                "date": f"{ff[2]}.{ff[3]}",
                "major": ff[1],
                "minor": ff[4]
            },
            "is_latest": True
        }]
        for i in firmwares.alternate:
            ii = KiesUtils.read_firmware(firmwares.latest)
            f.append({
                "firmware": i,
                "pda": {
                    "bootloader": ii[0],
                    "date": f"{ii[2]}.{ii[3]}",
                    "major": ff[1],
                    "minor": ff[4]
                },
            })
        return json(f)
    # Raise exception when device couldn't be found.
    if firmwares._versions == None:
        raise make_error(SamfetchError.FIRMWARE_LIST_EMPTY, 404)
    raise make_error(SamfetchError.FIRMWARE_CANT_PARSE, 404)


# Gets the binary details such as filename and decrypt key.
#
# {
#   "display_name": "Galaxy Note5"
#   "size": 2530817088,
#   "size_readable": "2.36 GB",
#   "filename": "SM-N920C_1_20190117104840_n2lqmc6w6w_fac.zip.enc4",
#   "path": "/neofus/9/",
#   "encrypt_version": 4,
#   "decrypt_key": "0727c304eea8a4d14835a4e6b02c0ce3"
# }
@bp.get("/firmware/<region:str>/<model:str>/<firmware:path>")
async def get_binary_details(request : Request, region: str, model: str, firmware: str):
    """
    Gets the binary details such as filename and decrypt key. \n
    `firmware` is the firmware code of the device that you got from `/list` endpoint. \n\n
    `decrypt_key` is used for decrypting the file after downloading.
    """
    # Create new session.
    client = httpx.AsyncClient()
    nonce = await client.send(KiesRequest.get_nonce())
    session = Session.from_response(nonce)
    # Make the request.
    binary_info = await client.send(
        KiesRequest.get_binary(region = region, model = model, firmware = firmware, session = session)
    )
    # Close client.
    await client.aclose()
    # Read the request.
    if binary_info.status_code == 200:
        kies = KiesData.from_xml(binary_info.text)
        # Return error when binary couldn't be found.
        if kies.status_code != 200:
            raise make_error(SamfetchError.FIRMWARE_NOT_FOUND, 404)
        # Return error if binary is not downloadable.
        # https://github.com/nlscc/samloader/issues/54
        if kies.body.get("BINARY_NAME") == None:
            raise make_error(SamfetchError.FIRMWARE_LOST, 404)
        # If file extension ends with .enc4 that means it is using version 4 encryption, otherwise 2 (.enc2).
        ENCRYPT_VERSION = 4 if str(kies.body["BINARY_NAME"]).endswith("4") else 2
        # Get binary details.
        return json({
            "display_name": kies.body["DEVICE_MODEL_DISPLAYNAME"],
            "size": int(kies.body["BINARY_BYTE_SIZE"]),
            # Convert bytes to GB, so it will be more readable for an end-user.
            "size_readable": "{:.2f} GB".format(float(kies.body["BINARY_BYTE_SIZE"]) / 1024 / 1024 / 1024),
            "filename": kies.body["BINARY_NAME"],
            "path": kies.body["MODEL_PATH"],
            "version": kies.body["CURRENT_OS_VERSION"].replace("(", " ("),
            "encrypt_version": ENCRYPT_VERSION,
            "last_modified": int(kies.body["LAST_MODIFIED"]),
            # Generate decrypted key for decrypting the file after downloading.
            # Decrypt key gives a list of bytes, but as it is not possible to send as query parameter, 
            # we are converting it to a single HEX value.
            "decrypt_key": \
                session.getv2key(firmware, model, region).hex() if ENCRYPT_VERSION == 2 else \
                session.getv4key(kies.body.get_first("LATEST_FW_VERSION", "ADD_LATEST_FW_VERSION"), kies.body["LOGIC_VALUE_FACTORY"]).hex(),
            # A URL of samsungmobile that includes release changelogs.
            # Not available for every device.
            "firmware_changelog_url": kies.body.get_first("DESCRIPTION", "ADD_DESCRIPTION"),
            "platform": kies.body["DEVICE_PLATFORM"]
        })
    # Raise exception when status is not 200.
    raise make_error(SamfetchError.KIES_SERVER_OUTER_ERROR, binary_info.status_code)


@bp.get("/download/<path:path>/<filename:str>")
async def download_binary(request : Request, path: str, filename: str):
    """
    Downloads the firmware and decrypts the file while downloading. 
    Decrypting can be skipped by providing "0" as decrypt_key.
    """
    args = request.get_args()
    decrypt_key = args.get("decrypt", None)
    DECRYPT_ENABLED : bool = decrypt_key != None
    CUSTOM_FILENAME : Optional[str] = None if "filename" not in args else str(args.get("filename")).removesuffix(".zip") + ".zip"
    # Create new session.
    client = httpx.AsyncClient()
    nonce = await client.send(KiesRequest.get_nonce())
    session = Session.from_response(nonce)
    # Make the request.
    download_info = await client.send(
        KiesRequest.get_download(
            path = KiesUtils.join_path(path, filename), 
            session = session
        )
    )
    # Refresh session.
    session.refresh_session(download_info)
    # Read the request.
    if download_info.status_code == 200:
        kies = KiesData.from_xml(download_info.text)
        # Return error when binary couldn't be found.
        if kies.status_code != 200:
            await client.aclose()
            raise make_error(SamfetchError.KIES_SERVER_ERROR, kies.status_code)
        # Else, make another request to get the binary.
        else:
            # Check and parse the range header.
            START_RANGE, END_RANGE = KiesUtils.parse_range_header(request.headers.get("Range", "bytes=0-"))
            # Check if range is invalid.
            if (START_RANGE == -1) or (END_RANGE == -1) or (DECRYPT_ENABLED and (END_RANGE != 0)):
                await client.aclose()
                raise make_error(SamfetchError.RANGE_HEADER_INVALID, 416)
            # Another request for streaming the firmware.
            download_file = await client.send(
                KiesRequest.start_download(
                    path = KiesUtils.join_path(path, filename), 
                    session = session,
                    custom_range = request.headers.get("Range", None)
                ),
                stream = True
            )
            # Check if status code is not 200 or 206.
            if download_file.status_code not in [200, 206]:
                # Raise HTTPException when status is not success.
                await client.aclose()
                raise make_error(SamfetchError.KIES_SERVER_ERROR, download_file.status_code)
            # Create headers.
            headers = { 
                "Content-Disposition": 'attachment; filename="' + \
                    (CUSTOM_FILENAME or (filename if not DECRYPT_ENABLED else filename.replace(".enc4", "").replace(".enc2", ""))) + '"',
                # Get the total size of binary.
                "Content-Length": download_file.headers["Content-Length"],
                "Accept-Ranges": "bytes",
                "Connection": "keep-alive"
            }
            if "Content-Range" in download_file.headers:
                headers["Content-Range"] = download_file.headers["Content-Range"]
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
                status = download_file.status_code
            )
            await start_decryptor(
                response = response,
                iterator = download_file.aiter_raw(chunk_size = request.app.config.SAMFETCH_CHUNK_SIZE),
                key = None if not DECRYPT_ENABLED else bytes.fromhex(decrypt_key),
                client = client
            )
    # Raise exception when status is not 200.
    raise make_error(SamfetchError.KIES_SERVER_OUTER_ERROR, download_info.status_code)


# Executes all required endpoints and directly starts dowloading the latest firmware with one call.
# It is useful for end-users who don't want to integrate the API in a client app.
@bp.get("/direct/<region:str>/<model:str>")
async def direct_download(request : Request, region: str, model: str):
    """
    Executes all required endpoints and directly starts dowloading the latest firmware with one call. \n
    It is useful for end-users who don't want to integrate the API in a client app.
    """
    version = await get_firmware_list(request, region, model)
    version_data = loads(version.body)
    binary = await get_binary_details(request, region, model, version_data["latest"])
    binary_data = loads(binary.body)
    return redirect(f'/download{binary_data["path"]}{binary_data["filename"]}?decrypt={binary_data["decrypt_key"]}')
