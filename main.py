import os
from sanic import Sanic, Request, HTTPResponse
from sanic.response import redirect, text, empty
from httpx import HTTPError, NetworkError
from web import bp, SamfetchError, make_error

def get_env_int(name : str, default) -> int:
    if name not in os.environ:
        return default
    _val = os.environ[name]
    if _val.isnumeric():
        return int(_val)
    else:
        return default


def get_env_bool(name : str, default : bool) -> bool:
    return bool(get_env_int(name, default))


# Environment variables
app = Sanic("SamFetch")
app.config.SAMFETCH_HIDE_TEXT = get_env_bool("SAMFETCH_HIDE_TEXT", False)
app.config.SAMFETCH_ALLOW_ORIGIN = os.environ.get("SAMFETCH_ALLOW_ORIGIN", None) or "*"
app.config.SAMFETCH_CHUNK_SIZE = get_env_int("SAMFETCH_CHUNK_SIZE", 1485760)
app.config.FALLBACK_ERROR_FORMAT = "json"


NOTICE = """
          _____                 ______   _       _     
         / ____|               |  ____| | |     | |    
        | (___   __ _ _ __ ___ | |__ ___| |_ ___| |__  
         \\___ \\ / _` | '_ ` _ \\|  __/ _ \\ __/ __| '_ \\ 
         ____) | (_| | | | | | | | |  __/ || (__| | | |
        |_____/ \\__,_|_| |_| |_|_|  \\___|\\__\\___|_| |_|

        A simple HTTP API to download Samsung Stock ROMs from Samsung's own servers without any restriction.
        It doesn't have any analytics, rate-limits, download speed limit, authorization or any crap that you don't want.
        
        SamFetch pulls firmware files from Samsung's servers and sends back to you, so it acts like a proxy. 
        Samsung's own firmwares are encrypted, but SamFetch can decrypt the firmware on-the-fly! This is an opt-in
        behavior, means you can also get the original, encrypted firmware if you want.

        ---

        SamFetch is free & open source, licensed under AGPLv3.
        https://github.com/ysfchn/SamFetch

        This is a Web API variant of samloader (https://github.com/nlscc/samloader).
        SamFetch wouldn't be possible without Samloader.
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
        raise make_error(SamfetchError.NETWORK_ERROR, 500)
    else:
        raise make_error(SamfetchError.GENERIC_HTTP_ERROR, 500)


@app.get("/")
async def home(request : Request):
    return empty() if request.app.config.SAMFETCH_HIDE_TEXT else \
    text(("\n".join(x.replace("        ", "  ", 1) for x in NOTICE.splitlines()) + "\n\n"))


@app.get("/github")
async def github(request : Request):
    return redirect("https://github.com/ysfchn/SamFetch")

# Register blueprint.
app.blueprint(bp)
