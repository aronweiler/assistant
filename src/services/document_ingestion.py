# document_ingestion.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from .documents.document_ingestion_tasks import process_document_task

router = APIRouter()


@router.post("/ingest")
async def ingest_documents(files: List[UploadFile] = File(...)):    
    for file in files:
        file_location = f"/tmp/{file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())
        # Hand off to Celery for processing
        process_document_task.delay(file_location)
        
    return {"message": "Documents are being processed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)