import os
import logging
import json
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel

from src.ai.interactions.interaction_manager import InteractionManager

from src.tools.documents.document_tool import DocumentTool
from src.tools.documents.spreadsheet_tool import SpreadsheetsTool
from src.tools.code.code_tool import CodeTool
from src.tools.code.code_review_tool import CodeReviewTool
from src.tools.llm.llm_tool import LLMTool
from src.tools.weather.weather_tool import WeatherTool
from src.tools.general.time_tool import TimeTool
from src.tools.news.g_news_tool import GNewsTool

from src.ai.agents.code.stubbing_agent import Stubber
from src.ai.agents.general.generic_tools_agent import GenericTool


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
        # "summarize_search_topic": {
        #     "display_name": "Summarize Searched Topic",
        #     "help_text": "Performs a deep search through the loaded documents, and summarizes the results of that search.",
        #     "enabled_by_default": True,
        #     "requires_documents": True,
        # },
        "summarize_entire_document": {
            "display_name": "Summarize Whole Document (⚠️ Slow / Expensive)",
            "help_text": "Summarizes an entire document using one of the summarization methods.  This is slow and expensive, so use it sparingly.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "list_documents": {
            "display_name": "List Documents",
            "help_text": "Lists all loaded documents.",
            "enabled_by_default": False,
            "requires_documents": True,
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
        "conduct_code_review_from_file_id": {
            "display_name": "Perform Code Review on Loaded Code File",
            "help_text": "Performs a code review of a specified code file.",
            "enabled_by_default": True,
            "requires_documents": True,
        },
        "conduct_code_review_from_url": {
            "display_name": "Perform Code Review on URL file",
            "help_text": "Performs a code review of a specified code file.",
            "enabled_by_default": True,
            "requires_documents": False,
        },
        "create_code_review_issue_tool": {
            "display_name": "Create Issue from Code Review",
            "help_text": "Creates an issue on your selected provider from a Code Review",
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
    }

    def get_enabled_tools(self) -> list[GenericTool]:
        # Filter the list by tools that are enabled in the environment (or their defaults)
        tools_that_should_be_enabled = [
            tool for tool in self.tools if self.is_tool_enabled(tool)
        ]

        # Now filter them down based on document-related tools, and if there are documents loaded
        if self.interaction_manager.get_loaded_documents_count() <= 0:
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
        val = os.environ.get(tool_name, None)
        if val is not None:
            # If it is, use the value
            return val.lower() == "true"
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
                    os.environ[tool_name] = 'False'
                else:
                    os.environ[tool_name] = 'True'
                break

    def initialize_tools(
        self,
        configuration,
        interaction_manager: InteractionManager,
        llm: BaseLanguageModel,
    ) -> None:
        self.configuration = configuration
        self.interaction_manager = interaction_manager
        self.llm = llm

        """Used to create the actual tools in the tool set."""
        document_tool = DocumentTool(
            configuration=configuration,
            interaction_manager=interaction_manager,
            llm=llm,
        )
        spreadsheet_tool = SpreadsheetsTool(
            configuration=configuration,
            interaction_manager=interaction_manager,
            llm=llm,
        )
        code_tool = CodeTool(
            configuration=configuration,
            interaction_manager=interaction_manager,
            llm=llm,
        )
        stubber_tool = Stubber(
            code_tool=code_tool,
            document_tool=document_tool,
            # callbacks=self.callbacks,
            interaction_manager=self.interaction_manager,
        )
        code_review_tool = CodeReviewTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )
        llm_tool = LLMTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )
        weather_tool = WeatherTool()

        generic_tools = [
            GenericTool(
                description="Uses an LLM to analyze data.",
                additional_instructions="Best used at the end of a chain of tools.  This tool is useful for when you want to generate a response from data you have gathered, such as after searching for various topics, or taking information from disparate sources in order to combine it into an answer for the user.",
                function=llm_tool.analyze_with_llm,
            ),
            GenericTool(
                description="Searches the loaded documents for a query.",
                additional_instructions="Searches the loaded files (or the specified file when target_file_id is set) for the given query. The target_file_id argument is optional, and can be used to search a specific file if the user has specified one.  Note: This tool only looks at a small subset of the document content in its search, it is not good for getting large chunks of content.",
                #The `search_type` parameter tells the tool what kind of search to perform.  You can perform a similarity search (default, 'Similarity'), which looks for similarity in the meaning of phrases.  Or it can perform a keyword search ('Keyword'), which matches a keyword or phrase.  Think carefully about which search_type to use.
                document_class="Code', 'Spreadsheet', or 'Document",  # lame formatting
                function=document_tool.search_loaded_documents,
            ),
            # GenericTool(
            #     description="Searches through all documents for the specified topic, and summarizes the results.",
            #     additional_instructions="Performs a deep search across the loaded documents in order to summarize a topic.  Similar to . Do not use this tool for specific document queries about topics, roles, or details. Instead, directly search the loaded documents for specific information related to the user's query. The target_file_id argument is required.",
            #     document_class="Code', 'Spreadsheet', or 'Document",  # lame formatting
            #     function=document_tool.summarize_search_topic,
            #     # return_direct=False,
            # ),
            GenericTool(
                description="Summarizes an entire document.",
                additional_instructions="This tool should only be used for getting a very general summary of an entire document. Do not use this tool for specific queries about topics, roles, or details. Instead, directly search the loaded documents for specific information related to the user's query. The target_file_id argument is required.",
                document_class="Code', 'Spreadsheet', or 'Document",  # lame formatting
                function=document_tool.summarize_entire_document,
            ),
            GenericTool(
                description="Lists all loaded documents.",
                function=document_tool.list_documents,
            ),
            GenericTool(
                description="Gets details about a specific part of a code file.",
                additional_instructions="Useful for getting the details of a specific signature (signature cannot be blank) in a specific loaded 'Code' file (required: target_file_id).",
                document_class="Code",
                function=code_tool.get_code_details,
            ),
            GenericTool(
                description="Gets the high-level structure of a code file.",
                additional_instructions="Useful for looking at the code structure of a single file. This tool only works when you specify a file. It will give you a list of module names, function signatures, and class method signatures in the specified file (represented by the 'target_file_id').",
                document_class="Code",
                function=code_tool.get_code_structure,
            ),
            GenericTool(
                description="Gets the dependency graph of a code file.",
                additional_instructions="Use this tool when a user is asking for the dependencies of any code file. This tool will return a dependency graph of the specified file (represented by the 'target_file_id').",
                document_class="Code",
                function=code_tool.get_pretty_dependency_graph,
                return_direct=False,
            ),
            GenericTool(
                description="Creates stubs for a specified code file.",
                additional_instructions="Create mocks / stubs for the dependencies of a given code file. Use this when the user asks you to mock or stub out the dependencies for a given file.",
                document_class="Code",
                function=stubber_tool.create_stubs,
                return_direct=False,
            ),
            GenericTool(
                description="Gets all of the code in the target file.",
                additional_instructions="Useful for getting all of the code in a specific 'Code' file when the user asks you to show them code from a particular file.",
                document_class="Code",
                function=code_tool.get_all_code_in_file,
                return_direct=False,
            ),
            GenericTool(
                description="Performs a code review of a specified code file.",
                function=code_review_tool.conduct_code_review_from_file_id,
                additional_instructions="Use this tool for conducting a code review on a loaded code file.  Use the additional_instructions field to pass any code review additional instructions from the user, if any.",
                return_direct=False,
            ),
            GenericTool(
                description="Performs a code review of a specified code file.",
                function=code_review_tool.conduct_code_review_from_url,
                additional_instructions="Use this tool for conducting a code review on a URL. Make sure to extract and pass the URL specified by the user as an argument to this tool.  Use the additional_instructions field to pass any code review additional instructions from the user, if any.",
                return_direct=False,
            ),
            GenericTool(
                description="Creates a Gitlab issue from Code Review.",
                function=code_review_tool.create_code_review_issue_tool,
                additional_instructions="",
                return_direct=False,
            ),
            GenericTool(
                description="Queries a specific spreadsheet.",
                document_class="Spreadsheet",
                additional_instructions="Useful for querying a specific spreadsheet.  If the target document is a 'Spreadsheet', always use this tool. Never use this tool on documents that are not classified as 'Spreadsheet'.",
                function=spreadsheet_tool.query_spreadsheet,
            ),
            GenericTool(
                description="Queries the weather at a given location.",
                additional_instructions="Location is a string representing the City, State, and Country (if outside the US) of the location to get the weather for, e.g. 'Phoenix, AZ'. Date is optional, and should be a string ('%Y-%m-%d') representing the date to get the weather for, e.g. '2023-4-15'.  If no date is provided, the weather for the current date will be returned.",
                function=weather_tool.get_weather,
            ),
            GenericTool(
                description="Get the current time in the specified IANA time zone.",
                additional_instructions="current_time_zone (str): The IANA time zone to get the current time in, for example: 'America/New_York'.",
                function=TimeTool().get_time,
            ),
            GenericTool(
                description="Get a list of news headlines and article URLs for a specified term.",
                additional_instructions="Always return the Headline, whatever summary there is, the source, and the URL.",
                function=GNewsTool().get_news_for_topic,
            ),
            GenericTool(
                description="Get a list of headlines and article URLs for the top news headlines.",
                additional_instructions="Always return the Headline, whatever summary there is, the source, and the URL.",
                function=GNewsTool().get_top_news_headlines,
            ),
        ]

        for tool in generic_tools:
            self.tools[tool.name]["tool"] = tool
