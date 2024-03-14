from pydantic import BaseModel


class DocumentIngestionModel(BaseModel):
    active_collection_id: int
    overwrite_existing_files: bool
    split_documents: bool
    create_summary_and_chunk_questions: bool
    summarize_document: bool
    chunk_size: int
    chunk_overlap: int
    user_id: int
    