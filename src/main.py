from typing import Iterator, Optional
import xmltodict
import requests
import json
import os

# Helper modules
from src.session import Session
from src.csc_list import CSC
from src.utils import Constants, Decryptor, KiesData

# FastAPI
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

_ = """
    A simple Web API to download Samsung Stock ROMs from Samsung's own servers without any restriction.
    It doesn't have any analytics, rate-limits, download speed limit, authorization or any crap that you don't want. 

    This project is licensed with AGPLv3.\n
    [https://github.com/ysfchn/SamFetch](https://github.com/ysfchn/SamFetch)

    This is a Web API variant of [samloader](https://github.com/nlscc/samloader). SamFetch wouldn't be possible without Samloader.
    
    ### Usage

    * If you want to integrate SamFetch in your application; you can use **developer** endpoints.\n
    * But if you just want to download the latest firmware without building a client app, just append region (CSC) and model to the end of url. (Remove other paths if exists)
    For example `.../TUR/SM-N920C`. After visiting to the URL, the firmware should start downloading instantly.
    """


app = FastAPI(
    title = "SamFetch",
    description = _.replace("    ", ""),
    docs_url = "/"
)

# Allow other origins, so everyone can access the service.
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["DELETE", "GET", "POST", "PUT"],
    allow_headers = ["*"]
)


# /api/csc
#
# Returns a known list of CSC/region codes. 
# Note that it doesn't give a warranty about having all CSC codes.
@app.get('/api/csc', tags = ["developer"], summary = "Returns a known list of CSC/region codes.")
def list_csc():
    """
    Returns a known list of CSC/region codes. Note that it doesn't give a warranty about having all CSC codes.
    """
    return CSC


# /api/list
#
# List the available firmware versions of a specified model and region.
# Use latest key to get latest firmware code.
#
# {
#   "latest": "N920CXXU5CRL3/N920COJV4CRB3/N920CXXU5CRL1/N920CXXU5CRL3",
#   "alternate": []
# }
@app.get('/api/list', tags = ["developer"], summary = "List the available firmware versions of a specified model and region.")
async def list_firmwares(region: str, model: str):
    """
    List the available firmware versions of a specified model and region.
    Use latest key to get latest firmware code.
    """
    # Request
    URL = Constants.GET_FIRMWARE_URL.format(region, model)
    r = requests.get(URL)
    # Check status.
    if r.status_code != 200:
        # Raise HTTPException when device couldn't be found.
        raise HTTPException(r.status_code, f"The service returned {r.status_code}. Maybe parameters are invalid?")
    req = xmltodict.parse(r.text, dict_constructor=dict)
    # Check if model is correct by checking the "versioninfo" key.
    if "versioninfo" in req:
        # Parse latest firmware version.
        versions = req["versioninfo"]["firmware"]["version"]
        # Check if value is None.
        if not versions.get("latest"):
            raise HTTPException(404, "No firmware found. Maybe parameters are invalid?")
        # Return the firmware data.
        return {
            # The are cases that "latest" key may return a dictionary or just a string in different regions and models.
            # If the "latest" field is dictionary, get the inner text, otherwise get its value directly.
            "latest": Constants.parse_firmware(versions["latest"] if isinstance(versions["latest"], str) else versions["latest"]["#text"]),
            # Some devices may contain alternate/older versions too, so include them with the response.
            "alternate": [Constants.parse_firmware(x["#text"]) for x in versions["upgrade"]["value"] or []]
        }
    else:
        # Raise HTTPException when device couldn't be found.
        raise HTTPException(404, "No firmware found. Maybe parameters are invalid?")


# /api/binary
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
@app.get('/api/binary', tags = ["developer"], summary = "Gets the binary details such as filename and decrypt key.")
async def get_binary_details(region: str, model: str, firmware: str):
    """
    Gets the binary details such as filename and decrypt key.\n
    `firmware` is the firmware code of the device that you got from `/latest` endpoint.\n\n
    `decrypt_key` is used for decrypting the file after downloading. It presents a hex string. Pass it to `/download` endpoint.
    """
    # Create new session.
    key = Session.from_response(requests.post(Constants.NONCE_URL, headers = Constants.HEADERS()))
    # Make the request.
    req = requests.post(
        url = Constants.BINARY_INFO_URL,
        data = Constants.BINARY_INFO(firmware, region, model, key.logic_check(firmware)),
        headers = Constants.HEADERS(key.encrypted_nonce, key.auth),
        cookies = Constants.COOKIES(key.session_id)
    )
    # Read the request.
    if req.status_code == 200:
        data = KiesData(req.text)
        # Return error when binary couldn't be found.
        if data.status_code != "200":
            raise HTTPException(400, "Firmware couldn't be found.")
        # If file extension ends with .enc4 that means it is using version 4 encryption, otherwise 2 (.enc2).
        _encrypt_version = 4 if str(data.body["BINARY_NAME"]).endswith("4") else 2
        # Get binary details
        return {
            "display_name": data.body["DEVICE_MODEL_DISPLAYNAME"],
            "size": int(data.body["BINARY_BYTE_SIZE"]),
            "filename": data.body["BINARY_NAME"],
            "path": data.body["MODEL_PATH"],
            "version": data.body["CURRENT_OS_VERSION"].replace("(", " ("),
            "encrypt_version": _encrypt_version,
            # Convert bytes to GB, so it will be more readable for an end-user.
            "size_readable": "{:.2f} GB".format(float(data.body["BINARY_BYTE_SIZE"]) / 1024 / 1024 / 1024),
            # Generate decrypted key for decrypting the file after downloading.
            # Decrypt key gives a list of bytes, but as it is not possible to send as query parameter, 
            # we are converting it to a single HEX value.
            "decrypt_key": \
                key.getv2key(firmware, model, region).hex() if _encrypt_version == 2 else \
                key.getv4key(data.body["LATEST_FW_VERSION"], data.body["LOGIC_VALUE_FACTORY"]).hex(),
            "firmware_catalog_url": data.body["DESCRIPTION"]
        }
    # Raise HTTPException when status is not 200.
    raise HTTPException(500, "Something went wrong when sending request to Kies servers.")


# /api/download
#
# Downloads the firmware and decrypts the file during download automatically. 
@app.get('/api/download', tags = ["developer"], summary = "Downloads the firmware and decrypts it.")
async def download_binary(filename: str, path: str, decrypt_key: str, request : Request):
    """
    Downloads the firmware and decrypts the file during download automatically.\n
    **Do not try the endpoint in the interactive API docs, because as it returns a file, it doesn't work in OpenAPI.** 
    """
    # Create new session.
    key = Session.from_response(requests.post(Constants.NONCE_URL, headers = Constants.HEADERS()))
    # Make the request.
    req = requests.post(
        url = Constants.BINARY_FILE_URL,
        data = Constants.BINARY_FILE(filename, key.logic_check(filename.split(".")[0][-16:])),
        headers = Constants.HEADERS(key.encrypted_nonce, key.auth),
        cookies = Constants.COOKIES(key.session_id)
    )
    # Refresh session.
    key.refresh_session(req)
    # Read the request.
    if req.status_code == 200:
        data = KiesData(req.text)
        # Return error when binary couldn't be found.
        if data.status_code != "200":
            raise HTTPException(int(data.status_code), f"The service returned {data.status_code}. Maybe parameters are invalid?")
        # Else, make another request to get the binary.
        else:
            # Check and parse the range header.
            START_RANGE, END_RANGE = (0, 0) if "Range" not in request.headers else Constants.parse_range_header(request.headers["Range"])
            # Check if range is invalid.
            if START_RANGE == -2 or END_RANGE == -2:
                raise HTTPException(416, "Range is invalid. If you didn't meant input a 'Range' header, remove it from request.")
            # Create headers.
            _headers = Constants.HEADERS(key.encrypted_nonce, key.auth)
            # If incoming request contains a Range header, directly pass it to request.
            if "Range" in _headers:
                _headers["Range"] = "bytes=" + Constants.make_range_header(START_RANGE, END_RANGE)
            # Another request for streaming the firmware.
            req2 = requests.get(
                url = Constants.BINARY_DOWNLOAD_URL,
                params = "file=" + path + filename,
                headers = _headers,
                cookies = Constants.COOKIES(key.session_id),
                stream = True
            )
            # Check if status code is not 200 or 206.
            if req2.status_code not in [200, 206]:
                # Raise HTTPException when status is not success.
                raise HTTPException(req2.status_code, f"The service returned {req2.status_code}. Maybe parameters are invalid?")
            # Get the total size of binary.
            CONTENT_LENGTH = int(req2.headers["Content-Length"]) - 10
            # Decrypt bytes while downloading the file.
            # So this way, we can directly serve the bytes to the client without downloading to the disk.
            return StreamingResponse(
                Decryptor(req2, bytes.fromhex(decrypt_key)), 
                media_type = "application/zip",
                headers = { 
                    "Content-Disposition": "attachment;filename=" + filename.replace(".enc4", "").replace(".enc2", ""),
                    "Content-Length": str(CONTENT_LENGTH),
                    "Accept-Ranges": "bytes",
                    "Content-Range": f"bytes {Constants.make_range_header(START_RANGE, END_RANGE)}"
                },
                status_code = 200 if not START_RANGE else 206
            )
    # Raise HTTPException when status is not 200.
    raise HTTPException(500, "Something went wrong when sending request to Kies servers.")


# /{region}/{model}
#
# Executes all required endpoints and directly starts dowloading the latest firmware with one call.
# It is useful for end-users who don't want to integrate the API in a client app.
@app.get('/{region}/{model}', tags = ["end-user"], summary = "Download latest firmware directly for end-users.")
async def automatic_download(region: str, model: str, request : Request):
    """
    Executes all required endpoints and directly starts dowloading the latest firmware with one call.\n
    It is useful for end-users who don't want to integrate the API in a client app.\n
    **Do not try the endpoint in the interactive API docs, because as it returns a file, it doesn't work in OpenAPI.** 
    """
    version = await list_firmwares(region, model)
    binary = await get_binary_details(region, model, version["latest"])
    return await download_binary(binary["filename"], binary["path"], binary["decrypt_key"], request)
