# SamFetch

A simple Web API and a module to download Samsung Stock ROMs from Samsung's own Kies servers, without any restriction, rate-limit, authorization, cookies, analytics, passwords and any 3rd party. 

The firmware file will directly stream to you, [while decrypting the firmware on-the-fly](#on-the-fly-decrypting), so no background-jobs, no queue, and no pre-storing the firmware in disk.

Made in Python, and web server has built with Sanic.

> **Warning**<br>
> Due to a change in Samsung servers, you can only download the latest firmware even if you asked for an older firmware. [See discussion here.](https://github.com/ysfchn/SamFetch/issues/6)

---

* [Web Server](#web-server)
    * [Running](#running)
    * [Endpoints](#endpoints)
    * [Environment variables](#envrionment-variables)
* [Module](#module)
    * [Low-level functions](#low-level-functions)
* [Topics](#topics)
    * [On-the-fly decrypting](#on-the-fly-decrypting)
    * [Partial downloads](#partial-downloads)
    * [Verifying downloads](#verifying-downloads)

---

## Web Server

SamFetch can be run as web server which provides a simple API to get information about and download given firmware version. Web-specific code can be found in [`web/`](web/) directory.

> SamFetch doesn't have any rate-limits to keep it free (as in freedom) as much as I can. However, since this can allow malicious requests (such as spams) I recommend hosting your own instance, as you will have more control over it and you will have own private instance.

### Running

SamFetch is currently tested and ready to be hosted on Docker, Heroku ([one-click deploy here](https://heroku.com/deploy?template=https://github.com/ysfchn/SamFetch)) and fly.io. As it is just Python, it should run in any Python environment by default.

To run locally, install dependencies with `pip install -r requirements.txt` and run with:

```
sanic main.app
```

Visit the URL you see in the console to get started with SamFetch.

<details>
    <summary>Examples</summary>

```bash
$ curl http://127.0.0.1:8000/firmware/TUR/SM-N920C/latest -L
{
    "display_name": "Galaxy Note5",
    "size": 2530817088,
    "size_readable": "2.36 GB",
    "filename": "SM-N920C_1_20190117104840_n2lqmc6w6w_fac.zip.enc4",
    "path": "/neofus/9/",
    "version": "Nougat (Android 7.0)",
    "encrypt_version": 4,
    "last_modified": 20190117144207,
    "decrypt_key": "0727c304eea8a4d14835a4e6b02c0ce3",
...

$ curl http://127.0.0.1:8000/file/neofus/9/SM-N920C_1_20220819152351_1eub6wdeqb_fac.zip.enc4?decrypt=22992da4a7f887d1c4f5bdc66d116367 -O .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 27.0M    0 27.0M    0     0  1282k      0 --:--:--  0:00:21 --:--:-- 1499k

$ curl http://127.0.0.1:8000/file/neofus/9/SM-N920C_1_20220819152351_1eub6wdeqb_fac.zip.enc4 -O .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0 2413M    0 17.1M    0     0  2604k      0  0:15:48  0:00:06  0:15:42 3651k
```
</details> 

### Endpoints

| Endpoint | Description      |
|:---------|:-----------------|
| <samp>/:region/:model/list</samp> | List the available firmware versions of a specified model and region. <br>The first item in the list represents the latest firmware available. |
| <samp>/:region/:model/:firmware</samp> | Returns the firmware details, such as Android version, changelog URL, <br>date and filename which is required for downloading firmware. |
| <samp>/file/:path/:filename</samp> | Starts downloading the firmware with given `path` and `filename` <br>which can be obtained in firmware details endpoint. <br>For decrypting, [add the given key as `decrypt` query parameter.](#on-the-fly-decrypting)<br>Also optionally, `filename` query parameter overwrites the <br>filename of the downloaded file. |
| <samp>/:region/:model/latest</samp> | Gets the latest firmware version for the device and <br>redirects to `/:region/:model/:firmware`. |
| <samp>/:region/:model/latest/download</samp> | Gets the latest firmware version for the device and <br>redirects to `/:region/:model/:firmware/download`. |
| <samp>/:region/:model/:firmware/download</samp> | Gets the firmware details for the device and <br>redirects to `/file/:path/:filename` with `decrypt` parameter. |

### Envrionment variables

| Variable | Description      |
|:---------|:-----------------|
| `SAMFETCH_HIDE_TEXT` | Hides the text shown when visiting the root path. |
| `SAMFETCH_ALLOW_ORIGIN` | Sets the "Access-Control-Allow-Origin" header value. Settings this to "\*" (wildcard) allows all domains to access this SamFetch instance. Default is set to "\*". |
| `SAMFETCH_CHUNK_SIZE` | Specifies how many bytes must read in a single iteration when downloading the firmware. Default is set to 1485760 (1 megabytes), bigger chunk size means faster but uses more resources. |

---

## Module

SamFetch can be used as module too.

```py
from samfetch import Device

# Create a new device.
device = Device("TUR", "SM-N920C")

# List available firmwares. First one in the list
# is the latest firmware.
firmwares = device.list_firmware()
```

### Low-level functions

* `samfetch.kies.KiesRequest` class contains premade HTTP Request objects which you can send them as-is with `httpx.Client.send`.
* `samfetch.kies.KiesUtils` class contains static functions for parsing firmware version strings.
* `samfetch.kies.KiesConstants` class for creating Kies request payloads (XML data).
* `samfetch.kies.KiesData` class for parsing Kies responses.
* `samfetch.crypto` module for creating authorization keys and decrypting firmware

---

## Topics

### On-the-fly decrypting

Samsung stores firmwares as encrypted. This means, in normally you are expected to download the encrypted firmware, and decrpyt it afterwards locally. However with SamFetch, the firmware file will directly stream to you, while decrypting the firmware on-the-fly, so no background-jobs, no queue, and no pre-storing the firmware in disk. 

<details>
    <summary>Web Server</summary><br>

**This behavior is opt-in**, so if you want SamFetch to decrypt the firmware on-the-fly, you need to insert the decryption key that you can also get it from SamFetch.

```bash
# Decrypt key can be found in firmware details.
$ curl http://127.0.0.1:8000/firmware/TUR/SM-N920C/latest -L | jq .decrypt_key
"22992da4a7f887d1c4f5bdc66d116367"

# Join path and filename. Add decryption key as "decrypt" query parameter
# The output is the URL path of the download.
$ curl http://127.0.0.1:8000/firmware/TUR/SM-N920C/latest -L | jq '.path + .filename + "?decrypt=" + .decrypt_key'
"/neofus/9/SM-N920C_1_20220819152351_1eub6wdeqb_fac.zip.enc4?decrypt=22992da4a7f887d1c4f5bdc66d116367"

# SamFetch also returns the full URLs in the response.
$ curl http://127.0.0.1:8000/firmware/TUR/SM-N920C/latest -L | jq '.download_path_decrypt'
"http://127.0.0.1:8000/file/neofus/9/SM-N920C_1_20220819152351_1eub6wdeqb_fac.zip.enc4?decrypt=22992da4a7f887d1c4f5bdc66d116367"
```
</details> 

### Partial downloads

When an encrypted file has decrypted, the file size becomes slightly different from the encrypted file. The thing is, SamFetch reports the firmware size, so you can see a progress bar and ETA in your browser. However, when the decrypted size is not equal with actual size, this will result in a failed download in 99%. To fix failed downloads, **SamFetch won't report the firmware size when decrypting has enabled.**

### Verifying downloads

As SamFetch doesn't pre-store firmware files, it is not possible to validate the downloaded files. Kies servers returns a CRC value but it is only for the encrypted file.

---

## Resources

If you want to do more with Samsung firmwares, or SamFetch is not enough for you, or just want to learn more stuff, you can check [resources](RESOURCES.md).

## Credits

This is a Web API variant of [Samloader](https://github.com/nlscc/samloader) project. I reimplemented the Samloader's functions as Web API routes and simplified the code for end-user to eliminate the authorization request, so SamFetch wouldn't be possible without Samloader.

## License

This project is licensed with AGPLv3 (or later).
