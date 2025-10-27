# Fix: Incorrect Week Detection Causing Wrong Matchup Data

## Problem

### Symptom
When user asked "who is my matchup this week?", the LLM provided incorrect opponent player names (e.g., Stephen Curry, Paul George, Kevin Durant) which were not actually on the opponent's roster.

### Root Cause
The `_get_current_round()` method in `LeagueDataCacheService` was:
1. **Using wrong event loop pattern** - Trying to call `asyncio.get_event_loop()` and `loop.run_until_complete()` from within an async context
2. **Causing "event loop already running" error**
3. **Falling back to default week 10** instead of the actual current week (week 1)
4. **Loading old cached matchup data from week 10** (likely from previous season)

### Evidence from Logs
```
2025-10-19 17:38:23,170 - backend.services.league_data_cache_service - WARNING - Failed to 
fetch current NBA week: this event loop is already running.
2025-10-19 17:38:23,170 - backend.services.league_data_cache_service - INFO - Using default week: 10
2025-10-19 17:38:23,171 - backend.services.league_data_cache_service - INFO - Matchup cache hit for league 1265480188934750208, week 10
```

**Result:** The LLM received matchup data from week 10 (old data) instead of week 1 (current week), leading to hallucinated/incorrect opponent information.

## Solution

### Changes Made

#### 1. Made `_get_current_round()` Properly Async

**File:** `backend/services/league_data_cache_service.py`

**Before:**
```python
def _get_current_round(self) -> int:
    """Get current NBA round/week from Sleeper state API with caching."""
    # ...cache check...
    
    # Fetch from API
    try:
        import asyncio
        loop = asyncio.get_event_loop()  # ❌ WRONG in async context
        
        async def fetch_state():
            async with SleeperService() as sleeper:
                return await sleeper.get_nba_state()
        
        state_data = loop.run_until_complete(fetch_state())  # ❌ Causes "already running" error
        # ...
    except Exception as e:
        logger.warning(f"Failed to fetch current NBA week: {e}")
    
    default_week = 10  # ❌ Wrong default
    return default_week
```

**After:**
```python
async def _get_current_round(self) -> int:  # ✅ Made async
    """Get current NBA round/week from Sleeper state API with caching."""
    # ...cache check...
    
    # Fetch from API (now properly async)
    try:
        async with SleeperService() as sleeper:  # ✅ Direct async call
            state_data = await sleeper.get_nba_state()
        
        if state_data:
            week = state_data.get("week") or state_data.get("leg") or 1  # ✅ Correct default
            # Cache for 1 hour
            self.redis_service.set(cache_key, str(week), ttl=3600)
            logger.info(f"Fetched current NBA week from API: {week}")
            return week
            
    except Exception as e:
        logger.warning(f"Failed to fetch current NBA week: {e}")
    
    default_week = 1  # ✅ Correct default (season start)
    return default_week
```

#### 2. Updated All Async Callers

**Files Modified:**
- `backend/services/roster_context_builder.py` (2 locations)
- `backend/services/league_data_cache_service.py` (2 locations in async methods)

**Changes:**
```python
# Before
current_week = self.league_cache._get_current_round()

# After
current_week = await self.league_cache._get_current_round()  # ✅ Await the async call
```

#### 3. Updated Sync Callers to Use Cached Value

For methods that are NOT async and cannot be easily converted, changed them to read the cached week value directly from Redis instead of calling `_get_current_round()`:

**Files Modified:**
- `backend/services/league_data_cache_service.py` (3 locations in sync methods)

**Pattern:**
```python
# Before
current_round = self._get_current_round()  # ❌ Can't call async from sync

# After
# Use cached week value if available, otherwise use default
cache_key_week = "sleeper:nba_state:current_week"
cached_week = self.redis_service.get(cache_key_week)
if cached_week is not None:
    try:
        current_round = int(cached_week)
    except (ValueError, TypeError):
        current_round = 1  # Default to week 1
else:
    current_round = 1  # Default to week 1
```

## Technical Details

### Async Pattern Fixed

**Problem Pattern:**
```python
# From SYNC context trying to run async code
loop = asyncio.get_event_loop()  # Gets current loop
state_data = loop.run_until_complete(async_function())  # Tries to run event loop again
# ❌ Error: "This event loop is already running"
```

**Solution Pattern:**
```python
# Make the method async
async def method(self):
    # Now you can directly await
    state_data = await async_function()  # ✅ Works correctly
```

### Week Caching Strategy

The fix maintains a 1-hour cache of the current NBA week in Redis:
- **Cache Key:** `"sleeper:nba_state:current_week"`
- **TTL:** 3600 seconds (1 hour)
- **Purpose:** Avoid excessive API calls to Sleeper's `/state/nba` endpoint
- **Sync Access:** Sync methods can read this cached value directly without async calls

### Default Week Changed

**Before:** Defaulted to week 10 (arbitrary mid-season value)
**After:** Defaults to week 1 (season start)

**Rationale:**
- Week 1 is safer because:
  - At season start, week 1 is correct
  - During season, the cache will have the correct week
  - Only fails to default if Redis is down AND API fails
- Week 10 was causing the LLM to pull old matchup data from previous seasons

## Impact

### Before Fix
```
User: "Who is my matchup this week?"

System fetches: Week 10 matchup data (old/wrong)
LLM receives: Incorrect opponent roster from cached week 10
LLM responds: "You're facing Stephen Curry, Paul George..." (❌ Wrong players)
```

### After Fix
```
User: "Who is my matchup this week?"

System fetches: Week 1 matchup data (current)
LLM receives: Correct current opponent roster
LLM responds: "You're facing [Actual Opponent] with [Actual Players]..." (✅ Correct)
```

## Files Modified

1. **`backend/services/league_data_cache_service.py`**
   - Made `_get_current_round()` async (line ~523)
   - Updated 2 async method calls to await `_get_current_round()`
   - Updated 3 sync methods to read cached week value from Redis
   - Changed default from week 10 to week 1

2. **`backend/services/roster_context_builder.py`**
   - Updated `_get_current_matchup_context()` to await (line ~306)
   - Updated `_get_recent_performance_context()` to await (line ~511)

## Testing

### Verification Steps
1. **Check logs** - Should no longer see "event loop already running" error
2. **Check week detection** - Should see "Fetched current NBA week from API: 1"
3. **Check matchup data** - Should see "Matchup cache hit for week 1" (not week 10)
4. **Ask LLM** - "Who is my matchup this week?" should return correct current opponent

### Expected Log Output
```
✅ INFO - Fetched current NBA week from API: 1
✅ INFO - Matchup cache hit for league ..., week 1
✅ INFO - This Week's Matchup: Week 1 - vs [Actual Opponent Name]
```

## Prevention

### Best Practices Applied
1. ✅ **Async methods call async methods directly** (use `await`, not `loop.run_until_complete`)
2. ✅ **Cache intermediate values** (week number cached in Redis for sync access)
3. ✅ **Sensible defaults** (week 1 instead of arbitrary week 10)
4. ✅ **Error handling** (graceful fallback if API or cache fails)

### Code Review Checklist
- [ ] Never use `loop.run_until_complete()` inside async functions
- [ ] If calling async from sync, either:
  - Make the sync function async, or
  - Read from a cached intermediate value
- [ ] Default values should make sense for season start
- [ ] Cache TTLs should balance freshness vs API load

## Related Issues

This fix also resolves:
- ❌ **Stale matchup data** - No longer shows old weeks
- ❌ **Incorrect opponent rosters** - LLM now gets current week data
- ❌ **Event loop warnings** - No more "already running" errors
- ❌ **Hardcoded fallbacks** - Better default (week 1 vs week 10)

---

**Status:** ✅ Fixed and Deployed
**Backend:** Running on port 3002
**Current Week:** Auto-detected as 1 (correct)
**Matchup Data:** Now pulls from correct week
