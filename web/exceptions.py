__all__ = [
    "SamfetchError",
    "make_error"
]

from enum import Enum
from sanic.exceptions import SanicException


class SamfetchError(Enum):
    # Region or model is incorrect.
    DEVICE_NOT_FOUND = "device_not_found"

    # Device is correct, but doesn't have an available firmware.
    FIRMWARE_LIST_EMPTY = "firmware_list_empty"

    # Device is correct, but having troubles when parsing the firmware list.
    FIRMWARE_CANT_PARSE = "firmware_cant_parse"

    # Firmware details not available because firmware is not found. 
    FIRMWARE_NOT_FOUND = "firmware_not_found"

    # Firmware found but couldn't be downloaded anymore.
    FIRMWARE_LOST = "firmware_lost"

    # Kies server returned a non 2xx status code
    # (payload).
    KIES_SERVER_ERROR = "kies_server_error"

    # Kies server returned a non 2xx status code
    # (not payload, actual server response status).
    KIES_SERVER_OUTER_ERROR = "kies_server_outer_error"

    # The server can't establish a HTTP connection to Kies endpoints.
    # (caused by no connection)
    NETWORK_ERROR = "network_error"

    # Non-handled HTTP request errors.
    GENERIC_HTTP_ERROR = "generic_http_error"

    # Range header is invalid.
    RANGE_HEADER_INVALID = "range_header_invalid"


ERROR_MESSAGES = {
    SamfetchError.DEVICE_NOT_FOUND: \
        "Couldn't get a list of firmwares, probably model or region is incorrect.",
    SamfetchError.FIRMWARE_LIST_EMPTY: \
        "No available firmware found for this device and region.",
    SamfetchError.FIRMWARE_CANT_PARSE: \
        "Looks like we got some firmware information, however SamFetch can't parse it due to it is represented in unknown format. " +
        "It is known that both new and old devices doesn't return same data. You can create a new Issue, so it can be helpful for fixing the problem.",
    SamfetchError.FIRMWARE_NOT_FOUND: \
        "Firmware couldn't be found.",
    SamfetchError.FIRMWARE_LOST: \
        "Sadly, it is not possible to download the firmware, because Samsung no longer serves this firmware.",
    SamfetchError.KIES_SERVER_ERROR: \
        "Kies server returned a non-expected status code. This could be due to a change in their end or invalid requests made by SamFetch. " +
        "You can create a new Issue, so it can be helpful for fixing the problem.",
    SamfetchError.KIES_SERVER_OUTER_ERROR: \
        "Kies server returned a non-expected status code. This may be because their servers are down. " +
        "Try again to see if it's a temporary issue.",
    SamfetchError.NETWORK_ERROR: \
        "SamFetch has lost connection with Kies servers. If you are running SamFetch locally, make sure you " + \
        "have an internet connection. If you are hosting SamFetch on cloud, check if something blocks the making HTTP requests.",
    SamfetchError.GENERIC_HTTP_ERROR: \
        "SamFetch couldn't connect to Kies servers. Trying again may fix the issue. " + \
        "If you still get this message, you can create a new Issue, so it can be helpful for fixing the problem.",
    SamfetchError.RANGE_HEADER_INVALID: \
        "Range header has an invalid range."
}

def make_error(enum : SamfetchError, status_code : int) -> SanicException:
    return SanicException(
        message = ERROR_MESSAGES.get(enum, "(No error message.)"),
        status_code = status_code,
        context = {
            "id": enum.value
        }
    )