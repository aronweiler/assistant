# Document Ingestion API
FROM assistant-api-base-image:latest

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
COPY ./app ./

# Install any additional requirements specific to this service
RUN pip install --no-cache-dir -r requirements.txt





CMD ["uvicorn", "document_api:router", "--host", "0.0.0.0", "--port", "8102"]