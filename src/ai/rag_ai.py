import logging
import json
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser
from langchain.memory.readonly import ReadOnlySharedMemory

from langchain.tools import StructuredTool

from langchain.agents import initialize_agent, AgentType

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfiguration,
)

from src.ai.destinations.output_parser import (
    CustomStructuredChatOutputParserWithRetries,
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
        streaming: bool = False
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
        return [
            tool["tool"]
            for tool in self.tools
            if tool["enabled"]            
        ]
    
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
        agent = initialize_agent(
            tools=self.get_enabled_tools(),
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            human_message_template=get_prompt(
                self.configuration.model_configuration.llm_type, "AGENT_TEMPLATE"
            ),
            memory=ReadOnlySharedMemory(
                memory=self.interaction_manager.conversation_token_buffer_memory
            ),
            agent_kwargs={
                "suffix": get_prompt(
                    self.configuration.model_configuration.llm_type, "TOOLS_SUFFIX"
                ),
                "format_instructions": get_prompt(
                    self.configuration.model_configuration.llm_type,
                    "TOOLS_FORMAT_INSTRUCTIONS",
                ),
                "output_parser": CustomStructuredChatOutputParserWithRetries(),
                "input_variables": [
                    "input",
                    "loaded_documents",
                    "chat_history",
                    "agent_scratchpad",
                    "system_information",
                ],
            },
            max_execution_time=agent_timeout,
            early_stopping_method="generate",  # try to generate a response if it times out
        )

        return agent

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
        self.check_summary(query=query)

        self.spreadsheet_tool.callbacks = agent_callbacks

        agent = self.create_agent(kwargs.get('agent_timeout', 120))

        # Run the agent
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

        # Adding this after the run so that the agent can't see it in the history
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_user_message(
            query
        )

        logging.debug(results)
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_ai_message(
            results
        )

        return results

    def check_summary(self, query):
        if self.interaction_manager.interaction_needs_summary:
            interaction_summary = self.llm.predict(
                get_prompt(
                    self.configuration.model_configuration.llm_type,
                    "SUMMARIZE_FOR_LABEL_TEMPLATE",
                ).format(query=query)
            )
            self.interaction_manager.set_interaction_summary(interaction_summary)
            self.interaction_manager.interaction_needs_summary = False

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
            llm=self.llm
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
                "tool": StructuredTool.from_function(
                    func=self.document_tool.search_loaded_documents
                ),
            },
            {
                "name": "Summarize Topic (All Documents))",
                "about": "Searches through all documents for the specified topic, and summarizes the results. Don't forget to set the top_k!  If the file override is set, it will use that file.",
                "enabled": True,
                "tool": StructuredTool.from_function(
                    func=self.document_tool.summarize_topic
                ),
            },
            {
                "name": "Summarize Whole Document (⚠️ Slow / Expensive)",
                "about": "Summarizes an entire document using one of the summarization methods.  This is slow and expensive, so use it sparingly.",
                "enabled": False,
                "tool": StructuredTool.from_function(
                    func=self.document_tool.summarize_entire_document
                ),
            },
            {
                "name": "List Documents",
                "about": "Lists all loaded documents.",
                "enabled": True,
                "tool": StructuredTool.from_function(func=self.document_tool.list_documents),
            },
            {
                "name": "Code Details",
                "about": "Gets details about a specific part of a code file.",
                "enabled": True,
                "tool": StructuredTool.from_function(func=self.code_tool.code_details),
            },
            {
                "name": "Code Structure",
                "about": "Gets the structure of a code file.",
                "enabled": True,
                "tool": StructuredTool.from_function(func=self.code_tool.code_structure),
            },
            {
                "name": "Dependency Graph",
                "about": "Gets the dependency graph of a code file.",
                "enabled": True,
                "tool": StructuredTool.from_function(
                    func=self.code_tool.get_pretty_dependency_graph,
                    return_direct=True,
                ),
            },
            {
                "name": "Create Stubs",
                "about": "Creates stubs for a specified code file.",
                "enabled": True,
                "tool": StructuredTool.from_function(
                    func=self.stubber_tool.create_stubs,
                    return_direct=True,
                ),
            },
            {
                "name": "Query Spreadsheet",
                "about": "Queries a specific spreadsheet.",
                "enabled": True,
                "tool": StructuredTool.from_function(
                    func=self.spreadsheet_tool.query_spreadsheet
                ),
            },
        ]

        return tools
