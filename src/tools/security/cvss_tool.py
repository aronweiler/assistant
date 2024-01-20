from src.ai.conversations.conversation_manager import ConversationManager
from src.ai.llm_helper import get_tool_llm
from src.ai.tools.tool_registry import register_tool, tool_class


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
    )
    def create_cvss_evaluation(self, vulnerability_data: str):
        """Creates a CVSS evaluation for the given vulnerability data.

        Args:
            vulnerability_data (str): The vulnerability data to evaluate.
        """

        llm = get_tool_llm(
            configuration=self.configuration,
            func_name=self.create_cvss_evaluation.__name__,
            streaming=True,
        )

        identify_vulnerable_component_prompt = (
            self.conversation_manager.prompt_manager.get_prompt(
                "security_tools_prompts", "IDENTIFY_VULNERABLE_COMPONENT_PROMPT"
            )
        )

        cvss_instruct_prompt = self.conversation_manager.prompt_manager.get_prompt(
            "security_tools_prompts", "CVSS_INSTRUCT_PROMPT"
        )

        vulnerable_component = llm.invoke(
            identify_vulnerable_component_prompt.format(
                vulnerability_data=vulnerability_data
            ),
            #callbacks=self.conversation_manager.agent_callbacks,
        ).content

        cvss_evaluation = llm.invoke(
            cvss_instruct_prompt.format(
                vulnerable_component=vulnerable_component,
                vulnerability_data=vulnerability_data,
            ),
            #callbacks=self.conversation_manager.agent_callbacks,
        )

        return cvss_evaluation.content
