#!/bin/bash

# Script to start both backend and frontend servers

echo "🚀 Starting Fantasy Basketball League servers..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "uvicorn backend.main" 2>/dev/null
pkill -f "vite --port 3000" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 2

# Verify ports are free
if lsof -ti:3002 >/dev/null 2>&1; then
    echo "⚠️  Port 3002 still in use, forcefully killing..."
    kill -9 $(lsof -ti:3002) 2>/dev/null
    sleep 1
fi

if lsof -ti:3000 >/dev/null 2>&1; then
    echo "⚠️  Port 3000 still in use, forcefully killing..."
    kill -9 $(lsof -ti:3000) 2>/dev/null
    sleep 1
fi

echo "✓ Ports cleared"
echo ""

# Start backend in background
echo "📡 Starting backend on port 3002..."
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 3002 --reload > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait a moment for backend to start
sleep 2

# Start frontend in background
echo "🎨 Starting frontend on port 3000..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "Frontend started with PID: $FRONTEND_PID"

echo ""
echo "✅ Both servers are running!"
echo "📊 Backend: http://localhost:3002"
echo "🌐 Frontend: http://localhost:3000"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "🛑 To stop servers:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop monitoring (servers will keep running)"
echo ""

# Keep script running and show combined logs
tail -f backend.log frontend.log
