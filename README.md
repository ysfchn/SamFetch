# SamFetch

A simple Web API to download Samsung Stock ROMs from Samsung's own Kies servers, without any restriction, rate-limit, authorization or passwords. Made in Python, built with Sanic, and ready to deploy to Heroku with one-click.

If you have a Heroku account already, you can click the "Deploy" button below and host your own instance without any setup. 

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ysfchn/SamFetch)

> **Why you wanting us to host it ourselves instead of publishing a public URL?**<br>
> SamFetch doesn't have any rate-limits to keep it free (as in freedom) as much as I can. However, since this will allow spammers I recommend hosting your own instance, as you will have more control over it and you will have own private instance.
>
> After typing your app name, deploy the app and your instance will be ready! Head over to `https://<app_name>.herokuapp.com/` and you will see a home page, and it will show how to use the SamFetch.

| ⚠ **WARNING** |
|:--------------|
| Due to a change in Samsung servers, you can only download the latest firmware even if you asked for an older firmware. [This is not related to SamFetch.](https://github.com/ysfchn/SamFetch/issues/6) |

## Features

* It doesn't collect any analytics, store cookies or have any rate-limits as it directly calls the Samsung servers.

* As Samsung server requests authorization before serving firmwares, it is made automatically by SamFetch itself, so you don't need any authorization or add any headers on your end.

* It doesn't pre-download the firmware and it doesn't have any background jobs/queue for downloading and decrypting the firmware, so this means the firmware file will directly stream to your browser or your download client, while decrypting the chunks. 

* SamFetch supports partial downloads _("Range" header)_ which means it supports pausing and resuming the download in your download client / browser's own downloader. [Note that partial downloads are not allowed when decrypting has enabled, see here.](#partial-downloads)

* You can configure your SamFetch instance such as adding CORS headers and change chunk size with environment variables.

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

## Notes

#### Downloading firmwares

Samsung gives firmwares as encrypted binaries. SamFetch gives an option to download firmware decrypted while downloading it or you can download it encrypted and decrypt manually yourself. When you get firmware details with `/binary`, SamFetch gives a `decrypt_key` (represented as hex string). Then you can give the key to `/download` endpoint by setting `decrypt` query parameter with your `decrypt_key`.

If you prefer to decrypt firmwares manually, sadly you can't do it with SamFetch (as it is an web application not a CLI), but you can use [Samloader](https://github.com/nlscc/samloader) which has a `decrypt` command.

#### Partial downloads

When an encrypted file has decrypted, the file size becomes slightly different from the encrypted file. The thing is, SamFetch sends the firmware size, so your download client can show a progress bar and calculate ETA. However, when the decrypted size is not equal with actual size, download clients will stop the downloads. To fix failed downloads, **SamFetch won't send the firmware size when decrypting has enabled.**

#### Verifing the files

Samsung (Kies) servers only gives a CRC hash value which is for encrypted file, but as SamFetch can also decrypt the file while sending it to user, it is not possible to know the hash of the firmware. You can download encrypted the file and decrypt manually after checking the CRC. 

#### Updating your SamFetch instance

There are several ways to update your Heroku app when it is deployed from deploy button, however the easiest one is deleting your old deployed app and deploying it again from deploy button. If you want to keep the same URL, you can always rename your app in Heroku dashboard, renaming app also changes the app URL.

## Credits

This is a Web API variant of [Samloader](https://github.com/nlscc/samloader) project. I reimplemented the Samloader's functions as Web API routes and simplified the code for end-user to eliminate the authorization request, so SamFetch wouldn't be possible without Samloader.

## License

This project is licensed with AGPLv3.
