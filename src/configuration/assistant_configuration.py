import json

class ModelConfiguration:
    def __init__(self, llm_type, model, temperature, max_model_supported_tokens, max_conversation_history_tokens, max_completion_tokens, max_retries):
        self.llm_type = llm_type
        self.model = model
        self.temperature = temperature
        self.max_model_supported_tokens = max_model_supported_tokens
        self.max_conversation_history_tokens = max_conversation_history_tokens
        self.max_completion_tokens = max_completion_tokens
        self.max_retries = max_retries

class Destination:
    def __init__(self, name, module, class_name, description, model_configuration):
        self.name = name
        self.module = module
        self.class_name = class_name
        self.description = description
        self.model_configuration = ModelConfiguration(**model_configuration)

class AssistantConfiguration:
    def __init__(self, user_email, db_env_location, request_router):
        self.user_email = user_email
        self.db_env_location = db_env_location
        self.request_router = request_router

class ConfigurationLoader:
    @staticmethod
    def from_file(file_path):
        with open(file_path, 'r') as file:
            config_data = json.load(file)
            return ConfigurationLoader.from_dict(config_data)
    
    @staticmethod
    def from_string(json_string):
        config_data = json.loads(json_string)
        return ConfigurationLoader.from_dict(config_data)
    
    @staticmethod
    def from_dict(config_dict):
        assistant_config_data = config_dict.get('assistant_configuration', {})
        request_router_data = assistant_config_data.get('request_router', {})
        destination_routes_data = request_router_data.get('destination_routes', [])
        
        destination_routes = []
        for route_data in destination_routes_data:
            destination_data = route_data.get('destination', {})
            destination = Destination(**destination_data)
            destination_routes.append(destination)
        
        assistant_configuration = AssistantConfiguration(
            user_email=assistant_config_data.get('user_email', ''),
            db_env_location=assistant_config_data.get('db_env_location', ''),
            request_router=destination_routes
        )
        
        return assistant_configuration

# Example usage
if __name__ == "__main__":
    json_file_path = "configurations/ui_configs/ui_config.json"
    with open(json_file_path, 'r') as file:
        json_string = file.read()
    
    config = ConfigurationLoader.from_file(json_file_path)
    # config = ConfigurationLoader.from_string(json_string)

    for route in config.request_router:
        print(route.name)
        print(route.module)
        print(route.class_name)
        print(route.description)
        print(route.model_configuration.model)
        print(route.model_configuration.temperature)
