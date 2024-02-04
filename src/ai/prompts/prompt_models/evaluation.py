
from typing import List
from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class EvaluationInput(BaseModel):
    chat_history_prompt: str = Field(description="The chat history prompt")
    user_query: str = Field(description="The user query to be analyzed")
    previous_ai_response: str = Field(description="The previous AI's response")
    tool_history: str = Field(description="The tool history")
    available_tool_descriptions: str = Field(description="The available tool descriptions")
    loaded_documents_prompt: str = Field(description="The loaded documents prompt")
    selected_repository_prompt: str = Field(description="The selected repository prompt")
    user_settings_prompt: str = Field(description="The user settings prompt")


class EvaluationOutput(BaseModel):
    evaluation: str = Field(description="The descriptive evaluation of the AI's response")
    score: float = Field(description="The score for the evaluation")

EvaluationOutput = output_type_example(
    EvaluationOutput(
        evaluation="The descriptive evaluation of the AI's response",
        score=0.5,
    )
)(EvaluationOutput)