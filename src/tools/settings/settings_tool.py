import logging
from src.ai.conversations.conversation_manager import ConversationManager

from src.ai.tools.tool_registry import register_tool, tool_class
from src.db.models.domain.user_settings_model import UserSettingModel
from src.db.models.user_settings import UserSettings


@tool_class
class SettingsTool:
    def __init__(self, configuration, conversation_manager: ConversationManager):
        self.configuration = configuration
        self.conversation_manager = conversation_manager
        self.user_settings_helper = UserSettings()

    @register_tool(
        display_name="Get Internal Settings",
        description="Gets a list of this application's internal user-specific settings.",
        additional_instructions="Use this tool to get a list of the internal settings (and their values) that are available for the current user.",
        category="Settings",
    )
    def get_settings(self):
        """Get the internal settings for the current user."""
        # Get the internal settings for the current user

        settings = self.user_settings_helper.get_user_settings(
            user_id=self.conversation_manager.user_id
        )

        return "Setting Name | Setting Value\n" + "\n".join(
            [f"{setting.name} | {setting.value}" for setting in settings]
        )

    @register_tool(
        display_name="Sets an Internal Setting Value",
        description="Sets a user-specific internal setting value.",
        additional_instructions="Use this tool to set an internal setting value for the current user.",
        category="Settings",
    )
    def set_setting(self, setting_name, setting_value, create_new_setting=False):
        setting = self.user_settings_helper.get_user_setting(
            user_id=self.conversation_manager.user_id, setting_name=setting_name
        )

        if setting:
            # The AI picked an existing setting, just update it
            self.user_settings_helper.add_update_user_setting(
                user_id=self.conversation_manager.user_id,
                setting_name=setting_name,
                setting_value=setting_value,
            )
        elif create_new_setting:
            # The AI picked a new setting, create it
            self.user_settings_helper.create_user_setting(
                user_setting_model=UserSettingModel(
                    user_id=self.conversation_manager.user_id,
                    setting_name=setting_name,
                    setting_value=setting_value,
                )
            )
        else:
            return f"Setting {setting_name} does not exist. But I found the following settings: {self.get_settings()}."

        return f"Setting {setting_name} has been set to {setting_value}."
