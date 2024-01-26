from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class DocumentChunkSummaryInput(BaseModel):
    chunk_text: str = Field(description="the chunk of text to be summarized")


class DocumentChunkSummaryOutput(BaseModel):
    summary: str = Field(
        description="Detailed and comprehensive summary of the chunk of text"
    )


DocumentChunkSummaryOutput = output_type_example(
    DocumentChunkSummaryOutput(
        summary="Detailed and comprehensive summary...",
    )
)(DocumentChunkSummaryOutput)
