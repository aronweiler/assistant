import logging
import json
from uuid import UUID
from typing import List

from langchain.base_language import BaseLanguageModel
from langchain.prompts import PromptTemplate
from langchain.chains.router.llm_router import LLMRouterChain, RouterOutputParser
from langchain.memory.readonly import ReadOnlySharedMemory

from langchain.tools import StructuredTool

from langchain.agents import (
    initialize_agent,
    AgentType
)

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
        callbacks: list = [],
        agent_timeout: int = 120,
    ):
        self.configuration = configuration        
        self.streaming = streaming
        self.callbacks = callbacks        

        self.llm = get_llm(
            self.configuration.model_configuration,
            callbacks=callbacks,
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

        tools = self.create_tools()

        self.agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            human_message_template=get_prompt(
                self.configuration.model_configuration.llm_type, "AGENT_TEMPLATE"
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
                    "agent_chat_history",
                    "agent_scratchpad",
                    "system_information",
                ],
            },
            max_execution_time=agent_timeout, 
            early_stopping_method="generate" # try to generate a response if it times out
        )

    def query(
        self,
        query: str,
        collection_id: int = None,
        kwargs: dict = {},
    ):
        """Routes the query to the appropriate AI, and returns the response."""

        # Set the document collection id on the interaction manager
        self.interaction_manager.collection_id = collection_id

        # Set the kwargs on the interaction manager (this is search params, etc.)
        self.interaction_manager.tool_kwargs = kwargs

        # Ensure we have a summary / title for the chat
        self.check_summary(query=query)
        
        # Run the agent        
        results = self.agent.run(
            input=input,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            agent_chat_history="\n".join(
                [
                    f"{'AI' if m.type == 'ai' else f'{self.interaction_manager.user_name} ({self.interaction_manager.user_email})'}: {m.content}"
                    for m in self.interaction_manager.conversation_token_buffer_memory.chat_memory.messages[
                        -4:
                    ]
                ]
            ),
            callbacks=self.callbacks            
        )

        # Adding this after the run so that the agent can't see it in the history
        self.interaction_manager.conversation_token_buffer_memory.chat_memory.add_user_message(
            input
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
        document_tool = DocumentTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )
        code_tool = CodeTool(
            configuration=self.configuration,
            interaction_manager=self.interaction_manager,
            llm=self.llm,
        )
        stubber_tool = Stubber(
            code_tool=code_tool,
            document_tool=document_tool,
            callbacks=self.callbacks,
            interaction_manager=self.interaction_manager,
        )

        tools = [
            StructuredTool.from_function(
                func=document_tool.search_loaded_documents,
                callbacks=self.callbacks
            ),            
            StructuredTool.from_function(
                func=document_tool.summarize_topic,
                callbacks=self.callbacks
            ),
            StructuredTool.from_function(
                func=document_tool.list_documents,
                callbacks=self.callbacks,
                return_direct=True,
            ),
            StructuredTool.from_function(
                func=code_tool.code_details, callbacks=self.callbacks
            ),
            StructuredTool.from_function(
                func=code_tool.code_structure, callbacks=self.callbacks
            ),
            StructuredTool.from_function(
                func=code_tool.create_stub_code, callbacks=self.callbacks, return_direct=True
            ),
            StructuredTool.from_function(
                func=code_tool.get_pretty_dependency_graph, callbacks=self.callbacks, return_direct=True
            ),
            StructuredTool.from_function(
                func=stubber_tool.create_stubs,
                callbacks=self.callbacks,
                return_direct=True,
            ),
        ]

        return tools