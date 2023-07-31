class UserInformation:
    def __init__(self, json_args) -> None:
        self.user_name = json_args.get("user_name", None)
        self.user_age = json_args.get("user_age", None)
        self.user_location = json_args.get("user_location", None)
        self.user_email = json_args.get("user_email", None)
        self.settings = json_args.get("settings", {})

    def __getitem__(self, key):
        # Allow accessing the attributes using square brackets like a dictionary
        return getattr(self, key, None)

class WakeWordModel:
    def __init__(self, json_args, default_tts_voice) -> None:
        self.model_name = json_args["model_name"]
        self.model_path = json_args["model_path"]
        self.training_data = json_args.get("training_data", None)
        self.user_information = UserInformation(json_args.get("user_information", {"user_name": "Unknown", "user_age": None, "user_location": None, "user_email": None, "settings": {}}))
        self.tts_voice = json_args.get("tts_voice", default_tts_voice)        
        self.personality_keywords = json_args.get(
            "personality_keywords", "helpful, friendly"
        )

    def __getitem__(self, key):
        # Allow accessing the attributes using square brackets like a dictionary
        return getattr(self, key, None)

class VoiceRunnerConfiguration:
    def __init__(self, json_args):
        self.activation_cooldown = json_args["activation_cooldown"]
        self.mute_while_listening = json_args.get("mute_while_listening", False)
        self.save_audio = json_args.get("save_audio", False)
        self.default_tts_voice = json_args.get("default_tts_voice", "Brian")        
        self.model_activation_threshold = json_args.get(
            "model_activation_threshold", 0.5
        )
        self.wake_word_models = self.get_wake_word_models(
            json_args.get("wake_word_models", {})
        )
        self.max_audio_queue_size = json_args.get("max_audio_queue_size", 1024)
        self.input_gain = json_args.get("input_gain", 1.0)
        self.sts_model = json_args.get("sts_model", "base")
        self.db_env_location = json_args.get("db_env_location", None)
        self.top_k = json_args.get("top_k", 5)        

    def get_wake_word_models(self, json_args) -> list[WakeWordModel]:
        wake_word_models = []
        for wake_word_model in json_args:
            wake_word_models.append(WakeWordModel(wake_word_model, self.default_tts_voice))
        return wake_word_models
    
    def __getitem__(self, key):
        # Allow accessing the attributes using square brackets like a dictionary
        return getattr(self, key, None)
