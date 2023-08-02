from typing import List, Union
from configuration.ai_configuration import AIConfiguration
from configuration.runner_configuration import RunnerConfiguration


class AssistantConfiguration:
    def __init__(
        self,
        config_file_path,
        ai: AIConfiguration,
        runners: Union[List[RunnerConfiguration], None],
    ):
        self.config_file_path = config_file_path
        self.ai = ai
        self.runners = runners

    @staticmethod
    def from_file(config_file_path: str) -> "AssistantConfiguration":
        import json

        with open(config_file_path, "r") as config_file:
            config = json.load(config_file)

        ai = AIConfiguration.from_dict(config["ai"])
        runners = [
            RunnerConfiguration.from_dict(runner) for runner in config["runners"]
        ]

        return AssistantConfiguration(config_file, ai, runners)
