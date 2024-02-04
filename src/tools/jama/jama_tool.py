from typing import Union
from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.tools.tool_registry import register_tool, tool_class
from src.db.models.user_settings import UserSettings
from src.integrations.jama.jama_session import JamaSession


@tool_class
class JamaTool:
    def __init__(self, configuration, conversation_manager: ConversationManager):
        self.configuration = configuration
        self.conversation_manager = conversation_manager
        self.user_settings_helper = UserSettings()

        if not conversation_manager:
            return None

        # Retrieve Jama configuration settings
        self.jama_api_url = self.user_settings_helper.get_user_setting(
            user_id=conversation_manager.user_id, setting_name="jama_api_url"
        ).setting_value
        self.jama_client_id = self.user_settings_helper.get_user_setting(
            user_id=conversation_manager.user_id, setting_name="jama_client_id"
        ).setting_value
        self.jama_client_secret = self.user_settings_helper.get_user_setting(
            user_id=conversation_manager.user_id, setting_name="jama_client_secret"
        ).setting_value

        # Initialize JamaSession with OAuth
        self.oauth = JamaSession(
            api_url=self.jama_api_url,
            auth_type="oauth",
            client_id=self.jama_client_id,
            client_secret=self.jama_client_secret,
        )

    # @register_tool(
    #     display_name="Get Jama Projects",
    #     description="Retrieves all projects from Jama",
    #     help_text="Retrieves all projects from Jama",
    #     requires_repository=False,
    #     requires_documents=False,
    #     category="Jama",
    # )
    # def get_jama_projects(self):
    #     endpoint = "projects"
    #     response = self.oauth.make_api_call(endpoint, method="GET")
    #     return response

    @register_tool(
        display_name="Make a Jama API Call",
        description="Make a call to the Jama API with a given endpoint and method, and optional data.",
        additional_instructions="You must know the specific endpoint (e.g. 'projects', 'items/{{item_id}}', etc.) in order to make this call.",
        requires_repository=False,
        requires_documents=False,
        category="Jama",
    )
    def make_jama_api_call(
        self, endpoint: str, method: str = "GET", data: Union[None, dict] = None
    ):
        response = self.oauth.make_api_call(endpoint, method=method, data=data)
        return response
