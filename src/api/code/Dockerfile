# Code API
FROM assistant-api-base-image:latest

WORKDIR /app

# Pulling requirements in first so that we can cache the layer
COPY ./app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what you need for this specific service
COPY ./app ./

CMD ["uvicorn", "code_api:router", "--host", "0.0.0.0", "--port", "8103"]