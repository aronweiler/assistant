import os
import discord
import logging

# include the root directory in the path so we can import the configuration
import sys

from langchain.chains.llm import LLMChain
from langchain.base_language import BaseLanguageModel
from langchain.memory.token_buffer import ConversationTokenBufferMemory
from langchain.memory.readonly import ReadOnlySharedMemory

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.ai.llm_helper import get_llm, get_prompt

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfigurationLoader,
)
from src.ai.rag_ai import RetrievalAugmentedGenerationAI


class JarvisBot(discord.Client):
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

        # memory = ConversationTokenBufferMemory(
        #     llm=self.chain.llm,
        #     human_prefix="(Discord User)",
        #     ai_prefix="Jarvis",
        #     memory_key="chat_history",
        #     input_key="input",
        #     max_token_limit=2000,
        # )

        # chain.memory = ReadOnlySharedMemory(memory=memory)

        response: str = ""

        if message.channel.name.lower() == "support":
            please_wait = self.llm.predict(f"The user has asked a question: '{message.content}'.  Please give me a one sentence answer that tells the user to please wait while I look into this.\n\nAI:")
            await message.channel.send(please_wait)
            response: str = self.ai.query(query=message.content, collection_id=4)
        elif message.channel.name.lower() == "general":
            self.have_conversation(message)

        if response != "":
            if not response.lower().startswith("no response necessary"):
                # if self.memory is not None:
                #     self.memory.chat_memory.add_ai_message(response)

                await message.channel.send(response)
            else:
                logging.debug("No response necessary")
                # Still add the message to the chat history for reference

                # if self.chain is not None and self.memory is not None:
                #     self.memory.chat_memory.add_user_message(
                #         f"{message.author.display_name}: {message.content}"
                #     )


    async def have_conversation(self, message):
        messages = []
        async for msg in message.channel.history(limit=None):
            if msg.channel.name.lower() == message.channel.name.lower():                    
                messages.append(f"{msg.author.display_name}: {msg.content}")

        prompt = get_prompt(
            configuration.model_configuration.llm_type,
            "DISCORD_TEMPLATE",
        )

        # Trim the messages by 1 to remove the current message
        messages = messages[:-1]
        messages.reverse()
        prompt = prompt.format(
            chat_history="\n".join(messages),
            input=f"{message.author.display_name}: {message.content}",
        )

        response: str = self.llm.predict(prompt)

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
    llm = get_llm(
        configuration.model_configuration,
        tags=["retrieval-augmented-generation-ai"],
        streaming=False,
    )

    return llm


# def load_llm_chain(llm, configuration):
#     chain = LLMChain(
#         llm=llm,
#         prompt=get_prompt(
#             configuration.model_configuration.llm_type,
#             "DISCORD_PROMPT",
#         ),
#     )

#     return chain, memory


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
