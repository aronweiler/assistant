# User API Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Pulling requirements in first so that we can cache the layer
COPY ./src/api/user/app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what you need for this specific service
# Copy in what I need for the API
COPY ./src/api/user/app ./
COPY ./src/api/shared ./src/api/shared
COPY ./src/shared/database ./src/shared/database


CMD ["uvicorn", "user_api:router", "--host", "0.0.0.0", "--port", "8101"]