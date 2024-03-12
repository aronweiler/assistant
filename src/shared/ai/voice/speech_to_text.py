import threading
import numpy as np
import torch
import time
import logging
import queue


class SpeechToText:
    def __init__(self, audio_queue_size=1024, model_name="base"):
        self.audio_queue = queue.Queue(audio_queue_size)
        self.transcription = ""
        self.thread = None
        self.queue_timeout = 1
        self.transcription_frame_chunk_size = 50

        # Load this here so that we don't load it when we are just loading classes
        import whisper

        model_name = "medium.en"  # or use: tiny.en, medium.en, large
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(
            model_name,
        ).to(device)

    def start_transcribing(self):
        self.transcription = ""
        self.thread = threading.Thread(target=self._start_transcribing)
        self.thread.start()

        logging.debug(
            "speech_to_text.start_transcribing :: Started transcription thread"
        )

    def stop_transcribing(self):
        logging.debug("speech_to_text.stop_transcribing :: Stopping transcription")
        # Stop transcribing by putting None into the buffer
        self.audio_queue.put(None, block=True, timeout=self.queue_timeout)

        if self.thread:
            self.thread.join()
            self.thread = None

        # Remove anything else in the queue
        while not self.audio_queue.empty():
            self.audio_queue.get()

    def get_transcription(self):
        return self.transcription

    def enqueue_audio(self, audio_frame):
        if self.audio_queue.full():
            logging.debug("Audio queue full, dropping first frame")
            self.audio_queue.get()

        self.audio_queue.put(audio_frame, block=True, timeout=self.queue_timeout)

    def _start_transcribing(self):
        logging.debug("speech_to_text._start_transcribing :: Starting transcription")
        stopping = False

        # Continuously transcribe the audio from the buffer starting at the start_index, when None is received, stop
        while not stopping:
            # Pause for a moment to allow audio to be added to the buffer
            # logging.debug("Pausing for 0.5 seconds to allow audio to be added to the buffer")
            # time.sleep(0.5)

            # Attempt to get the minimum number of frames to transcribe
            temp_buffer = []
            while len(temp_buffer) < self.transcription_frame_chunk_size:
                audio_frame = self.audio_queue.get(
                    block=True, timeout=self.queue_timeout
                )
                if audio_frame is not None:
                    temp_buffer.append(
                        np.frombuffer(audio_frame, np.int16)
                        .flatten()
                        .astype(np.float32)
                        / 32768.0
                    )
                else:
                    stopping = True
                    break

            logging.debug(
                f"Got {len(temp_buffer)} frames from the audio queue for transcription.  Stop token is {stopping}"
            )

            # if len(temp_buffer) > 0:
            #     # Join the frames into a single numpy array that can be ingested by whisper
            #     for i in range(len(temp_buffer)):
            #         temp_buffer[i] = np.frombuffer(temp_buffer[i], np.int16).flatten().astype(np.float32) / 32768.0

            if len(temp_buffer) <= 0:
                logging.debug("No audio frames to transcribe in temp_buffer")
            else:
                joined_frames = np.concatenate(temp_buffer)

                kwargs = {}
                kwargs["language"] = "en"
                kwargs["verbose"] = True
                kwargs["task"] = "transcribe"
                kwargs["temperature"] = 0
                kwargs["best_of"] = None
                kwargs["beam_size"] = None
                kwargs["patience"] = None
                kwargs["length_penalty"] = None
                kwargs["suppress_tokens"] = "-1"
                kwargs["initial_prompt"] = None
                kwargs["condition_on_previous_text"] = False
                kwargs["fp16"] = True  # for GPU
                kwargs["compression_ratio_threshold"] = 2.4
                kwargs["logprob_threshold"] = -0.5
                kwargs["no_speech_threshold"] = 0.2

                result = self.model.transcribe(audio=joined_frames, **kwargs)

                if type(result["text"]) is str and len(result["text"]) > 0:
                    text = result["text"]
                    self.transcription += text
                    logging.debug("Transcribed audio (one pass): " + text)

            logging.debug(f"Transcribed audio so far: '{self.transcription}'")
