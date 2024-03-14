from fastapi import APIRouter, File, UploadFile
from typing import List
import logging


from src.api.shared.models.document_ingestion_model import DocumentIngestionModel
import src.workers.document_processing.app.document_ingestion_tasks as document_ingestion_tasks


router = APIRouter()


@router.post("/ingest")
async def ingest_documents(
    data: DocumentIngestionModel,
    files: List[UploadFile] = File(...),
):

    for file in data.files:
        file_location = f"/app/shared/{file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())

        # Hand off to Celery for processing each file separately
        document_ingestion_tasks.process_document_task.delay(
            active_collection_id=data.active_collection_id,
            overwrite_existing_files=data.overwrite_existing_files,
            split_documents=data.split_documents,
            create_summary_and_chunk_questions=data.create_summary_and_chunk_questions,
            summarize_document=data.summarize_document,
            chunk_size=data.chunk_size,
            chunk_overlap=data.chunk_overlap,
            user_id=data.user_id,
            file_path=file_location,
        )

    return {"message": "Documents are being processed"}
