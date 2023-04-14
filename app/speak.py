import os
import uuid
import requests
from pathlib import Path
from pydub import AudioSegment
from utils import convert_mp3_to_opus_binary
from config import ELEVENLABS_API_KEY, USE_MAC_OS_TTS
import gtts
from threading import Lock, Semaphore


voices = ["ErXwobaYiN019PkySvjV", "EXAVITQu4vr4xnSDxMaL"]
index_cache_voice_dir = Path('/tmp/myGPTReader/voice/')
if not index_cache_voice_dir.is_dir():
    index_cache_voice_dir.mkdir(parents=True, exist_ok=True)
tts_headers = {
    "Content-Type": "application/json",
    "xi-api-key": ELEVENLABS_API_KEY
}

mutex_lock = Lock()
queue_semaphore = Semaphore(1)

def gtts_speech(text):
    tts = gtts.gTTS(text)
    file_path = f"{index_cache_voice_dir}{uuid.uuid4()}.mp3"
    tts.save(file_path)
    audio = AudioSegment.from_mp3(file_path)
    duration = audio.duration_seconds
    return file_path, duration

def macos_tts_speech(text):
    file_path = f"{index_cache_voice_dir}{uuid.uuid4()}.aiff"
    os.system(f'say "{text}" -o {file_path} --file-format=aiff')
    audio = AudioSegment.from_file(file_path, format="aiff")
    duration = audio.duration_seconds
    return file_path, duration

def eleven_labs_speech(text, voice_index=0):
    tts_url = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}".format(voice_id=voices[voice_index])
    formatted_message = {"text": text}
    response = requests.post(tts_url, headers=tts_headers, json=formatted_message)

    if response.status_code == 200:
        opus_content, duration = convert_mp3_to_opus_binary(response.content)
        file_path = f"{index_cache_voice_dir}{uuid.uuid4()}.opus"
        with open(file_path, "wb") as f:
            f.write(opus_content)
        return True, file_path, duration
    else:
        print("Request failed with status code:", response.status_code)
        print("Response content:", response.content)
        return False, None, 0

def get_video(text, voice_index=1):
    file_path = None
    duration = 0
    if not ELEVENLABS_API_KEY:
        if USE_MAC_OS_TTS == 'True':
            file_path, duration = macos_tts_speech(text)
        else:
            file_path, duration = gtts_speech(text)
    else:
        success, file_path, duration = eleven_labs_speech(text, voice_index)
        if not success:
            file_path, duration = gtts_speech(text)

    return file_path, duration
