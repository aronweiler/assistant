import json


class ModelConfiguration:
    def __init__(
        self,
        llm_type,
        model,
        temperature,
        max_retries,
        max_model_supported_tokens,
        max_conversation_history_tokens,
        max_completion_tokens,
    ):
        self.llm_type = llm_type
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.max_model_supported_tokens = max_model_supported_tokens
        self.max_conversation_history_tokens = max_conversation_history_tokens
        self.max_completion_tokens = max_completion_tokens


class Destination:
    def __init__(
        self, name, module, class_name, description, system_prompt, model_configuration, is_default=False
    ):
        self.name = name
        self.module = module
        self.class_name = class_name
        self.description = description
        self.is_default = is_default
        self.system_prompt = system_prompt
        self.model_configuration = ModelConfiguration(**model_configuration)

class RequestRouter:
    def __init__(self, model_configuration, destination_routes):
        self.model_configuration = ModelConfiguration(**model_configuration)
        self.destination_routes = []
        for route in destination_routes:
            self.destination_routes.append(route)

class AssistantConfiguration:
    def __init__(self, user_email, request_router):
        self.user_email = user_email
        self.request_router = request_router


class ConfigurationLoader:
    @staticmethod
    def from_file(file_path):
        with open(file_path, "r") as file:
            config_data = json.load(file)
            return ConfigurationLoader.from_dict(config_data)

    @staticmethod
    def from_string(json_string):
        config_data = json.loads(json_string)
        return ConfigurationLoader.from_dict(config_data)

    @staticmethod
    def from_dict(config_dict):
        assistant_config_data = config_dict.get("assistant_configuration", {})
        request_router_data = assistant_config_data.get("request_router", {})
        destination_routes_data = request_router_data.get("destination_routes", [])
        model_configuration = request_router_data.get("model_configuration", [])

        destination_routes = []
        for route_data in destination_routes_data:
            destination_data = route_data.get("destination", {})
            destination = Destination(**destination_data)
            destination_routes.append(destination)

        assistant_configuration = AssistantConfiguration(
            user_email=assistant_config_data.get("user_email", ""),
            request_router=RequestRouter(model_configuration, destination_routes)
        )

        return assistant_configuration


# Example usage
if __name__ == "__main__":
    json_file_path = "configurations/ui_configs/ui_config.json"
    with open(json_file_path, "r") as file:
        json_string = file.read()

    config = ConfigurationLoader.from_file(json_file_path)
    # config = ConfigurationLoader.from_string(json_string)

    print(config.user_email)

    print(config.request_router.model_configuration.llm_type)    
    print(config.request_router.model_configuration.model)
    print(config.request_router.model_configuration.temperature)

    for route in config.request_router.destination_routes:
        print(route.name)
        print(route.module)
        print(route.class_name)
        print(route.description)
        print(route.model_configuration.model)
        print(route.model_configuration.temperature)
