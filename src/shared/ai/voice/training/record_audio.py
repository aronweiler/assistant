import os
import pyaudio
import wave
import logging

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280


def record_audio(save_dir, clip_num, record_seconds):
    p = pyaudio.PyAudio()

    logging.debug(f"Recording clip {clip_num}...")
    stream = p.open(
        format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK
    )

    frames = []
    for i in range(0, int(RATE / CHUNK * record_seconds)):
        data = stream.read(CHUNK)
        frames.append(data)

    stream.stop_stream()
    stream.close()

    clip_filename = os.path.join(save_dir, f"clip_{clip_num}.wav")

    wf = wave.open(clip_filename, "wb")
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(frames))
    wf.close()

    p.terminate()
    logging.debug("Recording completed.")
