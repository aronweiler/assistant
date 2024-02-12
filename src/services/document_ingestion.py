from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from typing import List
import asyncio

app = FastAPI()

# Placeholder for your document loading logic
async def process_document(file_path: str):
    # Integrate your document_loader.py logic here
    pass

# Placeholder for your database interaction
async def store_document_in_db(document_data):
    # Integrate your documents.py logic here
    pass

@app.post("/ingest")
async def ingest_documents(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...)):
    for file in files:
        file_location = f"/tmp/{file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())
        # Process each document in the background
        background_tasks.add_task(process_document, file_location)

    return {"message": "Documents are being processed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)