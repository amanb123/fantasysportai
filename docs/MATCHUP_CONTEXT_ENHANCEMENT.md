# Dynamic Roster & Matchup Context Enhancement

## Summary
Enhanced the roster chat assistant to provide **dynamic, real-time** access to league data instead of relying solely on static context. The LLM now has proper matchup information and can access all league rosters through function calling.

## Problem Statement

### Issue 1: No Other Team Rosters
**Problem:** The LLM only had access to the user's roster in the static context, not other teams' rosters.

**Impact:**
- Could not suggest waiver pickups based on what other teams need
- Could not analyze opponent strategies
- Couldn't see league-wide roster trends

### Issue 2: Incorrect Matchup Information
**Problem:** When asked "who is my matchup this week?", the LLM responded with placeholder text like "you're facing off against [Team Name]"

**Root Cause:**
- No current week matchup data in context
- Only showed **past weeks** performance, not current matchup
- LLM had to hallucinate opponent information

## Solution Implemented

### 1. Added Current Matchup Context

**New Method:** `_get_current_matchup_context()`

**Location:** `backend/services/roster_context_builder.py` (lines 297-393)

**What it provides:**
- Current week number
- Opponent's team name
- Current score (user vs opponent)
- Opponent's top 5 starting players with positions and teams
- Reminder to use `get_opponent_roster` tool for full details

**Example Output:**
```
## This Week's Matchup
**Week 1** - vs **Team Awesome**
**Current Score:** 45.3 - 52.1

**Opponent's Key Players:**
- LeBron James (SF/PF) - LAL
- Stephen Curry (PG/SG) - GSW
- Nikola Jokić (C) - DEN
- Giannis Antetokounmpo (PF/C) - MIL
- Damian Lillard (PG) - MIL

*Use `get_opponent_roster` tool for full opponent roster details*
```

**Key Features:**
- Auto-detects current week from league cache
- Finds matchup_id to pair user with opponent
- Looks up opponent's name from league user data
- Shows real-time score comparison
- Gracefully handles bye weeks (returns empty string)

### 2. Dynamic Tool Access

The LLM already has **5 function calling tools** for real-time data access:

1. **`search_available_players`** - Waiver wire search by position
2. **`get_opponent_roster`** - Full roster of any team by name
3. **`get_recent_transactions`** - Recent adds/drops/trades
4. **`get_all_league_rosters`** - ALL team rosters with standings
5. **`search_player_details`** - Player stats, team, injury status

**Strategy:**
- **Static Context:** Core info (league rules, user's roster, current matchup summary)
- **Dynamic Tools:** Everything else (opponent details, league standings, waiver wire, transactions)

This approach:
✅ Keeps context tokens manageable
✅ Always provides fresh, real-time data
✅ Rosters update automatically (no stale data)
✅ LLM can explore league dynamically based on user questions

### 3. Updated System Prompt

**Location:** `backend/agents/agent_factory.py` (lines 544-586)

**Key Instructions Added:**
- Emphasizes using tools for dynamic data (opponent rosters, waiver wire)
- Reminds LLM it has full access to league data
- Encourages tool use for questions about other teams
- Makes it clear: "Never say you don't have access to data"

## Technical Details

### Context Flow
```
User asks: "Who is my matchup this week?"
    ↓
Backend builds context:
    1. League rules & scoring
    2. User's roster
    3. **[NEW]** Current matchup (opponent name, score, key players)
    4. Schedule & injuries
    5. Recent performance
    ↓
LLM receives context + 5 tools
    ↓
LLM can now answer with real opponent name
LLM can call get_opponent_roster() for more details
```

### Data Sources

**Static Context (Built Once Per Message):**
- League rules/scoring: From `league_cache.get_cached_league_details()`
- User's roster: From `league_cache.get_cached_rosters()`
- **Current matchup:** From `league_cache.get_cached_matchups(current_week)`
- Schedule: From `nba_cache.get_schedule()`
- Injuries: From `player_cache`
- Recent performance: From `league_cache.get_cached_matchups(past_weeks)`

**Dynamic Tools (Called On-Demand):**
- Waiver wire: Live API call to Sleeper
- Opponent rosters: Cached rosters (refreshed periodically)
- Transactions: Live API call to Sleeper
- All rosters: Cached rosters
- Player details: Cached player data

### Cache Strategy

- **Player Data:** Cached for 24 hours (2009 players)
- **Rosters:** Cached for ~30 minutes, refreshed automatically
- **Matchups:** Cached per week, updates as scores change
- **Transactions:** Always live (no cache)

## Benefits

### For Users
✅ **Accurate matchup information** - No more "[Team Name]" placeholders
✅ **Real opponent analysis** - See who you're actually playing
✅ **League-wide insights** - Can ask about any team's roster
✅ **Fresh data** - Rosters update as adds/drops happen
✅ **Better recommendations** - Suggestions based on all league rosters

### For System
✅ **Token efficient** - Minimal static context, dynamic tools for details
✅ **Scalable** - Doesn't grow context with league size
✅ **Maintainable** - Sleeper API changes only affect tools, not context
✅ **Flexible** - LLM explores data based on user needs

## Example Interactions

### Before Enhancement
```
User: "Who is my matchup this week?"
LLM: "You're facing off against the [Team Name]..."
     ❌ Incorrect - placeholder text
```

### After Enhancement
```
User: "Who is my matchup this week?"
LLM: "You're playing against Team Awesome this week! 
      Currently you're down 45.3 to 52.1. They've got 
      a strong lineup with LeBron, Curry, and Jokić 
      starting. Want me to pull up their full roster 
      to see where you might have an advantage?"
      ✅ Correct - real opponent name and score
```

### Dynamic Tool Usage
```
User: "What players are available at center?"
LLM: [Calls search_available_players(position="C")]
     "Here are the top available centers:
      1. Jonas Valančiūnas (26% rostered)
      2. Isaiah Hartenstein (18% rostered)
      3. ..."
      ✅ Real-time waiver wire data
```

```
User: "How does my opponent's roster look?"
LLM: [Calls get_opponent_roster(team_name="Team Awesome")]
     "Team Awesome has a pretty balanced roster with..."
      ✅ Full opponent roster details
```

## Files Modified

1. **`backend/services/roster_context_builder.py`**
   - Added `_get_current_matchup_context()` method (lines 297-393)
   - Integrated into `build_roster_context()` (line 87-90)
   - Provides current week matchup with opponent details

2. **`backend/agents/agent_factory.py`**
   - Enhanced system prompt to emphasize tool usage
   - Added instructions for dynamic data access
   - Clarified when to use each tool

## Testing Recommendations

1. **Test Current Matchup:**
   - Ask: "Who is my matchup this week?"
   - Should show real opponent name and current score
   - Should list opponent's key players

2. **Test Opponent Roster:**
   - Ask: "Show me [opponent name]'s full roster"
   - Should call `get_opponent_roster` tool
   - Should display all opponent players

3. **Test League Overview:**
   - Ask: "Show me all team standings"
   - Should call `get_all_league_rosters` tool
   - Should display league-wide data

4. **Test Waiver Wire:**
   - Ask: "What guards are available?"
   - Should call `search_available_players(position="PG")` or "SG"
   - Should show real-time free agents

## Future Enhancements

### Potential Improvements:
1. **Matchup Projections:** Add projected scores based on remaining games
2. **Head-to-Head Stats:** Compare user vs opponent in each category
3. **Roster Comparison:** Side-by-side roster analysis
4. **Trade Suggestions:** Based on both rosters' needs
5. **Streaming Strategy:** Suggest optimal pickups for current matchup

### Additional Tools to Consider:
- `get_matchup_projections` - Projected scores for current week
- `compare_rosters` - Direct comparison between two teams
- `get_category_breakdown` - Detailed scoring category analysis
- `suggest_lineup_changes` - Optimal lineup based on schedule

## Notes

- Matchup context returns empty string if no matchup data (bye week, season not started)
- Opponent name lookup cascades: display_name → username → "Unknown Team"
- Shows top 5 opponent players to keep context manageable
- Full opponent roster available via `get_opponent_roster` tool
- All data respects cache TTLs to balance freshness vs API load

---

**Status:** ✅ Implemented and Running (PID TBD)
**Backend:** Port 3002
**Season:** 2025 (Auto-detected)
**Tools:** 5 active function calling tools
**Context:** ~500-800 tokens (manageable size)
