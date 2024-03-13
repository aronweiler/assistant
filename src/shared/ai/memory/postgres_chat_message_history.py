from typing import List
from uuid import UUID

from langchain.schema.chat_history import BaseChatMessageHistory
from langchain.schema.messages import BaseMessage
from langchain.schema.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    FunctionMessage,
)

from src.shared.database.models.conversation_messages import ConversationMessages, ConversationMessageModel
from src.shared.database.models.domain.conversation_role_type import ConversationRoleType


class PostgresChatMessageHistory(BaseChatMessageHistory):
    """Chat message history stored in Postgres."""

    def __init__(self, conversation_id: UUID, conversation_messages: ConversationMessages):
        """Initialize the PostgresChatMessageHistory.

        Args:
            conversation_id: The ID of the conversation to store messages for.
            conversations: The Conversations object to use for storing messages.
        """
        self.conversation_id = conversation_id
        self.conversation_messages = conversation_messages

        self.user_id: int = None

    @property
    def messages(self) -> List[BaseMessage]:
        """A list of Messages stored in the DB."""
        # return self.chat_messages
        chat_messages = []
        messages = self.conversation_messages.get_conversations_for_conversation(
            self.conversation_id
        )
        for message in messages:
            if message.conversation_role_type == ConversationRoleType.USER:
                chat_message = HumanMessage(content=message.message_text)
            elif message.conversation_role_type == ConversationRoleType.ASSISTANT:
                chat_message = AIMessage(content=message.message_text)
            elif message.conversation_role_type == ConversationRoleType.SYSTEM:
                chat_message = SystemMessage(content=message.message_text)

            chat_message.additional_kwargs = {"id": message.id}
            chat_messages.append(chat_message)

        return chat_messages

    def add_message(self, message: BaseMessage) -> None:
        """Add a Message object to the store.

        Args:
            message: A BaseMessage object to store.
        """

        if type(message) == HumanMessage:
            role_type = ConversationRoleType.USER
        elif type(message) == AIMessage:
            role_type = ConversationRoleType.ASSISTANT
        elif type(message) == SystemMessage:
            role_type = ConversationRoleType.SYSTEM
        elif type(message) == FunctionMessage:
            role_type = ConversationRoleType.FUNCTION
        else:
            raise ValueError("Unknown message type")

        self.conversation_messages.add_conversation(
            ConversationMessageModel(
                conversation_id=self.conversation_id,
                message_text=message.content,
                conversation_role_type=role_type,
                user_id=self.user_id,
            )
        )

        # self.chat_messages.append(message)

    def clear(self) -> None:
        """Clear memory contents."""
        raise NotImplementedError(
            "clear() not implemented for PostgresChatMessageHistory"
        )
