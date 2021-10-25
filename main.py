import os
from sanic import Sanic, Request, HTTPResponse
from sanic.exceptions import SanicException
from sanic.response import redirect, text, empty
from httpx import HTTPError


app = Sanic("SamFetch")
app.config.SAMFETCH_HIDE_TEXT = os.environ.get("SAMFETCH_HIDE_TEXT", None) or 0
app.config.SAMFETCH_ALLOW_ORIGIN = os.environ.get("SAMFETCH_ALLOW_ORIGIN", None) or "*"
app.config.SAMFETCH_CHUNK_SIZE = os.environ.get("SAMFETCH_CHUNK_SIZE", None) or 10485760
app.config.FALLBACK_ERROR_FORMAT = "json"


@app.middleware("response")
async def set_cors(request : Request, response : HTTPResponse):
    response.headers["Access-Control-Allow-Origin"] = request.app.config.SAMFETCH_ALLOW_ORIGIN
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, POST, PUT, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"


@app.exception(HTTPError)
async def http_error(request : Request, exception : HTTPError):
    raise SanicException(message = \
        "An inner Kies request has failed. If you think you shouldn't get this error, " + \
        "make sure you reported that in the SamFetch repository. " + \
        str(exception.args), 
        status_code = 500
    )


@app.get("/")
async def home(request : Request):
    return empty() if request.app.config.SAMFETCH_HIDE_TEXT else \
    text(
        """
        # SamFetch

        A simple Web API to download Samsung Stock ROMs from Samsung's own servers without any restriction.
        It doesn't have any analytics, rate-limits, download speed limit, authorization or any crap that you don't want.

        This project is licensed with AGPLv3.\n
        https://github.com/ysfchn/SamFetch

        ## Credits

        This is a Web API variant of [samloader](https://github.com/nlscc/samloader).
        SamFetch wouldn't be possible without Samloader.
        
        ## Endpoints

        /csc                                    Lists all available CSC.
                                                Note that the list may be incomplete.

        /list/<REGION>/<MODEL>                  Lists all firmware versions for a specific
                                                device and region. 

        /binary/<REGION>/<MODEL>/<FIRMWARE>     Gets details for a firmware such as download
                                                size, file name and decryption key. You can
                                                get firmware from /list endpoint.

        /download/<DECRYPT_KEY>/<PATH>/<FILE>   Downloads a firmware while decrypting it. You
                                                can get decrypt key, path and file from
                                                /binary endpoint.

        /download/<PATH>/<FILE>                 Downloads a firmware. But it doesn't decrypt
                                                while downloading, so you need to decrypt
                                                yourself. Downloading without decrypting
                                                can speed up the download a bit. You
                                                can get path and file from /binary endpoint.

        /direct/<REGION>/<MODEL>                Fetches all endpoints and downloads the latest
                                                firmware file with decrypting.

        
        ## Environment Variables

        SAMFETCH_HIDE_TEXT                      Set the value to 1 if you don't want this
                                                landing response.

        SAMFETCH_ALLOW_ORIGIN                   Sets the "Access-Control-Allow-Origin" header
                                                value. Settings this to "*" (wildcard) allows
                                                all domains to access this SamFetch instance.
                                                Default is set to "*".

        SAMFETCH_CHUNK_SIZE                     Specifies how many bytes must read in
                                                a single iteration when downloading the firmware.
                                                Default is set to 10485760 (10 megabytes)
        """
    )


@app.get("/github")
async def github(request : Request):
    return redirect("https://github.com/ysfchn/SamFetch")
