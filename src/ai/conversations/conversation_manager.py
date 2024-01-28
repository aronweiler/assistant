import logging
from typing import List

from langchain.base_language import BaseLanguageModel
from src.ai.agents.general.generic_tool import GenericTool
from src.ai.system_info import get_system_information
from src.db.models.code import Code

from src.db.models.conversation_messages import (
    ConversationMessages,
    SearchType,
    ConversationMessageModel,
)
from src.db.models.domain.code_repository_model import CodeRepositoryModel
from src.db.models.domain.tool_call_results_model import ToolCallResultsModel
from src.db.models.users import Users
from src.db.models.documents import Documents
from src.db.models.conversations import Conversations

from src.memory.postgres_chat_message_history import PostgresChatMessageHistory
from src.memory.token_buffer import ConversationTokenBufferMemory

from src.ai.prompts.prompt_manager import PromptManager
from src.utilities.configuration_utilities import get_app_configuration


class ConversationManager:
    """Class that manages the interactions for the AI, including conversation history."""

    def __init__(
        self,
        conversation_id: int,
        user_email: str,
        prompt_manager: PromptManager,
        max_conversation_history_tokens: int = 1000,
        uses_conversation_history: bool = True,
        collection_id: int = None,
        selected_repository: CodeRepositoryModel = None,
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

        if selected_repository is not None:
            self.set_selected_repository(selected_repository)

        self.user_id = user_id
        self.user_name = user_name
        self.user_location = user_location
        self.conversation_needs_summary = conversation_needs_summary

        if conversation_id is None:
            raise Exception("conversation_id cannot be None")

        if user_email is None:
            raise Exception("user_email cannot be None")

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
                    max_conversation_history_tokens
                )
        else:
            self.conversation_token_buffer_memory = override_memory

    def set_conversation_summary(self, summary: str):
        """Sets the conversation summary to the specified summary."""

        self.conversations_helper.update_conversation_summary(
            self.conversation_id, summary, False
        )

        self.conversation_needs_summary = False

    def set_selected_repository(self, repository: CodeRepositoryModel):
        """Sets the selected repository for the current conversation."""

        self.conversations_helper.update_selected_code_repo(
            self.conversation_id, repository.id if repository is not None else -1
        )

    def get_selected_repository(self) -> CodeRepositoryModel:
        """Gets the selected repository, if any, for the current conversation."""

        conversation = self.get_conversation()

        if conversation.last_selected_code_repo != -1:
            return self.code_helper.get_repository(conversation.last_selected_code_repo)

        return None

    def get_previous_tool_calls_prompt(self):
        previous_tool_calls = self._get_previous_tool_call_headers()

        if previous_tool_calls and len(previous_tool_calls) > 0:
            previous_tool_calls_prompt = (
                self.prompt_manager.get_prompt_by_template_name(
                    "PREVIOUS_TOOL_CALLS_TEMPLATE",
                ).format(previous_tool_calls=previous_tool_calls)
            )
        else:
            previous_tool_calls_prompt = ""

        return previous_tool_calls_prompt

    def get_available_tool_descriptions(self, tools: List[GenericTool]):
        tool_strings = []
        for tool in tools:
            if tool.additional_instructions:
                additional_instructions = (
                    "\nAdditional Instructions: " + tool.additional_instructions
                )
            else:
                additional_instructions = ""

            if tool.document_classes:
                classes = ", ".join(tool.document_classes)
                document_class = f"\nIMPORTANT: Only use this tool with documents with classifications of: '{classes}'. For other types of files, refer to specialized tools."
            else:
                document_class = ""

            tool_strings.append(
                f"Name: {tool.name}\nDescription: {tool.description}{additional_instructions}{document_class}"
            )

        formatted_tools = "\n----\n".join(tool_strings)

        return formatted_tools

    def _get_previous_tool_call_headers(self):
        # Check the configuration to see if the get_previous_tool_call_results tool is enabled
        get_previous_tool_call_results_tool_enabled = get_app_configuration()[
            "tool_configurations"
        ]["get_previous_tool_call_results"].get("enabled", False)

        previous_tool_calls: List[
            ToolCallResultsModel
        ] = self.conversations_helper.get_tool_call_results(self.conversation_id)

        if not previous_tool_calls or len(previous_tool_calls) == 0:
            return None

        tool_call_list = []

        for tool_call in previous_tool_calls:
            if tool_call.include_in_conversation:
                tool_call_list.append(
                    f"{tool_call.record_created} - (ID: {tool_call.id}) Name: `{tool_call.tool_name}`, tool input: {tool_call.tool_arguments}, tool results: {tool_call.tool_results}"
                )
            elif get_previous_tool_call_results_tool_enabled:
                tool_call_list.append(
                    f"{tool_call.record_created} - (ID: {tool_call.id}) Name: `{tool_call.tool_name}`, tool input: {tool_call.tool_arguments}, tool results:\nUse the `get_previous_tool_call_results` tool with this ID to view the results."
                )

        return "\n----\n".join(tool_call_list)

    def get_selected_repository_prompt(self):
        selected_repo = self.get_selected_repository()

        if selected_repo:
            selected_repo_prompt = self.prompt_manager.get_prompt_by_template_name(
                "SELECTED_REPO_TEMPLATE",
            ).format(
                selected_repository=f"ID: {selected_repo.id} - {selected_repo.code_repository_address} ({selected_repo.branch_name})"
            )
        else:
            selected_repo_prompt = ""

        return selected_repo_prompt

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
            for file in self.documents_helper.get_files_in_collection(
                self.collection_id
            )
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
            for file in self.documents_helper.get_files_in_collection(
                self.collection_id
            )
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
            for file in self.documents_helper.get_files_in_collection(
                self.collection_id
            )
        ]

    def get_loaded_documents_prompt(self):
        loaded_documents = self.get_loaded_documents_for_reference()

        if loaded_documents:
            loaded_documents_prompt = (
                self.prompt_manager.get_prompt_by_template_name(
                    "LOADED_DOCUMENTS_TEMPLATE",
                ).format(loaded_documents=loaded_documents)
            )
        else:
            loaded_documents_prompt = "There are no documents loaded."

        return loaded_documents_prompt

    def get_conversation(self):
        """Gets the conversation for the specified conversation ID."""

        return self.conversations_helper.get_conversation(self.conversation_id)

    def get_chat_history_prompt(self):
        chat_history = self._get_chat_history()

        if chat_history and len(chat_history) > 0:
            chat_history_prompt = self.prompt_manager.get_prompt_by_template_name(
                "CHAT_HISTORY_TEMPLATE",
            ).format(chat_history=chat_history)
        else:
            chat_history_prompt = ""

        return chat_history_prompt

    def _get_chat_history(self):
        """Gets the chat history for the current conversation"""

        return self.conversation_token_buffer_memory.buffer_as_str

    def get_system_prompt(self):
        system_prompt = self.prompt_manager.get_prompt_by_template_name(
            "SYSTEM_TEMPLATE",
        ).format(
            system_information=get_system_information(),
        )

        return system_prompt

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

    def _create_default_conversation_memory(self, max_conversation_history_tokens):
        """Creates the conversation memory for the conversation."""

        self.postgres_chat_message_history = PostgresChatMessageHistory(
            self.conversation_id,
            conversation_messages=self.conversation_messages_helper,
        )

        self.postgres_chat_message_history.user_id = self.user_id

        self.conversation_token_buffer_memory = ConversationTokenBufferMemory(
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
