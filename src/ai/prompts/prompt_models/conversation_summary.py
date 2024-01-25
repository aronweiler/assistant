from pydantic import BaseModel, Field


class ConversationSummaryInput(BaseModel):
    user_query: str = Field(description="user query")

class ConversationSummaryOutput(BaseModel):
    summary: str = Field(description="Short summary")
