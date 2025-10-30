# Railway Cron Job Setup Guide

## Overview
Railway supports cron jobs through their Cron service. This allows you to run scheduled tasks directly on Railway without external services.

## Method 1: Railway Cron Service (Easiest)

### Step 1: Create a New Service in Railway

1. Go to your Railway project dashboard
2. Click **"+ New"** → **"Empty Service"**
3. Name it: `cache-warmup-cron`

### Step 2: Configure the Cron Service

In Railway dashboard for the cron service:

1. Go to **Settings** → **Service**
2. Set **Start Command**:
   ```bash
   */5 * * * * /bin/bash /app/scripts/railway-cron-warmup.sh
   ```

3. Add **Environment Variables**:
   ```
   RAILWAY_STATIC_URL=https://fantasysportai-production.up.railway.app
   ```

4. Deploy from the same repository (Railway will build it)

### Step 3: Verify It's Working

1. Check **Deployments** → **Logs**
2. Should see warmup messages every 5 minutes:
   ```
   🔄 Running cache warmup for: https://fantasysportai-production.up.railway.app
   ✅ Cache warmup successful (HTTP 200)
   ```

---

## Method 2: Add Cron to Existing Backend (All-in-One)

Use APScheduler to run cron jobs inside your existing FastAPI app.

### Step 1: Install APScheduler

Add to `backend/requirements.txt`:
```
APScheduler==3.10.4
```

### Step 2: Add Scheduler to FastAPI

Update `backend/main.py`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Initialize scheduler
scheduler = AsyncIOScheduler()

async def warmup_cache_job():
    """Background job to keep cache warm"""
    try:
        logger.info("🔄 Running scheduled cache warmup...")
        
        # Call warmup endpoint internally
        player_cache_service = get_player_cache_service()
        if player_cache_service:
            cache_stats = player_cache_service.get_cache_stats()
            if not cache_stats.get("is_valid"):
                logger.info("Initializing player cache...")
                asyncio.create_task(initialize_player_cache(player_cache_service))
        
        logger.info("✅ Cache warmup job completed")
    except Exception as e:
        logger.error(f"❌ Cache warmup job failed: {e}")

# Add job to scheduler (runs every 5 minutes)
@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(
        warmup_cache_job,
        CronTrigger.from_crontab('*/5 * * * *'),  # Every 5 minutes
        id='cache_warmup',
        name='Cache Warmup Job',
        replace_existing=True
    )
    scheduler.start()
    logger.info("🚀 Background scheduler started")

@app.on_event("shutdown")
async def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("🛑 Background scheduler stopped")
```

### Step 3: Deploy to Railway

Railway will automatically pick up the new dependency and start the scheduler.

---

## Method 3: Simple Keep-Alive Ping

If you just need to prevent Railway from sleeping (Railway Free tier doesn't sleep, but Hobby tier does):

### Create a simple ping service

`scripts/ping-server.py`:
```python
#!/usr/bin/env python3
import time
import requests
import os
from datetime import datetime

BACKEND_URL = os.getenv('BACKEND_URL', 'https://fantasysportai-production.up.railway.app')
INTERVAL = 300  # 5 minutes in seconds

def ping_warmup():
    try:
        print(f"🔄 [{datetime.now()}] Pinging {BACKEND_URL}/api/warmup")
        response = requests.get(f"{BACKEND_URL}/api/warmup", timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Success: {response.json()}")
        else:
            print(f"❌ Failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print(f"🚀 Starting warmup service (every {INTERVAL}s)")
    
    while True:
        ping_warmup()
        time.sleep(INTERVAL)
```

Deploy this as a separate Railway service with:
```
Start Command: python scripts/ping-server.py
```

---

## Recommended Approach

**For your setup, I recommend Method 2 (APScheduler)**:

✅ **Pros:**
- All-in-one solution
- No separate service needed
- Runs within your existing backend
- No external dependencies
- Works on Railway Free and Hobby tiers

❌ **Cons:**
- Slightly more complex code
- Adds dependency to backend

## Verification

To verify any method is working:

1. Check Railway logs
2. Call the warmup endpoint manually:
   ```bash
   curl https://fantasysportai-production.up.railway.app/api/warmup
   ```
3. Verify player cache stays valid (TTL doesn't drop to 0)

## Cost

All Railway-based solutions are **free** (included in Railway plan).
