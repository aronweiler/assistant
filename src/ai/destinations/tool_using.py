import logging
import json

from langchain.tools import StructuredTool

from langchain.agents.structured_chat.output_parser import (
    StructuredChatOutputParserWithRetries,
)

from langchain.agents import initialize_agent, AgentType

from src.configuration.assistant_configuration import Destination

from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_llm
from src.ai.system_info import get_system_information
from src.ai.system_info import get_system_information
from src.ai.destinations.destination_base import DestinationBase
from src.ai.callbacks.token_management_callback import TokenManagementCallbackHandler
from src.ai.callbacks.agent_callback import AgentCallback

from src.ai.rag_ai import RetrievalAugmentedGenerationAI

from src.tools.documents.document_tool import DocumentTool


class ToolUsingAI(DestinationBase):
    """A document-using AI that uses an LLM to generate responses"""

    def __init__(
        self,
        destination: Destination,
        interaction_id: int,
        user_email: str,
        streaming: bool = False,
    ):
        self.destination = destination

        self.rag_ai = RetrievalAugmentedGenerationAI(
            configuration=destination,
            streaming=streaming,
            interaction_id=interaction_id,
            user_email=user_email,
        )

    def run(
        self,
        input: str,
        collection_id: str = None,
        llm_callbacks: list = [],
        agent_callbacks: list = [],
        kwargs: dict = {},
    ):
        return self.rag_ai.query(
            query=input,
            collection_id=collection_id,
            agent_callbacks=agent_callbacks,
            kwargs=kwargs,
        )
