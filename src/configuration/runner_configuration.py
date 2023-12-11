import json

class RunnerConfig:
    def __init__(self, name, module_name, class_name, arguments):
        self.name = name
        self.module_name = module_name
        self.class_name = class_name
        self.arguments = arguments

    @staticmethod
    def load_from_dict(config_dict):
        name = config_dict['name']
        module_name = config_dict['module_name']
        class_name = config_dict['class_name']
        arguments = RunnerArguments(**config_dict['arguments'])
        return RunnerConfig(name, module_name, class_name, arguments)

    @staticmethod
    def load_from_file(config_file):
        with open(config_file, 'r') as f:
            config_dict = json.load(f)
            return RunnerConfig.load_from_dict(config_dict['runner_config'])

class RunnerArguments:
    def __init__(self, collection_name, conversation_id, user_email):
        self.collection_name = collection_name
        self.conversation_id = conversation_id
        self.user_email = user_email

if __name__ == "__main__":
    # Example usage
    config_dict = {
        "name": "Console Runner",
        "module_name": "runners.console.console_runner",
        "class_name": "ConsoleRunner",
        "arguments": {
            "collection_name": "Console Collection",
            "conversation_id": "d6c12a4d-ee36-4f10-9891-e31b4003d2c4"
        }
    }

    config = RunnerConfig.load_from_dict(config_dict)
    print(config.name)
    print(config.module_name)
    print(config.class_name)
    print(config.arguments.collection_name)
    print(config.arguments.conversation_id)
