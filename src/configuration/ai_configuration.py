from typing import List, Union
from configuration.type_configuration import TypeConfiguration
from configuration.llm_configuration import LLMConfiguration
from configuration.tool_configuration import ToolConfiguration


class AIConfiguration:
    def __init__(
        self,
        name,
        type_configuration: "TypeConfiguration",
        llm_configuration: "LLMConfiguration",
        subordinate_ais: Union[List["AIConfiguration"], None],
        tools: Union[List["ToolConfiguration"], None],
    ) -> None:
        self.name = name
        self.type_configuration:TypeConfiguration = type_configuration
        self.llm_configuration:LLMConfiguration = llm_configuration
        self.subordinate_ais:Union[List["AIConfiguration"], None] = subordinate_ais
        self.tools:Union[List["ToolConfiguration"], None] = tools


    @staticmethod
    def from_dict(config: dict) -> "AIConfiguration":
        name = config["name"]

        from configuration.type_configuration import TypeConfiguration
        from configuration.llm_configuration import LLMConfiguration

        # Also add the tools
        tools = [
            ToolConfiguration.from_dict(tool) for tool in config["tools"]
        ] if "tools" in config else None

        type_configuration = TypeConfiguration.from_dict(config)
        llm_configuration = LLMConfiguration.from_dict(config["llm"], tools)

        if "subordinate_ais" in config:
            subordinate_ais = [
                AIConfiguration.from_dict(sub_ai)
                for sub_ai in config["subordinate_ais"]
            ]
        else:
            subordinate_ais = None

        tools = [
            ToolConfiguration.from_dict(tool) for tool in config["tools"]
        ] if "tools" in config else None

        return AIConfiguration(
            name, type_configuration, llm_configuration, subordinate_ais, tools
        )
