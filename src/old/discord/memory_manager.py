import os
import discord
import logging
import threading

# include the root directory in the path so we can import the configuration
import sys

from langchain.base_language import BaseLanguageModel
from langchain.schema import AIMessage, HumanMessage
from langchain.memory.token_buffer import ConversationTokenBufferMemory
from langchain.memory.chat_memory import ChatMessageHistory

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.shared.utilities.token_helper import num_tokens_from_string

from src.shared.ai.prompts.prompt_manager import PromptManager

memory_map: dict = {}
lock = threading.Lock()


async def get_conversation_memory(llm, message):
    conversation_token_buffer_memory = memory_map.get(message.channel.name.lower())
    if conversation_token_buffer_memory is None:
        # Create the token buffer memory
        conversation_token_buffer_memory = ConversationTokenBufferMemory(
            llm=llm,
            memory_key="chat_history",
            input_key="input",
            max_token_limit=2000,
        )

        lock.acquire()  # Acquire the lock before accessing the shared resource
        try:
            total_token_count = 0
            async for msg in message.channel.history(limit=None):
                # Double-check the channel name, but shouldn't matter
                if msg.channel.name.lower() == message.channel.name.lower():
                    # Update the total token count
                    total_token_count += num_tokens_from_string(msg.content)
                    if (
                        total_token_count
                        > conversation_token_buffer_memory.max_token_limit
                    ):
                        break

                    if msg.author.display_name.startswith("Jarvis"):
                        if msg.content.strip() != "":
                            conversation_token_buffer_memory.chat_memory.add_message(
                                AIMessage(content=msg.content)
                            )
                    else:
                        if msg.content.strip() != "":
                            conversation_token_buffer_memory.chat_memory.add_message(
                                HumanMessage(
                                    content=f"{msg.author.display_name}: {msg.content}"
                                )
                            )

            # Pull the last message off the stack, because it's the message that triggered this
            conversation_token_buffer_memory.chat_memory.messages.reverse()
            conversation_token_buffer_memory.chat_memory.messages = (
                conversation_token_buffer_memory.chat_memory.messages[:-1]
            )
            # Reverse the list so that the most recent message is last
            # memory.reverse()

            memory_map[message.channel.name.lower()] = conversation_token_buffer_memory
        finally:
            lock.release()

    return conversation_token_buffer_memory
