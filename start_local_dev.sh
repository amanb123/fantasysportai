#!/bin/bash

# Start Local Development Environment

echo "🏀 Starting Fantasy Basketball League - Local Development Mode"
echo "=================================================="
echo "Backend: http://localhost:3002"
echo "Frontend: Run 'npm run dev' in frontend/ folder"
echo "=================================================="

# Kill any existing backend processes
pkill -9 -f "run_backend.py" 2>/dev/null
pkill -9 -f "uvicorn" 2>/dev/null
sleep 2

# Ensure we're using the virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv .venv"
    exit 1
fi

# Export environment variables
export NBA_STATS_ENABLED=true
export nba_stats_enabled=true
export CORS_ORIGINS="http://localhost:3000,http://localhost:5173"

# Start backend
echo "Starting backend server..."
.venv/bin/python run_backend.py > backend.log 2>&1 &

# Wait for backend to start
sleep 3

# Check if backend started successfully
if curl -s http://localhost:3002/health > /dev/null; then
    echo "✅ Backend started successfully at http://localhost:3002"
    echo "📊 Health check: http://localhost:3002/health"
    echo "📝 API docs: http://localhost:3002/docs"
    echo ""
    echo "To view logs: tail -f backend.log"
    echo "To stop: pkill -f run_backend.py"
else
    echo "❌ Backend failed to start. Check backend.log for errors"
    tail -20 backend.log
    exit 1
fi
