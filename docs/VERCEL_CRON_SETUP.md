# Vercel Cron Job - Cache Warmup

## Overview
This project uses Vercel Cron Jobs to keep the application cache warm and prevent cold starts on the production deployment.

## Configuration

### Cron Schedule
- **Path**: `/api/warmup`
- **Schedule**: `*/5 * * * *` (Every 5 minutes)
- **Configuration File**: `vercel.json`

### What It Does

The cron job calls the `/api/warmup` endpoint every 5 minutes to:

1. **Prevent Cold Starts**: Keeps the Vercel serverless function warm
2. **Initialize Player Cache**: Ensures the Sleeper player cache is populated
3. **Maintain Redis Connections**: Keeps Redis connection pool alive
4. **Check Service Health**: Verifies all critical services are available

## Cache Warmup Endpoint

### Endpoint: `GET /api/warmup`

**Response:**
```json
{
  "timestamp": "2025-10-30T18:30:00.000000",
  "status": "complete",
  "services": {
    "redis": "connected",
    "player_cache": {
      "status": "valid",
      "player_count": 4500,
      "ttl_remaining": 82800
    },
    "sleeper": "available",
    "nba_stats": "available"
  }
}
```

### Service Checks

1. **Redis**: Verifies connection to Redis cache
2. **Player Cache**: 
   - Checks if cache is valid (not expired)
   - Returns player count and TTL
   - Triggers background initialization if invalid
3. **Sleeper Service**: Confirms Sleeper API client is available
4. **NBA Stats Service**: Confirms NBA MCP service is available

## Cache TTL (Time-To-Live)

- **Player Cache**: 24 hours (86,400 seconds)
- **Roster Rankings**: 1 hour (3,600 seconds)
- **League Data**: 30 minutes (1,800 seconds)
- **NBA Player Info**: 24 hours (86,400 seconds)
- **NBA Schedule**: 12 hours (43,200 seconds)

## Benefits

### Before Cron Job
- First user request after inactivity hits cold start
- Player cache needs to initialize (10-30 seconds)
- User sees "Player cache is empty" error
- Must retry after cache warms up

### After Cron Job
- Application stays warm
- Player cache always populated
- No "cache empty" errors
- Immediate response to user requests

## Vercel Cron Job Setup

### 1. Enable Cron Jobs in Vercel Dashboard
1. Go to your Vercel project settings
2. Navigate to "Cron Jobs" tab
3. Verify the cron job appears from `vercel.json`

### 2. Monitor Cron Job Execution
- View logs in Vercel dashboard under "Deployments" → "Functions"
- Check the `/api/warmup` function logs
- Look for successful executions every 5 minutes

### 3. Environment Variables
Ensure these are set in Vercel:
- `REDIS_URL`: Redis connection string
- `SLEEPER_API_BASE_URL`: Sleeper API endpoint
- `NBA_MCP_SERVER_URL`: NBA stats MCP service URL (if using)

## Testing Locally

You can test the warmup endpoint locally:

```bash
# Start the backend
python -m uvicorn backend.main:app --reload

# Call the warmup endpoint
curl http://localhost:8000/api/warmup
```

## Troubleshooting

### Issue: Cron job not running
- Check Vercel project settings → Cron Jobs
- Verify `vercel.json` is committed to repository
- Check function logs for errors

### Issue: Cache still empty
- Verify Redis is connected (check `/api/warmup` response)
- Check backend logs for initialization errors
- Ensure `REDIS_URL` environment variable is set

### Issue: Timeout errors
- The warmup endpoint should complete in < 5 seconds
- If taking longer, check Redis/Sleeper API connectivity
- Review backend logs for slow queries

## Cost Considerations

**Vercel Cron Jobs:**
- Free tier: 100 cron invocations/day
- Our setup: 288 invocations/day (every 5 minutes)
- **Recommendation**: Upgrade to Pro plan or adjust schedule to `*/10 * * * *` (every 10 minutes = 144/day)

**Alternative for Free Tier:**
```json
{
  "crons": [
    {
      "path": "/api/warmup",
      "schedule": "*/10 * * * *"
    }
  ]
}
```

This reduces invocations to 144/day while still keeping cache reasonably warm.

## Monitoring

### Success Indicators
- `/api/warmup` returns `status: "complete"`
- `player_cache.status` = `"valid"`
- `player_cache.player_count` > 4000
- No 503 errors on roster ranking requests

### Failure Indicators
- `/api/warmup` returns `status: "error"`
- `redis` = `"disconnected"`
- `player_cache.status` = `"invalid"`
- Users report "Player cache is empty" errors

## Related Files

- `vercel.json` - Cron job configuration
- `backend/main.py` - Warmup endpoint implementation (line ~270)
- `backend/dependencies.py` - Service initialization
- `backend/services/player_cache_service.py` - Player cache logic
