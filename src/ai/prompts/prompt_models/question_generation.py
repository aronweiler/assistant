from typing import List
from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class QuestionGenerationInput(BaseModel):
    document_text: str = Field(description="The chunk of document text to be analyzed")
    number_of_questions: int = Field(description="Number of questions to be generated")


class QuestionGenerationOutput(BaseModel):
    questions: List[str] = Field(description="List of questions")

QuestionGenerationOutput = output_type_example(
    QuestionGenerationOutput(
        questions=["question1", "question2"],
    )
)(QuestionGenerationOutput)