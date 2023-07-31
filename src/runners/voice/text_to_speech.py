from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
import logging
import numpy as np

import os
import sys

# Add the path to the 'other_directory' to sys.path
other_directory_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(other_directory_path)

from runners.voice.player import  play_mp3_stream

class TextToSpeech():

    def __init__(self):        
        # Create a client using the credentials and region
        # section of the AWS credentials file (~/.aws/credentials).
        self.session = Session(profile_name="default")
        self.polly = self.session.client("polly")
        self.sample_rate = 16000

    def speak(self, text, voice_id="Brian", stop_event=None, speech_rate_percentage=100):
        try:
            # Request speech synthesis
            # Adjust the speaking rate using SSML prosody.  
            # This opens the door to having the AI generate SSML tags for things like emphasis, pauses, etc.
            text = f"<speak><prosody rate=\"{speech_rate_percentage}%\">" + text + "</prosody></speak>"
     
            response = self.polly.synthesize_speech(Text=text, OutputFormat="mp3", VoiceId=voice_id, SampleRate=str(self.sample_rate), TextType="ssml")
        except (BotoCoreError, ClientError) as error:
            logging.error(error)
            # TODO: Fallback to something else??            
            return

        # Access the audio stream from the response
        if "AudioStream" in response:
            # Note: Closing the stream is important because the service throttles on the
            # number of parallel connections. Here we are using contextlib.closing to
            # ensure the close method of the stream object will be called automatically
            # at the end of the with statement's scope.
            with closing(response["AudioStream"]) as stream:               

                try:
                    mp3_data = stream.read()
                    # Play the data by reading the stream until it is complete
                    while mp3_data != b"" and (stop_event is None or not stop_event.is_set()):                        
                        play_mp3_stream(mp3_data, stop_event)
                        # Read more data
                        mp3_data = stream.read()
                        
                except IOError as error:
                    # Could not play the audio
                    logging.error(error)
                    return

        else:
            # The response didn't contain audio data
            logging.error("Could not stream audio")
            return


if __name__ == "__main__":
    

    tts = TextToSpeech()
    tts.speak("Hello, my name is Jarvis.  I am a friendly AI voice assistant.  How can I help you today?")