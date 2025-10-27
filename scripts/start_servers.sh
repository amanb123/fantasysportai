#!/bin/bash

# Kill any existing processes
echo "Stopping any existing servers..."
pkill -9 -f "vite" 2>/dev/null
pkill -9 -f "uvicorn" 2>/dev/null
lsof -ti:3002 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 2

# Start backend
echo "Starting backend on port 3002..."
cd /Users/aman.buddaraju/fantasy-basketball-league
source .venv/bin/activate
python3 run_backend.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend on port 3000..."
cd /Users/aman.buddaraju/fantasy-basketball-league/frontend
npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to start
sleep 3

echo ""
echo "✅ Both servers started!"
echo "Backend:  http://localhost:3002 (PID: $BACKEND_PID)"
echo "Frontend: http://localhost:3000 (PID: $FRONTEND_PID)"
echo ""
echo "To view logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend/frontend.log"
echo ""
echo "To stop servers:"
echo "  pkill -f vite && pkill -f uvicorn"
