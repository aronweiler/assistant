import logging
import json
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel

from langchain.agents.structured_chat.output_parser import (
    StructuredChatOutputParserWithRetries,
)

from langchain.memory.readonly import ReadOnlySharedMemory

from langchain.tools import StructuredTool

from langchain.agents import initialize_agent, AgentType, AgentExecutor

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfiguration,
)

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information

from src.tools.documents.document_tool import DocumentTool
from src.tools.documents.spreadsheet_tool import SpreadsheetsTool
from src.tools.code.code_tool import CodeTool
from src.tools.code.code_review_tool import CodeReviewTool
from src.tools.llm.llm_tool import LLMTool

from src.ai.agents.code.stubbing_agent import Stubber
from src.ai.agents.general.generic_tools_agent import GenericToolsAgent, GenericTool



class RetrievalAugmentedGenerationAI:
    """A RAG AI"""

    llm: BaseLanguageModel = None
    configuration: RetrievalAugmentedGenerationConfiguration

    def __init__(
        self,
        configuration: RetrievalAugmentedGenerationConfiguration,
        interaction_id: UUID,
        user_email: str,
        streaming: bool = False,
    ):
        self.configuration = configuration
        self.streaming = streaming

        self.llm = get_llm(
            self.configuration.model_configuration,
            tags=["retrieval-augmented-generation-ai"],
            streaming=streaming,
        )

        # Set up the interaction manager
        self.interaction_manager = InteractionManager(
            interaction_id,
            user_email,
            self.llm,
            self.configuration.model_configuration.max_conversation_history_tokens,
        )

        self.tools = self.create_tools()

    def get_enabled_tools(self):
        tools_that_should_be_enabled = [tool for tool in self.tools if tool["enabled"]]

        # Now filter them down based on document-related tools, and if there are documents loaded
        if self.interaction_manager.get_loaded_documents_count() <= 0:
            tools_that_should_be_enabled = [
                tool["tool"]
                for tool in tools_that_should_be_enabled
                if not tool["is_document_related"]
            ]
        else:
            tools_that_should_be_enabled = [
                tool["tool"] for tool in tools_that_should_be_enabled
            ]

        return tools_that_should_be_enabled

    def get_all_tools(self):
        return self.tools

    def toggle_tool(self, tool_name: str):
        for tool in self.tools:
            if tool["name"] == tool_name:
                if tool["enabled"]:
                    tool["enabled"] = False
                else:
                    tool["enabled"] = True
                break

    def create_agent(self, agent_timeout: int = 120):
        tools = self.get_enabled_tools()

        agent = GenericToolsAgent(
            tools=tools, model_configuration=self.configuration.model_configuration, interaction_manager=self.interaction_manager
        )

        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent, tools=[t.structured_tool for t in tools], verbose=True, max_execution_time=agent_timeout, early_stopping_method="generate"
        )

        return agent_executor

    def ___old_create_agent(self, agent_timeout: int = 120):
        logging.debug("Setting human message template")
        human_message_template = get_prompt(
            self.configuration.model_configuration.llm_type, "AGENT_TEMPLATE"
        )

        logging.debug("Setting memory")
        memory = ReadOnlySharedMemory(
            memory=self.interaction_manager.conversation_token_buffer_memory
        )

        logging.debug("Setting suffix")
        suffix = get_prompt(
            self.configuration.model_configuration.llm_type, "TOOLS_SUFFIX"
        )

        logging.debug("Setting format instructions")
        format_instructions = get_prompt(
            self.configuration.model_configuration.llm_type,
            "TOOLS_FORMAT_INSTRUCTIONS",
        )

        # This is a problem with langchain right now- hopefully it resolves soon, because the StructuredChatOutputParserWithRetries is crap without the llm
        try:
            output_parser = StructuredChatOutputParserWithRetries.from_llm(llm=self.llm)
        except Exception as e:
            logging.error(f"Could not create output parser: {e}")
            logging.warning("Falling back to default output parser")
            output_parser = StructuredChatOutputParserWithRetries()

        logging.debug("Setting agent kwargs")
        agent_kwargs = {
            "suffix": suffix,
            "format_instructions": format_instructions,
            "output_parser": output_parser,
            "input_variables": [
                "input",
                "loaded_documents",
                "chat_history",
                "agent_scratchpad",
                "system_information",
            ],
            "verbose": True,
        }

        logging.debug(f"Creating agent with kwargs: {agent_kwargs}")
        agent = initialize_agent(
            tools=self.get_enabled_tools(),
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            human_message_template=human_message_template,
            memory=memory,
            agent_kwargs=agent_kwargs,
            max_execution_time=agent_timeout,
            early_stopping_method="generate",  # try to generate a response if it times out
        )

        return agent

    def generate_detailed_document_chunk_summary(
        self,
        document_text: str,
    ) -> str:
        summary = self.llm.predict(
            get_prompt(
                self.configuration.model_configuration.llm_type,
                "DETAILED_DOCUMENT_CHUNK_SUMMARY_TEMPLATE",
            ).format(text=document_text)
        )
        return summary

    def generate_detailed_document_summary(
        self,
        file_id: int,
    ) -> str:
        document_summary = self.document_tool.summarize_entire_document(file_id)

        return document_summary

    def query(
        self,
        query: str,
        collection_id: int = None,
        agent_callbacks: List = [],
        kwargs: dict = {},
    ):
        # Set the document collection id on the interaction manager
        self.interaction_manager.collection_id = collection_id

        # Set the kwargs on the interaction manager (this is search params, etc.)
        self.interaction_manager.tool_kwargs = kwargs

        # Ensure we have a summary / title for the chat
        logging.debug("Checking to see if summary exists for this chat")
        self.check_summary(query=query)

        self.spreadsheet_tool.callbacks = agent_callbacks

        timeout = kwargs.get("agent_timeout", 120)
        logging.debug(f"Creating agent with {timeout} second timeout")
        agent = self.create_agent(agent_timeout=timeout)

        # Run the agent
        logging.debug("Running agent")
        results = agent.run(
            input=query,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            callbacks=agent_callbacks,
        )
        logging.debug("Agent finished running")

        # Adding this after the run so that the agent can't see it in the history
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_user_message(
            query
        )

        logging.debug(results)
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_ai_message(
            results
        )

        logging.debug("Added results to chat memory")

        return results

    def check_summary(self, query):
        if self.interaction_manager.interaction_needs_summary:
            logging.debug("Interaction needs summary, generating one now")
            interaction_summary = self.llm.predict(
                get_prompt(
                    self.configuration.model_configuration.llm_type,
                    "SUMMARIZE_FOR_LABEL_TEMPLATE",
                ).format(query=query)
            )
            self.interaction_manager.set_interaction_summary(interaction_summary)
            self.interaction_manager.interaction_needs_summary = False
            logging.debug(f"Generated summary: {interaction_summary}")

    def create_tools(self):
        """Used to create the initial tool set.  After creation, this can be modified by enabling/disabling tools."""
        self.document_tool = DocumentTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )
        self.spreadsheet_tool = SpreadsheetsTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )
        self.code_tool = CodeTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )
        self.stubber_tool = Stubber(
            code_tool=self.code_tool,
            document_tool=self.document_tool,
            # callbacks=self.callbacks,
            interaction_manager=self.interaction_manager,
        )
        self.code_review_tool = CodeReviewTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
        )
        self.llm_tool = LLMTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm
        )

        tools = [
            {
                "name": "LLM Query Tool",
                "about": "Uses a conversational LLM as a tool to answer a query.",
                "enabled": True,
                "is_document_related": False,
                "tool": GenericTool(
                    description="Uses a conversational LLM as a tool to answer a query.",
                    additional_instructions="This is useful for when you want to just generate a response from an LLM with the given query, such as when you have gathered enough data and would like to combine it into an answer for the user.  This tool is also useful for when you just want to answer a general question that does not involve any documents.",
                    function=self.llm_tool.query_llm,
                ),
            },
            {
                "name": "Search Documents",
                "about": "Searches the loaded documents for a query. If the query is directed at a specific document, this will search just that document, otherwise, it will search all loaded documents.",
                "enabled": True,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Searches the loaded documents for a query.",
                    additional_instructions="Searches the loaded files (or the specified file when target_file_id is set) for the given query. The target_file_id argument is optional, and can be used to search a specific file if the user has specified one. IMPORTANT: If the user has not asked you to look in a specific file, don't use target_file_id.",
                    function=self.document_tool.search_loaded_documents,
                ),
            },
            {
                "name": "Summarize Topic (All Documents))",
                "about": "Searches through all documents for the specified topic, and summarizes the results. Don't forget to set the top_k!  If the file override is set, it will use that file.",
                "enabled": False,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Searches through all documents for the specified topic, and summarizes the results.",
                    additional_instructions="Useful for getting a very general summary of a topic across all of the loaded documents. Do not use this tool for specific document queries about topics, roles, or details. Instead, directly search the loaded documents for specific information related to the user's query. The target_file_id argument is required.",
                    function=self.document_tool.summarize_topic,
                    # return_direct=False,
                ),
            },
            {
                "name": "Summarize Whole Document (⚠️ Slow / Expensive)",
                "about": "Summarizes an entire document using one of the summarization methods.  This is slow and expensive, so use it sparingly.",
                "enabled": False,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Summarizes an entire document.",
                    additional_instructions="This tool should only be used for getting a very general summary of an entire document. Do not use this tool for specific queries about topics, roles, or details. Instead, directly search the loaded documents for specific information related to the user's query. The target_file_id argument is required.",
                    function=self.document_tool.summarize_entire_document,
                ),
            },
            {
                "name": "List Documents",
                "about": "Lists all loaded documents.",
                "enabled": False,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Lists all loaded documents.",
                    function=self.document_tool.list_documents,
                ),
            },
            {
                "name": "Code Details",
                "about": "Gets details about a specific part of a code file.",
                "enabled": True,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Gets details about a specific part of a code file.",
                    additional_instructions="Useful for getting the details of a specific signature (signature cannot be blank) in a specific loaded 'Code' file (required: target_file_id).",
                    function=self.code_tool.code_details,
                ),
            },
            {
                "name": "Code Structure",
                "about": "Gets the high-level structure of a code file.",
                "enabled": False,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Gets the high-level structure of a code file.",
                    additional_instructions="Useful for looking at the code structure of a single file. This tool only works when you specify a file. It will give you a list of module names, function signatures, and class method signatures in the specified file (represented by the 'target_file_id').",
                    function=self.code_tool.code_structure,
                ),
            },
            {
                "name": "Dependency Graph",
                "about": "Gets the dependency graph of a code file.",
                "enabled": True,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Gets the dependency graph of a code file.",
                    additional_instructions="Use this tool when a user is asking for the dependencies of any code file. This tool will return a dependency graph of the specified file (represented by the 'target_file_id').",
                    function=self.code_tool.get_pretty_dependency_graph,
                    return_direct=False,
                ),
            },
            {
                "name": "Create Stubs",
                "about": "Creates stubs for a specified code file.",
                "enabled": True,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Creates stubs for a specified code file.",
                    additional_instructions="Create mocks / stubs for the dependencies of a given code file. Use this when the user asks you to mock or stub out the dependencies for a given file.",
                    function=self.stubber_tool.create_stubs,
                    return_direct=False,
                ),
            },
            {
                "name": "Get All Code in File",
                "about": "Gets all of the code in the target file.",
                "enabled": True,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Gets all of the code in the target file.",
                    additional_instructions="Useful for getting all of the code in a specific file when the user asks you to show them code from a particular file.",
                    function=self.code_tool.get_all_code_in_file,
                    return_direct=False,
                ),
            },
            {
                "name": "Perform Code Review",
                "about": "Performs a code review of a specified code file.",
                "enabled": True,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Performs a code review of a specified code file.",
                    function=self.code_review_tool.conduct_code_review,
                    return_direct=False,
                ),
            },
            {
                "name": "Query Spreadsheet",
                "about": "Queries a specific spreadsheet.",
                "enabled": True,
                "is_document_related": True,
                "tool": GenericTool(
                    description="Queries a specific spreadsheet.",
                    additional_instructions="Useful for querying a specific spreadsheet.  If the target document is a 'Spreadsheet', always use this tool. Never use this tool on documents that are not classified as 'Spreadsheet'.",
                    function=self.spreadsheet_tool.query_spreadsheet,
                ),
            },
        ]

        return tools
