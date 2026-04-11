#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Starting Feishu Long Connection Listener ==="

if [ -d "venv" ]; then
    source venv/bin/activate
fi

python -m app.services.feishu.runner