from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class DocumentChunkSummaryInput(BaseModel):
    chunk_text: str = Field(description="the chunk of text to be summarized")

class DocumentSummaryRefineInput(BaseModel):
    text: str = Field(description="the chunk of text to be summarized")
    existing_answer: str = Field(description="the existing summary of the chunk of text")
    query: str = Field(description="the user's query")

class DocumentChunkSummaryOutput(BaseModel):
    summary: str = Field(
        description="Detailed and comprehensive summary of the chunk of text"
    )


DocumentChunkSummaryOutput = output_type_example(
    DocumentChunkSummaryOutput(
        summary="Detailed and comprehensive summary...",
    )
)(DocumentChunkSummaryOutput)
