#!/bin/bash
# Railway Cron Job - Cache Warmup
# This script is called by Railway's cron service every 5 minutes

# Get the backend URL (should be set as environment variable in Railway)
BACKEND_URL="${RAILWAY_STATIC_URL:-http://localhost:8000}"

echo "🔄 Running cache warmup for: $BACKEND_URL"
echo "⏰ Time: $(date)"

# Call the warmup endpoint
response=$(curl -s -w "\n%{http_code}" "$BACKEND_URL/api/warmup")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" -eq 200 ]; then
    echo "✅ Cache warmup successful (HTTP $http_code)"
    echo "📊 Response: $body"
else
    echo "❌ Cache warmup failed (HTTP $http_code)"
    echo "📄 Response: $body"
    exit 1
fi

echo "✨ Warmup completed at $(date)"
