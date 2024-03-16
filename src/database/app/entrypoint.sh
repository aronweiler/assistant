#!/bin/bash
# Start the PostgreSQL server in the background using the original entrypoint script
docker-entrypoint.sh postgres &

# Fetch POSTGRES_HOST and POSTGRES_PORT from the environment
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-postgres}

# Wait for PostgreSQL to become available
while ! pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d "postgres"; do
    echo "Waiting for PostgreSQL to become available..."
    sleep 10    
done

# Run the creation_utilities.py script to create the database, tables, and default data
echo "Running the creation utilities..."
python3 src/database/app/creation_utilities.py
echo "Creation utilities complete."

# Now, instead of calling `exec docker-entrypoint.sh postgres` again at the end,
# which would attempt to start another instance of the server,
# we simply wait indefinitely to keep the container running.
tail -f /dev/null