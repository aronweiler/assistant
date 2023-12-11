import datetime
import os
import platform
import time
import threading
import numpy as np
import pyaudio
import queue
from collections import deque
import logging
import json
import uuid

from src.ai.abstract_ai import AbstractAI

from src.runners.runner import Runner
from src.runners.voice.configuration.voice_runner_configuration import (
    VoiceRunnerConfiguration,
    UserInformation,
    WakeWordModel,
)
from src.runners.voice.player import play_wav_file
from src.runners.voice.sound import Sound
from src.runners.voice.prompts import FINAL_REPHRASE_PROMPT
from src.runners.voice.audio_transcriber import AudioTranscriber
from src.runners.voice.wake_word import WakeWord
from src.runners.voice.text_to_speech import TextToSpeech

from src.db.models.users import Users


from src.db.database.models import User


from TTS.api import TTS

from dotenv import load_dotenv

if platform.system() == "Windows":
    import pyaudiowpatch as pyaudio

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280
SILENCE_LIMIT_IN_SECONDS = 2


class VoiceRunner(Runner):
    def __init__(self, args):
        super().__init__()
        self.args = VoiceRunnerConfiguration(args)
        self.audio = pyaudio.PyAudio()

        self.wake_word = WakeWord()

        self.activation_thread = None
        self.stop_event = threading.Event()
        self.audio_transcriber = AudioTranscriber(
            transcription_model_name=self.args.sts_model
        )

        # Create a queue to store audio frames
        self.audio_queue = queue.Queue(self.args.max_audio_queue_size)

        # initialize the text to speech engine
        self.text_to_speech = TextToSpeech()

        self.users = Users()

        self.initialize_users()

    def run(self, abstract_ai: AbstractAI):
        self.abstract_ai = abstract_ai
        self.abstract_ai.final_rephrase_prompt = FINAL_REPHRASE_PROMPT

        # Create the verifier models
        self.wake_word.create_verifier_models(self.args.wake_word_models)

        # Start the thread that listens to the microphone, putting data into the audio_queue
        mic_thread = threading.Thread(target=self.listen_to_microphone)
        mic_thread.start()

        # Start the thread that looks for wake words in the audio_queue
        self.look_for_wake_words()

    def initialize_users(self):
        # TODO: Refactor users to be better
        # Probably should be storing them in the database initially- not in this config file
        # Need to find a way to separate the wake word activation models from the user information
        for wake_word_model in self.args.wake_word_models:
            # See if the user exists in the database
            with self.users.session_context(self.users.Session()) as session:
                user = self.users.get_user_by_email(
                    session,
                    wake_word_model.user_information.user_email
                )

                if user is None:
                    logging.error(
                        f"User does not exist!"
                    )
                    raise Exception("User does not exist!")
                else:
                    logging.info(f"User {user.name} exists")                

    def configure(self):
        # TODO: Add settings to control voice here
        pass

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
        last_activation = time.time() - self.args.activation_cooldown

        # Start listening for wake words
        logging.info("\n\n--- Listening for wake words...\n")

        while True:
            # Pull a frame from the queue fed by the mic thread
            frame = self.audio_queue.get(block=True)

            # Predict whether a wake word is in this frame
            predictions = self.wake_word.get_wake_word_predictions(frame)

            # Get the highest ranked prediction (I only care about the best one)
            prediction = self.wake_word.get_highest_ranked_prediction(
                predictions, self.args.wake_word_models
            )

            # Does this prediction meet our threshold, and has enough time passed since the last activation?
            if (
                prediction is not None
                and prediction["prediction"][
                    prediction["wake_word_model"]["model_name"]
                ]
                > self.args.model_activation_threshold
                and (time.time() - last_activation) >= self.args.activation_cooldown
            ):
                detect_time = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

                logging.info(
                    f"Detected activation from '{prediction['wake_word_model']['model_name']}' model at time {detect_time}!  I think you are: {prediction['wake_word_model'].user_information.user_name}"
                )

                # Alert the user we've detected an activation
                play_wav_file(
                    os.path.join(os.path.dirname(__file__), "audio", "activation.wav"),
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
        # Create an interaction ID for this activation
        #conversation_id = uuid.uuid4()

        wake_model = prediction["wake_word_model"]

        # Get the user that activated us
        with self.users.session_context(self.users.Session()) as session:
            conversation_user = self.users.get_user_by_email(
                session,
                wake_model.user_information.user_email
            )            

            if conversation_user is None:
                self.text_to_speech.speak(
                    "I'm sorry, you are not authorized to use this system.",
                    prediction["wake_word_model"].tts_voice,
                    self.stop_event,
                    125,
                )
                logging.error(
                    f"Could not find user {wake_model.user_information.user_email} in the database"
                )
                return
            else:
                logging.debug(f"Found user {conversation_user.name}")

            # Mute any audio playing
            if self.args.mute_while_listening:
                Sound.mute()

            transcription_start_time = time.time()

            self.audio_transcriber.transcribe_until_silence(
                RATE, SILENCE_LIMIT_IN_SECONDS
            )

            transcribed_audio = self.audio_transcriber.get_transcription()

            transcription_end_time = time.time()

            logging.info(
                f"Transcription took {transcription_end_time - transcription_start_time} seconds"
            )

            if transcribed_audio is None or len(transcribed_audio) == 0:
                logging.info("No audio detected")
                # Alert the response from the AI is back
                play_wav_file(
                    os.path.join(os.path.dirname(__file__), "audio", "error.wav"),
                    self.stop_event,
                )
                return           

            try:
                # Unmute the audio
                if self.args.mute_while_listening:
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

                ai_response = self.abstract_ai.query(transcribed_audio, user_id=conversation_user.id)

                ai_query_end_time = time.time()

                # Alert the response from the AI is back
                play_wav_file(
                    os.path.join(os.path.dirname(__file__), "audio", "deactivate.wav"),
                    self.stop_event,
                )

                logging.info(
                    f"AI query took {str(ai_query_end_time - ai_query_start_time)} seconds"
                )

                logging.debug("AI Response: " + ai_response)

                text_to_speech_start_time = time.time()
                self.text_to_speech.speak(
                    ai_response,
                    conversation_user.get_setting("tts_voice", "Brian"),                    
                    self.stop_event,
                    conversation_user.get_setting("speech_rate", 100),
                )
                text_to_speech_end_time = time.time()
                logging.info(
                    f"Text to speech took {str(text_to_speech_end_time - text_to_speech_start_time)} seconds"
                )
            except Exception as e:
                logging.error("Failed to process.  ", e)
                play_wav_file(
                    os.path.join(os.path.dirname(__file__), "audio", "error.wav"),
                    self.stop_event,
                )

                # Store the exception
                # self.conversations.store_conversation(
                #     session, "Interaction failed.  See exception for details.", conversation_id, conversation_user, exception=str(e)
                # )

    # def get_prompt(
    #     self,
    #     related_conversations,
    #     transcribed_audio,
    #     user: User,
    #     conversation_id: uuid.UUID,
    # ):
    #     user_info_string = f"associated_user: {user.email}, user_name: {user.name}, user_age: {user.age}, user_location: {user.location}"

    #     # Another dumbass way to get something out of a list- I swear there has to be something better
    #     personality_setting = next(
    #         (
    #             item
    #             for item in user.user_settings
    #             if item.setting_name == "personality_keywords"
    #         ),
    #         None,
    #     )

    #     prompt = VOICE_ASSISTANT_PROMPT.format(
    #         query=transcribed_audio,
    #         time_zone=datetime.datetime.now().astimezone().tzname(),
    #         current_date_time=datetime.datetime.now().strftime(
    #             "%I:%M %p %A, %B %d, %Y"
    #         ),
    #         user_information=user_info_string,
    #         personality_keywords=personality_setting.setting_value
    #         if personality_setting is not None
    #         else "",
    #         conversation_id=conversation_id,
    #         related_conversations="\n".join(
    #             [
    #                 f"{c.record_created}: {c.message_text}"
    #                 for c in related_conversations
    #             ]
    #         ),
    #         user_conversations="\n".join(
    #             [
    #                 f"{m.record_created}: {m.message_text}"
    #                 for m in user.conversations
    #             ]
    #         ),
    #     )

    #     return prompt
