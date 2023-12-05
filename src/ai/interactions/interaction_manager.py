import logging

from langchain.base_language import BaseLanguageModel

from src.db.models.conversations import Conversations, SearchType, ConversationModel
from src.db.models.users import Users
from src.db.models.documents import Documents
from src.db.models.interactions import Interactions

from src.memory.postgres_chat_message_history import PostgresChatMessageHistory
from src.memory.token_buffer import ConversationTokenBufferMemory

from src.ai.prompts.prompt_manager import PromptManager


class InteractionManager:
    """Class that manages the interactions for the AI, including conversation history."""

    def __init__(
        self,
        interaction_id: int,
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
        interaction_needs_summary: bool = True,
        override_memory: ConversationTokenBufferMemory = None,
    ):
        """Creates a new InteractionManager, and loads the conversation memory from the database.

        Args:
            interaction_id (int): The interaction ID to use to construct the interaction manager.
        """

        self.prompt_manager = prompt_manager
        self.tool_kwargs = tool_kwargs
        self.collection_id = collection_id
        self.user_id = user_id
        self.user_name = user_name
        self.user_location = user_location
        self.interaction_needs_summary = interaction_needs_summary

        if interaction_id is None:
            raise Exception("interaction_id cannot be None")

        if user_email is None:
            raise Exception("user_email cannot be None")

        if llm is None:
            raise Exception("llm cannot be None")

        # Set our internal interaction id
        self.interaction_id = interaction_id

        self.interactions_helper = Interactions()
        self.conversations_helper = Conversations()
        self.users_helper = Users()
        self.documents_helper = Documents()
        
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

        # Ensure the interaction exists
        self._ensure_interaction_exists(self.user_id)

        if not override_memory:
            # Create the conversation memory
            if uses_conversation_history:
                self._create_default_conversation_memory(
                    llm, max_conversation_history_tokens
                )
        else:
            self.conversation_token_buffer_memory = override_memory

    def set_interaction_summary(self, summary: str):
        """Sets the interaction summary to the specified summary."""

        self.interactions_helper.update_interaction_summary(
            self.interaction_id, summary, False
        )

        self.interaction_needs_summary = False

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

    def get_interaction(self):
        """Gets the interaction for the specified interaction ID."""

        return self.interactions_helper.get_interaction(self.interaction_id)

    def _ensure_interaction_exists(self, user_id: int):
        """Ensures the interaction exists, and creates it if it doesn't."""
        # Get the interaction from the db
        interaction = self.interactions_helper.get_interaction(self.interaction_id)

        # If the interaction doesn't exist, create it
        if interaction is None:
            self.interactions_helper.create_interaction(
                self.interaction_id,
                "New Chat",
                user_id,
            )
            self.interaction_needs_summary = True

            logging.info(
                f"Interaction ID: {self.interaction_id} created for user {user_id}"
            )
        else:
            # The interaction already exists, but could still need summary
            self.interaction_needs_summary = interaction.needs_summary

            logging.info(
                f"Interaction ID: {self.interaction_id} already exists for user {user_id}, needs summary: {self.interaction_needs_summary}"
            )

    def _create_default_conversation_memory(self, llm, max_conversation_history_tokens):
        """Creates the conversation memory for the interaction."""

        self.postgres_chat_message_history = PostgresChatMessageHistory(
            self.interaction_id, conversations=self.conversations_helper
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
            f"Conversation memory created for interaction {self.interaction_id}, with max_conversation_history_tokens limit {max_conversation_history_tokens}"
        )
