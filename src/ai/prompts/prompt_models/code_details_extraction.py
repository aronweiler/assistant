from typing import List
from pydantic import BaseModel, Field


class CodeDetailsExtractionInput(BaseModel):
    code: str = Field(description="The code to be analyzed")

class CodeDetailsExtractionOutput(BaseModel):
    keywords: List[str] = Field(description="List of keywords")
    descriptions: List[str] = Field(description="List of descriptions")
    summary: str = Field(description="Detailed summary")