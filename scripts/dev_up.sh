#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Starting local development dependencies ==="

if ! command -v docker &> /dev/null; then
    echo "Error: docker is not installed"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "Error: docker compose is not installed"
    exit 1
fi

echo "Starting PostgreSQL, Redis, Milvus..."
docker compose -f docker-compose.dev.yml up -d

echo "Waiting for services to be ready..."
sleep 5

echo "=== Checking service health ==="
docker compose -f docker-compose.dev.yml ps

echo ""
echo "=== Services started ==="
echo "PostgreSQL: localhost:5432"
echo "Redis: localhost:6379"
echo "Milvus: localhost:19530"
echo ""
echo "To stop: docker compose -f docker-compose.dev.yml down"
