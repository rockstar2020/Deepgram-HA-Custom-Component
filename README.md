# Deepgram-HA-Custom-Component

I was in the search of a more accurate/affordable API-based STT service and I came across Deepgram.
At the time of uploading this repository Deepgram offers $200 credit with no expiry pay-as-you-go service.
https://deepgram.com/pricing
That's a pretty good deal!
<br/>
After a satisfying results of my tests with Deppgram's STT, I decided to write this custom component.
Additionally, since I'm using multiple satellite ESPHome's microphones in my home, I added a bit of noise reduction and volume bump to the audio recieved from the mic stream in order to get a more accurate sppech to text conversion from Deepgram.

**How to install:**
1. Copy all contents of the custom component folder and paste it in your own HA's custom component folder.
2. Register on Deepgram and generate your API Key.
3. Add the following lines in your configuration YAML:
```
stt:
  - platform: deepgram_stt
    stt_api_key: 'Your-API-Key'
    vol_inc: 25 #Int Value of Volume to be increased
```
4. Restart Home Assistant
<br/>
**Important Note:**
<br/>
Please keep in mind that this method of STT integration within home assistant for some reason is not fully supported hence the reason you should expect to received similar error message in your home assistant log as below:
<br/><br/>
The stt integration does not support any configuration parameters, got [{'platform': 'deepgram_stt', 'stt_api_key': 'xxxxxxxxxxxxxxxxxxx', 'vol_inc': 25}]. Please remove the configuration parameters from your configuration.
<br/><br/>
There's a chance that Home Assistant will eventually remove the option of adding stt as custom component and my component, like few other custom components out there (ie Google, OpenAI) will stop working.
<br/><br/>
**Acknowledgement**
<br/>
I was inspired by the great work done by @shiipou for the OpenAI STT integration (https://github.com/shiipou/openai_stt).
