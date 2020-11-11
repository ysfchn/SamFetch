from typing import Iterator
from Crypto.Cipher import AES
import xmltodict
import requests
import json
import os

# Helper modules
from src.keyholder import Keyholder
from src.constants import Constants

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow other origins, so everyone can access the service.
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["DELETE", "GET", "POST", "PUT"],
    allow_headers = ["*"]
)

# A custom iterator to decrypt the bytes without writing the whole file to the disk.
class Decryptor:
    """
    Decrypts the file.
    """

    def __init__(self, response : Iterator, key : str):
        self.file_iterator = response
        self.cipher = AES.new(key, AES.MODE_ECB)

    def __iter__(self):
        return self

    def __next__(self):
        chunk = next(self.file_iterator, None)
        if chunk == None:
            raise StopIteration
        else:
            return self.cipher.decrypt(chunk)

_ = """
    # SamFetch

    A simple Web API to download Samsung Stock ROMs from Samsung's own servers without any restriction.
    It doesn't have any analytics, rate-limits, download speed limit, authorization or any crap that you don't want. 
    This is a Web API variant of https://github.com/nlscc/samloader project. SamFetch wouldn't be possible without Samloader.

    You can go /docs to see a list of endpoints along with interactive API docs.

    This project is licensed with AGPLv3.
    https://github.com/ysfchn/SamFetch
    """

CSC_CODES = json.loads(open(os.path.join("src", "csc_list.json"), "r").read())



@app.get('/', response_class = PlainTextResponse)
def home():
    return _



# Returns a list of CSC/region codes.
@app.get('/csc')
def list_csc():
    """
    Returns a known list of CSC/region codes. Note that it doesn't give a warranty about having all CSC codes.
    """
    return CSC_CODES



# Get the latest firmware of a specified model and region.
@app.get('/latest')
def get_latest_firmware(region : str, model : str):
    """
    Shows the latest firmware for the device.

    **Example Response:**
    ```json
    {
        "latest": "N920CXXU5CRL3/N920COJV4CRB3/N920CXXU5CRL1/N920CXXU5CRL3"
    }
    ```
    """
    # Request
    URL = Constants.GET_FIRMWARE_URL.format(region, model)
    r = requests.get(URL)
    req = xmltodict.parse(r.text)
    # Check if model is correct by checking the "versioninfo" key.
    if "versioninfo" in req:
        # Read latest firmware code.
        latest = req["versioninfo"]["firmware"]["version"]["latest"]["#text"].split("/")
        # TODO
        # Alternative and test version will be added soon.
        if len(latest) == 3:
            latest.append(latest[0])
        if latest[2] == "":
            latest[2] = latest[0]
        # Return latest firmware.
        return { "latest": "/".join(latest)}
    else:
        # Raise HTTPException when device couldn't be found.
        raise HTTPException(404, "No firmware found. Please check region and model again.")



@app.get('/binary')
def get_binary_details(region : str, model : str, firmware : str):
    """
    Gets the binary details.\n
    `firmware` is the firmware code of the device that you got from `/latest` endpoint.

    **Example Response:**
    ```json
    {
        "display_name": "Galaxy Note5"
        "size": 2530817088,
        "size_readable": "2.36 GB",
        "filename": "SM-N920C_1_20190117104840_n2lqmc6w6w_fac.zip.enc4",
        "path": "/neofus/9/",
        "encrypt_version": 4,
        "decrypt_key": "0727c304eea8a4d14835a4e6b02c0ce3"
    }
    ```\n
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
            # "crc": r["FUSMsg"]["FUSBody"]["Put"]["BINARY_CRC"]["Data"],
            # CRC won't be included until the issue has resolved.
            # https://github.com/ysfchn/SamFetch/issues/1
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

    raise HTTPException(500, "Something went wrong when sending request to Kies servers.")



@app.get('/download')
def download_binary(filename : str, path : str, decrypt_key : str):
    """
    Downloads the firmware and decrypts the file during download automatically. 
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
            # Decrypt bytes while downloading the file.
            # So this way, we can directly serve the bytes to the client without downloading to the disk.
            return StreamingResponse(
                Decryptor(req2.iter_content(chunk_size = 0x10000), bytes(bytearray.fromhex(decrypt_key))), 
                media_type = "application/zip",
                headers = { "Content-Disposition": "attachment;filename=" + filename.replace(".enc4", "").replace(".enc2", "") }
            )
    
    raise HTTPException(500, "Something went wrong when sending request to Kies servers.")