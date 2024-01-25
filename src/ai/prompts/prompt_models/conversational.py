from pydantic import BaseModel, Field


class ConversationalInput(BaseModel):
    system_prompt: str = Field(description="system prompt")
    system_information: str = Field(description="system information")
    user_name: str = Field(description="user name")
    user_email: str = Field(description="user email")
    chat_history: str = Field(description="chat history")
    user_query: str = Field(description="user query")


class ConversationalOutput(BaseModel):
    answer: str = Field(description="Complete and comprehensive answer to the user's query")
