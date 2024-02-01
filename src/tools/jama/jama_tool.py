from src.ai.tools.tool_registry import tool_class
from src.db.models.user_settings import UserSettingsCRUD
from src.integrations.jama.jama_session import JamaSession


@tool_class
class JamaTool:
    def __init__(self, configuration, conversation_manager):
        self.configuration = configuration
        self.conversation_manager = conversation_manager
        self.user_settings_helper = UserSettingsCRUD()

        # Retrieve Jama configuration settings
        self.jama_api_url = self.user_settings_helper.get_user_setting("jama_api_url")
        self.jama_client_id = self.user_settings_helper.get_user_setting(
            "jama_client_id"
        )
        self.jama_client_secret = self.user_settings_helper.get_user_setting(
            "jama_client_secret"
        )

        # Initialize JamaSession with OAuth
        self.oauth = JamaSession(
            self.jama_api_url,
            "oauth",
            client_id=self.jama_client_id,
            client_secret=self.jama_client_secret,
        )
