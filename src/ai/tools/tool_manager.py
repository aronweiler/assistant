import os
import logging
import json
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel

from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.tools.tool_loader import get_available_tools
from src.tools.code.code_commit_tool import CodeCommitTool
from src.tools.code.code_retriever_tool import CodeRetrieverTool
from src.tools.code.issue_tool import IssueTool

from src.tools.documents.document_tool import DocumentTool
from src.tools.documents.spreadsheet_tool import SpreadsheetsTool
from src.tools.code.code_tool import CodeTool
from src.tools.code.code_review_tool import CodeReviewTool
from src.tools.code.code_refactor_tool import CodeRefactorTool
from src.tools.email.gmail_tool import GmailTool
from src.tools.llm.llm_tool import LLMTool
from src.tools.restaurants.yelp_tool import YelpTool
from src.tools.security.cvss_tool import CvssTool
from src.tools.weather.weather_tool import WeatherTool
from src.tools.general.time_tool import TimeTool
from src.tools.news.g_news_tool import GNewsTool

from src.ai.agents.code.stubbing_agent import Stubber
from src.ai.agents.general.generic_tools_agent import GenericTool

from src.tools.images.llava import LlavaTool
from src.tools.web.website_tool import WebsiteTool


class ToolManager:
    tools = {}

    def __init__(self, configuration):
        self.configuration = configuration

    def get_enabled_tools(self) -> list[GenericTool]:
        # Filter the list by tools that are enabled in the environment (or their defaults)
        tools_that_should_be_enabled = [
            tool for tool in self.tools if self.is_tool_enabled(tool)
        ]

        # Now filter them down based on document-related tools, and if there are documents loaded
        if self.conversation_manager.get_loaded_documents_count() <= 0:
            tools_that_should_be_enabled = [
                self.tools[tool]["tool"]
                for tool in tools_that_should_be_enabled
                if not self.tools[tool]["requires_documents"]
            ]
        else:
            tools_that_should_be_enabled = [
                self.tools[tool]["tool"] for tool in tools_that_should_be_enabled
            ]

        return tools_that_should_be_enabled

    def is_tool_enabled(self, tool_name) -> bool:
        # See if this tool name is in the environment
        config = self.configuration["tool_configurations"].get(tool_name, None)
        if config is not None:
            # If it is, use the value
            return config.get("enabled", False)
        else:
            # If it's not, use the default from the tool
            for tool in self.tools:
                if tool == tool_name:
                    return bool(self.tools[tool]["enabled_by_default"])

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

    def initialize_tools(
        self, configuration, conversation_manager: ConversationManager
    ) -> None:
        self.configuration = configuration
        self.conversation_manager = conversation_manager

        generic_tools = get_available_tools(
            self.configuration, self.conversation_manager
        )
        
        self.tools = generic_tools   
