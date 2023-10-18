import os
import discord
import logging
import threading

# include the root directory in the path so we can import the configuration
import sys

from langchain.base_language import BaseLanguageModel
from langchain.schema import AIMessage, HumanMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.ai.llm_helper import get_prompt
from src.utilities.token_helper import num_tokens_from_string

from src.ai.rag_ai import RetrievalAugmentedGenerationAI
from src.configuration.assistant_configuration import AssistantConfiguration


class RagBot(discord.Client):
    memory_map: dict = {}
    lock = threading.Lock()

    def __init__(
        self,
        configuration: AssistantConfiguration,
        ai: RetrievalAugmentedGenerationAI,
        target_channel_name: str,
        target_collection_id: int,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level=logging.DEBUG)
        self.ai = ai
        self.configuration = configuration
        self.target_channel_name = target_channel_name
        self.target_collection_id = (
            target_collection_id if target_collection_id is not None else -1
        )

        # Set RAG mode
        if self.ai is not None:
            self.ai.set_mode("Auto")

    async def on_ready(self):
        logging.debug("Logged on as", self.user)

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        response: str = ""

        if message.channel.name.lower() == self.target_channel_name.lower():
            # Add typing indicator
            response: str = self.ai.query(
                query=message.content, collection_id=self.target_collection_id
            )
            await message.channel.send(response)
