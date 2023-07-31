import pyaudio
import wave
import logging
import pydub
import io
import numpy as np


def play_wav_file(file_path, stop_event):
    chunk_size = 1024

    try:
        # Open the .wav file for reading
        wav_file = wave.open(file_path, "rb")

        # Initialize PyAudio
        audio_player = pyaudio.PyAudio()

        # Open a stream to play the audio
        stream = audio_player.open(
            format=audio_player.get_format_from_width(wav_file.getsampwidth()),
            channels=wav_file.getnchannels(),
            rate=wav_file.getframerate(),
            output=True,
        )

        # Read data in chunks and play it
        data = wav_file.readframes(chunk_size)
        while data and not stop_event.is_set():
            stream.write(data)
            data = wav_file.readframes(chunk_size)

        if stop_event.is_set():
            logging.debug("Stop event is set, cancelling audio playback.")

        # Close the stream and PyAudio
        stream.stop_stream()
        stream.close()
        audio_player.terminate()

    except Exception as e:
        logging.debug("Error playing the .wav file:" + str(e))


def play_wav_data(audio_data, stop_event, sample_rate=16000):
    chunk_size = 1024
    try:
        

        # Convert the list of floats to a NumPy array
        audio_np_array = np.array(audio_data, dtype=np.float32)

        audio_bytes = audio_np_array.tobytes()
        
        play_audio_bytes(audio_bytes, chunk_size, sample_rate, stop_event)

    except Exception as e:
        logging.error("Error playing the wav data:" + str(e))


def play_audio_bytes(audio_bytes, chunk_size, sample_rate = 16000, stop_event = None):
    p = pyaudio.PyAudio()

    stream = p.open(
        format=pyaudio.paFloat32,
        channels=1,
        rate=sample_rate,
        output=True
    )

    # loop through all of the audio in chunks
    i = 0
    for i in range(0, len(audio_bytes), chunk_size):
        if stop_event is not None and stop_event.is_set():
            logging.debug("Stop event is set, cancelling audio playback.")
            break
        stream.write(audio_bytes[i:i+chunk_size])
    
    if stop_event is None or not stop_event.is_set(): # Write the last chunk of audio
        stream.write(audio_bytes[i+chunk_size:])

    stream.stop_stream()
    stream.close()

    p.terminate()

def play_mp3_stream(mp3_data, stop_event):
    audio_data = pydub.AudioSegment.from_mp3(io.BytesIO(mp3_data))
    chunk_size = 1024
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(audio_data.sample_width),
                    channels=audio_data.channels,
                    rate=audio_data.frame_rate,
                    output=True)

    for i in range(0, len(audio_data.raw_data), chunk_size):
        if stop_event.is_set():
            break
        chunk = audio_data.raw_data[i:i + chunk_size]
        stream.write(chunk)

    stream.stop_stream()
    stream.close()
    p.terminate()