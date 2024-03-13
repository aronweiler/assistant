from typing import List, Optional, Union
from pydantic import BaseModel, Field

from src.shared.ai.prompts.query_helper import output_type_example


class CodeReviewInput(BaseModel):
    code_review_instructions: Optional[str] = Field(
        description="Instructions for the code review"
    )
    additional_instructions: Optional[str] = Field(
        description="Additional instructions for the code review"
    )
    code_metadata: dict = Field(description="Metadata about the code")
    code: str = Field(description="Code to review")

    # diff_or_file_review_prompt: str = Field(
    #     description="The diff or the file review prompt to use"
    # )


class DiffComment(BaseModel):
    add_line_start: Optional[int] = Field(
        description="The starting line number for an add (+) line that this comment corresponds to (null if none)"
    )
    add_line_end: Optional[int] = Field(
        description="The ending line number for an add (+) line that this comment corresponds to (null if none)"
    )
    remove_line_start: Optional[int] = Field(
        description="The starting line number for a remove (-) line that this comment corresponds to (null if none)"
    )
    remove_line_end: Optional[int] = Field(
        description="The ending line number for a remove (-) line that this comment corresponds to (null if none)"
    )
    comment: str = Field(description="Comment in markdown")
    needs_change: bool = Field(
        description="True if modifications are recommended, false otherwise"
    )
    original_code_snippet: str = Field(description="The original code snippet")
    suggested_code_snippet: str = Field(description="The suggested code snippet")


class FileComment(BaseModel):
    start: Optional[int] = Field(
        description="The starting line number for a line that this comment corresponds to (null if none)"
    )
    end: Optional[int] = Field(
        description="The ending line number for a line that this comment corresponds to (null if none)"
    )
    comment: str = Field(description="Comment in markdown")
    needs_change: bool = Field(
        description="True if modifications are recommended, false otherwise"
    )
    original_code_snippet: str = Field(description="The original code snippet")
    suggested_code_snippet: str = Field(description="The suggested code snippet")


class CodeReviewOutput(BaseModel):
    language: str = Field(description="Programming language being reviewed")
    metadata: dict = Field(
        description="Metadata about the code snippet (from the original prompt)"
    )
    thoughts: str = Field(
        description="a single string containing your thoughts on the code, and any comments you may have about how you reviewed it"
    )
    comments: List[Union[DiffComment, FileComment]] = Field(
        description="A list of comments on the code"
    )


CodeReviewOutput = output_type_example(
    CodeReviewOutput(
        language="python",
        metadata={"file_name": "foo.py"},
        thoughts="I reviewed this code by doing X, Y, and Z",
        comments=[
            DiffComment(
                add_line_start=1,
                add_line_end=1,
                remove_line_start=None,
                remove_line_end=None,
                comment="This is a comment",
                needs_change=True,
                original_code_snippet="foo",
                suggested_code_snippet="bar",
            ),
            FileComment(
                start=1,
                end=1,
                comment="This is a comment",
                needs_change=True,
                original_code_snippet="foo",
                suggested_code_snippet="bar",
            ),
        ],
    )
)(CodeReviewOutput)
