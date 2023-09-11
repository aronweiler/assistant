from typing import Any, List, Tuple, Union

from langchain.agents import Tool, AgentExecutor, BaseSingleActionAgent
from langchain.schema import AgentAction, AgentFinish

# Create an basic agent that takes a single input, runs it through a tool, and returns the output

class StubbingAgent(BaseSingleActionAgent):
    
    @property
    def input_keys(self):
        return ["input"]

    def plan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[AgentAction, AgentFinish]:
        """Given input, decided what to do.

        Args:
            intermediate_steps: Steps the LLM has taken to date,
                along with observations
            **kwargs: User inputs.

        Returns:
            Action specifying what tool to use.
        """
        return AgentAction(tool="Search", tool_input=kwargs["input"], log="")

    async def aplan(
        self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[AgentAction, AgentFinish]:
        """Given input, decided what to do.

        Args:
            intermediate_steps: Steps the LLM has taken to date,
                along with observations
            **kwargs: User inputs.

        Returns:
            Action specifying what tool to use.
        """
        return AgentAction(tool="Search", tool_input=kwargs["input"], log="")