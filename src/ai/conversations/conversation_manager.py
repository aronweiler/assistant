import logging

from langchain.base_language import BaseLanguageModel
from src.db.models.code import Code

from src.db.models.conversation_messages import ConversationMessages, SearchType, ConversationMessageModel
from src.db.models.domain.code_repository_model import CodeRepositoryModel
from src.db.models.users import Users
from src.db.models.documents import Documents
from src.db.models.conversations import Conversations

from src.memory.postgres_chat_message_history import PostgresChatMessageHistory
from src.memory.token_buffer import ConversationTokenBufferMemory

from src.ai.prompts.prompt_manager import PromptManager


class ConversationManager:
    """Class that manages the interactions for the AI, including conversation history."""

    def __init__(
        self,
        conversation_id: int,
        user_email: str,
        llm: BaseLanguageModel,
        prompt_manager: PromptManager,
        max_conversation_history_tokens: int = 1000,
        uses_conversation_history: bool = True,
        collection_id: int = None,
        tool_kwargs: dict = {},
        user_id: int = None,
        user_name: str = None,
        user_location: str = None,
        conversation_needs_summary: bool = True,
        override_memory: ConversationTokenBufferMemory = None,
    ):
        """Creates a new ConversationManager, and loads the conversation memory from the database.

        Args:
            conversation_id (int): The conversation ID to use to construct the conversation manager.
        """

        self.prompt_manager = prompt_manager
        self.tool_kwargs = tool_kwargs
        self.collection_id = collection_id
        self.user_id = user_id
        self.user_name = user_name
        self.user_location = user_location
        self.conversation_needs_summary = conversation_needs_summary

        if conversation_id is None:
            raise Exception("conversation_id cannot be None")

        if user_email is None:
            raise Exception("user_email cannot be None")

        if llm is None:
            raise Exception("llm cannot be None")

        # Set our internal conversation id
        self.conversation_id = conversation_id

        self.conversations_helper = Conversations()
        self.conversation_messages_helper = ConversationMessages()
        self.users_helper = Users()
        self.documents_helper = Documents()
        self.code_helper = Code()
        
        self.agent_callbacks = []
        self.llm_callbacks = []

        # Get the user
        user = self.users_helper.get_user_by_email(user_email)

        if user is None:
            raise Exception(f"User with email {user_email} not found.")

        self.user_id = user.id
        self.user_name = user.name
        self.user_email = user.email
        self.user_location = user.location

        # Ensure the conversation exists
        self._ensure_conversation_exists(self.user_id)

        if not override_memory:
            # Create the conversation memory
            if uses_conversation_history:
                self._create_default_conversation_memory(
                    llm, max_conversation_history_tokens
                )
        else:
            self.conversation_token_buffer_memory = override_memory

    def set_conversation_summary(self, summary: str):
        """Sets the conversation summary to the specified summary."""

        self.conversations_helper.update_conversation_summary(
            self.conversation_id, summary, False
        )

        self.conversation_needs_summary = False

    def get_selected_repository(self) -> CodeRepositoryModel:
        """Gets the selected repository, if any, for the current conversation."""
        conversation = self.get_conversation()
        
        if conversation.last_selected_code_repo  != -1:
            return self.code_helper.get_repository(conversation.last_selected_code_repo)
        
        return None

    def get_loaded_documents_for_display(self):
        """Gets the loaded documents for the specified collection."""

        if self.collection_id is None:
            logging.warning(
                "No document collection ID specified, cannot get loaded documents."
            )
            return [
                "There is no document collection selected, so I can't see what documents are loaded."
            ]

        return [
            f"{file.file_name} (Class: '{file.file_classification}')"
            for file in self.documents_helper.get_files_in_collection(self.collection_id)
        ]

    def get_loaded_documents_count(self):
        """Gets the loaded documents for the specified collection."""

        if self.collection_id is None:
            logging.warning(
                "No document collection ID specified, cannot get loaded documents."
            )
            return 0

        return len(self.documents_helper.get_files_in_collection(self.collection_id))

    def get_loaded_documents_for_reference(self):
        """Gets the loaded documents for the specified collection."""

        if self.collection_id is None:
            logging.warning(
                "No document collection ID specified, cannot get loaded documents."
            )
            return [
                "There is no document collection selected, so I can't see what documents are loaded."
            ]

        return [
            f"file_id='{file.id}' ({file.file_name}, Class: '{file.file_classification}')"
            for file in self.documents_helper.get_files_in_collection(self.collection_id)
        ]

    def get_loaded_documents_delimited(self):
        """Gets the loaded documents for the specified collection."""

        if self.collection_id is None:
            logging.warning(
                "No document collection ID specified, cannot get loaded documents."
            )
            return [
                "There is no document collection selected, so I can't see what documents are loaded."
            ]

        return [
            f"{file.id}:{file.file_name}"
            for file in self.documents_helper.get_files_in_collection(self.collection_id)
        ]

    def get_conversation(self):
        """Gets the conversation for the specified conversation ID."""

        return self.conversations_helper.get_conversation(self.conversation_id)

    def _ensure_conversation_exists(self, user_id: int):
        """Ensures the conversation exists, and creates it if it doesn't."""
        # Get the conversation from the db
        conversation = self.conversations_helper.get_conversation(self.conversation_id)

        # If the conversation doesn't exist, create it
        if conversation is None:
            self.conversations_helper.create_conversation(
                self.conversation_id,
                "New Chat",
                user_id,
            )
            self.conversation_needs_summary = True

            logging.info(
                f"Interaction ID: {self.conversation_id} created for user {user_id}"
            )
        else:
            # The conversation already exists, but could still need summary
            self.conversation_needs_summary = conversation.needs_summary

            logging.info(
                f"Interaction ID: {self.conversation_id} already exists for user {user_id}, needs summary: {self.conversation_needs_summary}"
            )

    def _create_default_conversation_memory(self, llm, max_conversation_history_tokens):
        """Creates the conversation memory for the conversation."""

        self.postgres_chat_message_history = PostgresChatMessageHistory(
            self.conversation_id, conversation_messages=self.conversation_messages_helper
        )

        self.postgres_chat_message_history.user_id = self.user_id

        self.conversation_token_buffer_memory = ConversationTokenBufferMemory(
            llm=llm,
            memory_key="chat_history",
            input_key="input",
            chat_memory=self.postgres_chat_message_history,
            max_token_limit=max_conversation_history_tokens,
        )

        self.conversation_token_buffer_memory.human_prefix = (
            f"{self.user_name} ({self.user_email})"
        )

        logging.info(
            f"Conversation memory created for conversation {self.conversation_id}, with max_conversation_history_tokens limit {max_conversation_history_tokens}"
        )
