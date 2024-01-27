from typing import Optional
from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class CodeRefactorInput(BaseModel):
    code_refactor_instructions: Optional[str] = Field(
        description="Instructions for the code refactor"
    )
    additional_instructions: Optional[str] = Field(
        description="Additional instructions for the code refactor"
    )
    code_metadata: dict = Field(description="Metadata about the code")
    code: str = Field(description="Code to refactor")
    


class CodeRefactorOutput(BaseModel):
    language: str = Field(description="Programming language being refactored")
    metadata: dict = Field(
        description="Metadata about the code snippet (from the original prompt)"
    )
    thoughts: str = Field(
        description="a single string containing your thoughts on the code, and any comments you may have about how you refactored it"
    )
    refactored_code: str = Field(
        description="A single string containing the entire refactored code- do not abbreviate or shorten the output code.  This should always be a single string, not a list, with no line-number annotations or other extraneous information.  The code should be formatted exactly as it would be if you were to copy and paste it into a code editor."
    )


CodeRefactorOutput = output_type_example(
    CodeRefactorOutput(
        language="python",
        metadata={"file_name": "foo.py"},
        thoughts="I refactored this code by doing X, Y, and Z",
        refactored_code="def foo():\n    print('hello world')",
    )
)(CodeRefactorOutput)
