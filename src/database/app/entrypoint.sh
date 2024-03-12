#!/bin/bash
# Start the PostgreSQL server in the background using the original entrypoint script
docker-entrypoint.sh postgres &

# Wait for PostgreSQL to become available
while ! pg_isready -h localhost; do
    echo "Waiting for PostgreSQL to become available..."
    sleep 10    
done

# Run your Python script
python3 /app/creation_utilities.py

# Now, instead of calling `exec docker-entrypoint.sh postgres` again at the end,
# which would attempt to start another instance of the server,
# simply wait indefinitely to keep the container running.
# This is useful if the container's main process is the PostgreSQL server started above.
tail -f /dev/null