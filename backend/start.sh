#!/bin/bash
# Railway start script for FastAPI backend

# Use PORT environment variable from Railway, default to 8000
PORT=${PORT:-8000}

echo "Starting FastAPI server on port $PORT..."

# Set PYTHONPATH to parent directory so imports work
export PYTHONPATH=/app

# Run from root directory with backend.main module
exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT
