import os
import discord
import logging

# include the root directory in the path so we can import the configuration
import sys

from langchain.chains.llm import LLMChain
from langchain.memory.token_buffer import ConversationTokenBufferMemory

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.ai.llm_helper import get_llm, get_prompt

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfigurationLoader,
)
from src.ai.rag_ai import RetrievalAugmentedGenerationAI


class JarvisBot(discord.Client):
    def __init__(self, ai: RetrievalAugmentedGenerationAI=None, chain:LLMChain=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level=logging.DEBUG)
        self.ai = ai
        self.chain = chain
        
        if self.ai is not None:
            self.ai.set_mode("conversation")        

    async def on_ready(self):
        logging.debug("Logged on as", self.user)

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        # if message.content.lower().startswith("hey jarvis"):
        #response = ai.query(message.content)
        
        response = self.chain.run(input=f"{message.author.name}: {message.content}")

        await message.channel.send(response)


def load_configuration():
    """Loads the configuration from the path"""
    rag_config_path = os.environ.get(
        "RAG_CONFIG_PATH",
        "configurations/rag_configs/openai_rag.json",
    )

    return RetrievalAugmentedGenerationConfigurationLoader.from_file(rag_config_path)


def load_rag_ai(configuration, discord_interaction_id, discord_bot_email):
    """Loads the AI from the configuration"""
    return RetrievalAugmentedGenerationAI(
        configuration=configuration,
        interaction_id=discord_interaction_id,
        user_email=discord_bot_email,
        streaming=False,
    )


def load_llm_chain(configuration):
    llm = get_llm(
            configuration.model_configuration,
            tags=["retrieval-augmented-generation-ai"],
            streaming=False,
            
        )
    
    chain = LLMChain(
        llm=llm,
        prompt=get_prompt(
            configuration.model_configuration.llm_type, "DISCORD_PROMPT",
        
        ),
        memory = ConversationTokenBufferMemory(
            llm=llm,
            human_prefix="(Discord User)",
            memory_key="chat_history",
            input_key="input",
            max_token_limit=2000,
        ),
    )
    
    return chain


if __name__ == "__main__":
    # Get the token from the environment
    discord_token = os.environ.get("DISCORD_BOT_TOKEN")
    discord_interaction_id = os.environ.get("DISCORD_INTERACTION_ID")
    discord_bot_email = os.environ.get("DISCORD_BOT_EMAIL")

    configuration = load_configuration()
    #ai = load_ai(configuration, discord_interaction_id, discord_bot_email)
    chain = load_llm_chain(configuration)

    # Run it!
    intents = discord.Intents.default()
    intents.message_content = True
    client = JarvisBot(intents=intents, chain=chain)
    client.run(discord_token)
