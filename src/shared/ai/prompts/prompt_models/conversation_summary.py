from pydantic import BaseModel, Field

from src.shared.ai.prompts.query_helper import output_type_example


class ConversationSummaryInput(BaseModel):
    user_query: str = Field(description="user query")


class ConversationSummaryOutput(BaseModel):
    summary: str = Field(description="Short summary")


ConversationSummaryOutput = output_type_example(
    ConversationSummaryOutput(
        summary="Short summary goes here...",
    )
)(ConversationSummaryOutput)
