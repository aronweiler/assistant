import os
import logging

from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.tools.tool_loader import get_available_tools

from src.ai.agents.general.generic_tool import GenericTool


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
            if self.is_tool_enabled(tool.name)
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

    def is_tool_enabled(self, tool_name) -> bool:
        # See if this tool name is in the environment
        config = self.configuration["tool_configurations"].get(tool_name, None)
        if config is not None:
            # If it is, use the value
            return config.get("enabled", False)

        # Disabled by default
        return False

    def get_all_tools(self):
        return self.tools

    def toggle_tool(self, tool_name: str):
        for tool in self.tools:
            if tool == tool_name:
                if self.is_tool_enabled(tool_name):
                    os.environ[tool_name] = "False"
                else:
                    os.environ[tool_name] = "True"
                break

    def should_return_direct(self, tool_name):
        if tool_name in self.configuration["tool_configurations"]:
            return self.configuration["tool_configurations"][tool_name].get(
                "return_direct", False
            )
        else:
            return False
