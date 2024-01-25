from pydantic import BaseModel, Field


class DocumentChunkSummaryInput(BaseModel):
    chunk_text: str = Field(description="the chunk of text to be summarized")


class DocumentChunkSummaryOutput(BaseModel):
    summary: str = Field(description="Detailed and comprehensive summary of the chunk of text")
