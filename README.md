# SamFetch

A simple Web API to download Samsung Stock ROMs from Samsung's own Kies servers without any restriction in Python with help of FastAPI, and ready to deploy to Heroku with one-click.

I recommend hosting your own instance, as you will have more control over it. Scroll down to get started.

## Features

* It doesn't collect any analytics, cookies and doesn't have any rate-limits as it directly calls the Kies servers.

* As Kies requests authorization, it is done automatically by server side, so you don't need any authorization or add any headers on your end.

* It doesn't have any background jobs for downloading and decrypting the firmware, so this means the firmware file will directly stream to your browser (and it decrypts automatically too).

## Endpoints

After hosting your instance you can go the `/docs` endpoint which opens a interactive API docs that created automatically. But if you need to learn the endpoints before hosting an instance, here is a table:

| Name | Query Parameters | Result (in a JSON) | Description |
|:--------------:|:------------------:|:-------------------|:------------------:|
| `/latest` | `region`<br>`model` | ```"latest": "N920CXXU5CRL3/N920COJV4CRB3/N920CXXU5CRL1/N920CXXU5CRL3"``` | Shows the latest firmware code for the device. Pass the firmware code to `/binary` endpoint. |
| `/binary`| `region`<br>`model`<br>`firmware` | ```"display_name": "Galaxy Note5"```<br>```"size": 2530817088```<br>```"size_readable": "2.36 GB"```<br>```"filename": "SM-N920C_1_20190117104840_n2lqmc6w6w_fac.zip.enc4"```<br>```"path": "/neofus/9/"```<br>```"encrypt_version": 4```<br>```"decrypt_key": "0727c304eea8a4d14835a4e6b02c0ce3"``` | Gets the binary details.<br>Pass `decrypt_key`, `filename` and `path` to `/download` endpoint. |
| `/download` | `filename`<br>`path`<br>`decrypt_key` | -- | Streams the firmware file to the browser while downloading and decrypting it. (Basically, starts the download) |


## Get Started

Just use the "Deploy to Heroku" button, Heroku will ask for app name.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ysfchn/SamFetch)

After typing your app name, deploy the app and your instance will be ready! Head over to `https://<app_name>.herokuapp.com/` and use the endpoints!


## Credits

This is a Web API variant of [Samloader](https://github.com/nlscc/samloader) project. I reimplemented the Samloader's functions as Web routes and simplified the code for end-user to eliminate the authorization request, so SamFetch wouldn't be possible without Samloader.


## License

This project is licensed with AGPLv3.
