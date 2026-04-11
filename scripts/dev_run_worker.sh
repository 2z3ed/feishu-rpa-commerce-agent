#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Starting Celery Worker ==="

if [ -d "venv" ]; then
    source venv/bin/activate
fi

python -m celery -A app.workers.celery_app worker --loglevel=info