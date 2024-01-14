import os
import discord
import logging
import threading

# include the root directory in the path so we can import the configuration
import sys

from langchain.base_language import BaseLanguageModel
from langchain.schema import AIMessage, HumanMessage

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.utilities.token_helper import num_tokens_from_string

from src.ai.prompts.prompt_manager import PromptManager
from src.discord.memory_manager import get_conversation_memory


class ConversationalBot(discord.Client):
    def __init__(
        self,
        configuration,
        llm: BaseLanguageModel,
        target_channel_name: str,
        prompt_manager: PromptManager,
        conversation_template: str = "DISCORD_TEMPLATE",
        status: str = "the good little chatbot",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level=logging.DEBUG)
        self.llm = llm
        self.configuration = configuration
        self.conversation_template = conversation_template
        self.target_channel_name = target_channel_name
        self.prompt_manager = prompt_manager
        self.status = status

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

    async def have_conversation(self, message, template):
        memory = await get_conversation_memory(self.llm, message)

        prompt = self.prompt_manager.get_prompt(
            "discord_llm_prompts",
            template,
        )

        messages = [
            f'{"" if m.type == "human" else "Jarvis:"} {m.content}' for m in memory.buffer_as_messages
        ]
        prompt = prompt.format(
            chat_history="\n".join([m.strip() for m in messages]),
            input=f"{message.author.display_name}: {message.content}",
        )

        response = await self.llm.apredict(prompt)
        
        memory.save_context(inputs={"input": f"{message.author.display_name}: {message.content}"}, outputs={"output": response})

        if (
            response.lower().startswith("no response necessary")
            or response.strip() == ""
        ):
            logging.info("No response necessary")
        else:            
            await message.channel.send(response)
