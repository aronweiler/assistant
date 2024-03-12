# User API Dockerfile
FROM assistant-api-base-image:latest

WORKDIR /app

# Copy only what you need for this specific service
COPY ./app ./

# Install any additional requirements specific to this service
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "user_api:router", "--host", "0.0.0.0", "--port", "8101"]