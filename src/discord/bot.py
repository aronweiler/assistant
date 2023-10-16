import os
import discord
import logging
import threading

# include the root directory in the path so we can import the configuration
import sys

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.memory.token_buffer import ConversationTokenBufferMemory
from langchain.memory.readonly import ReadOnlySharedMemory
from langchain.schema import AIMessage, HumanMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.ai.llm_helper import get_llm, get_prompt
from src.utilities.token_helper import num_tokens_from_string

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfigurationLoader,
)
from src.ai.rag_ai import RetrievalAugmentedGenerationAI


class JarvisBot(discord.Client):
    memory_map: dict = {}
    lock = threading.Lock()

    def __init__(
        self,
        ai: RetrievalAugmentedGenerationAI = None,
        llm: BaseLanguageModel = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level=logging.DEBUG)
        self.ai = ai
        self.llm = llm

        if self.ai is not None:
            self.ai.set_mode("Auto")

    async def on_ready(self):
        logging.debug("Logged on as", self.user)

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        response: str = ""

        if message.channel.name.lower() == "support":
            please_wait = await self.llm.apredict(
                f"The user has asked a question: '{message.content}'.  Please give me a one sentence answer that tells the user to please wait while I look into this.\n\nAI:"
            )
            await message.channel.send(please_wait)
            response: str = self.ai.query(query=message.content, collection_id=4)
            await message.channel.send(response)
        elif message.channel.name.lower() == "general":
            await self.have_conversation(message, "DISCORD_TEMPLATE")
        elif message.channel.name.lower() == "smack-talk":
            await self.have_conversation(message, "SMACK_TALK_TEMPLATE")

    async def get_conversation_memory(self, message):
        memory = self.memory_map.get(message.channel.name.lower())
        if memory is None:
            self.lock.acquire()  # Acquire the lock before accessing the shared resource
            try:
                memory = []
                async for msg in message.channel.history(limit=None):
                    if msg.channel.name.lower() == message.channel.name.lower():
                        if msg.author.display_name.startswith("Jarvis"):
                            memory.append(AIMessage(content=msg.content))
                        else:
                            memory.append(
                                HumanMessage(
                                    content=f"{msg.author.display_name}: {msg.content}"
                                )
                            )

                # pull the last message off the stack, because it's the message that triggered this
                memory = memory[1:]
                memory.reverse()

                self.memory_map[message.channel.name.lower()] = memory
            finally:
                self.lock.release()

        return memory

    async def have_conversation(self, message, template="DISCORD_TEMPLATE"):
        memory = await self.get_conversation_memory(message)

        prompt = get_prompt(
            configuration.model_configuration.llm_type,
            template,
        )

        messages = []
        total = 0
        count = 0
        for m in reversed(memory):
            total += num_tokens_from_string(m.content)
            if total < 500:
                count += 1
            else:
                break

        messages = memory[-count:]

        messages = [
            f'{"" if m.type == "human" else "Jarvis:"} {m.content}' for m in messages
        ]
        prompt = prompt.format(
            chat_history="\n".join([m.strip() for m in messages]),
            input=f"{message.author.display_name}: {message.content}",
        )

        memory.append(
            HumanMessage(content=f"{message.author.display_name}: {message.content}")
        )

        response = await self.llm.apredict(prompt)

        if not response.lower().startswith("no response necessary"):
            memory.append(AIMessage(content=response))

            await message.channel.send(response)
        else:
            logging.info("No response necessary")


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


def get_the_llm(configuration):
    configuration.model_configuration.temperature = 1.0

    llm = get_llm(
        configuration.model_configuration,
        tags=["retrieval-augmented-generation-ai"],
        streaming=False,
        model_kwargs={
            "frequency_penalty": 1.0,
            "presence_penalty": 1.0,
        },
    )

    return llm


def set_tool_environment_variables():
    os.environ["search_loaded_documents"] = "True"
    os.environ["analyze_with_llm"] = "True"
    os.environ["summarize_search_topic"] = "True"

    os.environ["summarize_entire_document"] = "False"
    os.environ["list_documents"] = "False"
    os.environ["get_code_details"] = "False"
    os.environ["get_code_structure"] = "False"
    os.environ["get_pretty_dependency_graph"] = "False"
    os.environ["create_stubs"] = "False"
    os.environ["get_all_code_in_file"] = "False"
    os.environ["conduct_code_review_from_file_id"] = "False"
    os.environ["conduct_code_review_from_url"] = "False"
    os.environ["create_code_review_issue_tool"] = "False"
    os.environ["query_spreadsheet"] = "False"
    os.environ["get_weather"] = "False"
    os.environ["get_time"] = "False"
    os.environ["get_news_for_topic"] = "False"
    os.environ["get_top_news_headlines"] = "False"


if __name__ == "__main__":
    # Get the token from the environment
    discord_token = os.environ.get("DISCORD_BOT_TOKEN")
    discord_interaction_id = os.environ.get("DISCORD_INTERACTION_ID")
    discord_bot_email = os.environ.get("DISCORD_BOT_EMAIL")

    set_tool_environment_variables()

    configuration = load_configuration()
    ai = load_rag_ai(configuration, discord_interaction_id, discord_bot_email)
    # chain, memory = load_llm_chain(configuration)
    llm = get_the_llm(configuration)

    # Run it!
    intents = discord.Intents.default()
    intents.message_content = True
    client = JarvisBot(intents=intents, ai=ai, llm=llm)
    client.run(discord_token)
