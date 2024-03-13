from pydantic import BaseModel, Field

from src.shared.ai.prompts.query_helper import output_type_example


class DocumentChunkSummaryInput(BaseModel):
    chunk_text: str = Field(description="The chunk of text to be summarized")


class DocumentQuerySummaryRefineInput(BaseModel):
    text: str = Field(description="The chunk of text to be summarized")
    existing_answer: str = Field(description="The existing summary of the document")
    query: str = Field(description="The user's query")


class DocumentSummaryRefineInput(BaseModel):
    text: str = Field(description="The additional context to be added to the summary")
    existing_summary: str = Field(description="The existing summary of the document")


class DocumentSummaryOutput(BaseModel):
    summary: str = Field(description="Detailed and comprehensive summary.")


DocumentSummaryOutput = output_type_example(
    DocumentSummaryOutput(
        summary="The quick brown fox jumped over the lazy dog...",
    )
)(DocumentSummaryOutput)
