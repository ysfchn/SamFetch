# SamFetch

A simple Web API to download Samsung Stock ROMs from Samsung's own Kies servers, without any restriction, rate-limit, authorization or passwords. Made in Python, built with FastAPI, and ready to deploy to Heroku with one-click.

If you have a Heroku account already, you can click the "Deploy" button below and host your own instance without any setup. 

> **Why you wanting us to host it ourselves instead of publishing a public URL?**<br>
> SamFetch doesn't have any restriction itself, and I don't want to set up any restrictions such as rate-limit etc to keep it free (freedom) as much as I can. However, since this will allow spammers I recommend hosting your own instance, as you will have more control over it and you will have own private instance.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ysfchn/SamFetch)

After typing your app name, deploy the app and your instance will be ready! Head over to `https://<app_name>.herokuapp.com/` and you will redirected to the OpenAPI docs, and it will show how to use the SamFetch.

| ⚠ **WARNING** |
|:--------------|
| Due to a change in Samsung Kies servers, you can only download the latest firmware even if you asked for a older firmware. This is not related to SamFetch.<br>[Issue Link](https://github.com/ysfchn/SamFetch/issues/6) |

## Features

* It doesn't collect any analytics, store cookies or have any rate-limits as it directly calls the Kies servers.

* As Kies requests authorization, it is managed automatically by SamFetch itself, so you don't need any authorization or add any headers on your end.

* It doesn't have any background jobs/queue for downloading and decrypting the firmware, so this means the firmware file will directly stream to your browser / your download client, while decrypting the chunks. 

* SamFetch supports partial downloads which means it supports pausing and resuming the download in your download client / browser's own downloader.

## Credits

This is a Web API variant of [Samloader](https://github.com/nlscc/samloader) project. I reimplemented the Samloader's functions as Web API routes and simplified the code for end-user to eliminate the authorization request, so SamFetch wouldn't be possible without Samloader.

## License

This project is licensed with AGPLv3.
