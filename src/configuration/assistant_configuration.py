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


# Example usage
if __name__ == "__main__":
    json_file_path = "configurations/ui_configs/ui_config.json"
    with open(json_file_path, "r") as file:
        json_string = file.read()

    config = AssistantConfigurationLoader.from_file(json_file_path)
    # config = AssistantConfigurationLoader.from_string(json_string)

    print(config.general_ai.model_configuration.llm_type)
    print(config.general_ai.model_configuration.model)
    print(config.general_ai.model_configuration.temperature)

    for route in config.general_ai.destination_routes:
        print(route.name)
        print(route.module)
        print(route.class_name)
        print(route.description)
        print(route.model_configuration.model)
        print(route.model_configuration.temperature)
