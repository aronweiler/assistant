import os
import logging
from typing import List

from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.tools.tool_loader import get_available_tools

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
            tool for tool in self.tools if ToolManager.is_tool_enabled(tool.name)
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
    def is_tool_enabled(tool_name) -> bool:
        # See if this tool name is in the environment
        configuration = get_app_configuration()
        config = configuration["tool_configurations"].get(tool_name, None)
        if config is not None:
            # If it is, use the value
            return config.get("enabled", False)

        # Disabled by default
        return False

    @staticmethod
    def should_include_in_conversation(tool_name):
        configuration = get_app_configuration()
        if tool_name in configuration["tool_configurations"]:
            return configuration["tool_configurations"][tool_name].get(
                "include_in_conversation", False
            )
        else:
            return False

    @staticmethod
    def should_return_direct(tool_name):
        configuration = get_app_configuration()
        if tool_name in configuration["tool_configurations"]:
            return configuration["tool_configurations"][tool_name].get(
                "return_direct", False
            )
        else:
            return False

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
