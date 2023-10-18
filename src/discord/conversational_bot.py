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


class ConversationalBot(discord.Client):
    memory_map: dict = {}
    lock = threading.Lock()

    def __init__(
        self,
        configuration: AssistantConfiguration,
        llm: BaseLanguageModel,
        target_channel_name: str,
        conversation_template: str = "DISCORD_TEMPLATE",
        status: str = "Chatting",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level=logging.DEBUG)
        self.llm = llm
        self.configuration = configuration
        self.conversation_template = conversation_template
        self.target_channel_name = target_channel_name

    async def on_ready(self):
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name=self.status
            )
        )

        logging.debug(f"Connected as: {self.user.name}")
        logging.debug(f"Bot ID: {self.user.id}")

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        if message.channel.name.lower() == self.target_channel_name.lower():
            async with message.channel.typing():
                await self.have_conversation(message, self.conversation_template)

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

    async def have_conversation(self, message, template):
        memory = await self.get_conversation_memory(message)

        prompt = get_prompt(
            self.configuration.model_configuration.llm_type,
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

        if response.lower().startswith("no response necessary") or response.strip() == "":
            logging.info("No response necessary")            
        else:
            memory.append(AIMessage(content=response))
            await message.channel.send(response)
            
