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

from langchain.agents import initialize_agent, AgentType

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfiguration,
)

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information

from src.tools.documents.document_tool import DocumentTool
from src.tools.documents.spreadsheet_tool import SpreadsheetsTool
from src.tools.documents.code_tool import CodeTool

from src.ai.agents.code.stubbing_agent import Stubber


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
            "output_parser": output_parser,  # (output_fixing_parser=CustomOutputFixingParser()),
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
            loaded_documents="\n".join(
                self.interaction_manager.get_loaded_documents_for_reference()
            ),
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

        tools = [
            {
                "name": "Search Documents",
                "about": "Searches the loaded documents for a query. If the query is directed at a specific document, this will search just that document, otherwise, it will search all loaded documents.",
                "enabled": True,
                "is_document_related": True,
                "tool": StructuredTool.from_function(
                    func=self.document_tool.search_loaded_documents,
                    #return_direct=True,
                ),
            },
            {
                "name": "Summarize Topic (All Documents))",
                "about": "Searches through all documents for the specified topic, and summarizes the results. Don't forget to set the top_k!  If the file override is set, it will use that file.",
                "enabled": True,
                "is_document_related": True,
                "tool": StructuredTool.from_function(
                    func=self.document_tool.summarize_topic,
                    #return_direct=True,
                ),
            },
            {
                "name": "Summarize Whole Document (⚠️ Slow / Expensive)",
                "about": "Summarizes an entire document using one of the summarization methods.  This is slow and expensive, so use it sparingly.",
                "enabled": False,
                "is_document_related": True,
                "tool": StructuredTool.from_function(
                    func=self.document_tool.summarize_entire_document,
                    return_direct=True,
                ),
            },
            {
                "name": "List Documents",
                "about": "Lists all loaded documents.",
                "enabled": True,
                "is_document_related": False,
                "tool": StructuredTool.from_function(
                    func=self.document_tool.list_documents
                ),
            },
            {
                "name": "Code Details",
                "about": "Gets details about a specific part of a code file.",
                "enabled": True,
                "is_document_related": True,
                "tool": StructuredTool.from_function(func=self.code_tool.code_details),
            },
            {
                "name": "Code Structure",
                "about": "Gets the structure of a code file.",
                "enabled": True,
                "is_document_related": True,
                "tool": StructuredTool.from_function(
                    func=self.code_tool.code_structure
                ),
            },
            {
                "name": "Dependency Graph",
                "about": "Gets the dependency graph of a code file.",
                "enabled": True,
                "is_document_related": True,
                "tool": StructuredTool.from_function(
                    func=self.code_tool.get_pretty_dependency_graph,
                    return_direct=True,
                ),
            },
            {
                "name": "Create Stubs",
                "about": "Creates stubs for a specified code file.",
                "enabled": True,
                "is_document_related": True,
                "tool": StructuredTool.from_function(
                    func=self.stubber_tool.create_stubs,
                    return_direct=True,
                ),
            },
            {
                "name": "Query Spreadsheet",
                "about": "Queries a specific spreadsheet.",
                "enabled": True,
                "is_document_related": True,
                "tool": StructuredTool.from_function(
                    func=self.spreadsheet_tool.query_spreadsheet
                ),
            },
        ]

        return tools
