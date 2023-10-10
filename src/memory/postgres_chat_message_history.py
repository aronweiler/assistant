from typing import List
from uuid import UUID

from langchain.schema.chat_history import BaseChatMessageHistory
from langchain.schema.messages import BaseMessage
from langchain.schema.messages import HumanMessage, AIMessage, SystemMessage, FunctionMessage

from src.db.models.conversations import Conversations, ConversationModel
from src.db.models.domain.conversation_role_type import ConversationRoleType

class PostgresChatMessageHistory(BaseChatMessageHistory):
    """Chat message history stored in Postgres."""

    interaction_id: UUID
    conversations: Conversations
    user_id: int

    def __init__(self, interaction_id: UUID, conversations: Conversations):
        """Initialize the PostgresChatMessageHistory.

        Args:
            interaction_id: The ID of the interaction to store messages for.
            conversations: The Conversations object to use for storing messages.
        """
        self.interaction_id = interaction_id
        self.conversations = conversations

    @property
    def messages(self) -> List[BaseMessage]:
        """A list of Messages stored in the DB."""
        #return self.chat_messages    
        chat_messages = []       
        messages = self.conversations.get_conversations_for_interaction(
            self.interaction_id
        )
        for message in messages:
            if message.conversation_role_type == ConversationRoleType.USER:
                chat_message = HumanMessage(content=message.conversation_text)
            elif message.conversation_role_type == ConversationRoleType.ASSISTANT:
                chat_message = AIMessage(content=message.conversation_text)
            elif message.conversation_role_type == ConversationRoleType.SYSTEM:
                chat_message = SystemMessage(content=message.conversation_text)

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

        self.conversations.add_conversation(ConversationModel(            
            interaction_id=self.interaction_id,
            conversation_text=message.content,
            conversation_role_type=role_type,
            user_id=self.user_id,
        ))

        #self.chat_messages.append(message)

    def clear(self) -> None:
        """Clear memory contents."""
        raise NotImplementedError(
            "clear() not implemented for PostgresChatMessageHistory"
        )