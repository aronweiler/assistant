import os
import logging
import json
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel

from src.ai.interactions.interaction_manager import InteractionManager
from src.tools.code.issue_tool import IssueTool

from src.tools.documents.document_tool import DocumentTool
from src.tools.documents.spreadsheet_tool import SpreadsheetsTool
from src.tools.code.code_tool import CodeTool
from src.tools.code.code_review_tool import CodeReviewTool
from src.tools.email.gmail_tool import GmailTool
from src.tools.llm.llm_tool import LLMTool
from src.tools.restaurants.yelp_tool import YelpTool
from src.tools.weather.weather_tool import WeatherTool
from src.tools.general.time_tool import TimeTool
from src.tools.news.g_news_tool import GNewsTool

from src.ai.agents.code.stubbing_agent import Stubber
from src.ai.agents.general.generic_tools_agent import GenericTool

from src.tools.images.llava import LlavaTool


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
        "create_code_review_issue": {
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

    def initialize_tools(
        self, configuration, interaction_manager: InteractionManager
    ) -> None:
        self.configuration = configuration
        self.interaction_manager = interaction_manager

        """Used to create the actual tools in the tool set."""
        document_tool = DocumentTool(
            configuration=configuration, interaction_manager=interaction_manager
        )
        spreadsheet_tool = SpreadsheetsTool(
            configuration=configuration, interaction_manager=interaction_manager
        )
        code_tool = CodeTool(
            configuration=configuration,
            interaction_manager=interaction_manager,
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
        )
        issue_tool = IssueTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
        )
        llm_tool = LLMTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
        )
        weather_tool = WeatherTool()

        llava_tool = LlavaTool(
            llava_path=os.environ.get("LLAVA_PATH", None),
            llava_model=os.environ.get("LLAVA_MODEL", None),
            llava_mmproj=os.environ.get("LLAVA_MMPROJ", None),
            llava_temp=float(os.environ.get("LLAVA_TEMP", 0.1)),
            llava_gpu_layers=int(os.environ.get("LLAVA_GPU_LAYERS", 50)),
        )
        
        yelp_tool = YelpTool()

        generic_tools = [
            GenericTool(
                description="Analyze results of another query or queries.",
                additional_instructions="This tool is useful for when you want to combine data you have gathered, or just take a moment to think about things.  IMPORTANT: This tool does not have access to documents, or any data outside of what you pass in the 'data_to_analyze' argument.",
                function=llm_tool.analyze_with_llm,
            ),
            GenericTool(
                description="Searches the loaded documents for a query.",
                additional_instructions="Searches the loaded files (or the specified file when target_file_id is set).  The user's input should be reworded to be both a keyword search (keywords_list: list of important keywords) and a semantic similarity search query (semantic_similarity_query: a meaningful phrase).  user_query should be a succinctly phrased version of the original user input (phrased as the ultimate question to answer). The target_file_id argument is optional, and can be used to search a specific file if the user has specified one.  Note: This tool only looks at a small subset of the document content in its search, it is not good for getting large chunks of content.",
                document_class="Code', 'Spreadsheet', or 'Document",  # lame formatting
                function=document_tool.search_loaded_documents,
            ),
            GenericTool(
                description="Exhaustively searches a single document for one or more queries.",
                additional_instructions="Exhaustively searches a single document for one or more queries.  The input to this tool (queries) should be a list of one or more stand-alone FULLY FORMED questions you want answered.  Make sure that each question can stand on its own, without referencing the chat history or any other context.  The question should be formed for the purpose of having an LLM use it to search a chunk of text, e.g. 'What is the origin of the universe?', or 'What is the meaning of life?'.",
                document_class="Code', 'Spreadsheet', or 'Document",  # lame formatting
                function=document_tool.search_entire_document,
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
                function=issue_tool.create_code_review_issue,
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
                additional_instructions="When using this tool, always return the Headline, whatever summary there is, the source, and the URL.",
                function=GNewsTool().get_news_for_topic,
            ),
            GenericTool(
                description="Get a list of headlines and article URLs for the top news headlines.",
                additional_instructions="When using this tool, always return the Headline, whatever summary there is, the source, and the URL.",
                function=GNewsTool().get_top_news_headlines,
            ),
            GenericTool(
                description="Queries a loaded Image file.  This only works on Image classified files.",
                additional_instructions="Never use this tool on documents that are not classified as 'Image'.  The 'query' argument should always be a stand-alone FULLY-FORMED query, no co-references, no keywords, etc., (e.g. 'What is going on in this image?', or 'Where is object X located in relation to object Y?').",
                function=llava_tool.query_image,
            ),
            GenericTool(
                description="Searches for businesses matching the criteria and returns a list of businesses.",
                additional_instructions="Allows specifying the location, search term, categories, whether to only return open businesses, price range (1=low-price, 2=med-price, 3=high=price- can be combined), minimum rating, and maximum number of businesses to return.",
                function=yelp_tool.search_businesses,
            ),
            GenericTool(
                description="Retrieves details of a specific business, matching the business_id.",
                additional_instructions="business_id is the id of the business, discovered by using the search_businesses tool.",
                function=yelp_tool.get_all_business_details,
            ),
        ]

        self.add_gmail_tools(generic_tools)

        for tool in generic_tools:
            self.tools[tool.name]["tool"] = tool

    def add_gmail_tools(self, generic_tools):
        gmail_tool = GmailTool()

        if gmail_tool.toolkit is not None:
            generic_tools.append(
                GenericTool(
                    description="Searches for a specific topic in the user's email.",
                    additional_instructions="Always use this tool when the user asks to search for an email message or messages. The input must be a valid Gmail query.",
                    function=gmail_tool.search_for_emails,
                    name="search_for_emails",
                )
            )

            generic_tools.append(
                GenericTool(
                    description="Gets one or more emails by message ID.",
                    additional_instructions="Use this tool to fetch one or more emails by message ID. Returns the thread ID, snippet, body, subject, and sender.  The message_ids field is required.  You should not use this tool if you dont have one or more valid message ID (from search_for_emails) to pass in.",
                    function=gmail_tool.get_email_by_ids,
                    name="get_email_by_ids",
                )
            )
