import datetime
import os
import platform
import sys
import time
import threading
import numpy as np
import pyaudio
import queue
from collections import deque
import logging
import json
import uuid

from src.db.models.user_settings import UserSettings

# Append the path to the tools directory to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.ai.prompts.prompt_manager import PromptManager
from src.ai.rag_ai import RetrievalAugmentedGenerationAI
from src.ai.voice.player import play_wav_file
from src.ai.voice.sound import Sound
from src.ai.voice.prompts import FINAL_REPHRASE_PROMPT
from src.ai.voice.audio_transcriber import AudioTranscriber
from src.ai.voice.wake_word import WakeWord
from src.ai.voice.text_to_speech import TextToSpeech

from src.db.models.users import Users


from src.utilities.configuration_utilities import (
    get_voice_configuration,
    get_app_configuration,
)

if platform.system() == "Windows":
    import pyaudiowpatch as pyaudio

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280
SILENCE_LIMIT_IN_SECONDS = 2


class VoiceRunner:
    def __init__(self):
        # Get the configurations
        self.voice_configuration = get_voice_configuration()
        self.app_configuration = get_app_configuration()

        self.audio = pyaudio.PyAudio()

        self.mic_thread = None

        self.wake_word = WakeWord(
            wake_word_model_paths=[self.voice_configuration.wake_word_model_path]
        )

        self.activation_thread = None
        self.stop_event = threading.Event()
        self.audio_transcriber = AudioTranscriber(
            transcription_model_name=self.voice_configuration.sts_model
        )

        # Create a queue to store audio frames
        self.audio_queue = queue.Queue(self.voice_configuration.max_audio_queue_size)

        # initialize the text to speech engine
        self.text_to_speech = TextToSpeech()

        # Get the configured user, and settings
        self.settings = UserSettings()
        users = Users()
        self.user = users.get_user_by_email(self.voice_configuration.user_email)

        # initialize settings
        # self.initialize_settings()

        self.prompt_manager = PromptManager(
            self.app_configuration["jarvis_ai"]["model_configuration"]["llm_type"]
        )

        # Initialize RAG AI
        self.rag_ai = RetrievalAugmentedGenerationAI(
            configuration=self.app_configuration,
            conversation_id=uuid.UUID(
                "123e4567-e89b-12d3-a456-426614174000"
            ),  # probably should be in settings or something
            user_email=self.user.email,
            prompt_manager=self.prompt_manager,
            streaming=False,  # Look at changing this later
        )

    def run(self):
        # Start the thread that listens to the microphone, putting data into the audio_queue
        self.mic_thread = threading.Thread(target=self.listen_to_microphone)
        self.mic_thread.start()

        # Start the thread that looks for wake words in the audio_queue
        self.look_for_wake_words()

    def listen_to_microphone(self):
        # Set up the mic stream
        mic_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
        )

        while True:
            # If the wake word detection queue is full, pop the oldest frame
            if self.audio_queue.full():
                self.audio_queue.get()

            # Read a frame from the mic and add it to the queue used by the wake word detection
            frame = mic_stream.read(CHUNK, exception_on_overflow=False)
            self.audio_queue.put(frame, block=True)

            # Also put the frame into the audio transcriber
            self.audio_transcriber.add_frame_to_buffer(frame)

    def look_for_wake_words(self):
        # Set the last activation time to cooldown seconds ago so that we can activate immediately
        last_activation = time.time() - self.voice_configuration.activation_cooldown

        # Start listening for wake words
        logging.info("\n\n--- Listening for wake words...\n")

        while True:
            # Pull a frame from the queue fed by the mic thread
            frame = self.audio_queue.get(block=True)

            # Predict whether a wake word is in this frame
            predictions = self.wake_word.get_wake_word_predictions(frame)

            # Get the highest ranked prediction (I only care about the best one)
            prediction = self.wake_word.get_highest_ranked_prediction(
                predictions, [self.voice_configuration.wake_word_model_path]
            )

            # Does this prediction meet our threshold, and has enough time passed since the last activation?
            if (
                prediction is not None
                and prediction["prediction"][prediction["wake_word_model"]]
                > self.voice_configuration.model_activation_threshold
                and (time.time() - last_activation)
                >= self.voice_configuration.activation_cooldown
            ):
                detect_time = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

                logging.info(
                    f"Detected activation from '{prediction['wake_word_model']}' model at time {detect_time}!"
                )

                # Alert the user we've detected an activation
                play_wav_file(
                    os.path.join(
                        os.path.dirname(__file__), "voice/audio", "activation.wav"
                    ),
                    self.stop_event,
                )

                # Detected an activation!  Let's process it on a different thread after stopping any other activations
                if self.activation_thread is not None:
                    self.stop_event.set()
                    self.audio_transcriber.stop_transcribing()
                    self.activation_thread.join()
                    self.activation_thread = None
                    self.stop_event.clear()

                self.activation_thread = threading.Thread(
                    target=self.process_activation, args=(prediction,)
                )
                self.activation_thread.start()

                last_activation = time.time()
                logging.info("--- Continuing to listen for wake words...")

    def process_activation(self, prediction):
        wake_model = prediction["wake_word_model"]

        # Mute any audio playing
        if self.voice_configuration.mute_while_listening:
            Sound.mute()

        transcription_start_time = time.time()

        self.audio_transcriber.transcribe_until_silence(RATE, SILENCE_LIMIT_IN_SECONDS)

        transcribed_audio = self.audio_transcriber.get_transcription()

        transcription_end_time = time.time()

        logging.info(
            f"Transcription took {transcription_end_time - transcription_start_time} seconds"
        )

        if transcribed_audio is None or len(transcribed_audio) == 0:
            logging.info("No audio detected")
            # Alert the response from the AI is back
            play_wav_file(
                os.path.join(os.path.dirname(__file__), "voice/audio", "error.wav"),
                self.stop_event,
            )
            return

        try:
            # Unmute the audio
            if self.voice_configuration.mute_while_listening:
                Sound.volume_up()

            logging.info("Transcribed audio: " + transcribed_audio)

            if transcribed_audio is None or len(transcribed_audio) == 0:
                logging.debug("No audio detected")
                return

            if (
                transcribed_audio.strip().lower() == "stop"
                or transcribed_audio.strip().lower() == "stop."
                or transcribed_audio.strip().lower() == "cancel"
                or transcribed_audio.strip().lower() == "cancel."
            ):
                logging.debug("Stop keyword detected")
                return

            if self.stop_event.is_set():
                logging.debug("Stop event is set, cancelling interaction")
                return

            ai_query_start_time = time.time()

            ai_response = self.rag_ai.query(query=transcribed_audio, ai_mode="Auto")

            ai_query_end_time = time.time()

            # Alert the response from the AI is back
            play_wav_file(
                os.path.join(
                    os.path.dirname(__file__), "voice/audio", "deactivate.wav"
                ),
                self.stop_event,
            )

            logging.info(
                f"AI query took {str(ai_query_end_time - ai_query_start_time)} seconds"
            )

            logging.debug("AI Response: " + ai_response)

            text_to_speech_start_time = time.time()
            self.text_to_speech.speak(
                ai_response,
                self.voice_configuration.default_tts_voice,
                self.stop_event,
                self.voice_configuration.speech_rate,
            )
            text_to_speech_end_time = time.time()
            logging.info(
                f"Text to speech took {str(text_to_speech_end_time - text_to_speech_start_time)} seconds"
            )
        except Exception as e:
            logging.error("Failed to process.  ", e)
            play_wav_file(
                os.path.join(os.path.dirname(__file__), "voice/audio", "error.wav"),
                self.stop_event,
            )


if __name__ == "__main__":
    voice_runner = VoiceRunner()
    voice_runner.run()
