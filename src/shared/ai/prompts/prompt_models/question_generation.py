from typing import List
from pydantic import BaseModel, Field

from src.shared.ai.prompts.query_helper import output_type_example


class QuestionGenerationInput(BaseModel):
    document_text: str = Field(description="The chunk of document text to be analyzed")
    number_of_questions: int = Field(description="Number of questions to be generated")


class QuestionGenerationOutput(BaseModel):
    summary: str = Field(description="Summary of the document chunk")
    questions: List[str] = Field(description="List of questions that could be answered using the document chunk")

QuestionGenerationOutput = output_type_example(
    QuestionGenerationOutput(
        summary="Detailed summary",
        questions=["question1", "question2"],
    )
)(QuestionGenerationOutput)