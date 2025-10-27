# NBA News Integration for Roster Assistant

## Implementation Summary

Successfully integrated NBA news API to provide the LLM with latest injury updates and player news for better free agent recommendations.

## Changes Made

### 1. New NBA News Service
**File:** `backend/services/nba_news_service.py`

**Features:**
- Fetches latest news from ESPN, Bleacher Report, NBA.com, Yahoo, and SLAM
- Methods:
  - `get_player_news(player_name, limit)` - Get player-specific news
  - `get_team_news(team_name, limit)` - Get team news
  - `get_latest_nba_news(source, limit)` - General NBA news
  - `check_injury_status(player_name)` - Analyze news for injury keywords
- Redis caching with 30-minute TTL
- Error handling for timeouts and HTTP errors
- Graceful degradation if API is unavailable

**Injury Detection:**
Scans news article titles for keywords:
- injury, injured, out, questionable, doubtful
- day-to-day, return, comeback, cleared, protocol
- surgery, rehab, sidelined, ruled out

### 2. Updated Dependencies
**File:** `backend/dependencies.py`

Added `get_nba_news_service()` dependency injector for the news service.

### 3. Enhanced Free Agent Tool
**File:** `backend/agents/tools.py`

**Updates:**
- Added `nba_news_service` parameter to `RosterAdvisorTools` constructor
- Free agent search now fetches injury news for top 5 players (parallel requests)
- Displays both:
  - **Sleeper Status**: From Sleeper API (Out, IR, DTD)
  - **Latest News**: From news sources with injury updates
  
**Output Format:**
```
1. **Jayson Tatum** (PF/SF) - BOS
   📊 2024-25 Stats: 26.8 PPG, 8.7 RPG, 6.0 APG
   ⭐ Fantasy Score: 48.1
   🏥 Sleeper Status: Out
   📰 ⚠️ Injury Update for Jayson Tatum:
   • Jayson Tatum Injury Update Return Timeline
   • Celtics Without Tatum Rotation Changes
```

### 4. Updated Roster Chat Endpoint
**File:** `backend/main.py`

- Imports `get_nba_news_service()`
- Passes news service to `RosterAdvisorTools`
- News is now available to LLM during roster advice

## API Integration

**Base URL:** `https://nba-stories.onrender.com`

**Endpoints Used:**
```
GET /articles?player=lebron-james&limit=5
GET /articles?team=lakers&limit=10
GET /articles?source=espn&limit=10
```

**Response Format:**
```json
[
  {
    "title": "lebron-james-injury-update-return-timeline",
    "url": "https://...",
    "source": "espn"
  }
]
```

## Benefits

### For Users:
1. **Injury Awareness**: LLM warns about players with recent injury news
2. **Return Timeline**: Latest updates on when injured players might return
3. **Informed Decisions**: Avoid picking up players who are long-term injured
4. **Multi-Source Verification**: News from 5 trusted NBA sources

### For LLM:
1. **Real-Time Context**: Latest injury reports instead of just Sleeper status
2. **Detailed Information**: Can see actual news headlines about injuries
3. **Better Recommendations**: Avoid suggesting players with concerning injury news
4. **Transparency**: Can cite specific news sources in recommendations

## Example LLM Behavior

**Before (No News Integration):**
```
Top free agent: Brook Lopez - 28.1 fantasy score
Status: DTD
Recommendation: Consider adding Lopez for rebounds
```

**After (With News Integration):**
```
Top free agent: Brook Lopez - 28.1 fantasy score
Status: DTD
📰 Latest: "Brook Lopez Ankle Injury Sidelines Him Indefinitely"

⚠️ CAUTION: Lopez has concerning injury news. He's day-to-day with 
an ankle injury and there's no clear return timeline. Consider 
waiting for more updates before adding him.

Better alternative: Dereck Lively (26.8 fantasy score) - No injury 
concerns, actively playing.
```

## Testing

### Test Results:
```bash
python test_free_agents.py
```

**Output:**
- ✅ Stats displayed: PPG, RPG, APG, Fantasy Score
- ✅ Ranked by fantasy value
- ✅ Sleeper injury status shown
- ✅ News API integration working (fetches injury news)
- ⚠️ API may have rate limits or downtime (handles gracefully)

## Error Handling

The implementation gracefully handles:
1. **API Timeouts**: 10-second timeout, returns empty list
2. **HTTP Errors**: Logs warning, continues without news
3. **Network Issues**: Doesn't break free agent search
4. **Rate Limiting**: Cached for 30 minutes to reduce API calls
5. **Missing Data**: Shows only Sleeper status if news unavailable

## Performance Considerations

1. **Parallel Requests**: Fetches news for top 5 players concurrently
2. **Redis Caching**: 30-minute TTL reduces redundant API calls
3. **Timeout Protection**: 10-second timeout prevents hanging
4. **Limited Scope**: Only checks top players to avoid excessive requests

## Future Enhancements

1. **Fallback Sources**: If primary API is down, scrape directly from ESPN/BR
2. **Sentiment Analysis**: Analyze if news is positive/negative
3. **Return Date Extraction**: Parse articles for specific return dates
4. **Trade Impact News**: "Player X traded to Team Y" updates
5. **Performance News**: "Player hits career high" for hot pickups
6. **Coach Comments**: Track coach quotes about playing time

## Configuration

No configuration needed - service initializes automatically with Redis caching if available, works without Redis if not.

**Dependencies:**
- `httpx` for async HTTP requests (already installed)
- `backend.services.redis_service` for caching (optional)

## API Source

GitHub: https://github.com/kevinn03/nba_api
Hosted: https://nba-stories.onrender.com

**Credit:** Built by Kevin Nguyen, aggregates articles from:
- NBA.com
- ESPN
- Bleacher Report
- Yahoo Sports
- SLAM Magazine
