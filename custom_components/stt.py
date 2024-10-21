import logging
import async_timeout
import json
import requests
import voluptuous as vol
import wave, io
import noisereduce as nr
import numpy as np
from pydub import AudioSegment
from scipy.io import wavfile

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    Provider,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

### Deepgram's API Endpoint ###
url = 'https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true'

CONF_API_KEY = 'stt_api_key'
DEFAULT_VOL = 5
VOL_INC = 'vol_inc'

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_API_KEY): cv.string,
    vol.Optional(VOL_INC, default=DEFAULT_VOL): cv.positive_int
})

async def async_get_engine(hass, config, discovery_info=None):
    stt_api_key = config[CONF_API_KEY]
    vol_inc = config.get(VOL_INC, DEFAULT_VOL)
    return DeepgramSTTServer(hass, stt_api_key, vol_inc)

### Noise removal and volume increase ####
def process_audio(audio_bytes,sample_rate=16000, channels=1, sampwidth=2, volume_increase_db=5):
    """
    Convert PCM binary data to WAV file format.
    :param audio_bytes: The raw PCM binary audio data.
    :param sample_rate: The sample rate (e.g., 16000 Hz).
    :param channels: Number of audio channels (1 for mono, 2 for stereo).
    :param sampwidth: Sample width in bytes (e.g., 2 bytes for 16-bit audio).
    :return: A BytesIO object containing the WAV data.
    """
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)  # 1 for mono, 2 for stereo
        wav_file.setsampwidth(sampwidth) # 2 bytes = 16 bits per sample
        wav_file.setframerate(sample_rate) # Set the sample rate (e.g., 16000 Hz)
        wav_file.writeframes(audio_bytes)
    wav_buffer.seek(0)
    sample_rate, data = wavfile.read(wav_buffer)
    # Apply noise reduction
    reduced_noise = nr.reduce_noise(y=data, sr=sample_rate)
    # Convert the processed numpy array back to AudioSegment
    processed_audio = AudioSegment(
        reduced_noise.tobytes(),
        frame_rate=sample_rate,
        sample_width=reduced_noise.dtype.itemsize,
        channels=1  # Adjust this if your audio has multiple channels
    )
    # Increase volume
    louder_audio = processed_audio + volume_increase_db  # Increase volume by specified dB
    # Export the modified audio to bytes
    output_wav_io = io.BytesIO()
    louder_audio.export(output_wav_io, format="wav")
    output_wav_io.seek(0)
    return output_wav_io

class DeepgramSTTServer(Provider):
    """The Deepgram STT API provider."""

    def __init__(self, hass, stt_api_key, vol_inc):
        """Initialize Deepgram STT Server."""
        self.hass = hass
        self._stt_api_key = stt_api_key
        self._vol_inc=vol_inc
        self._language = "en-US"  # Set default language

    @property
    def default_language(self) -> str:
        """Return the default language."""
        return self._language

    @property
    def supported_languages(self) -> list[str]:
        """Return the list of supported languages."""
        return [self._language]

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """Return a list of supported formats."""
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return a list of supported codecs."""
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return a list of supported bitrates."""
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return a list of supported sample rates."""
        return [AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return a list of supported channels."""
        return [AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream
    ) -> SpeechResult:
        # Collect data
        audio_data = b""
        async for chunk in stream:
            audio_data += chunk

        ### Prepare POST data ###
        headers = {
            "Authorization": f"Token {self._stt_api_key}",
            "Content-Type": "audio/wav"
        }
        def job():
            wav_file = process_audio(audio_data, volume_increase_db=self._vol_inc)
            response = requests.post(url, headers=headers, data=wav_file.getvalue())
            transcript='STT Error'
            if response.status_code == 200:
                response_json = response.json()  # Parse the response as JSON
                transcript = response_json["results"]["channels"][0]["alternatives"][0]["transcript"]
            else:
                _LOGGER.error(f"Error occurred: {response.status_code}")
            _LOGGER.info(f"Transcription from Deepgram STT is: {transcript}")
            return transcript

        async with async_timeout.timeout(20):
            assert self.hass
            response = await self.hass.async_add_executor_job(job)
            if len(response) > 0:
                return SpeechResult(
                    response,
                    SpeechResultState.SUCCESS,
                )
            return SpeechResult("", SpeechResultState.ERROR)
