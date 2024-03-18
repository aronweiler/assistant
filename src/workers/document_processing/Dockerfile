# Document processing worker
FROM python:3.11-slim

WORKDIR /app

# Update the package list and install system dependencies, specifically LibreOffice
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libreoffice \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

COPY ./src/workers/document_processing/app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what is needed for this specific service
COPY ./src/workers/document_processing/app ./src/workers/document_processing/app
COPY ./src/shared ./src/shared

WORKDIR /app/src/workers/document_processing/app

# TODO: Remove this after moving these settings to the database
COPY ./configurations ./configurations

CMD ["celery", "-A", "celery_worker", "worker", "--loglevel=info"]