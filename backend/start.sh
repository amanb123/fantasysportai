#!/bin/bash
# Railway start script for FastAPI backend

# Use PORT environment variable from Railway, default to 8000
PORT=${PORT:-8000}

echo "Starting FastAPI server on port $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT
