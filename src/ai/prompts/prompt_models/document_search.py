from typing import List, Optional
from pydantic import BaseModel, Field

from src.ai.prompts.query_helper import output_type_example


class DocumentSearchInput(BaseModel):
    summaries: List[str] = Field(
        description="The summaries of the document to search through."
    )
    question: str = Field(description="The question to answer.")


class DocumentSearchOutput(BaseModel):
    answer: str = Field(description="The answer to the question.")
    relevant_text_segments: Optional[List[str]] = Field(
        description="The relevant text segments (verbatim) from the document that helped to answer the question."
    )
    document_page_or_line: Optional[str] = Field(
        description="The page or line of the document that the relevant text is found on."
    )
    document_name: str = Field(
        description="The name of the document that the relevant text is found in."
    )
    document_id: int = Field(
        description="The id of the document that the relevant text is found in."
    )


DocumentSearchOutput = output_type_example(
    DocumentSearchOutput(
        answer="The answer to the question.",
        relevant_text_segments=["relevant text segment 1", "relevant text segment 2"],
        document_page_or_line="Page 1",
        document_name="document name",
        document_id=23,
    )
)(DocumentSearchOutput)