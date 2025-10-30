# APScheduler implementation for Railway cron jobs
# Add this to backend/main.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

# Initialize scheduler
scheduler = AsyncIOScheduler()

async def warmup_cache_job():
    """
    Background job to keep cache warm.
    Runs every 5 minutes to prevent cold starts and maintain cache.
    """
    try:
        logger.info("🔄 [CRON] Running scheduled cache warmup...")
        
        # Check and initialize player cache if needed
        player_cache_service = get_player_cache_service()
        if player_cache_service:
            cache_stats = player_cache_service.get_cache_stats()
            logger.info(f"[CRON] Player cache status: {cache_stats.get('is_valid')} ({cache_stats.get('player_count', 0)} players, TTL: {cache_stats.get('ttl_remaining', 0)}s)")
            
            if not cache_stats.get("is_valid"):
                logger.info("[CRON] Player cache invalid, initializing...")
                asyncio.create_task(initialize_player_cache(player_cache_service))
        
        # Check Redis connection
        redis_service = get_redis_service()
        if redis_service and redis_service.is_connected():
            logger.info("[CRON] Redis: Connected ✅")
        else:
            logger.warning("[CRON] Redis: Disconnected ⚠️")
        
        logger.info("✅ [CRON] Cache warmup job completed successfully")
    except Exception as e:
        logger.error(f"❌ [CRON] Cache warmup job failed: {e}")
        import traceback
        logger.error(f"[CRON] Traceback: {traceback.format_exc()}")

# Add to lifespan or startup event
@app.on_event("startup")
async def start_background_scheduler():
    """Start the APScheduler for background jobs"""
    try:
        # Add cache warmup job (every 5 minutes)
        scheduler.add_job(
            warmup_cache_job,
            CronTrigger.from_crontab('*/5 * * * *'),  # Every 5 minutes
            id='cache_warmup',
            name='Cache Warmup Job',
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )
        
        scheduler.start()
        logger.info("🚀 Background scheduler started - Cache warmup every 5 minutes")
        
        # Run once immediately on startup
        await warmup_cache_job()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_background_scheduler():
    """Gracefully shutdown the scheduler"""
    try:
        scheduler.shutdown(wait=False)
        logger.info("🛑 Background scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
