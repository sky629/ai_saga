#!/bin/bash
# run_local.sh - Run the AI Saga backend locally

# 1. Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Please start Docker Desktop."
  exit 1
fi

# 2. Ensure Infrastructure is running in Docker
echo "Checking infrastructure..."
docker compose up -d postgres redis kafka
if [ $? -ne 0 ]; then
    echo "Error: Failed to start infrastructure."
    exit 1
fi

# Wait for Postgres to be ready
echo "Waiting for Postgres..."
until nc -z localhost 5432; do
  echo "  - Postgres not ready... waiting"
  sleep 2
done

# 3. Stop the Dockerized App (to avoid port conflicts)
echo "Stopping Dockerized app..."
docker compose stop app

# 3. Load Environment Variables from .env
if [ -f .env ]; then
  echo "Loading .env..."
  export $(grep -v '^#' .env | xargs)
else
  echo "Error: .env file not found!"
  exit 1
fi

# 4. Override Hosts for Localhost Access
echo "Configuring for Localhost..."
export POSTGRES_HOST=localhost
export REDIS_URL=redis://localhost:6379
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# 5. Run with uv
echo "Starting Application..."
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
