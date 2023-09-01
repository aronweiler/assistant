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

from ai.prompts import MEMORY_PROMPT


class MemoryAI(DestinationBase):
    """A conversational AI that uses an LLM to generate responses"""

    def __init__(
        self, destination: Destination, interaction_manager: InteractionManager
    ):
        self.destination = destination
        self.interaction_manager = interaction_manager

        self.llm = get_llm(destination.model_configuration)

        self.chain = LLMChain(
            llm=self.llm,
            prompt=MEMORY_PROMPT,
            memory=self.interaction_manager.conversation_token_buffer_memory,
        )

    def run(self, input: str):
        """Runs the memory AI with the given input"""
        
        # Look up some stuff based on the query
        # Looking into the conversations table for now

        with self.interaction_manager.conversations_helper.session_context(
            self.interaction_manager.conversations_helper.Session()
        ) as session:

            previous_conversations = self.interaction_manager.conversations_helper.search_conversations_with_user_id(
                session,
                conversation_text_search_query=input,
                search_type=SearchType.similarity,
                top_k=100,
                associated_user_id=self.interaction_manager.user_id,
            )

            # De-dupe the conversations
            previous_conversations = list(
                set([pc.conversation_text for pc in previous_conversations])
            )

            return self.chain.run(input=input, context="\n".join(previous_conversations)) 