from typing import List, Optional
from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class PlanningStageInput(BaseModel):
    system_prompt: str = Field(description="The system prompt")
    loaded_documents_prompt: str = Field(description="The loaded documents prompt")
    selected_repository_prompt: str = Field(description="The selected repository prompt")
    previous_tool_calls_prompt: str = Field(description="The previous tool calls prompt")
    available_tool_descriptions: str = Field(description="The available tool descriptions")
    chat_history_prompt: str = Field(description="The chat history prompt")
    user_query: str = Field(description="The user query to be analyzed")

class Step(BaseModel):
    step_num: int = Field(description="The step number")
    step_description: str = Field(description="The step description")
    tool: str = Field(description="The name of the tool to be used")

class PlanningStageOutput(BaseModel):
    preliminary_thoughts: str = Field(description="Comprehensive outline of the initial reasoning and decision-making process used to arrive at a plan using the available tools, or to issue a direct answer.")
    action: str = Field(description="The action to be taken. One of 'execute_steps', or 'answer'.")
    answer: Optional[str] = Field(description="The direct answer to the user query, if applicable.", default=None)
    steps: Optional[List[Step]] = Field(description="List of steps to be taken, if applicable.", default=None)

PlanningStageOutput = output_type_example(
    PlanningStageOutput(
        preliminary_thoughts="Comprehensive outline of the initial reasoning and decision-making process.",
        action="execute_steps or answer",
        answer="The direct answer to the user query, if applicable.",
        steps=[
            Step(
                step_num=1,
                step_description="The step description",
                tool="The name of the tool to be used",
            )
        ]
    )
)(PlanningStageOutput)