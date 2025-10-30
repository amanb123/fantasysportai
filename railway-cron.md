# Railway Cron Job Setup

## How to Add Cron Job to Railway

Railway doesn't have built-in cron scheduling like Vercel, but you have options:

### Option 1: External Cron Service (Easiest)

Use a free external service to ping your Railway backend:

1. **Cron-job.org** (Free tier: https://cron-job.org)
   - Create account
   - Add new cron job
   - URL: `https://your-railway-app.railway.app/api/warmup`
   - Schedule: Every 5 minutes
   - Method: GET

2. **UptimeRobot** (Free tier: https://uptimerobot.com)
   - Create HTTP(s) monitor
   - URL: `https://your-railway-app.railway.app/api/warmup`
   - Monitoring Interval: 5 minutes
   - Side benefit: Also monitors uptime!

### Option 2: Self-Hosted Cron (Advanced)

Add a background task runner to your FastAPI app using APScheduler:

```python
# In backend/main.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

async def warmup_task():
    """Background task to keep cache warm"""
    try:
        # Call warmup endpoint internally
        async with httpx.AsyncClient() as client:
            await client.get("http://localhost:8000/api/warmup")
    except Exception as e:
        logger.error(f"Warmup task failed: {e}")

# Start scheduler
scheduler.add_job(warmup_task, 'interval', minutes=5)
scheduler.start()
```

### Option 3: Remove Cron, Rely on Traffic

If your app gets regular traffic, you may not need cron jobs:
- First request after 24h will initialize cache
- Subsequent requests will be fast
- Only first user of the day sees slight delay

## Current Recommendation

For your use case, I recommend **UptimeRobot**:
- ✅ Free forever
- ✅ Monitors uptime AND keeps cache warm
- ✅ Email alerts if backend goes down
- ✅ No code changes needed
- ✅ Works with Railway backend
