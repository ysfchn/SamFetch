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

    # Build custom headers so Kies servers will think the
    # request is coming from the Kies client.
    HEADERS = lambda nonce = "", signature = "": \
        {
            "Authorization": f'FUS nonce="{nonce}", signature="{signature}", nc="", type="", realm="", newauth="1"',
            "User-Agent": "Kies2.0_FUS"
        }

    COOKIES = lambda session_id = "": {"JSESSIONID": session_id}
    
    # Creates data for sending to BINARY_INFO_URL
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

    # Creates data for sending to BINARY_FILE_URL
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