import logging
from uuid import UUID
from typing import List

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.prompts import PromptTemplate

from src.configuration.assistant_configuration import Destination

from src.db.models.conversations import SearchType
from src.db.models.domain.conversation_role_type import ConversationRoleType

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm, get_prompt
from src.ai.system_info import get_system_information
from src.ai.destination_route import DestinationRoute
from src.ai.system_info import get_system_information
from src.ai.destinations.destination_base import DestinationBase
from src.ai.callbacks.token_management_callback import TokenManagementCallbackHandler


class ConversationalAI(DestinationBase):
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
            tags=["conversational"],
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
                self.destination.model_configuration.llm_type, "CONVERSATIONAL_PROMPT"
            ),
            memory=self.interaction_manager.conversation_token_buffer_memory,
        )

    def run(
        self,
        input: str,
        collection_id: str = None,
        llm_callbacks: list = [],
        agent_callbacks: list = [],
    ):
        """Runs the conversational AI with the given input"""
        self.interaction_manager.collection_id = collection_id
        return self.chain.run(
            system_prompt=self.destination.system_prompt,
            input=input,
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            context=self._get_related_context(input),
            loaded_documents="\n".join(
                self.interaction_manager.get_loaded_documents_for_display()
            ),
            callbacks=llm_callbacks,
        )

    def _get_related_context(self, query):
        """Gets the related context for the query"""
        related_context = self.interaction_manager.conversations_helper.search_conversations_with_user_id(
            search_query=query,
            associated_user_id=self.interaction_manager.user_id,
            search_type=SearchType.similarity,
            top_k=10,
        )

        # De-dupe the conversations
        related_context = list(
            set(
                [
                    f"{'AI' if m.conversation_role_type == ConversationRoleType.ASSISTANT else f'{self.interaction_manager.user_name} ({self.interaction_manager.user_email})'}: {m.conversation_text}"
                    for m in related_context
                ]
            )
        )

        related_context = "\n".join(related_context)

        return related_context
