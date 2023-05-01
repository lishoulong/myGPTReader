import io
from pydub import AudioSegment

# 根据二进制文件获取音频格式
def identify_audio_format(binary_data):
    # Check magic numbers
    if binary_data.startswith(b'\xFF\xF1') or binary_data.startswith(b'\xFF\xF9'):
        return 'mp3'
    elif binary_data.startswith(b'RIFF') and binary_data[8:12] == b'WAVE':
        return 'wav'
    elif binary_data.startswith(b'OggS'):
        return 'ogg'
    elif binary_data.startswith(b'fLaC'):
        return 'flac'
    elif binary_data.startswith(b'\x00\x00\x00\x1CftypM4A'):
        return 'm4a'
    elif binary_data.startswith(b'\x1aE\xdf\xa3'):
        return 'webm'
    else:
        return 'ogg'
    
# 音频格式转化
def convert_ogg_to_mp3_binary(ogg_binary_data, audio_format):
    supported_formats = ['m4a', 'mp3', 'webm', 'mp4', 'mpga', 'wav', 'mpeg']
    # If the audio format is already supported, return the original data
    if audio_format.lower() in supported_formats:
        return ogg_binary_data
    # Create a BytesIO object from the binary data
    ogg_buffer = io.BytesIO(ogg_binary_data)

    # Read OGG data from the BytesIO object
    ogg_audio = AudioSegment.from_ogg(ogg_buffer)

    # Create a BytesIO object for the MP3 data
    mp3_buffer = io.BytesIO()

    # Export the audio as MP3 to the BytesIO object
    ogg_audio.export(mp3_buffer, format="mp3")

    # Return the binary MP3 data
    return mp3_buffer.getvalue()

def convert_mp3_to_opus_binary(mp3_binary_data, audio_format="MP3"):
    # If the audio format is already opus, return the original data
    if audio_format.lower() == 'opus':
        return mp3_binary_data

    # Create a BytesIO object from the binary data
    mp3_buffer = io.BytesIO(mp3_binary_data)

    # Read MP3 data from the BytesIO object
    mp3_audio = AudioSegment.from_mp3(mp3_buffer)

    # Get the duration of the audio in seconds
    duration_seconds = mp3_audio.duration_seconds

    # Create a BytesIO object for the Opus data
    opus_buffer = io.BytesIO()

    # Export the audio as Opus to the BytesIO object
    mp3_audio.export(opus_buffer, format="opus")

    # Return the binary Opus data and the duration in seconds
    return opus_buffer.getvalue(), duration_seconds
