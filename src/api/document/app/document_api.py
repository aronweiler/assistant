from fastapi import APIRouter, File, UploadFile
from typing import List
import logging


import src.workers.document_processing.app.document_ingestion_tasks as document_ingestion_tasks


router = APIRouter()


@router.post("/ingest")
async def ingest_documents(
    active_collection_id: int,
    overwrite_existing_files: bool,
    split_documents: bool,
    create_summary_and_chunk_questions: bool,
    summarize_document: bool,
    chunk_size: int,
    chunk_overlap: int,
    user_id: int,
    files: List[UploadFile] = File(...),
):
    raise NotImplementedError("This endpoint is not implemented- sending this task directly to celery from the UI")

    # for file in files:
    #     file_location = f"/app/shared/{file.filename}"
    #     with open(file_location, "wb+") as file_object:
    #         file_object.write(file.file.read())

    #     # Hand off to Celery for processing each file separately
    #     document_ingestion_tasks.process_document_task.delay(
    #         active_collection_id=active_collection_id,
    #         overwrite_existing_files=overwrite_existing_files,
    #         split_documents=split_documents,
    #         create_summary_and_chunk_questions=create_summary_and_chunk_questions,
    #         summarize_document=summarize_document,
    #         chunk_size=chunk_size,
    #         chunk_overlap=chunk_overlap,
    #         user_id=user_id,
    #         file_path=file_location,
    #     )

    # return {"message": "Documents are being processed"}
