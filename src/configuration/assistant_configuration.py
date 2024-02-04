import json


class ModelConfiguration:
    def __init__(
        self,
        llm_type,
        model,
        temperature,
        max_retries,
        max_model_supported_tokens,
        uses_conversation_history,
        max_conversation_history_tokens,
        max_completion_tokens,
        model_kwargs=None,
    ):
        self.llm_type = llm_type
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.max_model_supported_tokens = max_model_supported_tokens
        self.uses_conversation_history = uses_conversation_history
        self.max_conversation_history_tokens = max_conversation_history_tokens
        self.max_completion_tokens = max_completion_tokens
        self.model_kwargs = model_kwargs


class ApplicationConfigurationLoader:
    @staticmethod
    def from_file(file_path):
        with open(file_path, "r") as file:
            config_data = json.load(file)

        return config_data

    @staticmethod
    def save_to_file(config_data, file_path):
        with open(file_path, "w") as file:
            json.dump(config_data, file, indent=4)

