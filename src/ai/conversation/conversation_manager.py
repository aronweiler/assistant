from enum import Enum
import uuid
from typing import Dict, List

# Add the root path to the python path so we can import the database
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from db.database.models import Conversation, ConversationRoleType, User

from db.models.users import Users
from db.models.conversations import Conversations


class MessageRole(Enum):
    """The role of a conversation entry"""

    # Note: These are the roles that are currently in the database, and this enum must be updated if the database is updated
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
    FUNCTION = "function"
    ERROR = "error"


class ConversationManager:
    def __init__(
        self,
        db_env_location: str,
        system_prompts: List[str] = None,
        include_system_information: bool = True,
    ) -> None:
        """Creates a new conversation using a unique interaction ID"""
        self.interaction_id = uuid.uuid4()
        self.users = Users(db_env_location)
        self.conversations = Conversations(db_env_location)
        self.messages: List[Dict[MessageRole, str]] = []
        self.system_prompts = system_prompts
        self.include_system_information = include_system_information

    def create_message(self, content: str, role: MessageRole = MessageRole.USER):
        """Creates a message without adding it to the conversation.

        Args:
            content (str): The content of the message
        """
        return {"role": role.value, "content": content}

    def store_message(
        self, user_id, content: str, role: MessageRole = MessageRole.USER
    ) -> None:
        # Update the database
        with self.conversations.session_context(
            self.conversations.Session()
        ) as session:
            role_type = (
                session.query(ConversationRoleType)
                .filter(ConversationRoleType.role_type == role.value)
                .first()
            )
            # Create a new conversation entry
            self.conversations.store_conversation(
                session,
                user_id=user_id,
                interaction_id=self.interaction_id,
                conversation_text=content,
                conversation_role_type_id=role_type.id,
            )
        
    def add_message(
        self, user_id, content: str, role: MessageRole = MessageRole.USER, store_message: bool = False
    ) -> None:
        """Adds a message to the conversation.  Conversation can have entries from multiple users."""
        message = {"role": role.value, "content": content}

        # Append to the list of messages
        self.messages.append(message)

        if store_message:
            self.store_message(user_id, content, role)
        

    def get_system_prompts(self, system_information):
        """Gets the system prompts

        Returns:
            List[str]: The system prompts
        """
        return [self.create_message(system_information, MessageRole.SYSTEM)] + [self.create_message(p, MessageRole.SYSTEM) for p in self.system_prompts]

    def get_messages(self, system_information, user_information, related_conversations) -> List[Dict[MessageRole, str]]:
        """Gets the messages in the conversation.  Prepends the system prompts, and the system information if they are set.

        Returns:
            List[Dict[MessageRole, str]]: The messages in the conversation
        """

        temp_messages = self.messages

        # Prepend the system prompts
        if self.system_prompts:
            temp_messages = [self.create_message(p, MessageRole.SYSTEM) for p in self.system_prompts] + temp_messages

        # Prepend the system information
        if self.include_system_information and system_information:
            temp_messages = [self.create_message(system_information, MessageRole.SYSTEM)] + temp_messages

        # Prepend the user information
        if user_information:
            temp_messages = [self.create_message(user_information, MessageRole.USER)] + temp_messages

        # Add the related conversations
        if related_conversations:
            related_conversations_header = self.create_message("Related conversations:", MessageRole.SYSTEM)            
            temp_messages += related_conversations_header + [c for c in related_conversations]


        return temp_messages

    def get_last_message(self) -> Dict[MessageRole, str]:
        """Gets the last message in the conversation

        Returns:
            Dict[MessageRole, str]: The last message in the conversation
        """
        return self.messages[-1]

    def trim_conversation(self) -> None:
        """If we are over our token limit, remove the oldest messages from the conversation"""
        raise NotImplementedError("Not implemented yet")


# Testing
if __name__ == "__main__":
    conversation_manager = ConversationManager("src/db/database/db.env")
    conversation_manager.add_message(1, "Hello")  # user
    conversation_manager.add_message(1, "How are you?", MessageRole.ASSISTANT)
    conversation_manager.add_message(1, "I'm good thanks", MessageRole.USER)
    print(conversation_manager.get_messages())
