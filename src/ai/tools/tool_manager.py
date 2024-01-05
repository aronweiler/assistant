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
    tools = {
        "analyze_with_llm": {
            "display_name": "Analyze Results",
            "help_text": "Uses an LLM to analyze results of another query or queries",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "search_loaded_documents": {
            "display_name": "Search Documents",
            "help_text": "Searches the loaded documents for a query. If the query is directed at a specific document, this will search just that document, otherwise, it will search all loaded documents.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "search_entire_document": {
            "display_name": "Search Entire Document",
            "help_text": "Exhaustively searches a single document for one or more queries. ⚠️ This can be slow and expensive, as it will process the entire target document.",
            "enabled_by_default": False,
            "requires_documents": True,
        },
        # "summarize_search_topic": {
        #     "display_name": "Summarize Searched Topic",
        #     "help_text": "Performs a deep search through the loaded documents, and summarizes the results of that search.",
        #     "enabled_by_default": True,
        #     "requires_documents": True,
        # },
        "summarize_entire_document": {
            "display_name": "Summarize Whole Document ( Slow / Expensive)",
            "help_text": "Summarizes an entire document using one of the summarization methods.  ⚠️ If you did not ingest your documents with the summary turned on, this can be slow and expensive, as it will process the entire document.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "list_documents": {
            "display_name": "List Documents",
            "help_text": "Lists all loaded documents.",
            "enabled_by_default": False,
            "requires_documents": False,
        },
        "get_code_details": {
            "display_name": "Code Details",
            "help_text": "Gets details about a specific part of a code file.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "get_code_structure": {
            "display_name": "Code Structure",
            "help_text": "Gets the high-level structure of a code file.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "get_pretty_dependency_graph": {
            "display_name": "Dependency Graph",
            "help_text": "Gets the dependency graph of a code file.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "create_stubs": {
            "display_name": "Create Stubs",
            "help_text": "Creates stubs for a specified code file.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "get_all_code_in_file": {
            "display_name": "Get All Code in File",
            "help_text": "Gets all of the code in the target file.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "retrieve_source_code_from_url": {
            "display_name": "Get Source Code from URL",
            "help_text": "Gets source code from supported provider, such as a GitHub or GitLab.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "conduct_code_review_from_file_id": {
            "display_name": "Perform a Code Review on Loaded Code File",
            "help_text": "Performs a code review of a specified code file.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "conduct_code_review_from_url": {
            "display_name": "Perform a Code Review on URL file",
            "help_text": "Performs a code review of a specified code file.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "create_code_review_issue": {
            "display_name": "Create Issue from Code Review",
            "help_text": "Creates an issue on your selected provider from a Code Review",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "commit_single_code_file": {
            "display_name": "Commit Code File",
            "help_text": "Commits a single code file to source control.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "conduct_code_refactor_from_file_id": {
            "display_name": "Perform a Code Refactor on Loaded Code File",
            "help_text": "Performs a code refactor of a specified code file.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "conduct_code_refactor_from_url": {
            "display_name": "Perform a Code Refactor via URL",
            "help_text": "Performs a refactor of a specified code file.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "create_cvss_evaluation": {
            "display_name": "Perform CVSS Evaluation",
            "help_text": "Creates a CVSS evaluation from vulnerability data.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "query_spreadsheet": {
            "display_name": "Query Spreadsheet",
            "help_text": "Queries a specific spreadsheet.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "get_weather": {
            "display_name": "Weather",
            "help_text": "Queries the weather at a given location.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "get_time": {
            "display_name": "Time",
            "help_text": "Get the current time in the specified IANA time zone.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "get_text_from_website": {
            "display_name": "Get Text from Website",
            "help_text": "Reads text from the specified URL.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "get_news_for_topic": {
            "display_name": "Search News",
            "help_text": "Get news headlines and article URLs for a search query.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "get_top_news_headlines": {
            "display_name": "Top News Headlines",
            "help_text": "Gets the top news headlines and article URLs.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "query_image": {
            "display_name": "Query Image",
            "help_text": "Queries an image.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "search_for_emails": {
            "display_name": "Search Email",
            "help_text": "Allows Jarvis to search for a message in your email.",
            "enabled_by_default": False,
            "requires_documents": False,
        },
        "get_email_by_ids": {
            "display_name": "Get Email Messages",
            "help_text": "Enables Jarvis to fetch emails by message ID.",
            "enabled_by_default": False,
            "requires_documents": False,
        },
        "search_businesses": {
            "display_name": "Search Businesses",
            "help_text": "Allows Jarvis to search for businesses matching the criteria and returns a list of businesses.",
            "enabled_by_default": False,
            "requires_documents": False,
        },
        "get_all_business_details": {
            "display_name": "Get Business Details",
            "help_text": "Allows Jarvis to get all of the details of a specific business.",
            "enabled_by_default": False,
            "requires_documents": False,
        },
    }

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

        generic_tools = get_available_tools(self.configuration, self.conversation_manager)

        for tool_name, tool in generic_tools:
            self.tools[tool_name]["tool"] = tool

    # def add_gmail_tools(self, generic_tools):
    #     gmail_tool = GmailTool()

    #     if gmail_tool.toolkit is not None:
    #         generic_tools.append(
    #             GenericTool(
    #                 description="Searches for a specific topic in the user's email.",
    #                 additional_instructions="Always use this tool when the user asks to search for an email message or messages. The input must be a valid Gmail query.",
    #                 function=gmail_tool.search_for_emails,
    #                 name="search_for_emails",
    #                 return_direct=self.should_return_direct(
    #                     gmail_tool.search_for_emails.__name__
    #                 ),
    #             )
    #         )

    #         generic_tools.append(
    #             GenericTool(
    #                 description="Gets one or more emails by message ID.",
    #                 additional_instructions="Use this tool to fetch one or more emails by message ID. Returns the thread ID, snippet, body, subject, and sender.  The message_ids field is required.  You should not use this tool if you dont have one or more valid message ID (from search_for_emails) to pass in.",
    #                 function=gmail_tool.get_email_by_ids,
    #                 name="get_email_by_ids",
    #                 return_direct=self.should_return_direct(
    #                     gmail_tool.get_email_by_ids.__name__
    #                 ),
    #             )
    #         )
