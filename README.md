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

| Endpoint | Description      | Notes       |
|:---------|:-----------------|:------------|
| `/csc`   | Lists all available CSC. Note that the list may be incomplete. | |
| `/list/:region/:model` | Lists all firmware versions for a specific device and region. Region examples can be found on /csc endpoint. Note that some firmwares may be only available to specific regions. | |
| `/binary/:region/:model/:firmware` | Gets details for a firmware such as download size, file name and decryption key. You can get firmware from /list endpoint. | |
| `/download/:path/:firmware` | Downloads a firmware. You can get decrypt key, path and file from /binary endpoint. | Query parameters are available for this endpoint:<br><br>`decrypt` - Takes an decrypt key, so SamFetch can decrypt the firmware while sending it to you. If not provided, SamFetch will download the encrypted file and you will need to decrypt manually.<br>`filename` - Overwrites the filename that shows up in the download client, defaults to Samsung's own firmware name. |
| `/direct/:region/:model` or `/:region/:model` | Executes all required endpoints and directly starts dowloading the latest firmware with one call. It is useful for end-users who don't want to integrate the API in a client app. |

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
