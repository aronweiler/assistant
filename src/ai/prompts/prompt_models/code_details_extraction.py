from typing import List
from pydantic import BaseModel, Field


class CodeDetailsExtractionInput(BaseModel):
    code: str = Field(description="The code to be analyzed")

class CodeDetailsExtractionOutput(BaseModel):
    keywords: List[str] = Field(description="List of keywords that can be extracted from this code.")
    descriptions: List[str] = Field(description="List of descriptions that can be extracted from this code.")
    summary: str = Field(description="Detailed summary of what this code does.")