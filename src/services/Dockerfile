FROM python:3.11-slim

WORKDIR /app

# Update the package list and install system dependencies (LibreOffice)
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     libreoffice \
#     software-properties-common \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY / ./

CMD ["uvicorn", "document_ingestion:router", "--host", "0.0.0.0", "--port", "8000"]