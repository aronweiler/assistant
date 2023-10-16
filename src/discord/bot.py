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
from src.utilities.token_helper import num_tokens_from_string

from src.configuration.assistant_configuration import (
    RetrievalAugmentedGenerationConfigurationLoader,
)
from src.ai.rag_ai import RetrievalAugmentedGenerationAI


class JarvisBot(discord.Client):
    memory_map: dict = {}
    
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
            please_wait = await self.llm.apredict(f"The user has asked a question: '{message.content}'.  Please give me a one sentence answer that tells the user to please wait while I look into this.\n\nAI:")
            await message.channel.send(please_wait)
            response: str = self.ai.query(query=message.content, collection_id=4)
        elif message.channel.name.lower() == "general":
            response = await self.have_conversation(message, "DISCORD_TEMPLATE")
        elif message.channel.name.lower() == "smack-talk":
            response = await self.have_conversation(message, "SMACK_TALK_TEMPLATE")

        if response != "":
            if not response.lower().startswith("no response necessary"):
                memory = await self.get_conversation_memory(message)
                
                if memory is not None:
                    memory.chat_memory.add_ai_message(response)

                await message.channel.send(response)
            else:
                logging.info("No response necessary")

    async def get_conversation_memory(self, message):
        memory = self.memory_map.get(message.channel.name.lower())
        if memory is None:
            memory = ConversationTokenBufferMemory(
                llm=self.llm,
                human_prefix="User",
                ai_prefix="Jarvis",
                memory_key="chat_history",
                input_key="input",
                max_token_limit=1000,
            )
            
            async for msg in message.channel.history(limit=None):
                if msg.channel.name.lower() == message.channel.name.lower():
                    if msg.author.display_name.startswith("Jarvis"):
                        memory.chat_memory.add_ai_message(msg.content)
                    else:
                        memory.chat_memory.add_user_message(f"{msg.author.display_name}: {msg.content}")
                    #     memory.buffer_as_messages.append(f"{msg.author.display_name}: {msg.content}")
                    # messages.append(f"{msg.author.display_name}: {msg.content}")
            
            # pull the last message off the stack, because it's the message that triggered this
            memory.chat_memory.messages = memory.chat_memory.messages[1:]
            
            self.memory_map[message.channel.name.lower()] = memory

        return memory

    async def have_conversation(self, message, template="DISCORD_TEMPLATE"):
                
        memory = await self.get_conversation_memory(message)

        prompt = get_prompt(
            configuration.model_configuration.llm_type,
            template,
        )

        # Trim the messages by 1 to remove the current message        
        messages = []
        total = 0
        for m in memory.buffer_as_messages:
            total += num_tokens_from_string(f"{message.author.display_name}: {message.content}")
            if total < 1000:
                messages.append(m)
            
        #messages = memory.buffer_as_messages
        messages.reverse()
        messages = [f'{"" if m.type == "human" else "Jarvis:"} {m.content}' for m in messages]
        prompt = prompt.format(
            chat_history="\n".join([m.strip() for m in messages]),
            input=f"{message.author.display_name}: {message.content}",
        )
        
        memory.chat_memory.add_user_message(f"{message.author.display_name}: {message.content}")

        response = await self.llm.apredict(prompt)
        
        memory.chat_memory.add_ai_message(response)
        
        return response

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
