import logging
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel
from langchain.agents import AgentExecutor
from langchain.chains.llm import LLMChain
from langchain.memory.readonly import ReadOnlySharedMemory

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfiguration,
)
from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm
from src.ai.prompts.prompt_manager import PromptManager
from src.ai.system_info import get_system_information
from src.ai.agents.general.generic_tools_agent import GenericToolsAgent
from src.tools.documents.document_tool import DocumentTool
from src.ai.tools.tool_manager import ToolManager


class RetrievalAugmentedGenerationAI:
    """A RAG AI"""

    llm: BaseLanguageModel = None
    configuration: RetrievalAugmentedGenerationConfiguration
    mode: str = "Auto"

    def __init__(
        self,
        configuration: RetrievalAugmentedGenerationConfiguration,
        interaction_id: UUID,
        user_email: str,
        prompt_manager: PromptManager,
        streaming: bool = False,
        override_memory=None,
    ):
        self.configuration = configuration
        self.streaming = streaming
        self.prompt_manager = prompt_manager

        self.llm = get_llm(
            self.configuration.model_configuration,
            tags=["retrieval-augmented-generation-ai"],
            streaming=streaming,
        )

        # Set up the interaction manager
        self.interaction_manager = InteractionManager(
            interaction_id=interaction_id,
            user_email=user_email,
            llm=self.llm,
            prompt_manager=self.prompt_manager,
            max_token_limit=self.configuration.model_configuration.max_conversation_history_tokens,
            override_memory=override_memory,
        )

        memory = ReadOnlySharedMemory(
            memory=self.interaction_manager.conversation_token_buffer_memory
        )

        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt_manager.get_prompt(
                "conversational", "CONVERSATIONAL_PROMPT"
            ),
            memory=memory,
        )

        # The tool manager contains all of the tools available to the AI
        self.tool_manager = ToolManager()
        self.tool_manager.initialize_tools(
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
            self.prompt_manager.get_prompt(
                "summary",
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
        llm_callbacks: List = [],
        kwargs: dict = {},
    ):
        # Set the document collection id on the interaction manager
        self.interaction_manager.collection_id = collection_id

        # Set the kwargs on the interaction manager (this is search params, etc.)
        self.interaction_manager.tool_kwargs = kwargs

        # Ensure we have a summary / title for the chat
        logging.debug("Checking to see if summary exists for this chat")
        self.check_summary(query=query)

        if self.mode == "Conversation":
            logging.debug("Running chain 'Conversation Only' mode")
            results = self.run_chain(
                query=query, llm_callbacks=llm_callbacks, kwargs=kwargs
            )
        else:
            # Run the agent
            logging.debug("Running agent 'Auto' mode")
            results = self.run_agent(
                query=query, agent_callbacks=agent_callbacks, kwargs=kwargs
            )

        # Adding this after the run so that the agent can't see it in the history
        self.interaction_manager.conversation_token_buffer_memory.save_context(
            inputs={"input": query}, outputs={"output": results}
        )
        logging.debug(results)

        logging.debug("Added results to chat memory")

        return results

    def run_chain(self, query: str, llm_callbacks: List = [], kwargs: dict = {}):
        return self.chain.run(
            system_prompt="You are a friendly AI who's purpose it is to engage a user in conversation.  Try to mirror their emotional state, and answer their questions.  If you don't know the answer, don't make anything up, just say you don't know.",
            input=query,
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            context="N/A",
            loaded_documents="\n".join(
                self.interaction_manager.get_loaded_documents_for_display()
            ),
            callbacks=llm_callbacks,
        )

    def run_agent(self, query: str, agent_callbacks: List = [], kwargs: dict = {}):
        timeout = kwargs.get("agent_timeout", 300)
        logging.debug(f"Creating agent with {timeout} second timeout")
        agent = self.create_agent(agent_timeout=timeout)

        # Run the agent
        logging.debug("Running agent")
        return agent.run(
            input=query,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            callbacks=agent_callbacks,
        )

    def check_summary(self, query):
        if self.interaction_manager.interaction_needs_summary:
            logging.debug("Interaction needs summary, generating one now")
            interaction_summary = self.llm.predict(
                self.prompt_manager.get_prompt(
                    "summary",
                    "SUMMARIZE_FOR_LABEL_TEMPLATE",
                ).format(query=query)
            )
            self.interaction_manager.set_interaction_summary(interaction_summary)
            self.interaction_manager.interaction_needs_summary = False
            logging.debug(f"Generated summary: {interaction_summary}")

    def set_mode(self, mode: str):
        if mode.lower().startswith("conversation"):
            # Use the LLM with a chat prompt
            self.mode = "Conversation"
        else:
            # Normal mode, let the AI decide what to do (agent)
            self.mode = "Auto"
