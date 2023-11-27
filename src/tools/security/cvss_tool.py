from src.ai.interactions.interaction_manager import InteractionManager
from src.ai.llm_helper import get_tool_llm


class CvssTool:
    def __init__(
        self,
        configuration,
        interaction_manager: InteractionManager,
    ):
        self.configuration = configuration
        self.interaction_manager = interaction_manager

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
            self.interaction_manager.prompt_manager.get_prompt(
                "security_tools", "IDENTIFY_VULNERABLE_COMPONENT_PROMPT"
            )
        )

        cvss_instruct_prompt = self.interaction_manager.prompt_manager.get_prompt(
            "security_tools", "CVSS_INSTRUCT_PROMPT"
        )

        vulnerable_component = llm.predict(
            identify_vulnerable_component_prompt.format(
                vulnerability_data=vulnerability_data
            ),
            callbacks=self.interaction_manager.agent_callbacks,
        )

        cvss_evaluation = llm.predict(
            cvss_instruct_prompt.format(
                vulnerable_component=vulnerable_component,
                vulnerability_data=vulnerability_data,
            ),
            callbacks=self.interaction_manager.agent_callbacks,
        )

        return cvss_evaluation
