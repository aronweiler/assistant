from typing import List
from src.ai.agents.general.generic_tool import GenericTool
from src.ai.conversations.conversation_manager import ConversationManager
from src.db.models.domain.tool_call_results_model import ToolCallResultsModel
from src.utilities.configuration_utilities import get_app_configuration


class GenericToolAgentHelpers:
    def __init__(self, conversation_manager: ConversationManager):
        self.conversation_manager = conversation_manager

    def get_selected_repo_prompt(self):
        selected_repo = self.conversation_manager.get_selected_repository()

        if selected_repo:
            selected_repo_prompt = self.conversation_manager.prompt_manager.get_prompt_by_category_and_name(
                "generic_tools_agent_prompts",
                "SELECTED_REPO_TEMPLATE",
            ).format(
                selected_repository=f"ID: {selected_repo.id} - {selected_repo.code_repository_address} ({selected_repo.branch_name})"
            )
        else:
            selected_repo_prompt = ""
        return selected_repo_prompt

    def get_loaded_documents_prompt(self):
        loaded_documents = self._get_loaded_documents()

        if loaded_documents:
            loaded_documents_prompt = (
                self.conversation_manager.prompt_manager.get_prompt_by_category_and_name(
                    "generic_tools_agent_prompts",
                    "LOADED_DOCUMENTS_TEMPLATE",
                ).format(loaded_documents=loaded_documents)
            )
        else:
            loaded_documents_prompt = "There are no documents loaded."
        return loaded_documents_prompt

    def get_previous_tool_calls_prompt(self):
        previous_tool_calls = self._get_previous_tool_call_headers()

        if previous_tool_calls and len(previous_tool_calls) > 0:
            previous_tool_calls_prompt = (
                self.conversation_manager.prompt_manager.get_prompt_by_category_and_name(
                    "generic_tools_agent_prompts",
                    "PREVIOUS_TOOL_CALLS_TEMPLATE",
                ).format(previous_tool_calls=previous_tool_calls)
            )
        else:
            previous_tool_calls_prompt = ""

        return previous_tool_calls_prompt

    def _get_loaded_documents(self):
        if self.conversation_manager:
            return "\n".join(
                self.conversation_manager.get_loaded_documents_for_reference()
            )
        else:
            return None

    def get_chat_history_prompt(self):
        chat_history = self.get_chat_history()

        if chat_history and len(chat_history) > 0:
            chat_history_prompt = self.conversation_manager.prompt_manager.get_prompt_by_category_and_name(
                "generic_tools_agent_prompts",
                "CHAT_HISTORY_TEMPLATE",
            ).format(chat_history=chat_history)
        else:
            chat_history_prompt = ""

        return chat_history_prompt

    

    def get_chat_history(self):
        if self.conversation_manager:
            return (
                self.conversation_manager.conversation_token_buffer_memory.buffer_as_str
            )
        else:
            return "No chat history."

    def get_available_tool_descriptions(self, tools: list[GenericTool]):
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

    def get_system_prompt(self, system_information):
        system_prompt = self.conversation_manager.prompt_manager.get_prompt_by_template_name(
            "SYSTEM_TEMPLATE",
        ).format(
            system_information=system_information,
        )

        return system_prompt

    def _get_previous_tool_call_headers(self):
        # Check the configuration to see if the get_previous_tool_call_results tool is enabled
        get_previous_tool_call_results_tool_enabled = get_app_configuration()[
            "tool_configurations"
        ]["get_previous_tool_call_results"].get("enabled", False)

        previous_tool_calls: List[
            ToolCallResultsModel
        ] = self.conversation_manager.conversations_helper.get_tool_call_results(
            self.conversation_manager.conversation_id
        )

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
