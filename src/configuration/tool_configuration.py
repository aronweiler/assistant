from typing import List
from configuration.type_configuration import TypeConfiguration


class ToolConfiguration:
    def __init__(self, name, type_configuration: TypeConfiguration, function_name: str, arguments: dict = None):
        self.name = name
        self.type_configuration = type_configuration
        self.function_name = function_name
        self.arguments = arguments

    @staticmethod
    def from_json_file(file_path: str) -> List["ToolConfiguration"]:
        import json
        import os

        current_directory = os.getcwd()

        with open(file_path, "r") as json_file:
            config = json.load(json_file)

        return [ToolConfiguration.from_dict(tool) for tool in config["tools"]]

    @staticmethod
    def from_dict(config: dict) -> "ToolConfiguration":
        name = config["name"]
        function_name = config["function_name"]
        if "arguments" in config:
            arguments = config["arguments"]
        else:
            arguments = None

        type_configuration = TypeConfiguration.from_dict(config)

        return ToolConfiguration(name, type_configuration, function_name, arguments)

