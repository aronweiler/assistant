
from typing import List
from pydantic import BaseModel, Field


class EvaluationInput(BaseModel):
    chat_history_prompt: str = Field(description="The chat history prompt")
    user_query: str = Field(description="The user query to be analyzed")
    previous_ai_response: str = Field(description="The previous AI's response")
    tool_history: str = Field(description="The tool history")
    available_tool_descriptions: str = Field(description="The available tool descriptions")
    loaded_documents_prompt: str = Field(description="The loaded documents prompt")
    selected_repository_prompt: str = Field(description="The selected repository prompt")


class EvaluationOutput(BaseModel):
    evaluation: str = Field(description="The descriptive evaluation of the AI's response")
    score: float = Field(description="The score for the evaluation")
