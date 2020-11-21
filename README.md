# SamFetch

A simple Web API to download Samsung Stock ROMs from Samsung's own Kies servers without any restriction in Python with help of FastAPI, and ready to deploy to Heroku with one-click.

I recommend hosting your own instance, as you will have more control over it and you will have own private instance. 

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ysfchn/SamFetch)

After typing your app name, deploy the app and your instance will be ready! Head over to `https://<app_name>.herokuapp.com/` and you will redirected to the docs, and it will show how to use the SamFetch.

## Features

* It doesn't collect any analytics, cookies and doesn't have any rate-limits as it directly calls the Kies servers.

* As Kies requests authorization, it is managed automatically by SamFetch itself, so you don't need any authorization or add any headers on your end.

* It doesn't have any background jobs/queue for downloading and decrypting the firmware, so this means the firmware file will directly stream to your browser while decrypting the chunks.

## Credits

This is a Web API variant of [Samloader](https://github.com/nlscc/samloader) project. I reimplemented the Samloader's functions as Web routes and simplified the code for end-user to eliminate the authorization request, so SamFetch wouldn't be possible without Samloader.

## License

This project is licensed with AGPLv3.
