import sys
import os
import platform

# Add the path to the 'other_directory' to sys.path
other_directory_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(other_directory_path)

if platform.system() == "Windows":
    import pyaudiowpatch as pyaudio
else:
    import pyaudio

import openwakeword

from record_audio import record_audio
from player import play_wav_file

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280


def run_training(training_data_dir):
    # List all of the files in the training data directory, and then create paths for each
    positive_clips = []
    for root, dirs, files in os.walk(f"{training_data_dir}/positive"):
        for file in files:
            positive_clips.append(os.path.join(root, file))

    negative_clips = []
    for root, dirs, files in os.walk(f"{training_data_dir}/negative"):
        for file in files:
            negative_clips.append(os.path.join(root, file))

    # Train a custom verifier
    openwakeword.train_custom_verifier(
        positive_reference_clips=positive_clips,  # path to directory containing positive clips
        negative_reference_clips=negative_clips,  # path to directory containing negative clips
        output_path=f"{training_data_dir}/model.pkl",
        model_name="src\\runners\\voice\\models\\hey_jarvis_v0.1.onnx",  # the target model path which matches the wake word/phrase of the collected positive examples
    )


def record_samples(training_data_dir):
    # Record some positive and negative samples using pyaudio and the microphone

    if not os.path.exists(f"{training_data_dir}/negative"):
        os.makedirs(f"{training_data_dir}/negative")

    if not os.path.exists(f"{training_data_dir}/positive"):
        os.makedirs(f"{training_data_dir}/positive")

    input("Press enter to record positive samples...")
    for i in range(20):
        # Record a 3 second clip, 1 channel, 16Khz sample rate, 16 bit depth, and save it to the positive directory
        record_seconds = 3
        print("Say, 'Hey Jarvis!'")
        record_audio(f"{training_data_dir}/positive", i, record_seconds)

    input("Press enter to record negative samples...")
    for i in range(20):
        # Record a 3 second clip, 1 channel, 16Khz sample rate, 16 bit depth, and save it to the negative directory
        record_seconds = 3
        print("Anything but 'Hey Jarvis!'")
        record_audio(f"{training_data_dir}/negative", i, record_seconds)


if __name__ == "__main__":
    #record_samples("src/runners/voice/training/aron")
    run_training("src/runners/voice/training/aron")
    # run_training("src/runners/voice/training/gaia")

