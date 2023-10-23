import logging
from uuid import UUID
from typing import List

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.prompts import PromptTemplate

from src.configuration.assistant_configuration import Destination

from src.db.models.conversations import SearchType

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm
from src.ai.system_info import get_system_information
from src.ai.destination_route import DestinationRoute
from src.ai.system_info import get_system_information
from src.ai.destinations.destination_base import DestinationBase
from src.ai.callbacks.token_management_callback import TokenManagementCallbackHandler


class MemoryAI(DestinationBase):
    """A conversational AI that uses an LLM to generate responses"""

    def __init__(
        self,
        destination: Destination,
        interaction_id: int,
        user_email: str,
        streaming: bool = False,
    ):
        self.destination = destination

        self.token_management_handler = TokenManagementCallbackHandler()

        self.llm = get_llm(
            destination.model_configuration,
            callbacks=[self.token_management_handler],
            tags=["memory"],
            streaming=streaming,
        )

        self.interaction_manager = InteractionManager(
            interaction_id,
            user_email,
            self.llm,
            destination.model_configuration.max_conversation_history_tokens,
        )

        self.chain = LLMChain(
            llm=self.llm,
            prompt=get_prompt(
                self.destination.model_configuration.llm_type, "MEMORY_PROMPT"
            ),
            memory=self.interaction_manager.conversation_token_buffer_memory,
        )

    def run(
        self,
        input: str,
        collection_id: str = None,
        llm_callbacks: list = [],
        agent_callbacks: list = [],
        kwargs: dict = {},
    ):
        """Runs the memory AI with the given input"""
        self.interaction_manager.collection_id = collection_id
        self.interaction_manager.tool_kwargs = kwargs

        with self.interaction_manager.conversations_helper.session_context(
            self.interaction_manager.conversations_helper.Session()
        ) as session:
            previous_conversations = self.interaction_manager.conversations_helper.search_conversations_with_user_id(
                session,
                conversation_text_search_query=input,
                search_type=SearchType.Similarity,
                top_k=100,
                associated_user_id=self.interaction_manager.user_id,
            )

            # De-dupe the conversations
            previous_conversations = list(
                set([pc.conversation_text for pc in previous_conversations])
            )

            return self.chain.run(
                input=input,
                context="\n".join(previous_conversations),
                callbacks=llm_callbacks,
            )
