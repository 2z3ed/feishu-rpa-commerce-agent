#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Starting FastAPI ==="

if [ -d "venv" ]; then
    source venv/bin/activate
fi

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload