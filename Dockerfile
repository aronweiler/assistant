# Dockerfile for the streamlit application

FROM python:latest

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy your local files
COPY . /app
COPY ./src/runners/ui/streamlit_ui.py streamlit_ui.py

RUN pip3 install -r requirements.txt

EXPOSE 8500

HEALTHCHECK CMD curl --fail http://localhost:8500/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit_ui.py", "--server.port=8500", "--server.address=0.0.0.0"]