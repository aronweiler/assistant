import json


class VoiceConfiguration:
    def __init__(
        self,
        user_email,
        activation_cooldown,
        mute_while_listening,
        save_audio,
        model_activation_threshold,
        wake_word_model_path,
        max_audio_queue_size,
        input_gain,
        sts_model,
    ):
        self.user_email = user_email
        self.activation_cooldown = activation_cooldown
        self.mute_while_listening = mute_while_listening
        self.save_audio = save_audio
        self.model_activation_threshold = model_activation_threshold
        self.wake_word_model_path = wake_word_model_path
        self.max_audio_queue_size = max_audio_queue_size
        self.input_gain = input_gain
        self.sts_model = sts_model

    @staticmethod
    def from_file(file_path):
        with open(file_path, "r") as file:
            config_data = json.load(file)
        return VoiceConfiguration(**config_data)

    @staticmethod
    def save_to_file(config_data, file_path):
        with open(file_path, "w") as file:
            json.dump(config_data, file, indent=4)
