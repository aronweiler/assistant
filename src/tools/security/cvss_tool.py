from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.utilities.llm_helper import get_llm
from src.ai.tools.tool_registry import register_tool, tool_class
from src.configuration.model_configuration import ModelConfiguration
from src.db.models.user_settings import UserSettings


@tool_class
class CvssTool:
    def __init__(
        self,
        configuration,
        conversation_manager: ConversationManager,
    ):
        self.configuration = configuration
        self.conversation_manager = conversation_manager

    @register_tool(
        display_name="Create CVSS Evaluation",
        help_text="Creates a CVSS evaluation from user provided data.",
        requires_documents=False,
        description="Creates a CVSS evaluation from user provided data.",
        additional_instructions="Use this tool to create a CVSS evaluation (and score) from data provided by the user.  The vulnerability_data argument should be a string containing the data to evaluate- this data should be whatever the user has given you to evaluate.",
        category="Security",
    )
    def create_cvss_evaluation(self, vulnerability_data: str):
        """Creates a CVSS evaluation for the given vulnerability data.

        Args:
            vulnerability_data (str): The vulnerability data to evaluate.
        """

        # Get the setting for the tool model
        tool_model_configuration = UserSettings().get_user_setting(
            user_id=self.conversation_manager.user_id,
            setting_name=f"{self.create_cvss_evaluation.__name__}_model_configuration",
            default_value=ModelConfiguration.default().model_dump(),
        ).setting_value

        llm = get_llm(
            model_configuration=tool_model_configuration,
            streaming=True,
            callbacks=self.conversation_manager.agent_callbacks,
        )

        identify_vulnerable_component_prompt = (
            self.conversation_manager.prompt_manager.get_prompt_by_template_name(
                "IDENTIFY_VULNERABLE_COMPONENT_PROMPT"
            )
        )

        cvss_instruct_prompt = (
            self.conversation_manager.prompt_manager.get_prompt_by_template_name(
                "CVSS_INSTRUCT_PROMPT"
            )
        )

        vulnerable_component = llm.invoke(
            identify_vulnerable_component_prompt.format(
                vulnerability_data=vulnerability_data
            ),
            # # callbacks=self.conversation_manager.agent_callbacks,
        ).content

        cvss_evaluation = llm.invoke(
            cvss_instruct_prompt.format(
                vulnerable_component=vulnerable_component,
                vulnerability_data=vulnerability_data,
            ),
            # # callbacks=self.conversation_manager.agent_callbacks,
        )

        return cvss_evaluation.content
