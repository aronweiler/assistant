# Document processing worker
FROM python:3.11-slim

WORKDIR /app

COPY ./src/workers/document_processing/app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what is needed for this specific service
COPY ./src/workers/document_processing/app ./src/workers/document_processing/app
COPY ./src/shared ./src/shared

WORKDIR /app/src/workers/document_processing/app

CMD ["celery", "-A", "celery_worker", "worker", "--loglevel=info"]