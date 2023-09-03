import logging

from langchain.base_language import BaseLanguageModel

from db.models.conversations import Conversations, SearchType
from db.models.users import Users
from db.models.documents import Documents
from db.models.interactions import Interactions

from memory.postgres_chat_message_history import PostgresChatMessageHistory
from memory.token_buffer import ConversationTokenBufferMemory


class InteractionManager:
    """Class that manages the interactions for the AI, including conversation history."""

    interaction_id: int
    collection_id: int = None

    user_id: int
    user_email: str
    user_name: str
    user_location: str

    db_env_location: str

    interaction_needs_summary: bool = True

    interactions_helper: Interactions
    conversations_helper: Conversations

    postgres_chat_message_history: PostgresChatMessageHistory
    conversation_token_buffer_memory: ConversationTokenBufferMemory

    @classmethod
    def set_collection_id(cls, value):
        # Class method to set the collection_id
        cls.collection_id = value

    @classmethod
    def get_collection_id(cls):
        # Class method to get the collection_id
        return cls.collection_id

    def __init__(
        self,
        interaction_id: int,
        user_email: str,
        llm: BaseLanguageModel,
        db_env_location: str,
        max_token_limit: int = 1000,
    ):
        """Creates a new InteractionManager, and loads the conversation memory from the database.

        Args:
            interaction_id (int): The interaction ID to use to construct the interaction manager.
        """

        if interaction_id is None:
            raise Exception("interaction_id cannot be None")

        if user_email is None:
            raise Exception("user_email cannot be None")

        if llm is None:
            raise Exception("llm cannot be None")

        if db_env_location is None:
            raise Exception("db_env_location cannot be None")

        # Set our internal interaction id
        self.interaction_id = interaction_id

        self.db_env_location = db_env_location

        self.interactions_helper = Interactions(db_env_location)
        self.conversations_helper = Conversations(db_env_location)
        self.users_helper = Users(db_env_location)
        self.documents_helper = Documents(db_env_location)

        # Get the user
        with self.users_helper.session_context(self.users_helper.Session()) as session:
            user = self.users_helper.get_user_by_email(session, user_email)

            if user is None:
                raise Exception(f"User with email {user_email} not found.")

            self.user_id = user.id
            self.user_name = user.name
            self.user_email = user.email
            self.user_location = user.location

        # Ensure the interaction exists
        self._ensure_interaction_exists(self.user_id)

        # Create the conversation memory
        self._create_conversation_memory(llm, max_token_limit)

    def set_interaction_summary(self, summary: str):
        """Sets the interaction summary to the specified summary."""

        with self.interactions_helper.session_context(
            self.interactions_helper.Session()
        ) as session:
            self.interactions_helper.update_interaction(
                session, self.interaction_id, summary, False
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

        with self.documents_helper.session_context(
            self.documents_helper.Session()
        ) as session:
            return [
                f"Document name: '{file.file_name}' Type: {file.file_classification}"
                for file in self.documents_helper.get_collection_files(
                    session, self.collection_id
                )
            ]
        
    def get_loaded_documents_for_reference(self):
        """Gets the loaded documents for the specified collection."""

        if self.collection_id is None:
            logging.warning(
                "No document collection ID specified, cannot get loaded documents."
            )
            return [
                "There is no document collection selected, so I can't see what documents are loaded."
            ]

        with self.documents_helper.session_context(
            self.documents_helper.Session()
        ) as session:
            return [
                f"file_id='{file.id}' ({file.file_name}, {file.file_classification})"
                for file in self.documents_helper.get_collection_files(
                    session, self.collection_id
                )
            ]

    def _ensure_interaction_exists(self, user_id: int):
        """Ensures the interaction exists, and creates it if it doesn't."""

        with self.interactions_helper.session_context(
            self.interactions_helper.Session()
        ) as session:
            # Get the interaction from the db
            interaction = self.interactions_helper.get_interaction(
                session, self.interaction_id
            )

            # If the interaction doesn't exist, create it
            if interaction is None:
                self.interactions_helper.create_interaction(
                    session,
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

    def _create_conversation_memory(self, llm, max_token_limit):
        """Creates the conversation memory for the interaction."""

        self.postgres_chat_message_history = PostgresChatMessageHistory(
            self.interaction_id,
            conversations=self.conversations_helper,
            max_token_limit=max_token_limit,
        )

        self.postgres_chat_message_history.user_id = self.user_id

        self.conversation_token_buffer_memory = ConversationTokenBufferMemory(
            llm=llm,
            memory_key="chat_history",
            input_key="input",
            chat_memory=self.postgres_chat_message_history,
            max_token_limit=max_token_limit,
        )

        # Required because when pulling the database memory in the first time, there might be too many messages.
        self.conversation_token_buffer_memory.prune_buffer()

        logging.info(
            f"Conversation memory created for interaction {self.interaction_id}, with max token limit {max_token_limit}"
        )
