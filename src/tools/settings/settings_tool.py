import logging
from src.ai.conversations.conversation_manager import ConversationManager

from src.ai.tools.tool_registry import register_tool, tool_class


@tool_class
class SettingsTool:
    def __init__(self, configuration, conversation_manager: ConversationManager):
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    def get_setting_names(self):
        return [
            setting.setting_name
            for setting in self.conversation_manager.get_all_user_settings()
        ]

    @register_tool(
        display_name="Get Internal Settings",
        description="Gets a list of this application's internal user-specific settings.",
        additional_instructions="Use this tool to get a single specific setting (by passing the `setting_name` argument) or a complete list of the internal settings (and their values) that are available for the current user.",
        category="Settings",
    )
    def get_settings(self, setting_name=None):
        """Get the internal settings for the current user."""
        # Get the internal settings for the current user

        if setting_name:
            setting = self.conversation_manager.get_user_setting(
                setting_name=setting_name
            )

            return (
                f"Setting Name | Setting Value\n{setting.setting_name} | {setting.setting_value}"
                if setting
                else f"Setting {setting_name} does not exist. But I found the following settings: {', '.join(self.get_setting_names())}"
            )
        else:

            settings = self.conversation_manager.get_all_user_settings()

            return "Setting Name | Setting Value\n" + "\n".join(
                [
                    f"{setting.setting_name} | {setting.setting_value}"
                    for setting in settings
                ]
            )

    @register_tool(
        display_name="Sets an Internal Setting Value",
        description="Sets a user-specific internal setting value.",
        additional_instructions="Use this tool to set an internal setting value for the current user.",
        category="Settings",
    )
    def set_setting(self, setting_name, setting_value, create_new_setting=False):
        setting = self.conversation_manager.get_user_setting(setting_name=setting_name)

        if setting:
            # The AI picked an existing setting, just update it
            self.conversation_manager.set_user_setting(
                setting_name=setting_name,
                setting_value=setting_value,
            )
        elif create_new_setting:
            # The AI picked a new setting, create it
            self.conversation_manager.set_user_setting(
                setting_name=setting_name,
                setting_value=setting_value,
            )
        else:
            return f"Setting {setting_name} does not exist. But I found the following settings: {', '.join(self.get_setting_names())}."

        return f"Setting {setting_name} has been set to {setting_value}."
