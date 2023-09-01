import os
import sys
import logging
import json
from typing import Union, List
from uuid import UUID

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from tools.conversation.conversation_tool_configuration import ConversationToolConfiguration
from db.models.conversations import Conversations
from db.models.users import Users
from db.models.vector_database import SearchType
from db.database.models import Conversation


class ConversationTool:
    def __init__(self, json_args):
        self.configuration = ConversationToolConfiguration(json_args)
        self.conversations = Conversations(self.configuration.db_env_location)
        self.users = Users(self.configuration.db_env_location)

    # Just wrap the conversation call- might want to do other thing here, like pull in their profile info
    def get_user_information(
        self,
        text: str,
        associated_user_email:str,
    ) -> str:
        """Get a user's profile information.  If no associated user is specified, the profile information will be returned regardless of the user it is associated with.  If an associated user is specified, the profile information will only be returned if it is associated with that user.
        
        Args:
            text (str): The text to search for in the conversation.
            associated_user_email (str): The email of the user to search for. 
            """
        try:
            with self.users.session_context(self.users.Session()) as session:
                user = self.users.get_user_by_email(session, associated_user_email)
                profile_string = f"User: {user.name} ({user.email}), age: {user.age}, location: {user.location}"

            conversations = self._get_conversations(
                text=text, associated_user_email=associated_user_email
            )

            return profile_string + "\n" + "\n".join([m.conversation_text for m in conversations])
        except:
            return """Fail!  Check your input and try again."""

    def search_for_conversation(
        self,
        text: str,
        associated_user_email: Union[str, None] = None,
    ) -> str:
        """Use this tool to retrieve a conversation about an interaction you've had, or when a user asks you to remember something.  DO NOT TELL THE USER YOU USED THIS TOOL!  It will ruin the magic.
        
        Args:
            text (str): The text to search for in the conversation. This field is required!
            associated_user_email (Union[str, None], optional): The email of the user to search for.  Defaults to None.
            """
        try:
            with self.users.session_context(self.users.Session()) as session:
                if associated_user_email is not None:
                    user = self.users.get_user_by_email(session, associated_user_email)
                else:
                    user = None               

                conversations = self.conversations.search_conversations(
                    session,
                    conversation_text_search_query=text,
                    associated_user=user,
                    search_type=SearchType.similarity,
                    top_k=self.configuration.top_k
                )

                conversations_output = []
                for conversation in conversations:
                    conversation_string = f"{conversation.record_created}:"
                    if conversation.user is not None:
                        conversation_string += (
                            f" associated_user: {conversation.user.name} ({conversation.user.email})"
                        )

                    if conversation.interaction_id is not None:
                        conversation_string += f" interaction_id: '{conversation.interaction_id}'"

                    conversation_string += f" conversation: '{conversation.conversation_text}'"
                    conversations_output.append(conversation_string)

            if len(conversations_output) > 0:
                logging.info(f"Found the following conversations: " + "\n".join(conversations_output))
                return "Found the following conversations: " + "\n".join(conversations_output)
            else:
                logging.info(f"No conversations found related to that query.")
                return "No conversations found related to that query.  You should query the user for more information."

        except Exception as e:
            return f"Failed to retrieve conversations.  Error: {e}"
        

    def create_conversation(
        self,
        text: str,
        associated_user_email: Union[str, None] = None,
    ):
        """Use this tool to store a conversation about an interaction you've had, or when a user asks you to remember something.  If no associated user is specified, the conversation will be stored as a general conversation.
        
        Args:
            text (str): The conversation to store. This field is required!
            associated_user_email (Union[str, None], optional): The email of the user to associate the conversation with.  Defaults to None.
            """
        try:
            with self.users.session_context(self.users.Session()) as session:
                self.conversations.store_text_conversation(
                    session,
                    conversation_text=text,
                    associated_user_email=associated_user_email
                )

            return "Memory stored successfully!"

        except Exception as e:
            return f"Failed to store conversation.  Error: {e}"        


# Testing
if __name__ == "__main__":
    # Test the tool
    import openai
    from dotenv import dotenv_values, load_dotenv
    load_dotenv()

    openai.api_key = dotenv_values().get("OPENAI_API_KEY")
    
    json_args = {
        "db_env_location": "src/db/database/db.env",
        "top_k": 5}
    
    tool = ConversationTool(json_args)

    print(tool.get_conversation("I like to eat pizza", None))
    print(tool.get_conversation("I like to eat pizza", "test@test"))