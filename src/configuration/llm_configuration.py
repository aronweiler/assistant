from configuration.type_configuration import TypeConfiguration
from configuration.llm_arguments_configuration import LLMArgumentsConfiguration


class LLMConfiguration:
    def __init__(
        self,
        name,
        type_configuration: TypeConfiguration,
        llm_arguments_configuration: LLMArgumentsConfiguration,
        tools,
    ) -> None:
        self.name = name
        self.type_configuration = type_configuration
        self.llm_arguments_configuration = llm_arguments_configuration
        self.tools = tools

    @staticmethod
    def from_dict(config: dict, tools):
        name = config["name"]
        type_configuration = TypeConfiguration.from_dict(config)
        llm_arguments_configuration = LLMArgumentsConfiguration.from_dict(
            config["arguments"], tools
        )

        return LLMConfiguration(name, type_configuration, llm_arguments_configuration, tools)
