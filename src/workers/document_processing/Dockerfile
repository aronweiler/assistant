# User API Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy only what you need for this specific service
COPY ./app ./

# Install any additional requirements specific to this service
RUN pip install --no-cache-dir -r requirements.txt

CMD ["celery", "-A", "document_ingestion_tasks", "worker", "--loglevel=info"]