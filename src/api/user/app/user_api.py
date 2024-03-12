from fastapi import APIRouter, UploadFile, File
from typing import List

router = APIRouter()

@router.get("/test")
async def test():
    return {"message": "Hello World"}