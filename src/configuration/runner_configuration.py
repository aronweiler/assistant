from typing import List, Union

from configuration.type_configuration import TypeConfiguration


class RunnerConfiguration:
    def __init__(self, name, enabled, type_configuration: TypeConfiguration, arguments: dict):
        self.name = name
        self.type_configuration = type_configuration
        self.arguments = arguments
        self.enabled = enabled

    @staticmethod
    def from_dict(config: dict) -> 'RunnerConfiguration':
        name = config["name"]
        type_configuration = TypeConfiguration.from_dict(config)
        arguments = config["arguments"]
        enabled = config.get("enabled", True)

        return RunnerConfiguration(name, enabled, type_configuration, arguments)
