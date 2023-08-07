from typing import Union, List
import logging
from datetime import datetime

from configuration.ai_configuration import AIConfiguration
from ai.abstract_ai import AbstractAI
from llms.abstract_llm import AbstractLLM
from utilities.instance_utility import create_instance_from_module_and_class
from ai.conversation.conversation_manager import ConversationManager, MessageRole


class ToolUsingAI(AbstractAI):
    def __init__(self, ai_configuration: AIConfiguration):
        self.ai_configuration = ai_configuration

        # Initialize the AbstractLLM and dependent AIs
        self.configure()

        # This creates a new conversation with a unique interaction ID
        # There can be multiple participants in a conversation
        self.conversation_manager = ConversationManager(
            ai_configuration.db_env_location, self.ai_configuration.system_prompts
        )

    def query(self, query, user_id):
        """Query the AI

        Args:
            query (str): Query for the AI
            user_id (int): ID of the user making the query

        Returns:
            str: Result of the query
        """

        self.llm: AbstractLLM

        if self.ai_configuration.store_conversation_history:
            # Add the message to the conversation
            self.conversation_manager.add_message(user_id, query)

        try:
            # This will include the system prompts and system info, however they won't go into the history
            # Create a string with the system information (e.g. date/time, time zone, etc.)
            system_information = f"Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}. Time Zone: {datetime.now().astimezone().tzinfo}"
            messages = self.conversation_manager.get_messages(system_information)

            # Send it!
            response = self.llm.query(messages)

            logging.debug(f"xxxxResponse from LLM: {response}")

            # Add the response to the conversation
            if self.ai_configuration.store_conversation_history:
                self.conversation_manager.add_message(
                    user_id, response.result_string, MessageRole.ASSISTANT
                )

            # General AI returns a string
            return response.result_string
        except Exception as e:
            logging.exception(e)
            return "Sorry, I'm not feeling well right now. Please try again later."
