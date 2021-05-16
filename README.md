# SamFetch

A simple Web API to download Samsung Stock ROMs from Samsung's own Kies servers, without any restriction, rate-limit, authorization or passwords. Made in Python, built with FastAPI, and ready to deploy to Heroku with one-click.

If you have a Heroku account already, you can click the "Deploy" button below and host your own instance without any setup. 

> **Why you wanting us to host it ourselves instead of publishing a public URL?**<br>
> SamFetch doesn't have any restriction itself, and I don't want to set up any restrictions such as rate-limit etc to keep it free (freedom) as much as I can. However, since this will allow spammers I recommend hosting your own instance, as you will have more control over it and you will have own private instance.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/ysfchn/SamFetch)

After typing your app name, deploy the app and your instance will be ready! Head over to `https://<app_name>.herokuapp.com/` and you will redirected to the OpenAPI docs, and it will show how to use the SamFetch.

| ⚠ **WARNING** |
|:--------------|
| Due to a change in Samsung Kies servers, you can only download the latest firmware even if you asked for an older firmware. [This is not related to SamFetch.](https://github.com/ysfchn/SamFetch/issues/6) |

## Features

* It doesn't collect any analytics, store cookies or have any rate-limits as it directly calls the Kies servers.

* As Kies requests authorization, it is managed automatically by SamFetch itself, so you don't need any authorization or add any headers on your end.

* It doesn't have any background jobs/queue for downloading and decrypting the firmware, so this means the firmware file will directly stream to your browser / your download client, while decrypting the chunks. 

* SamFetch supports partial downloads ("Range" header) which means it supports pausing and resuming the download in your download client / browser's own downloader. 

    ⚠ Note that pausing and resuming the download may end up with corrupted downloads in some download clients due to their handling with the headers. If you find a universal method that will work for all download clients, feel free to create a new PR.

### Verifing the files

* There is currently no way to verify if the downloaded files are downloaded correctly. Because Samsung (Kies) servers only gives a CRC value which is for encrypted file, but as SamFetch decrypts the file while sending it to user, it is not possible to know the hash of the firmware without downloading it fully.

* Also, SamFetch adds 1 empty byte to start and 10 empty bytes to end of the file, so this may cause inconsistency when comparing hashes of firmware files which downloaded from somewhere else. Don't worry, this won't corrupt the firmware files as these bytes are empty.

    The reason behind about adding empty bytes is, 
    
    * The first empty byte is added for checking if download has finished before sending it to user. Because the last chunk requires additional decrypting, so SamFetch needs to go 1 step early from the user.

    * The last 10 empty bytes are added for preventing the inconsistency in file size. As mentioned before, the last chunk requires additional decrypting. In result of decrypting the last chunk, it makes the file 10 bytes smaller. However, this is not good at all because it won't work correctly when downloading the file with download managers. Download managers sets a "Range" header to requests which specifies the range in bytes such as 0-1023, so they expect these bytes without more or less.


## Credits

This is a Web API variant of [Samloader](https://github.com/nlscc/samloader) project. I reimplemented the Samloader's functions as Web API routes and simplified the code for end-user to eliminate the authorization request, so SamFetch wouldn't be possible without Samloader.

## License

This project is licensed with AGPLv3.
