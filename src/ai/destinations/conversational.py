import logging
from uuid import UUID
from typing import List

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.prompts import PromptTemplate

from configuration.assistant_configuration import Destination

from db.models.conversations import SearchType

from ai.interactions.interaction_manager import InteractionManager
from ai.llm_helper import get_llm
from ai.system_info import get_system_information
from ai.destination_route import DestinationRoute
from ai.system_info import get_system_information
from ai.destinations.destination_base import DestinationBase

from ai.prompts import CONVERSATIONAL_PROMPT


class ConversationalAI(DestinationBase):
    """A conversational AI that uses an LLM to generate responses"""

    def __init__(
        self, destination: Destination, interaction_manager: InteractionManager
    ):
        self.destination = destination
        self.interaction_manager = interaction_manager

        self.llm = get_llm(destination.model_configuration)

        self.chain = LLMChain(
            llm=self.llm,
            prompt=CONVERSATIONAL_PROMPT,
            memory=self.interaction_manager.conversation_token_buffer_memory,
        )

    def run(self, input: str):
        """Runs the conversational AI with the given input"""
        return self.chain.run(
            system_prompt=self.destination.system_prompt,
            input=input,
            user_name=self.interaction_manager.user_name,
            user_email=self.interaction_manager.user_email,
            system_information=get_system_information(
                self.interaction_manager.user_location
            ),
            context=self._get_related_context(input),
            loaded_documents=self.interaction_manager.get_loaded_documents(),
        )

    def _get_related_context(self, query):
        """Gets the related context for the query"""

        with self.interaction_manager.conversations_helper.session_context(
            self.interaction_manager.conversations_helper.Session()
        ) as session:
            related_context = (
                self.interaction_manager.conversations_helper.search_conversations(
                    session, query, SearchType.similarity, top_k=20
                )
            )

            # De-dupe the conversations
            related_context = list(
                set(
                    [
                        f"{'AI' if m.conversation_role_type_id == 2 else f'{self.interaction_manager.user_name} ({self.interaction_manager.user_email})'}: {m.conversation_text}"
                        for m in related_context
                    ]
                )
            )

            related_context = "\n".join(related_context)

        return related_context
