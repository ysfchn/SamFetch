# Resources

These are some resources about Samsung firmwares that I find useful. If you want to do more with Samsung firmwares, or SamFetch is not enough for you, or just want to learn more stuff, you are in the right place.

#### Table of contents
* [Listing all CSC for a specific model](#listing-all-csc-for-a-specific-model)
* [Beta (test) firmwares](#beta-test-firmwares)

---

### Listing all CSC for a specific model

After I searched a lot, I couldn't find an "official" endpoint that does this job, however if you are okay with connecting to a 3rd party, then using SamMobile can be an option.

<samp>https://www.sammobile.com/wp-content/plugins/sam-firmwarepage/includes/SMFirmware/ajax/ajax.countriesbymodel.php?model=SM-N920C</samp> <sup>[Archive][4]<sup>

Here is a small part of the response:

```json
[
    {
        "id": "AFG",
        "value": "Afghanistan (AFG)",
        "url": "/samsung/galaxy-note-5/firmware/SM-N920C/AFG/"
    },
    {
        "id": "TMC",
        "value": "Algeria (TMC)",
        "url": "/samsung/galaxy-note-5/firmware/SM-N920C/TMC/"
    }
]
```

Note that retrieving information from SamMobile can be problematic as they may have terms about their content, and there is no public information about this URL. Even they may not allow fetching information from their website (and it is not even a scraping, just an endpoint that is hosted by themselves), it can be still useful for personal projects, at least.

---

### Beta (test) firmwares

Beta firmwares, as its name implies, are non-production firmwares which served on Samsung servers, like the other firmwares. The only difference is, they don't use the same method to access the firmware file.

Beta firmwares can be listed with this URL, with region and model.

<samp>http://fota-cloud-dn.ospserver.net/firmware/INS/SM-G975F/version.test.xml</samp> <sup>[Archive][3]<sup>

Here is a small part of the response, as you can see, they are not in common firmware string pattern, instead they are represented in hexadecimal.<sup><a href="#f-1">1</a></sup>

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<versioninfo>
	<url>https://fota-cloud-dn.ospserver.net/firmware/</url>
	<firmware>
		<model/>
		<cc>INS</cc>
		<version>
			<latest/>
			<upgrade>
				<value rcount='22' fwsize='213625809'>7439e752534c915d444c11866c06f671</value>
				<value rcount='10' fwsize='2281952421'>eeb5fb477058ad98b6a31bc7940b5e3d</value>
				<value rcount='12' fwsize='250040379'>5cc3e14f6ab351d0a25521553e0385f5</value>
				<value rcount='7' fwsize='1381041546'>9f2b0b91d9cdf0fd39b2413c85203586</value>
...
```

After researching a bit, I came across to this URL:

<samp>http://fota-secure-dn.ospserver.net/firmware/INS/SM-G975F/nspx/e1dff8735a1747839526d7975d87d402.bin</samp>

Obviously, simply visiting the URL says "Forbidden" because it appears to be, some type of authorization is needed. Searching [the pattern on Google][2] returned other firmware URLs and they all contain bunch of query parameters.

<samp>http://fota-secure-dn.ospserver.net/firmware/INS/SM-G975F/nspx/e1dff8735a1747839526d7975d87d402.bin?px-time=60267a1a&px-hash=95f16190460fb143455b9b293ac49410&px-wid=67220201214-WCA15575373&px-wctime=2020-12-14%2012:52:41&px-unum=&px-nb=UGtezEZ854jbmFcvWGxLEA==</samp><br>
<sup>[Source][5] ・ [Source in archive.org][6]</sup>

<samp>http://fota-secure-dn.ospserver.net/firmware/TMB/SM-F926U1/nspx/aa9c125f0ead436c9db1cbf4a80eeff2.bin?px-time=61ef7655&px-hash=81dc7034209ba5844f16c8299d988292&px-wid=5050010-WSA211126040227&px-wctime=2021-11-26%2004:02:27&px-unum=&px-nb=UGtezEZ854jbmFcvWGxLEA==</samp><br>
<sup>[Source][7] ・ [Source in archive.org][8]</sup>

<samp>http://fota-secure-dn.ospserver.net/firmware/DBT/SM-G991B/nspx/cb1275be4f1a4fd399e5da632e5b6bfc.bin?px-time=6199f52e&px-hash=917270a21173323c4ba14ea728608e7d&px-wid=6095013-WSA210922072845&px-wctime=2021-09-22%2007:28:45&px-unum=&px-nb=UGtezEZ854jbmFcvWGxLEA==</samp><br>
<sup>[Source][9] ・ [Source in archive.org][10]</sup>

However these URLs return 403 Forbidden too, I think they was available for a short time (the newest published link was posted 7 months ago), now released to production, or Samsung has just changed the way of access to the beta firmwares. According to some people who share these links, they say they got these download links by joining to some type of [Samsung Beta Program][1] and captured the download URL. 

Enrolling to Beta program is done on Samsung Members application. However, the program is geo-restricted, so even you have a combatible device, a VPN and a SIM card from the connected VPN's country may be needed.<sup><a href="#f-2">2</a></sup> After, enrolling to Beta program, beta firmwares can be downloaded from Software Update in Settings.

Without enrolling to Beta program and downloading the firmware through the links above, manual installation is possible from stock recovery via ADB.<sup><a href="#f-3">3</a></sup>

By looking to these URLs, it is possible to say `px-nb` query parameter is a constant with `UGtezEZ854jbmFcvWGxLEA==` value, because it exists on all URLs regardless device model and firmware name.

---

### Footnotes

<sup id="f-1">1</sup> In some cases, beta firmwares can be displayed in classic firmware format too (I assume once beta is released as stable).<br>
<sup id="f-2">2</sup> https://youtu.be/TF90XALbJ-0?t=164<br>
<sup id="f-3">3</sup> https://youtu.be/TPBPik9V2_8?t=421<br>

[1]: https://developer.samsung.com/one-ui-beta
[2]: https://google.com/search?q="http://fota-secure-dn.ospserver.net/firmware/*/*/nspx"
[3]: https://web.archive.org/web/20220610213308/http://fota-cloud-dn.ospserver.net/firmware/INS/SM-G975F/version.test.xml
[4]: https://web.archive.org/web/20220610213411/https://www.sammobile.com/wp-content/plugins/sam-firmwarepage/includes/SMFirmware/ajax/ajax.countriesbymodel.php?model=SM-N920C
[5]: https://r1.community.samsung.com/t5/galaxy-s/one-ui-3-beta-s10/td-p/7994711/page/2
[6]: https://web.archive.org/web/20220610211813/https://r1.community.samsung.com/t5/galaxy-s/one-ui-3-beta-s10/td-p/7994711/page/2
[7]: https://www.reddit.com/r/GalaxyFold/comments/r2dhqd/beta_3_available_on_tmobile_unlocked/
[8]: https://web.archive.org/web/20220610212404/https://www.reddit.com/r/GalaxyFold/comments/r2dhqd/beta_3_available_on_tmobile_unlocked/
[9]: https://github.com/fonix232/OneUI4/blob/main/README.md
[10]: https://web.archive.org/web/20220610212854/https://github.com/fonix232/OneUI4/blob/main/README.md