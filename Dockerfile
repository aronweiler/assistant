# Dockerfile for the streamlit application

# Use the official Python 3.11 image as the base image
FROM python:3.11

# Set the working directory to /app inside the container
WORKDIR /app

# Update the package list and install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libreoffice \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy the Python requirements file into the container at /app
COPY requirements-ui.txt /app
RUN pip3 install -r requirements-ui.txt

# Copy the Python requirements file into the container at /app
COPY requirements-services.txt /app
RUN pip3 install -r requirements-services.txt

# Copy the Discord requirements file into the container at /app
COPY discord_requirements.txt /app
RUN pip3 install -r discord_requirements.txt

# Copy the local files to the image
# This copies everything over after the pip install so that we don't have to
# reinstall the dependencies every time we make a change to the code
COPY . /app

# Inform Docker that the container listens on port 8500 at runtime
EXPOSE 8500

# Define the container's health check command
HEALTHCHECK CMD curl --fail http://localhost:8500/_stcore/health

# Set the container's entrypoint to the streamlit command, running the About.py script
ENTRYPOINT ["streamlit", "run", "About.py", "--server.port=8500", "--server.address=0.0.0.0", "--server.fileWatcherType=none"]