from typing import List
from pydantic import BaseModel, Field


class AnswerInput(BaseModel):
    user_query: str = Field(description="The user query to be analyzed")
    chat_history: str = Field(description="The chat history")
    helpful_context: str = Field(description="The helpful context")

class AnswerOutput(BaseModel):
    status: str = Field(description="Status of the answer- either 'success' or 'failure'.")
    answer: str = Field(description="The answer to the user query, or explanation of why the answer could not be found. (markdown format for display)")
    suggestions: List[str] = Field(description="List of suggestions on how to resolve the query.")