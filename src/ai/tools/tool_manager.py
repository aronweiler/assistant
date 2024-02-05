import os
import logging
from typing import List

from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.tools.tool_loader import get_available_tools, get_tool_setting

from src.ai.agents.general.generic_tool import GenericTool
from src.utilities.configuration_utilities import (
    get_app_configuration,
    get_tool_configuration,
)


class ToolManager:
    def __init__(self, configuration, conversation_manager: ConversationManager):
        self.configuration = configuration
        self.conversation_manager = conversation_manager

        self.tools = get_available_tools(
            configuration=configuration, conversation_manager=conversation_manager
        )

    def get_enabled_tools(self) -> list[GenericTool]:
        # Filter the list by tools that are enabled in the environment (or their defaults)
        tools_that_should_be_enabled = [
            tool
            for tool in self.tools
            if ToolManager.is_tool_enabled(
                conversation_manager=self.conversation_manager, tool_name=tool.name
            )
        ]

        # Now filter them down based on document-related tools, and if there are documents loaded
        if self.conversation_manager.get_loaded_documents_count() <= 0:
            tools_that_should_be_enabled = [
                tool
                for tool in tools_that_should_be_enabled
                if not tool.requires_documents
            ]

        # Now filter them down based on repo-related tools, and if there is a repository loaded
        if self.conversation_manager.get_selected_repository() is None:
            tools_that_should_be_enabled = [
                tool
                for tool in tools_that_should_be_enabled
                if not tool.requires_repository
            ]

        return tools_that_should_be_enabled

    def get_all_tools(self):
        return self.tools

    @staticmethod
    def is_tool_enabled(conversation_manager, tool_name) -> bool:
        # See if this tool name is in the environment

        setting = get_tool_setting(
            conversation_manager=conversation_manager,
            function_name=tool_name,
            setting_name="enabled",
            default_value=False,
        )
        
        logging.debug(f"ToolManager.is_tool_enabled: {tool_name} setting: {setting}")
        
        # If the setting is a string, then we need to convert it to a boolean
        if isinstance(setting, str):
            return setting.lower() == "true"
        else:
            return setting

    @staticmethod
    def get_tool_category(tool_name, conversation_manager):
        setting = get_tool_setting(
            conversation_manager=conversation_manager,
            function_name=tool_name,
            setting_name="get_tool_category",
            default_value=False,
        )

        return setting

    @staticmethod
    def should_include_in_conversation(tool_name, conversation_manager):
        setting = get_tool_setting(
            conversation_manager=conversation_manager,
            function_name=tool_name,
            setting_name="include_in_conversation",
            default_value=False,
        )

        # If the setting is a string, then we need to convert it to a boolean
        if isinstance(setting, str):
            return setting.lower() == "true"
        else:
            return setting

    @staticmethod
    def should_return_direct(tool_name, conversation_manager):
        setting = get_tool_setting(
            conversation_manager=conversation_manager,
            function_name=tool_name,
            setting_name="return_direct",
            default_value=False,
        )
        
        # If the setting is a string, then we need to convert it to a boolean
        if isinstance(setting, str):
            return setting.lower() == "true"
        else:
            return setting

    @staticmethod
    def get_tool_details(tool_name: str, tools: List[GenericTool]):
        tool_details = ""
        for tool in tools:
            if tool.name == tool_name:
                tool_details = ToolManager._get_formatted_tool_string(tool=tool)

        return tool_details

    @staticmethod
    def _get_formatted_tool_string(tool: GenericTool):
        args_schema = "\n\t".join(
            [
                f"{t['argument_name']}, {t['argument_type']}, {t['required']}"
                for t in tool.schema["parameters"]
            ]
        )
        if tool.additional_instructions:
            additional_instructions = (
                "\nAdditional Instructions: " + tool.additional_instructions
            )
        else:
            additional_instructions = ""

        return f"Name: {tool.name}\nDescription: {tool.description}{additional_instructions}\nArgs (name, type, optional/required):\n\t{args_schema}"
