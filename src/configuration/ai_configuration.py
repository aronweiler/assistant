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
        subordinate_ais: Union[List[str], None],
        tools: Union[List[str], None],
        store_conversation_history: bool,
        db_env_location: str = None,
        system_prompts: List[str] = None,
        include_system_info: bool = True,
    ) -> None:
        self.name = name
        self.type_configuration: TypeConfiguration = type_configuration
        self.llm_configuration: LLMConfiguration = llm_configuration
        self.subordinate_ais: Union[List[str], None] = subordinate_ais
        self.tools: Union[List[str], None] = tools
        self.store_conversation_history = store_conversation_history
        self.db_env_location = db_env_location
        self.system_prompts = system_prompts
        self.include_system_info = include_system_info

    @staticmethod
    def from_json_file(json_file_path: str) -> "AIConfiguration":
        import json

        with open(json_file_path, "r") as json_file:
            config = json.load(json_file)

        return AIConfiguration.from_dict(config)

    @staticmethod
    def from_dict(config: dict) -> "AIConfiguration":
        name = config["name"]

        from configuration.type_configuration import TypeConfiguration
        from configuration.llm_configuration import LLMConfiguration

        store_conversation_history = config["store_conversation_history"]
        db_env_location = config.get("db_env_location", None)

        system_prompts = config["system_prompts"]
        include_system_info = config["include_system_info"]
        
        # Load the tools files from the config and parse them into ToolConfiguration objects
        tools = ToolConfiguration.from_json_file(config["tools"])

        type_configuration = TypeConfiguration.from_dict(config)
        llm_configuration = LLMConfiguration.from_dict(config["llm"], tools)

        if "subordinate_ais" in config:
            subordinate_ais = [
                AIConfiguration.from_json_file(sub_ai)
                for sub_ai in config["subordinate_ais"]
            ]
        else:
            subordinate_ais = None

        # tools = (
        #     [ToolConfiguration.from_dict(tool) for tool in config["tools"]]
        #     if "tools" in config
        #     else None
        # )

        return AIConfiguration(
            name,
            type_configuration,
            llm_configuration,
            subordinate_ais,
            tools,
            store_conversation_history,
            db_env_location,
            system_prompts,
            include_system_info,
        )
