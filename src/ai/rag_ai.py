import logging
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel
from langchain.agents import AgentExecutor

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfiguration,
)
from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information
from src.ai.agents.general.generic_tools_agent import GenericToolsAgent
from src.tools.documents.document_tool import DocumentTool
from src.ai.tools.tool_manager import ToolManager


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

        self.tool_manager = ToolManager(
            self.configuration, self.interaction_manager, self.llm
        )

    def create_agent(self, agent_timeout: int = 300):
        tools = self.tool_manager.get_enabled_tools()

        agent = GenericToolsAgent(
            tools=tools,
            model_configuration=self.configuration.model_configuration,
            interaction_manager=self.interaction_manager,
        )

        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=[t.structured_tool for t in tools],
            verbose=True,
            max_execution_time=agent_timeout,  # early_stopping_method="generate" <- this is not supported, but somehow in their docs
        )

        return agent_executor

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
        document_tool = DocumentTool(
            self.configuration, self.interaction_manager, self.llm
        )
        document_summary = document_tool.summarize_entire_document(file_id)

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

        timeout = kwargs.get("agent_timeout", 300)
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
