from typing import List, Optional
from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class AnswerInput(BaseModel):
    user_query: str = Field(description="The user query to be analyzed")
    chat_history: str = Field(description="The chat history")
    helpful_context: str = Field(description="The helpful context")
    rephrase_answer_instructions_prompt: Optional[str] = Field(
        description="Use this prompt to rephrase the answer, if necessary."
    )


class AnswerOutput(BaseModel):
    status: str = Field(
        description="Status of the answer- 'success' if you could answer the query using the provided context, or 'failure' if you cannot."
    )
    answer: str = Field(
        description="The answer to the user query, or explanation of why the answer could not be found."
    )
    disclaimer: Optional[str] = Field(
        description="Place your disclaimer here any time you have a disclaimer to be shown to the user about this answer."
    )
    # suggestions: List[str] = Field(description="List of suggestions on how to resolve the query.")


AnswerOutput = output_type_example(
    AnswerOutput(
        status="success",
        answer="The answer to the user query, or explanation of why the answer could not be found.",
        disclaimer="Any disclaimer to be shown to the user about this answer.",
    )
)(AnswerOutput)
