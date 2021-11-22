import os
from sanic import Sanic, Request, HTTPResponse
from sanic.exceptions import SanicException
from sanic.response import redirect, text, empty
from httpx import HTTPError, NetworkError
from web import bp

def get_env_int(name : str, default):
    if name not in os.environ:
        return default
    _val = os.environ[name]
    if _val.isnumeric():
        return int(_val)
    else:
        return default


app = Sanic("SamFetch")
app.config.SAMFETCH_HIDE_TEXT = bool(get_env_int("SAMFETCH_HIDE_TEXT", 0))
app.config.SAMFETCH_ALLOW_ORIGIN = os.environ.get("SAMFETCH_ALLOW_ORIGIN", None) or "*"
app.config.SAMFETCH_CHUNK_SIZE = get_env_int("SAMFETCH_CHUNK_SIZE", 1485760)
app.config.FALLBACK_ERROR_FORMAT = "json"


NOTICE = \
"""
          _____                 ______   _       _     
         / ____|               |  ____| | |     | |    
        | (___   __ _ _ __ ___ | |__ ___| |_ ___| |__  
         \___ \ / _` | '_ ` _ \|  __/ _ \ __/ __| '_ \ 
         ____) | (_| | | | | | | | |  __/ || (__| | | |
        |_____/ \__,_|_| |_| |_|_|  \___|\__\___|_| |_|

        A simple HTTP API to download Samsung Stock ROMs from Samsung's own servers without any restriction.
        It doesn't have any analytics, rate-limits, download speed limit, authorization or any crap that you don't want.
        
        SamFetch pulls firmware files from Samsung's servers and sends back to you. Oh, Samsung's own firmware
        files are encrypted, however, SamFetch can decrypt the firmware while sending it to you! But if you want to
        speed up the download process, you can prefer to not to decrypt the firmware and get the encrypted archive.

        This project is licensed with AGPLv3.
        https://github.com/ysfchn/SamFetch

        ## Credits

        This is a Web API variant of samloader (https://github.com/nlscc/samloader).
        SamFetch wouldn't be possible without Samloader.
        
        ## Endpoints

        /csc                                            Lists all available CSC.
                                                        Note that the list may be incomplete.

        /list/<REGION>/<MODEL>                          Lists all firmware versions for a specific
                                                        device and region. Region examples can be found
                                                        on /csc endpoint. Note that some firmwares may
                                                        be only available to specific regions.

        /binary/<REGION>/<MODEL>/<FIRMWARE>             Gets details for a firmware such as download
                                                        size, file name and decryption key. You can
                                                        get firmware from /list endpoint.

        /download/<PATH>/<FILE>?decrypt=<DECRYPT_KEY>   Downloads a firmware while decrypting it. You
                                                        can get decrypt key, path and file from
                                                        /binary endpoint.

        /download/<PATH>/<FILE>                         Downloads a firmware. But it doesn't decrypt
                                                        while downloading, so you need to decrypt
                                                        yourself. Downloading without decrypting
                                                        can speed up the download a bit. You
                                                        can get path and file from /binary endpoint.

        /direct/<REGION>/<MODEL>                        Fetches all endpoints and downloads the latest
        /<REGION>/<MODEL>                               firmware file with decrypting.

        
        ## Global Configuration

        You can set environment variables to change configuration of your SamFetch instance.

        SAMFETCH_HIDE_TEXT                              Only 0 or 1. Set the value to 1 if you don't 
                                                        want this help text.

        SAMFETCH_ALLOW_ORIGIN                           Sets the "Access-Control-Allow-Origin" header
                                                        value. Settings this to "*" (wildcard) allows
                                                        all domains to access this SamFetch instance.
                                                        Default is set to "*".

        SAMFETCH_CHUNK_SIZE                             Specifies how many bytes must read in
                                                        a single iteration when downloading the firmware.
                                                        Default is set to 1485760 (1 megabytes)
"""


@app.middleware("response")
async def set_cors(request : Request, response : HTTPResponse):
    response.headers["Access-Control-Allow-Origin"] = request.app.config.SAMFETCH_ALLOW_ORIGIN
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, POST, PUT, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"


@app.exception(HTTPError)
async def http_error(request : Request, exception : HTTPError):
    if isinstance(exception, NetworkError):
        raise SanicException(message = \
            "SamFetch has lost connection with Kies servers. If you are running SamFetch locally, make sure you " + \
            "have an internet connection. If you are currently hosting SamFetch somewhere, you can also check " + \
            "if something (such as firewall) blocking the connection. If you need help, create a new Issue in " + \
            "https://git.io/JPAbu",
            status_code = 500
        )
    else:
        raise SanicException(message = \
            "SamFetch couldn't connect to Kies servers. This is probably not related to you. " + \
            "Please try again if you didn't. Make sure you reported that in the SamFetch repository " + \
            "by creating a new Issue in " + \
            "https://git.io/JPAbu",
            status_code = 500
        )


@app.get("/")
async def home(request : Request):
    return empty() if request.app.config.SAMFETCH_HIDE_TEXT else \
    text(
        "\n".join(x.replace("        ", "  ", 1) for x in NOTICE.splitlines()) + "\n\n"
    )


@app.get("/github")
async def github(request : Request):
    return redirect("https://github.com/ysfchn/SamFetch")

# Register blueprint.
app.blueprint(bp)
