from typing import List
from pydantic import BaseModel, Field


class QuestionGenerationInput(BaseModel):
    chunk_text: str = Field(description="The chunk of text to be analyzed")
    number_of_questions: int = Field(description="Number of questions to be generated")


class QuestionGenerationOutput(BaseModel):
    questions: List[str] = Field(description="List of questions")
