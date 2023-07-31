import os
import webrtcvad
import queue
import logging
import threading

from runners.voice.speech_to_text import SpeechToText
from runners.voice.player import play_wav_file

class AudioTranscriber:
    def __init__(self, transcription_model_name = "base"):
        # Initialize WebRTC VAD
        self.vad = webrtcvad.Vad()
        # Aggressive VAD mode
        self.vad.set_mode(3)

        self.audio_queue = queue.Queue()
        self.buffer_size = 100  # This should never be reached while transcribing
        self.queue_timeout = 1
        self.pre_capture_audio_buffer_size = 20

        self.vad_chunk_size = 320  # Needs to be multiples of 80

        self.speech_to_text = SpeechToText(model_name=transcription_model_name)

        self.stop_event = threading.Event()

    def add_frame_to_buffer(self, frame):
        if self.audio_queue.full():
            logging.debug("Audio queue full, dropping first frame")
            self.audio_queue.get()

        self.audio_queue.put(frame, block=True, timeout=self.queue_timeout)

    def transcribe_until_silence(self, audio_rate, silence_limit):
        logging.debug(
            f"transcribe_until_silence called with rate={audio_rate},and silence_limit={silence_limit}"
        )

        self.stop_event.clear()

        # Get the pre-capture audio
        self.enqueue_pre_capture_audio()

        # Start transcribing
        self.speech_to_text.start_transcribing()

        # Start listening for silence
        self.listen_for_silence(audio_rate, silence_limit, self.stop_event)

    def stop_transcribing(self):
        # Start transcribing
        self.speech_to_text.stop_transcribing()
        self.stop_event.set()

    def enqueue_pre_capture_audio(self):
        # Since sometimes the wake word capture is late, or the wake word is at the end of the buffer, we need to capture some audio around the wake word
        # Get the last X frames in the transcription queue.
        # This has the effect of getting the surrounding audio, and also dropping any audio that was captured long before (like silence)

        # Loop to retrieve all of the entries from the audio_queue
        all_entries = []
        while not self.audio_queue.empty():
            frame = self.audio_queue.get()
            all_entries.append(frame)

        # Get the last 10 entries from the list using slicing
        pre_wake_word_frames_list = all_entries[-10:]

        # Append the last 10 entries to the pre_wake_word_frames deque
        for frame in pre_wake_word_frames_list:
            self.speech_to_text.enqueue_audio(frame)

    def listen_for_silence(self, audio_rate, silence_limit, stop_event):
        accumulated_silence = 0

        # Start listening for silence, enqueueing the audio as it comes in
        # When we see silence that exceeds the silence limit, stop listening
        while True and not stop_event.is_set():
            # Get the current frames out of the buffer and send them to the speech to text system
            while not self.audio_queue.empty():
                current_frame = self.audio_queue.get(
                    block=True, timeout=self.queue_timeout
                )
                self.speech_to_text.enqueue_audio(current_frame)

                # Also listen for silence in these frames
                # Get the length of the silence in the current frames
                # Any time speech is detected, the silence length should be reset
                # The returned silence length is a concatenation of the accumulated silence and the silence in the current frames
                accumulated_silence = self.get_silence_length(
                    current_frame, accumulated_silence, audio_rate
                )

            # If the silence threshold is met, stop listening
            if silence_limit < (self.vad_chunk_size / audio_rate) * accumulated_silence:
                logging.debug(
                    f"Silence threshold met, accumulated_silence={accumulated_silence}"
                )

                # When we hit the silence threshold, stop transcribing
                self.speech_to_text.stop_transcribing()

                break

        play_wav_file(
            os.path.join(os.path.dirname(__file__), "audio", "boop-beep.wav"),
            self.stop_event,
        )

    def get_silence_length(self, frame, accumulated_silence, audio_rate):
        evaluation_frames = []
        # Split the frame into chunks of vad_chunk_size for the VAD
        for i in range(0, len(frame), self.vad_chunk_size):
            chunk = frame[i : i + self.vad_chunk_size]
            evaluation_frames.append(chunk)

        # Loop over all of the frames and evaluate them
        for vad_frame in evaluation_frames:
            # If the frame is speech, reset the accumulated silence, otherwise increment it
            if self.vad.is_speech(vad_frame, sample_rate=audio_rate):
                # logging.debug("Speech detected")
                accumulated_silence = 0
            else:
                # logging.debug("Silence detected")
                accumulated_silence += 1

        return accumulated_silence

    def get_transcription(self):
        return self.speech_to_text.get_transcription()
