__all__ = ["bp"]

from sanic import Blueprint
from sanic.exceptions import SanicException
from sanic.request import Request
from json import loads
from sanic.response import json, redirect, stream
from samfetch.csc import CSC
from samfetch.kies import KiesData, KiesRequest, KiesUtils
from samfetch.session import Session
from samfetch.crypto import Decryptor
import httpx
import xmltodict

bp = Blueprint(name = "Routes")


# /csc
#
# Returns a known list of CSC/region codes. 
# Note that it doesn't give a warranty about having all CSC codes.
@bp.get("/csc")
async def get_csc_list(request : Request):
    """
    Returns a known list of CSC/region codes. Note that it doesn't give a warranty about having all CSC codes.
    """
    return json(CSC)


# /list/<region:str>/<model:str>
#
# List the available firmware versions of a specified model and region.
# Use latest key to get latest firmware code.
#
# {
#   "latest": "N920CXXU5CRL3/N920COJV4CRB3/N920CXXU5CRL1/N920CXXU5CRL3",
#   "alternate": []
# }
@bp.get("/list/<region:str>/<model:str>")
async def get_firmware_list(request : Request, region : str, model : str):
    """
    List the available firmware versions of a specified model and region.
    Use latest key to get latest firmware code.
    """
    client = httpx.AsyncClient()
    response = await client.send(
        KiesRequest.list_firmware(region = region, model = model)
    )
    # Close client.
    await client.aclose()
    # Raise exception when firmware list couldn't be fetched.
    if response.status_code != 200:
        raise SanicException(
            "Looks like SamFetch couldn't get a list of firmwares, probably model or region is incorrect.", 
            response.status_code
        )
    # Parse XML
    firmwares = xmltodict.parse(response.text, dict_constructor=dict)
    # Check if model is correct by checking the "versioninfo" key.
    if "versioninfo" in firmwares:
        # Parse latest firmware version.
        versions = firmwares["versioninfo"]["firmware"]["version"]
        # Check if value is None.
        if (not versions.get("latest")) or (isinstance(versions["latest"], dict) and "#text" not in versions["latest"]):
            raise SanicException(
                "Looks like SamFetch couldn't find firmwares, maybe some or all of parameters are invalid?", 404
            )
        # Return the firmware data.
        return json({
            # The are cases that "latest" key may return a dictionary or just a string in different regions and models.
            # If the "latest" field is dictionary, get the inner text, otherwise get its value directly.
            "latest": KiesUtils.parse_firmware(versions["latest"] if isinstance(versions["latest"], str) else versions["latest"]["#text"]),
            # Some devices may contain alternate/older versions too, so include them with the response.
            "alternate": [KiesUtils.parse_firmware(x["#text"]) for x in versions["upgrade"]["value"] or []]
        })
    else:
        # Raise exception when device couldn't be found.
        raise SanicException(
            "Looks like SamFetch couldn't find firmwares, maybe some or all of parameters are invalid?", 404
        )


# /binary/<region:str>/<model:str>/<firmware:path>
#
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
@bp.get("/binary/<region:str>/<model:str>/<firmware:path>")
async def get_binary_details(request : Request, region: str, model: str, firmware: str):
    """
    Gets the binary details such as filename and decrypt key.\n
    `firmware` is the firmware code of the device that you got from `/list` endpoint.\n\n
    `decrypt_key` is used for decrypting the file after downloading. It presents a hex string. Pass it to `/download` endpoint.
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
            raise SanicException(
                "Firmware couldn't be found.", 
                404
            )
        # If file extension ends with .enc4 that means it is using version 4 encryption, otherwise 2 (.enc2).
        ENCRYPT_VERSION = 4 if str(kies.body["BINARY_NAME"]).endswith("4") else 2
        # Get binary details
        return json({
            "display_name": kies.body["DEVICE_MODEL_DISPLAYNAME"],
            "size": int(kies.body["BINARY_BYTE_SIZE"]),
            "filename": kies.body["BINARY_NAME"],
            "path": kies.body["MODEL_PATH"],
            "version": kies.body["CURRENT_OS_VERSION"].replace("(", " ("),
            "encrypt_version": ENCRYPT_VERSION,
            "last_modified": int(kies.body["LAST_MODIFIED"]),
            # Convert bytes to GB, so it will be more readable for an end-user.
            "size_readable": "{:.2f} GB".format(float(kies.body["BINARY_BYTE_SIZE"]) / 1024 / 1024 / 1024),
            # Generate decrypted key for decrypting the file after downloading.
            # Decrypt key gives a list of bytes, but as it is not possible to send as query parameter, 
            # we are converting it to a single HEX value.
            "decrypt_key": \
                session.getv2key(firmware, model, region).hex() if ENCRYPT_VERSION == 2 else \
                session.getv4key(kies.body.get("LATEST_FW_VERSION", kies.body["ADD_LATEST_FW_VERSION"]), kies.body["LOGIC_VALUE_FACTORY"]).hex(),
            # A URL of samsungmobile that includes release changelogs.
            # Not available for every device.
            "firmware_changelog_url": kies.body["DESCRIPTION"],
            "platform": kies.body["DEVICE_PLATFORM"]
        })
    # Raise exception when status is not 200.
    raise SanicException(
        "Firmware couldn't be found.", 
        binary_info.status_code
    )


# /download/<path:path>/<filename:str>
#
# Downloads the firmware and decrypts the file during download automatically. 
# Decrypting can be skipped by providing "0" as decrypt_key.
@bp.get(r"/download/<path:path>/<filename:str>")
async def download_binary(request : Request, path: str, filename: str):
    """
    Downloads the firmware and decrypts the file while downloading.
    """
    decrypt_key = request.get_args().get("decrypt")
    # Create new session.
    client = httpx.AsyncClient()
    nonce = await client.send(KiesRequest.get_nonce())
    session = Session.from_response(nonce)
    # Make the request.
    download_info = await client.send(
        KiesRequest.get_download(
            path = "/" + KiesUtils.join_path(path, filename), 
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
            raise SanicException(
                f"Kies returned {kies.status_code}. Maybe parameters are invalid?", 
                kies.status_code
            )
        # Else, make another request to get the binary.
        else:
            # Check and parse the range header.
            START_RANGE, END_RANGE = (0, 0) if "Range" not in request.headers else KiesUtils.parse_range_header(request.headers["Range"])
            RANGE_HEADER = KiesUtils.make_range_header(START_RANGE, END_RANGE)
            # Check if range is invalid.
            if START_RANGE == -1 or END_RANGE == -1:
                await client.aclose()
                raise SanicException(
                    "'Range' header is invalid. If you didn't meant input a 'Range' header, remove it from request.",
                    416
                )
            # Another request for streaming the firmware.
            download_file = await client.send(
                KiesRequest.start_download(
                    path = "/" + KiesUtils.join_path(path, filename), 
                    session = session, 
                    custom_range = None if "Range" not in request.headers else RANGE_HEADER
                ),
                stream = True
            )
            # Check if status code is not 200 or 206.
            if download_file.status_code not in [200, 206]:
                # Raise HTTPException when status is not success.
                await client.aclose()
                raise SanicException(
                    f"Kies returned {download_file.status_code}. Maybe parameters are invalid?", 
                    download_file.status_code
                )
            # Get the total size of binary.
            CONTENT_LENGTH = int(download_file.headers["Content-Length"])
            # Decrypt bytes while downloading the file.
            # So this way, we can directly serve the bytes to the client without downloading to the disk.
            return stream(
                # If an decrpytion key has provided, enable decryption,
                # otherwise just download the encryted archive.
                download_file.aiter_raw(chunk_size = request.app.config.SAMFETCH_CHUNK_SIZE) \
                if decrypt_key == None else \
                Decryptor(iterator = download_file.aiter_raw(chunk_size = request.app.config.SAMFETCH_CHUNK_SIZE), key = bytes.fromhex(decrypt_key)),
                headers = { 
                    "Content-Disposition": "attachment;filename=" + filename.replace(".enc4", "").replace(".enc2", ""),
                    "Content-Length": str(CONTENT_LENGTH),
                    "Accept-Ranges": "bytes",
                    "Content-Range": RANGE_HEADER.replace("=", "")
                },
                content_type = "application/zip",
                status = 200 if not START_RANGE else 206
            )
    # Raise exception when status is not 200.
    raise SanicException(
        "Something went wrong when sending request to Kies servers.", 
        500
    )


# /direct/<region:str>/<model:str>
#
# Executes all required endpoints and directly starts dowloading the latest firmware with one call.
# It is useful for end-users who don't want to integrate the API in a client app.
@bp.get("/direct/<region:str>/<model:str>")
async def direct_download(request : Request, region: str, model: str):
    """
    Executes all required endpoints and directly starts dowloading the latest firmware with one call.\n
    It is useful for end-users who don't want to integrate the API in a client app.
    """
    version = await get_firmware_list(request, region, model)
    version_data = loads(version.body)
    binary = await get_binary_details(request, region, model, version_data["latest"])
    binary_data = loads(binary.body)
    return redirect(f'/download{binary_data["path"]}{binary_data["filename"]}?decrypt={binary_data["decrypt_key"]}')
