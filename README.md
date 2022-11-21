# SamFetch

A simple Web API to download Samsung Stock ROMs from Samsung's own Kies servers, without any restriction, rate-limit, authorization or passwords. Made in Python and built with Sanic.

> **Warning**<br>
> Due to a change in Samsung servers, you can only download the latest firmware even if you asked for an older firmware. [See discussion here.](https://github.com/ysfchn/SamFetch/issues/6)

## Deploy & Use

SamFetch doesn't have any rate-limits to keep it free (as in freedom) as much as I can. However, since this can allow malicious requests (such as spams) I recommend hosting your own instance, as you will have more control over it and you will have own private instance.

SamFetch is currently tested and ready to be hosted on Docker, Heroku ([one-click deploy here](https://heroku.com/deploy?template=https://github.com/ysfchn/SamFetch)) and fly.io. As it is just Python, it should run in any Python environment by default.

You can also [run in your computer locally](#running) if you don't need to host publicly.

## Features

* It doesn't include any analytics, store cookies or have any rate-limits as it directly calls the Samsung servers without involving any 3rd party.

* As Samsung server requests authorization before serving firmwares, it is done automatically by SamFetch itself, so you don't need any authorization or add any headers on your end.

* The firmware file will directly stream to you, [while decrypting the firmware on-the-fly](#on-the-fly-decrypting), so no background-jobs, no queue, and no storing the firmware in disk. 

* SamFetch supports partial downloads with ["Range" header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Range) which means it supports pausing and resuming the download. Note that partial downloads are not allowed when decrypting has enabled, due to some problems, [see here.](#partial-downloads)

* You can configure your SamFetch instance with environment variables and edit allowed origin for CORS headers and chunk size.

## Endpoints

| Endpoint | Description      |
|:---------|:-----------------|
| <samp>/:region/:model/list</samp> | List the available firmware versions of a specified model and region. <br>The first item in the list represents the latest firmware available. |
| <samp>/:region/:model/:firmware</samp> | Returns the firmware details, such as Android version, changelog URL, <br>date and filename which is required for downloading firmware. |
| <samp>/:path/:filename</samp> | Starts downloading the firmware with given `path` and `filename` <br>which can be obtained in firmware details endpoint. <br>For decrypting, [add the given key as `decrypt` query parameter.](#on-the-fly-decrypting)<br>Also optionally, `filename` query parameter overwrites the <br>filename of the downloaded file. |

### Redirects

| Endpoint | Description      |
|:---------|:-----------------|
| <samp>/:region/:model/latest</samp> | Gets the latest firmware version for the device and <br>redirects to `/:region/:model/:firmware`. |
| <samp>/:region/:model/latest/download</samp> | Gets the latest firmware version for the device and <br>redirects to `/:region/:model/:firmware/download`. |
| <samp>/:region/:model/:firmware/download</samp> | Gets the firmware details for the device and <br>redirects to `/file/:path/:filename` with `decrypt` parameter. |

## Envrionment Variables

| Variable | Description      |
|:---------|:-----------------|
| `SAMFETCH_HIDE_TEXT` | Hides the text shown when visiting the root path. |
| `SAMFETCH_ALLOW_ORIGIN` | Sets the "Access-Control-Allow-Origin" header value. Settings this to "\*" (wildcard) allows all domains to access this SamFetch instance. Default is set to "\*". |
| `SAMFETCH_CHUNK_SIZE` | Specifies how many bytes must read in a single iteration when downloading the firmware. Default is set to 1485760 (1 megabytes), bigger chunk size means faster but uses more resources. |

## On-the-fly Decrypting

Samsung stores firmwares as encrypted. This means, in normally you are expected to download the encrypted firmware, and decrpyt it afterwards locally. However with SamFetch, the firmware file will directly stream to you, while decrypting the firmware on-the-fly, so no background-jobs, no queue, and no storing the firmware in disk. 

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

If you prefer to decrypt firmwares manually, sadly you can't do it with SamFetch (as it is an web application not a CLI), but you can use [Samloader](https://github.com/nlscc/samloader) which has a `decrypt` command.

### Partial downloads

When an encrypted file has decrypted, the file size becomes slightly different from the encrypted file. The thing is, SamFetch reports the firmware size, so you can see a progress bar and ETA in your browser. However, when the decrypted size is not equal with actual size, this will result in a failed download in 99%. To fix failed downloads, **SamFetch won't report the firmware size when decrypting has enabled.**

## Running

Install dependencies with `pip install -r requirements.txt` and run with:

```
sanic main.app
```

Visit the URL you see in the console to get started with SamFetch.

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

## Resources

If you want to do more with Samsung firmwares, or SamFetch is not enough for you, or just want to learn more stuff, you can check [resources](RESOURCES.md).

## Credits

This is a Web API variant of [Samloader](https://github.com/nlscc/samloader) project. I reimplemented the Samloader's functions as Web API routes and simplified the code for end-user to eliminate the authorization request, so SamFetch wouldn't be possible without Samloader.

## License

This project is licensed with AGPLv3.
