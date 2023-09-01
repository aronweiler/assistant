from typing import List
from uuid import UUID

from langchain.schema.memory import BaseChatMessageHistory
from langchain.schema.messages import BaseMessage
from langchain.schema.messages import HumanMessage, AIMessage, SystemMessage

from db.models.conversations import Conversations, SearchType

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

        # Fill the chat messages list from the DB
        self.chat_messages = []
        with self.conversations.session_context(
            self.conversations.Session()
        ) as session:
            messages = self.conversations.get_conversations_for_interaction(
                session, self.interaction_id
            )
            for message in messages:
                if message.conversation_role_type.role_type == "user":
                    self.chat_messages.append(
                        HumanMessage(content=message.conversation_text)
                    )
                elif message.conversation_role_type.role_type == "assistant":
                    self.chat_messages.append(AIMessage(content=message.conversation_text))
                elif message.conversation_role_type.role_type == "system":
                    self.chat_messages.append(
                        SystemMessage(content=message.conversation_text)
                    )

    @property
    def messages(self) -> List[BaseMessage]:
        """A list of Messages stored in the DB."""
        return self.chat_messages    
    
    def get_related_conversation(self, query:str) -> List[BaseMessage]:        
        chat_messages = []
        with self.conversations.session_context(
            self.conversations.Session()
        ) as session:
            messages = self.conversations.search_conversations(
                session,
                conversation_text_search_query=query,
                search_type=SearchType.similarity
            )

            for message in messages:
                if message.conversation_role_type.role_type == "user":
                    chat_messages.append(
                        HumanMessage(content=message.conversation_text)
                    )
                elif message.conversation_role_type.role_type == "assistant":
                    chat_messages.append(AIMessage(content=message.conversation_text))
                elif message.conversation_role_type.role_type == "system":
                    chat_messages.append(
                        SystemMessage(content=message.conversation_text)
                    )

        return chat_messages

    def add_message(self, message: BaseMessage) -> None:
        """Add a Message object to the store.

        Args:
            message: A BaseMessage object to store.
        """

        # TODO: Make this a lookup
        role_type_id = 3
        if type(message) == HumanMessage:            
            role_type_id = 3
        elif type(message) == AIMessage:
            role_type_id = 2
        elif type(message) == SystemMessage:
            role_type_id = 1

        with self.conversations.session_context(
            self.conversations.Session()
        ) as session:
            self.conversations.store_conversation(
                session,
                interaction_id=self.interaction_id,
                conversation_text=message.content,
                conversation_role_type_id=role_type_id,
                user_id=self.user_id,
            )

        self.chat_messages.append(message)

    def clear(self) -> None:
        """Clear memory contents."""
        raise NotImplementedError(
            "clear() not implemented for PostgresChatMessageHistory"
        )