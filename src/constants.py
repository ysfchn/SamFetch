import dicttoxml

class Constants:

    # Get firmware information url
    GET_FIRMWARE_URL = "http://fota-cloud-dn.ospserver.net/firmware/{0}/{1}/version.xml"

    # Generate nonce url
    NONCE_URL = "https://neofussvr.sslcs.cdngc.net/NF_DownloadGenerateNonce.do"

    # Binary information url
    BINARY_INFO_URL = "https://neofussvr.sslcs.cdngc.net/NF_DownloadBinaryInform.do"

    # Binary file url
    BINARY_FILE_URL = "https://neofussvr.sslcs.cdngc.net/NF_DownloadBinaryInitForMass.do"

    # Binary download url
    BINARY_DOWNLOAD_URL = "http://cloud-neofussvr.sslcs.cdngc.net/NF_DownloadBinaryForMass.do"

    HEADERS = lambda nonce = "", signature = "": \
        {
            "Authorization": f'FUS nonce="{nonce}", signature="{signature}", nc="", type="", realm="", newauth="1"',
            "User-Agent": "Kies2.0_FUS"
        }

    COOKIES = lambda session_id = "": {"JSESSIONID": session_id}

    # Build parameters
    PARAMETERS = lambda data = None, nonce = "", signature = "", session_id = "": \
        {
            "headers": {
                "Authorization": f'FUS nonce="{nonce}", signature="{signature}", nc="", type="", realm="", newauth="1"',
                "User-Agent": "Kies2.0_FUS"
            },
            "data": data
        }
    
    BINARY_INFO = lambda firmware_version, region, model, logic_check: \
        dicttoxml.dicttoxml({
            "FUSMsg": {
                "FUSHdr": {"ProtoVer": "1.0"}, 
                "FUSBody": {
                    "Put": {
                        "ACCESS_MODE": {"Data": "2"},
                        "BINARY_NATURE": {"Data": "1"},
                        "CLIENT_PRODUCT": {"Data": "Smart Switch"},
                        "DEVICE_FW_VERSION": {"Data": firmware_version},
                        "DEVICE_LOCAL_CODE": {"Data": region},
                        "DEVICE_MODEL_NAME": {"Data": model},
                        "LOGIC_CHECK": {"Data": logic_check}
                    }
                }
            }
        }, attr_type = False, root = False)

    BINARY_FILE = lambda filename, logic_check: \
        dicttoxml.dicttoxml({
            "FUSMsg": {
                "FUSHdr": {"ProtoVer": "1.0"}, 
                "FUSBody": {
                    "Put": {
                        "BINARY_FILE_NAME": {"Data": filename},
                        "LOGIC_CHECK": {"Data": logic_check}
                    }
                }
            }
        }, attr_type = False, root = False)

    # It doesn't have a use (yet).
    # Maybe we can implement region control to endpoints before making a request?
    US_CARRIERS = {
        "ACG": "Nextech / C-Spire branded",
        "ATT": "AT&T branded",
        "BST": "BST (unknown)",
        "CCT": "Comcast branded",
        "GCF": "GCF (unknown)",
        "LRA": "Bluegrass Cellular branded",
        "SPR": "Sprint (CDMA) branded",
        "TFN": "Tracfone branded ",
        "TMB": "T-Mobile branded",
        "USC": "USA unbranded",
        "VMU": "Virgin Mobile USA branded",
        "VZW": "Verizon branded",
        "XAA": "USA unbranded (default)",
        "XAS": "XAS (unknown)"
    }

    # It doesn't have a use (yet).
    # Maybe we can implement region control to endpoints before making a request?
    CANADA_CARRIERS = {
        "BMC": "Bell Mobile branded",
        "BWA": "SaskTel branded",
        "CHR": "Canada (unknown)",
        "ESK": "EastLink branded",
        "FMC": "Fido Mobile branded",
        "GLW": "Globalive Wind Mobile branded",
        "KDO": "Koodo Mobile branded",
        "MTB": "Belarus branded",
        "RWC": "Rogers branded",
        "TLS": "Telus branded",
        "VMC": "Virgin Mobile branded",
        "VTR": "Vidéotron branded",
        "XAC": "Canada unbranded (default)"
    }

    # It doesn't have a use (yet).
    # Maybe we can implement region control to endpoints before making a request?
    VODAFONE_CARRIERS = {
        "ATL": "Spain Vodafone branded",
        "AVF": "Albania Vodafone branded",
        "CNX": "Romania Vodafone branded",
        "CYV": "Cyprus Vodafone branded",
        "MOB": "Austria A1 branded",
        "MTL": "Bulgaria MTL branded",
        "OMN": "Italy Vodafone branded",
        "PRO": "Belgium Proximus branded",
        "SIM": "Slovenia Si.mobile branded",
        "SWC": "Switzerland Swisscom branded",
        "TCL": "Portugal Vodafone branded",
        "VD2": "Germany Vodafone branded (default)",
        "VDC": "Czech Republic Vodafone branded",
        "VDF": "Netherlands Vodafone branded",
        "VDH": "Hungary Vodafone branded",
        "VDI": "Ireland Vodafone branded",
        "VGR": "Greece Vodafone branded",
        "VIP": "Croatia VIP-Net branded",
        "VOD": "United Kingdom Vodafone branded",
        "XFV": "South Africa Vodafone branded"
    }

    # It doesn't have a use (yet).
    # Maybe we can implement region control to endpoints before making a request?
    COUNTRIES = {}

    CSC_CODES = {**VODAFONE_CARRIERS, **COUNTRIES, **CANADA_CARRIERS, **US_CARRIERS}