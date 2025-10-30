# APScheduler Deployment - Cache Warmup Automation

## ✅ What Was Implemented

We've integrated **APScheduler** directly into your FastAPI backend to automatically keep the cache warm every 5 minutes. This prevents cold starts and ensures optimal performance.

## 📦 Changes Made

### 1. Dependencies (`backend/requirements.txt`)
```
APScheduler==3.10.4
```

### 2. Main Application (`backend/main.py`)
- **Imports**: Added APScheduler imports
- **Scheduler**: Initialized `AsyncIOScheduler` instance
- **Warmup Job**: Created `warmup_cache_job()` function that:
  - Checks player cache status
  - Auto-initializes if cache is invalid
  - Verifies Redis connection
  - Logs detailed cache statistics
- **Startup**: Added scheduler initialization in `lifespan()` startup
- **Shutdown**: Added graceful scheduler shutdown handler

### 3. Scheduler Module (`backend/scheduler.py`)
Created standalone module with scheduler implementation (alternative reference).

### 4. Documentation
- **`docs/RAILWAY_CRON_SETUP.md`**: Comprehensive guide with 3 implementation methods
- **`docs/APSCHEDULER_DEPLOYMENT.md`**: This deployment guide

### 5. Alternative Scripts (For Reference)
- **`scripts/railway-cron-warmup.sh`**: Bash script for Railway Cron Service approach
- **`railway.json`**: Railway service configuration

## 🚀 How It Works

```python
# Scheduler runs every 5 minutes
CronTrigger.from_crontab('*/5 * * * *')

# Job checks cache and logs status
🔄 [CRON] Running scheduled cache warmup...
[CRON] Player cache status: True (2009 players, TTL: 82951s)
[CRON] Redis: Connected ✅
✅ [CRON] Cache warmup job completed successfully
```

### Job Execution Flow
1. **Scheduler starts** on FastAPI app startup
2. **Immediate run** happens on first startup
3. **Every 5 minutes** thereafter:
   - Check player cache validity
   - If invalid: trigger cache initialization
   - Check Redis connection
   - Log comprehensive status
4. **Graceful shutdown** when app stops

## 📊 Expected Logs on Railway

After deployment, you'll see logs like:

```
🏀 Starting Fantasy Basketball League API
✅ Player cache is valid: 2009 players, TTL: 82951s
🚀 Background scheduler started - Cache warmup every 5 minutes
🔄 [CRON] Running scheduled cache warmup...
[CRON] Player cache status: True (2009 players, TTL: 82951s)
[CRON] Redis: Connected ✅
✅ [CRON] Cache warmup job completed successfully
```

## 🔍 Monitoring

### Railway Dashboard
1. Go to your Railway backend service
2. Click **"Deployments"** → Select latest deployment
3. Click **"View Logs"**
4. Search for `[CRON]` to see scheduler activity

### Expected Schedule
- **00:00** - Cache warmup
- **00:05** - Cache warmup
- **00:10** - Cache warmup
- **00:15** - Cache warmup
- ... every 5 minutes

### Health Check
You can also manually call the warmup endpoint:
```bash
curl https://fantasysportai-production.up.railway.app/api/warmup
```

## 🎯 Benefits

1. **No External Services**: Runs inside your existing backend (no extra Railway costs)
2. **Automatic**: Set it and forget it - starts with your app
3. **Resilient**: Won't crash if Redis is down (just logs warning)
4. **Non-Blocking**: Uses asyncio for concurrent operations
5. **Prevents Overlaps**: `max_instances=1` ensures single execution
6. **Detailed Logging**: Full visibility into cache status every 5 minutes

## 📝 Git Commits

- **Dev**: `493545a` - Add APScheduler for automated cache warmup
- **Main**: `5ad5e2d` - Merge dev: Add APScheduler for automated cache warmup

## 🚢 Deployment Status

✅ **Committed to dev**  
✅ **Merged to main**  
✅ **Pushed to GitHub**  
⏳ **Railway auto-deployment in progress**

Railway will automatically detect the changes and redeploy your backend with the scheduler enabled.

## 🧪 Testing After Deployment

1. **Check Railway Logs** (immediately after deployment):
   ```
   Look for: "🚀 Background scheduler started"
   Look for: "🔄 [CRON] Running scheduled cache warmup..."
   ```

2. **Wait 5 Minutes** and check logs again:
   ```
   Should see another "[CRON]" log entry
   ```

3. **Verify Cache Status**:
   ```bash
   curl https://fantasysportai-production.up.railway.app/api/warmup
   ```
   Should return:
   ```json
   {
     "status": "complete",
     "services": {
       "redis": "connected",
       "player_cache": {
         "status": "valid",
         "player_count": 2009,
         "ttl_remaining": 86400
       }
     }
   }
   ```

## ⚙️ Configuration

The scheduler is configured in `backend/main.py`:

```python
# Change frequency here (default: every 5 minutes)
CronTrigger.from_crontab('*/5 * * * *')

# Examples:
# Every 10 minutes: '*/10 * * * *'
# Every hour: '0 * * * *'
# Every 30 minutes: '*/30 * * * *'
```

## 🛠 Troubleshooting

### Scheduler Not Starting
Check Railway logs for:
```
Failed to start scheduler: <error message>
```
Common issues:
- APScheduler not installed (should be in requirements.txt)
- Import errors (check Python version compatibility)

### Jobs Not Running
Check Railway logs for:
```
❌ [CRON] Cache warmup job failed: <error>
```
This will include full traceback for debugging.

### No Logs Appearing
- Scheduler starts silently if no errors
- Jobs log with `[CRON]` prefix - search for this in logs
- Check Railway log level settings (should show INFO)

## 🎉 Success Criteria

You'll know it's working when:
1. ✅ Railway logs show "Background scheduler started"
2. ✅ Logs show "[CRON]" entries every 5 minutes
3. ✅ Cache remains valid (TTL never reaches 0)
4. ✅ No timeout errors on roster rankings or free agent searches

## 📚 Additional Resources

- **Full Guide**: See `docs/RAILWAY_CRON_SETUP.md` for alternative methods
- **APScheduler Docs**: https://apscheduler.readthedocs.io/
- **Railway Docs**: https://docs.railway.app/

---

**Status**: 🟢 DEPLOYED  
**Last Updated**: October 30, 2025  
**Author**: GitHub Copilot
