from typing import Iterator
import xmltodict
import requests
import json
import os

# Helper modules
from src.keyholder import Keyholder
from src.utils import Constants, Decryptor

# FastAPI
from fastapi import FastAPI, HTTPException
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


CSC_CODES = json.loads(open(os.path.join("src", "csc_list.json"), "r").read())



# /api/csc
#
# Returns a known list of CSC/region codes. 
# Note that it doesn't give a warranty about having all CSC codes.
@app.get('/api/csc', tags = ["developer"], summary = "Returns a known list of CSC/region codes.")
def list_csc():
    """
    Returns a known list of CSC/region codes. Note that it doesn't give a warranty about having all CSC codes.
    """
    return CSC_CODES


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
def list_firmwares(region: str, model: str):
    """
    List the available firmware versions of a specified model and region.
    Use latest key to get latest firmware code.
    """
    # Request
    URL = Constants.GET_FIRMWARE_URL.format(region, model)
    r = requests.get(URL)
    req = xmltodict.parse(r.text)
    # Check if model is correct by checking the "versioninfo" key.
    if "versioninfo" in req:
        # Parse latest firmware version.
        l = req["versioninfo"]["firmware"]["version"]["latest"]
        # Check if value is None.
        if l == None:
            raise HTTPException(404, "No firmware found. Please check region and model again.")
        # If the latest field is dictionary, get the inner text, otherwise get its value directly.
        latest = Constants.parse_firmware(l if isinstance(l, str) else l["#text"])
        # Parse alternate firmware version.
        # If none, it will return a empty list.
        alternate = [Constants.parse_firmware(x["#text"]) for x in req["versioninfo"]["firmware"]["version"]["upgrade"]["value"] or []]
        # Return latest firmware.
        return { "latest": latest, "alternate": alternate }
    else:
        # Raise HTTPException when device couldn't be found.
        raise HTTPException(404, "No firmware found. Please check region and model again.")


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
def get_binary_details(region: str, model: str, firmware: str):
    """
    Gets the binary details such as filename and decrypt key.\n
    `firmware` is the firmware code of the device that you got from `/latest` endpoint.\n\n
    `decrypt_key` is used for decrypting the file after downloading. It presents a hex string. Pass it to `/download` endpoint.
    """
    # Create new keyholder.
    key = Keyholder.from_response(requests.post(Constants.NONCE_URL, headers = Constants.HEADERS()))
    # Make the request.
    req = requests.post(
        url = Constants.BINARY_INFO_URL,
        data = Constants.BINARY_INFO(firmware, region, model, key.logic_check(firmware)),
        headers = Constants.HEADERS(key.encrypted_nonce, key.auth),
        cookies = Constants.COOKIES(key.session_id)
    )

    # Read the request.
    if req.status_code == 200:
        r = xmltodict.parse(req.text)
        # Return error when binary couldn't be found.
        if r["FUSMsg"]["FUSBody"]["Results"]["Status"] != "200":
            raise HTTPException(400, "Firmware couldn't be found.")
        # Get binary details
        result = {
            "display_name": r["FUSMsg"]["FUSBody"]["Put"]["DEVICE_MODEL_DISPLAYNAME"]["Data"],
            "size": int(r["FUSMsg"]["FUSBody"]["Put"]["BINARY_BYTE_SIZE"]["Data"]),
            "filename": r["FUSMsg"]["FUSBody"]["Put"]["BINARY_NAME"]["Data"],
            "path": r["FUSMsg"]["FUSBody"]["Put"]["MODEL_PATH"]["Data"],
            "version": r["FUSMsg"]["FUSBody"]["Put"]["CURRENT_OS_VERSION"]["Data"].replace("(", " ("),
            "encrypt_version": 4 if str(r["FUSMsg"]["FUSBody"]["Put"]["BINARY_NAME"]["Data"]).endswith("4") else 2,
        }
        result["size_readable"] = "{:.2f} GB".format(float(result["size"]) / 1024 / 1024 / 1024)
        decrypt_key = ""
        # Generate decrypted key for decrypting the file after downloading.
        # If file extension ends with .enc4 that means it is using version 4, otherwise 2 (.enc2).
        if result["encrypt_version"] == 4:
            firmware_ver = r["FUSMsg"]["FUSBody"]["Results"]["LATEST_FW_VERSION"]["Data"]
            logic_value = r["FUSMsg"]["FUSBody"]["Put"]["LOGIC_VALUE_FACTORY"]["Data"]
            decrypt_key = key.getv4key(firmware_ver, logic_value)
        else:
            decrypt_key = key.getv2key(firmware, model, region)
        # Save decrypt key.
        result["decrypt_key"] = bytearray(decrypt_key).hex()
        # Return the result
        return result
    # Raise HTTPException when status is not 200.
    raise HTTPException(500, "Something went wrong when sending request to Kies servers.")


# /api/download
#
# Downloads the firmware and decrypts the file during download automatically. 
@app.get('/api/download', tags = ["developer"], summary = "Downloads the firmware and decrypts it.")
def download_binary(filename: str, path: str, decrypt_key: str):
    """
    Downloads the firmware and decrypts the file during download automatically.\n
    **Do not try the endpoint in the interactive API docs, because as it returns a file, it doesn't work in OpenAPI.** 
    """
    # Create new keyholder.
    key = Keyholder.from_response(requests.post(Constants.NONCE_URL, headers = Constants.HEADERS()))
    # Make the request.
    req = requests.post(
        url = Constants.BINARY_FILE_URL,
        data = Constants.BINARY_FILE(filename, key.logic_check(filename.split(".")[0][-16:])),
        headers = Constants.HEADERS(key.encrypted_nonce, key.auth),
        cookies = Constants.COOKIES(key.session_id)
    )
    # Refresh keyholder.
    key.refresh_keyholder(req)
    # Return error when binary couldn't be found.
    if req.status_code == 200:
        r = xmltodict.parse(req.text)
        status_code = r["FUSMsg"]["FUSBody"]["Results"]["Status"]
        if status_code != "200":
            raise HTTPException(int(status_code), f"The service returned {status_code}. Maybe firmware couldn't be found?")
        # Else, return true.
        else:
            req2 = requests.get(
                url = Constants.BINARY_DOWNLOAD_URL,
                params = {"file": path + filename},
                headers = Constants.HEADERS(key.encrypted_nonce, key.auth),
                cookies = Constants.COOKIES(key.session_id),
                stream = True
            )
            if req2.status_code != 200:
                # Raise HTTPException when status is not 200.
                raise HTTPException(500, "Looks like Kies doesn't allow us to download the file since they changed their methods. SamFetch will be updated as soon as possible until a new fix has been discovered.")
            # Decrypt bytes while downloading the file.
            # So this way, we can directly serve the bytes to the client without downloading to the disk.
            return StreamingResponse(
                Decryptor(req2, bytes(bytearray.fromhex(decrypt_key))), 
                media_type = "application/zip",
                headers = { "Content-Disposition": "attachment;filename=" + filename.replace(".enc4", "").replace(".enc2", "") }
            )
    # Raise HTTPException when status is not 200.
    raise HTTPException(500, "Something went wrong when sending request to Kies servers.")


# /{region}/{model}
#
# Executes all required endpoints and directly starts dowloading the latest firmware with one call.
# It is useful for end-users who don't want to integrate the API in a client app.
@app.get('/{region}/{model}', tags = ["end-user"], summary = "Download latest firmware directly for end-users.")
def automatic_download(region: str, model: str):
    """
    Executes all required endpoints and directly starts dowloading the latest firmware with one call.\n
    It is useful for end-users who don't want to integrate the API in a client app.\n
    **Do not try the endpoint in the interactive API docs, because as it returns a file, it doesn't work in OpenAPI.** 
    """
    version = list_firmwares(region, model)
    binary = get_binary_details(region, model, version["latest"])
    return download_binary(binary["filename"], binary["path"], binary["decrypt_key"])
