# Document Ingestion API
FROM python:3.11-slim

WORKDIR /app

# TODO: Uncomment this when I get the containers all working
# Update the package list and install system dependencies (LibreOffice)
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     libreoffice \
#     software-properties-common \
#     && rm -rf /var/lib/apt/lists/*

# Copy only what you need for this specific service

# Pulling requirements in first so that we can cache the layer
COPY ./src/api/document/app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy in what I need for the API
COPY ./src/api/document/app ./
COPY ./src/workers/document_processing/app ./src/workers/document_processing/app


CMD ["uvicorn", "document_api:router", "--host", "0.0.0.0", "--port", "8102"]