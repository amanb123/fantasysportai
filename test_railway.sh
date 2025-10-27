#!/bin/bash
# Test Railway Backend Deployment
# Usage: ./test_railway.sh https://your-app.up.railway.app

BACKEND_URL="${1:-https://your-app.up.railway.app}"

echo "🧪 Testing Railway Backend: $BACKEND_URL"
echo ""

# Test 1: Health Check
echo "1️⃣ Testing root endpoint..."
curl -s "$BACKEND_URL/" | head -20
echo ""

# Test 2: Docs endpoint
echo "2️⃣ Testing API docs..."
curl -s -o /dev/null -w "Status: %{http_code}\n" "$BACKEND_URL/docs"
echo ""

# Test 3: Check if Redis is connected
echo "3️⃣ Testing an API endpoint (this might fail without env vars, that's ok)..."
curl -s -o /dev/null -w "Status: %{http_code}\n" "$BACKEND_URL/api/health" || echo "Health endpoint not configured"
echo ""

echo "✅ If you see HTML/JSON responses above, your backend is deployed!"
echo ""
echo "📝 Next steps:"
echo "   1. Set up Redis on Railway (if not done)"
echo "   2. Add environment variables to Railway"
echo "   3. Update Vercel frontend with this URL"
