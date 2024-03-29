from typing import List, Optional
from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class ToolUseInput(BaseModel):
    system_prompt: str = Field(description="The system prompt")
    loaded_documents_prompt: str = Field(description="The loaded documents prompt")
    selected_repository_prompt: str = Field(
        description="The selected repository prompt"
    )
    previous_tool_calls_prompt: str = Field(
        description="The previous tool calls prompt"
    )
    user_query: str = Field(description="The user query to be analyzed")
    chat_history_prompt: str = Field(description="The chat history prompt")
    helpful_context: str = Field(description="Helpful context for the tool's use")
    tool_name: str = Field(description="The name of the tool to be used")
    tool_details: str = Field(description="Details of the tool to be used")
    tool_use_description: str = Field(description="Description of the tool's use")


class ToolUseRetryInput(BaseModel):
    system_prompt: str = Field(description="The system prompt")
    loaded_documents_prompt: str = Field(description="The loaded documents prompt")
    selected_repository_prompt: str = Field(
        description="The selected repository prompt"
    )
    previous_tool_calls_prompt: str = Field(
        description="The previous tool calls prompt"
    )
    user_query: str = Field(description="The user query to be analyzed")
    chat_history_prompt: str = Field(description="The chat history prompt")
    failed_tool_attempts: str = Field(description="The failed tool attempts")
    available_tool_descriptions: str = Field(
        description="The available tool descriptions"
    )


class ToolUseOutput(BaseModel):
    tool_use_description: str = Field(description="Description of the tool's use")
    tool: str = Field(description="The name of the tool to be used")
    tool_args: Optional[dict] = Field(
        description="The arguments to be used with the tool (from the tool use description)",
        default={},
    )
    
ToolUseOutput = output_type_example(
    ToolUseOutput(
        tool_use_description="Description of the tool's use",
        tool="The name of the tool to be used",
        tool_args={"arg1": "value1", "arg2": "value2"},
    )
)(ToolUseOutput)    


class AdditionalToolUseInput(BaseModel):
    system_prompt: str = Field(description="The system prompt")
    loaded_documents_prompt: str = Field(description="The loaded documents prompt")
    selected_repository_prompt: str = Field(
        description="The selected repository prompt"
    )
    previous_tool_calls_prompt: str = Field(
        description="The previous tool calls prompt"
    )
    chat_history_prompt: str = Field(description="The chat history prompt")
    user_query: str = Field(description="The user query to be analyzed")
    tool_name: str = Field(description="The name of the tool to be used")
    tool_use_description: str = Field(description="Description of the tool's use")
    additional_tool_uses: int = Field(
        description="The number of additional tool uses to be generated"
    )
    initial_tool_use: str = Field(
        description="The initial tool use JSON object to be used as a starting point"
    )


class AdditionalToolUseOutput(BaseModel):
    additional_tool_use_objects: List[ToolUseOutput] = Field(
        description="A list of the additional tool use JSON objects.  Ensure that the tool use JSON objects are unique, and that they are complete (include all required arguments)."
    )

AdditionalToolUseOutput = output_type_example(
    AdditionalToolUseOutput(
        additional_tool_use_objects=[
            ToolUseOutput(
                tool_use_description="Description of the tool's use",
                tool="The name of the tool to be used",
                tool_args={"arg1": "value1", "arg2": "value2"},
            )
        ]
    )
)(AdditionalToolUseOutput)    