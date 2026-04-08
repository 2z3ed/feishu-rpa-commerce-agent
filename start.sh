#!/bin/bash

echo "Feishu RPA Commerce Agent - Development Setup"
echo "============================================="

echo "1. Creating .env file from .env.example..."
cp .env.example .env

if [ "$1" == "docker" ]; then
    echo "2. Starting Docker Compose..."
    docker-compose up -d
    echo "3. Docker containers started successfully!"
    echo "   - API: http://localhost:8000"
    echo "   - PostgreSQL: localhost:5432"
    echo "   - Redis: localhost:6379"
    echo "   - Milvus: localhost:19530"
    
    echo "4. Checking container status..."
    docker-compose ps
    
else
    echo "2. Installing dependencies..."
    pip install -r requirements.txt
    
    echo "3. Starting development server..."
    uvicorn src.api.main:app --reload
fi