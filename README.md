# SamFetch

A simple Web API to download Samsung Stock ROMs from Samsung's own Kies servers, without any restriction, rate-limit, authorization or passwords. Made in Python, built with Sanic, and ready to deploy to Heroku with one-click.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ysfchn/SamFetch)

> **Why you wanting us to host it ourselves instead of publishing a public instance URL?**<br>
> SamFetch doesn't have any rate-limits to keep it free (as in freedom) as much as I can. However, since this can allow malicious requests (such as spams) I recommend hosting your own instance, as you will have more control over it and you will have own private instance.
>
> After typing your app name, deploy the app and your instance will be ready! Head over to `https://<app_name>.herokuapp.com/` and you will see a home page which includes a help text.

| ⚠ **WARNING** |
|:--------------|
| Due to a change in Samsung servers, you can only download the latest firmware even if you asked for an older firmware. [This is not related to SamFetch.](https://github.com/ysfchn/SamFetch/issues/6) |

## Features

* It doesn't include any analytics, store cookies or have any rate-limits as it directly calls the Samsung servers without involving any 3rd party.

* As Samsung server requests authorization before serving firmwares, it is done automatically by SamFetch itself, so you don't need any authorization or add any headers on your end.

* It doesn't pre-download the firmware and have any background jobs/queue for downloading and decrypting the firmware, so this means the firmware file will directly stream to you, while decrypting the firmware on-the-fly. 

* SamFetch supports partial downloads with ["Range" header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Range) which means it supports pausing and resuming the download. Note that partial downloads are not allowed when decrypting has enabled, due to some problems, [see here.](#partial-downloads)

* You can configure your SamFetch instance with environment variables and edit allowed origin for CORS headers and chunk size.

## Endpoints

| Endpoint | Description      |
|:---------|:-----------------|
| <samp>/firmware/:region/:model/list</samp> | List the available firmware versions of a specified model and region. The first item in the list is the latest version (with also "is_latest" key) |
| <samp>/firmware/:region/:model/latest</samp><br><samp>/firmware/:region/:model/latest?download=1</samp> | Gets the latest firmware version for the device and redirects to `/firmware/:region/:model/:firmware`<br><br>_If "download" query parameter has provided with any value, the download will start automatically with decryption enabled. It basically redirects to next endpoint._ |
| <samp>/firmware/:region/:model/:firmware</samp><br><samp>/firmware/:region/:model/:firmware?download=1</samp> | Gets the firmware details and includes values that required for downloading the firmware such as path, filename and decryption key. To start a download, provide these values to `/download` endpoint.<br><br>_If "download" query parameter has provided with any value, the download will start automatically with decryption enabled. It basically redirects to next endpoint._ |
| <samp>/download/:path/:filename</samp><br><samp>/download/:path/:filename?decrypt=(KEY)</samp> | Downloads the firmware with given path and filename. Path, filename and decryption key can be found on `/firmware/:region/:model/:firmware` endpoint. To enable decrypting, add "decrypt" query parameter with decryption key. If "decrypt" parameter is not provided, the encrypted firmware will be downloaded instead.<br><br>Additionally, with "filename" query parameter, you can change the name of the downloaded file. If you want to do that, don't include file extension, as it will be added automatically according to non-decrypt mode and decrypt mode. |

## Running

Install dependencies with `pip install -r requirements.txt` and run with:

```
sanic main.app
```

<details>
    <summary><b>Example requests</b></summary>

    ```
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
        "firmware_changelog_url": null,
        "platform": "Android",
        "crc": "1505693374",
        "pda": {
            "bootloader": "U5",
            "date": "2018.11",
            "major": 2,
            "minor": 3
        }
    }
    ```

    ```
    $ curl http://127.0.0.1:8000/firmware/TUR/SM-N920C/list
    [
        {
            "firmware": "N920CXXU5CRL3/N920COJV4CRB3/N920CXXU5CRL1/N920CXXU5CRL3",
            "pda": {
            "bootloader": "U5",
            "date": "2018.11",
            "major": 2,
            "minor": 3
            },
            "is_latest": true
        }
    ]
    ```

    ```
    $ curl http://127.0.0.1:8000/download/neofus/9/SM-N920C_1_20190117104840_n2lqmc6w6w_fac.zip.enc4?decrypt=0727c304eea8a4d14835a4e6b02c0ce3 -O .
      % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                     Dload  Upload   Total   Spent    Left  Speed
    100 27.0M    0 27.0M    0     0  1282k      0 --:--:--  0:00:21 --:--:-- 1499k
    ```

</details>

## Notes

#### Downloading firmwares

Normally, Samsung gives firmware files as encrypted. To actually get the firmware archive, you need to decrypt it before. SamFetch can decrypt firmware files on-the-fly, so in both method (decrypt and non-decrypt) you see no difference when downloading the firmwares.

To enable decryption in `/download` endpoint, you need to give a decryption key which can be found in `/firmware/:region/:model/:firmware` endpoint. Get the `decrypt_key` and pass it to `/download` endpoint with `decrypt` query parameter.

If you prefer to decrypt firmwares manually, sadly you can't do it with SamFetch (as it is an web application not a CLI), but you can use [Samloader](https://github.com/nlscc/samloader) which has a `decrypt` command.

#### Partial downloads

When an encrypted file has decrypted, the file size becomes slightly different from the encrypted file. The thing is, SamFetch reports the firmware size, so your download client can show a progress bar and calculate ETA. However, when the decrypted size is not equal with actual size, download clients will stop the downloads. To fix failed downloads, **SamFetch won't report the firmware size when decrypting has enabled.**

#### Verifing the files

Samsung (Kies) servers only gives a CRC hash value which is for encrypted file, but as SamFetch can also decrypt the file while sending it to user, it is not possible to know the hash of the decrypted firmware. You can download encrypted the file and decrypt manually after checking the CRC. 

#### Updating your SamFetch instance (Heroku)

There are several ways to update your Heroku app when it is deployed from deploy button, however the easiest one is deleting your old deployed app and deploying it again from deploy button. If you want to keep the same URL, you can always rename your app in Heroku dashboard, renaming app also changes the app URL.

## Credits

This is a Web API variant of [Samloader](https://github.com/nlscc/samloader) project. I reimplemented the Samloader's functions as Web API routes and simplified the code for end-user to eliminate the authorization request, so SamFetch wouldn't be possible without Samloader.

## License

This project is licensed with AGPLv3.
