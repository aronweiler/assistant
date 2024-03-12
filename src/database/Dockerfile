FROM ankane/pgvector

# Install locales package and generate en_US.UTF-8
RUN apt-get update && apt-get install -y locales && \
    sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8

# Install Python, pip, and venv
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv

# Create a virtual environment
RUN python3 -m venv /venv

# Activate the virtual environment
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

# Install Python dependencies within the virtual environment
# Pulling requirements in first so that we can cache the layer
COPY ./app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

#CMD ["python3", "creation_utilities.py"]
#CMD python3 creation_utilities.py && tail -f /dev/null
#CMD pg_isready -h localhost -p 5433 && python3 creation_utilities.py && tail -f /dev/null
# Set the entrypoint script to be executed
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["postgres"]