# Roster Assistant Free Agent Bug Fix

## Problem
User reported: "I asked the roster assistant to show me good free agents to pick up this week and it wasn't able to give me a data-oriented answer even though I prompted it multiple times."

**Root Cause:** The `search_available_players` tool was only returning player names, positions, and teams - **no performance statistics**. Players were sorted alphabetically instead of by value.

## Solution Implemented

### 1. Enhanced `search_available_players` Tool
**File:** `backend/agents/tools.py`

**Changes:**
- Now fetches real player stats using `NBAStatsService`
- Implements same fallback logic as matchup simulation:
  - Uses 2025-26 season if player has 25+ games
  - Falls back to 2024-25 season if current season has < 25 games
  - Uses most recent available season data
- Calculates fantasy score: `PTS + 1.2×REB + 1.5×AST + 3×STL + 3×BLK - TOV`
- Sorts results by fantasy score (descending) instead of alphabetically

**Output Format:**
```
**Top 5 Available Free Agents:**
(Ranked by fantasy value - stats from most recent season with 25+ games)

1. **Brook Lopez** (C) - LAC
   📊 2024-25 Stats: 13.0 PPG, 5.0 RPG, 1.8 APG
   ⭐ Fantasy Score: 28.1
   🏥 Status: DTD

2. **Dereck Lively** (C) - DAL
   📊 2024-25 Stats: 8.7 PPG, 7.5 RPG, 2.4 APG
   ⭐ Fantasy Score: 26.8
```

### 2. Updated System Prompt
**File:** `backend/agents/agent_factory.py`

**Changes:**
- Emphasized that `search_available_players` is the PRIMARY tool for free agent questions
- Added instructions to compare stats with user's roster gaps
- Provided example responses showing data-driven recommendations
- Clarified that stats are from 2024-25 for most players

**Example Good Response Format:**
```
Top 3 available centers ranked by fantasy value:
1. **Brook Lopez** - 13.0 PPG, 5.0 RPG, 1.8 APG (Fantasy: 28.1)
2. **Dereck Lively** - 8.7 PPG, 7.5 RPG, 2.4 APG (Fantasy: 26.8)
3. **Yves Missi** - 9.1 PPG, 8.2 RPG, 1.4 APG (Fantasy: 25.3)

Your current centers average 6.5 PPG and 4.2 RPG. Adding Brook Lopez 
would improve scoring by +6.5 PPG and rebounding by +0.8 RPG.
```

### 3. Updated Simulation Disclaimer
**File:** `backend/services/matchup_simulation_service.py`

**Changes:**
- Updated disclaimer to clearly state using 2024-25 season data
- Explains that projections will auto-switch to 2025-26 once 25+ games played
- More transparent about data source

## Testing

### Test Results
```bash
python test_free_agents.py
```

**Before Fix:**
- Players: AJ Green, AJ Johnson, Aaron Holiday (alphabetical)
- No stats shown
- No fantasy scores
- No ranking by value

**After Fix:**
- Players: Brook Lopez (28.1), Dereck Lively (26.8), Yves Missi (25.3)
- Real 2024-25 stats: PPG, RPG, APG
- Fantasy scores calculated and displayed
- Ranked by value (best first)

## Impact

### User Experience
1. **Data-Driven Recommendations:** LLM now provides specific stats when suggesting free agents
2. **Roster Gap Analysis:** Can compare free agent stats with current roster
3. **Transparent Data Source:** Users know stats are from 2024-25 season
4. **Value-Based Ranking:** Best players shown first, not random alphabetical order

### Technical Benefits
1. **Consistent Logic:** Same season fallback logic as matchup simulation
2. **Cached Performance:** Uses existing Redis cache for player stats
3. **Rate Limiting:** Respects NBA API rate limits
4. **Error Handling:** Gracefully handles missing stats

## Files Modified

1. **backend/agents/tools.py**
   - Enhanced `_search_available_players()` method (lines 202-330)
   - Added stats fetching with season fallback logic
   - Updated tool description to mention stats

2. **backend/agents/agent_factory.py**
   - Updated system prompt for roster advisor (lines 590-620)
   - Added emphasis on data-driven free agent recommendations
   - Provided example responses with stats comparison

3. **backend/services/matchup_simulation_service.py**
   - Updated simulation disclaimer (lines 268-276)
   - More transparent about using 2024-25 season data

## Future Enhancements

1. **Schedule Integration:** Add "games this week" count to free agent results
2. **Trending Stats:** Show if player is hot/cold in last 5-10 games
3. **Matchup Quality:** Factor in upcoming opponent difficulty
4. **Roster Fit Score:** Auto-calculate how well free agent fills roster gaps
