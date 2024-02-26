from typing import Optional
from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class ConversationalInput(BaseModel):
    system_prompt: str = Field(description="system prompt")
    system_information: str = Field(description="system information")
    user_name: str = Field(description="user name")
    user_email: str = Field(description="user email")
    chat_history: str = Field(description="chat history")
    user_query: str = Field(description="user query")


class ConversationalOutput(BaseModel):
    answer: str = Field(
        description="Complete and comprehensive answer to the user's query"
    )

    disclaimer: Optional[str] = Field(
        description="Place your disclaimer here any time you have a disclaimer to be shown to the user about this answer."
    )


ConversationalOutput = output_type_example(
    ConversationalOutput(
        answer="Example answer to the user's query",
        disclaimer="Any disclaimer to be shown to the user about this answer.",
    )
)(ConversationalOutput)
