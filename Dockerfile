# Dockerfile for the streamlit application

FROM python:latest

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libreoffice \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Install the requirements
COPY requirements.txt /app

RUN pip3 install -r requirements.txt

# Copy the local files to the image
# This copies everything over after the pip install so that we don't have to
# reinstall the dependencies every time we make a change to the code
COPY . /app

EXPOSE 8500

HEALTHCHECK CMD curl --fail http://localhost:8500/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit_ui.py", "--server.port=8500", "--server.address=0.0.0.0"]