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

            # Find any related conversations to this query
            related_conversations: List[
                Conversation
            ] = self.conversations.search_conversations(
                session,
                conversation_text_search_query=query,
                associated_user=current_user,
                search_type=SearchType.similarity,
                top_k=5,  # TODO: Make this configurable
                eager_load=[Conversation.conversation_role_type],
            )

            messages_with_roles: List[str] = []
            for c in related_conversations:
                messages_with_roles.append(
                    [
                        {
                            "role": c.conversation_role_type.role_type,
                            "content": c.conversation_text,
                        }
                        for c in related_conversations
                    ]
                )

            # Add the message to the conversation
            self.conversation_manager.add_message(user_id, query)

        try:
            system_information = f"Date/Time: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}. Time Zone: {datetime.now().astimezone().tzinfo}"

            # This will include the system prompts and system info, however they won't go into the history
            # Create a string with the system information (e.g. date/time, time zone, etc.)
            messages = self.conversation_manager.get_messages(
                system_information, user_information, related_conversations
            )

            # rephrased_message = self.conversation_manager.create_message(self.rephrase_prompt(messages), MessageRole.USER)
            # rephrased_messages = self.conversation_manager.get_system_prompts(system_information) + [rephrased_message]

            # Send it!
            response: LLMResult = self.llm.query(messages, True)

            # if response.is_tool_result:
            #     response = self.handle_tool_call(response)

            logging.debug(f"Response from LLM: {response}")

            # Add the messages to the conversation- don't do this before we have a successful response
            if self.ai_configuration.store_conversation_history:
                self.conversation_manager.add_message(user_id, query, MessageRole.USER)
                self.conversation_manager.add_message(user_id, response.result_string, MessageRole.ASSISTANT)

            # General AI returns a string
            return response.result_string
        except Exception as e:
            logging.exception(e)
            return "Sorry, I'm not feeling well right now. Please try again later."

    def rephrase_prompt(self, messages) -> str:
        logging.debug("Rephrasing messages to stand-alone query")
        # Rephrase the messages to be a stand-alone query
        summary = ""
        for message in messages:
            summary += message["content"]

        last_query = messages[-1]["content"]

        rephrase_prompts = [
            self.conversation_manager.create_message(summary, MessageRole.USER),
            self.conversation_manager.create_message(
                "Please summarize and rephrase the preceding messages to be a stand-alone query from the user's perspective.",
                MessageRole.USER,
            ),
            self.conversation_manager.create_message(
                "Keep the final user's query intact, and make sure you include all prior information that is relevant to the user's query.",
                MessageRole.USER,
            ),
            self.conversation_manager.create_message(last_query, MessageRole.USER),
            self.conversation_manager.create_message(
                "Sure, here is the stand-alone query including all relevant information from the previous conversation, phrased as coming directly from the user:",
                MessageRole.ASSISTANT,
            ),
        ]

        rephrased_message = self.llm.query(rephrase_prompts, False)

        return rephrased_message.result_string

    # def handle_tool_call(tool_call:LLMResult):
    #     """Handle a tool call

    #     Args:
    #         tool_call (LLMResult): Parameters for the tool call in JSON
    #     """
    #     logging.debug(f"Handling tool call: {tool_call}")

    # def evaluate_for_tool_use(self, query: str) -> LLMResult:
    #     """Evaluate the query for tool use

    #     Args:
    #         query (str): Query to evaluate
    #     """

    #     response = self.llm.query([self.conversation_manager.create_message(query)], True)

    #     # If the response contains a tool recommendation, then we need to evaluate it
    #     return response
