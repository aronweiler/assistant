# Dockerfile for the streamlit application

# Use the official Python 3.11 image as the base image
FROM python:3.11

# Set the working directory to /app inside the container
WORKDIR /app

# Pulling requirements in first so that we can cache the layer
COPY ./src/ui/app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/ui/app ./src/ui/app
COPY ./src/shared ./src/shared
COPY ./configurations ./configurations

# Inform Docker that the container listens on port 8500 at runtime
EXPOSE 8600

# Define the container's health check command
HEALTHCHECK CMD curl --fail http://localhost:8600/_stcore/health

# Set the container's entrypoint to the streamlit command, running the About.py script
ENTRYPOINT ["streamlit", "run", "src/ui/app/About.py", "--server.port=8600", "--server.address=0.0.0.0", "--server.fileWatcherType=none"]