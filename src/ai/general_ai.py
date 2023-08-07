from typing import Union, List
import logging
from datetime import datetime

from db.database.models import User, Conversation
from db.models.users import Users
from db.models.conversations import Conversations, SearchType
from configuration.ai_configuration import AIConfiguration
from ai.abstract_ai import AbstractAI
from llms.abstract_llm import AbstractLLM
from llms.llm_result import LLMResult
from utilities.instance_utility import create_instance_from_module_and_class
from ai.conversation.conversation_manager import ConversationManager, MessageRole


class GeneralAI(AbstractAI):
    def __init__(self, ai_configuration: AIConfiguration):
        self.ai_configuration = ai_configuration

        # Initialize the AbstractLLM and dependent AIs
        self.configure()

        self.users = Users(self.ai_configuration.db_env_location)
        self.conversations = Conversations(self.ai_configuration.db_env_location)

        # This creates a new conversation with a unique interaction ID
        # There can be multiple participants in a conversation
        self.conversation_manager = ConversationManager(
            ai_configuration.db_env_location,
            self.ai_configuration.system_prompts,
            self.ai_configuration.store_conversation_history,
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

        # Get the user information
        with self.users.session_context(self.users.Session()) as session:
            current_user = self.users.get_user(
                session, user_id, eager_load=[User.user_settings]
            )

            settings = ", ".join(
                [
                    f"{s.setting_name}={s.setting_value}"
                    for s in current_user.user_settings
                ]
            )
            user_information = f"My user information:  Name: {current_user.name}. Email: {current_user.email}. Location: {current_user.location}. Age: {current_user.age}. User Settings: {settings}"

            self.user_name = current_user.name
            self.user_email = current_user.email
            self.user_id = current_user.id

            # Find any related conversations to this query
            # related_conversations: List[
            #     Conversation
            # ] = self.conversations.search_conversations(
            #     session,
            #     conversation_text_search_query=query,
            #     associated_user=current_user,
            #     search_type=SearchType.similarity,
            #     top_k=5,  # TODO: Make this configurable
            #     eager_load=[Conversation.conversation_role_type],
            # )

            # messages_with_roles: List[str] = []
            # for c in related_conversations:
            #     messages_with_roles.append(
            #         [
            #             {
            #                 "role": c.conversation_role_type.role_type,
            #                 "content": c.conversation_text,
            #             }
            #             for c in related_conversations
            #         ]
            #     )

            # Add the message to the conversation
            #self.conversation_manager.add_message(user_id, query)

        try:
            system_information = f"Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}. Time Zone: {datetime.now().astimezone().tzinfo}"

            # This will include the system prompts and system info, however they won't go into the history
            # Create a string with the system information (e.g. date/time, time zone, etc.)
            # messages = self.conversation_manager.get_messages(
            #     system_information, user_information#, related_conversations
            # )

            # Send it!
            response: LLMResult = self.llm.query(query, user_id=self.user_id, user_name=self.user_name, user_email=self.user_email, system_information=system_information)

            logging.debug(f"Response from LLM: {response.result_string}")

            # Add the messages to the conversation- don't do this before we have a successful response
            # if self.ai_configuration.store_conversation_history:
            #     self.conversation_manager.store_message(user_id, query, MessageRole.USER)
            #     self.conversation_manager.store_message(user_id, response.result_string, MessageRole.ASSISTANT)

            # General AI returns a string
            return response.result_string
        except Exception as e:
            logging.exception(e)
            return "Sorry, I'm not feeling well right now. Please try again later."