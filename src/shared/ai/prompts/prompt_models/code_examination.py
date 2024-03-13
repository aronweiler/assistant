from typing import List, Optional
from pydantic import BaseModel, Field

from src.shared.ai.prompts.query_helper import output_type_example


class GetRelevantSnippetsInput(BaseModel):
    file_id: int = Field(description="The file ID")
    file_name: str = Field(description="The file name")
    code: str = Field(description="The code to be analyzed")
    code_description: str = Field(description="The code description")


class RelevantSnippet(BaseModel):
    file_id: Optional[int] = Field(description="The file ID")
    file_name: str = Field(description="The file name")
    start_line: Optional[int] = Field(description="The start line of the code snippet")
    end_line: Optional[int] = Field(description="The end line of the code snippet")
    code: str = Field(description="The relevant code snippet")


class GetRelevantSnippetsOutput(BaseModel):
    relevant_snippets: List[RelevantSnippet] = Field(
        description="List of relevant code snippets"
    )


GetRelevantSnippetsOutput = output_type_example(
    GetRelevantSnippetsOutput(
        relevant_snippets=[
            RelevantSnippet(
                file_id=1,
                file_name="file_name.py",
                start_line=1,
                end_line=2,
                code="relevant code snippet",
            )
        ]
    )
)(GetRelevantSnippetsOutput)


class IdentifyLikelyFilesInput(BaseModel):
    user_query: str = Field(description="The user's query")
    summaries: List[str] = Field(description="List of file summaries")


class IdentifyLikelyFilesOutput(BaseModel):
    likely_files: List[int] = Field(
        description="List of file IDs that are likely to contain the relevant code"
    )


IdentifyLikelyFilesOutput = output_type_example(
    IdentifyLikelyFilesOutput(likely_files=[1, 2, 3])
)(IdentifyLikelyFilesOutput)


class AnswerQueryInput(BaseModel):
    user_query: str = Field(description="The user's query")
    code: str = Field(description="The code to be analyzed")


class AnswerQueryOutput(BaseModel):
    answer: str = Field(description="The answer to the user's query")
    code_snippets: List[RelevantSnippet] = Field(
        description="List of relevant code snippets"
    )
    file_ids: List[int] = Field(
        description="List of file IDs that contain a possible answer to the user's query"
    )

AnswerQueryOutput = output_type_example(
    AnswerQueryOutput(
        file_ids=[1, 2, 3],
        code_snippets=[
            RelevantSnippet(
                file_id=1,
                file_name="file_name.py",
                start_line=1,
                end_line=2,
                code="relevant code snippet",
            )
        ],
        answer="The answer to the user's query",
    )
)(AnswerQueryOutput)