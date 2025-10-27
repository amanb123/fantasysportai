# Roster Chat Data Flow Documentation

## Overview
This document explains the complete data flow for the roster chat feature, including what data comes from cache vs. live Sleeper API calls.

---

## 🔄 Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER SENDS CHAT MESSAGE                       │
│                  "Who should I pick up from waivers?"                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND: send_chat_message()                      │
│                         (backend/main.py)                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
        ┌────────────────────┐  ┌────────────────────┐
        │  Save User Message │  │  Detect Historical │
        │    to Database     │  │      Query?        │
        └────────────────────┘  └────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP 1: PRE-WARM CACHES (if needed)                     │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ League Details Cache Check                                   │   │
│  │ • Check: league_cache.get_cached_league_details(league_id)  │   │
│  │ • If MISS → API Call: sleeper.get_league(league_id)         │   │
│  │ • Cache Result: Redis TTL = 1 hour                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Rosters Cache Check                                          │   │
│  │ • Check: league_cache.get_cached_rosters(league_id)         │   │
│  │ • If MISS → API Call: sleeper.get_league_rosters(league_id) │   │
│  │ • Cache Result: Redis TTL = 30 minutes                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Matchups Cache Check                                         │   │
│  │ • Check: league_cache.get_cached_matchups(league_id, week)  │   │
│  │ • If MISS → API Call: sleeper.get_matchups(league_id, week) │   │
│  │ • Cache Result: Redis TTL = 1 hour                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Player Data Cache (Global)                                   │   │
│  │ • Check: player_cache.get_cached_players()                  │   │
│  │ • Source: Redis (pre-loaded at startup)                     │   │
│  │ • Cache TTL: 48 hours                                       │   │
│  │ • Contains: ~2000 NBA players (name, team, position, etc.)  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│         STEP 2: BUILD ROSTER CONTEXT (Static Context)                │
│                  build_roster_context()                              │
│                                                                       │
│  All data from CACHE (no new API calls):                            │
│                                                                       │
│  1️⃣ League Rules & Scoring                                          │
│     • Source: Redis cache                                           │
│     • Data: Scoring categories, roster positions, league settings   │
│                                                                       │
│  2️⃣ User's Roster Summary                                           │
│     • Source: Redis cache (rosters + player data)                   │
│     • Data: Starters, bench, player names, positions, injury status │
│                                                                       │
│  3️⃣ Historical Stats (if requested)                                 │
│     • Source: nba_api (direct NBA.com API - NOT Sleeper)           │
│     • Only called if user asks about past performance              │
│                                                                       │
│  4️⃣ Upcoming Schedule (7 days)                                      │
│     • Source: Redis cache (NBA schedule data)                       │
│     • Data: Next 7 days of games for rostered players              │
│                                                                       │
│  5️⃣ Injury Report                                                   │
│     • Source: Redis cache (player data includes injury_status)      │
│     • Data: Current injury statuses for rostered players            │
│                                                                       │
│  6️⃣ Recent Performance (2 weeks)                                    │
│     • Source: Redis cache (matchup data)                            │
│     • Data: Last 2 weeks of fantasy scoring                         │
│                                                                       │
│  📊 OUTPUT: ~1500 char context string                               │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│           STEP 3: INITIALIZE FUNCTION CALLING TOOLS                  │
│                                                                       │
│  Create RosterAdvisorTools with access to:                          │
│  • league_cache_service (Redis cache interface)                     │
│  • player_cache_service (Redis cache interface)                     │
│  • sleeper_service (LIVE Sleeper API client)                        │
│                                                                       │
│  Available Tools (5 functions):                                     │
│  1️⃣ search_available_players(position, limit)                       │
│  2️⃣ get_opponent_roster(team_name)                                  │
│  3️⃣ get_recent_transactions(limit)                                  │
│  4️⃣ get_all_league_rosters()                                        │
│  5️⃣ search_player_details(player_name)                              │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP 4: CREATE LLM AGENT & SEND REQUEST                │
│                                                                       │
│  Create SimpleAssistantAgent with:                                  │
│  • System message (includes static context from Step 2)            │
│  • Tool definitions (5 functions)                                   │
│  • Tool executor (for making API calls)                             │
│                                                                       │
│  Send to OpenAI GPT-3.5-turbo:                                     │
│  • Messages: [system, ...history, user_message]                    │
│  • Tools: 5 function definitions                                    │
│  • tool_choice: "auto"                                              │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 5: LLM PROCESSING                            │
│                      (OpenAI GPT-3.5)                                │
│                                                                       │
│  LLM Analyzes:                                                      │
│  • User question: "Who should I pick up from waivers?"             │
│  • Static context: Your roster, league rules, scoring              │
│  • Available tools: search_available_players, etc.                  │
│                                                                       │
│  LLM Decision Tree:                                                 │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ If question can be answered with static context:              │ │
│  │   → Return text answer (no tool calls)                        │ │
│  │                                                                │ │
│  │ If question requires external data:                           │ │
│  │   → Request tool call(s)                                      │ │
│  │   → Example: search_available_players(position="PG", limit=10)│ │
│  └──────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│           STEP 6: TOOL EXECUTION (If LLM requests it)                │
│                                                                       │
│  Example: search_available_players(position="", limit=10)          │
│                                                                       │
│  Tool Execution Flow:                                               │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 1. Check roster cache for rostered players                  │  │
│  │    • Source: league_cache.get_cached_rosters(league_id)     │  │
│  │    • If MISS → API: sleeper.get_league_rosters(league_id)   │  │
│  │                                                              │  │
│  │ 2. Get all players from cache                               │  │
│  │    • Source: player_cache.get_cached_players()              │  │
│  │    • Always from Redis (48hr cache)                         │  │
│  │                                                              │  │
│  │ 3. Filter out rostered players                              │  │
│  │    • Logic: exclude player_id in rostered_ids               │  │
│  │                                                              │  │
│  │ 4. Filter by position (if specified)                        │  │
│  │                                                              │  │
│  │ 5. Sort and limit results                                   │  │
│  │                                                              │  │
│  │ 6. Return formatted string                                  │  │
│  │    Example: "Available Players (Top 10):                    │  │
│  │             - John Collins (PF/C) - UTA - Healthy"          │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  Result sent back to LLM as tool response                           │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP 7: LLM FINAL RESPONSE                              │
│                                                                       │
│  LLM receives tool result and generates natural language answer:    │
│                                                                       │
│  "Based on your roster needs and available players, I recommend:    │
│   1. John Collins (PF/C) - He fills your frontcourt need           │
│   2. Dennis Schroder (PG) - Adds guard depth                       │
│   3. Brook Lopez (C) - Provides blocks (3.0 pts each in your       │
│      league)                                                        │
│                                                                       │
│   Consider dropping [bench player] who has limited minutes."        │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│            STEP 8: SAVE & BROADCAST RESPONSE                         │
│                                                                       │
│  1. Save assistant message to database (SQLite)                     │
│  2. Broadcast via WebSocket to frontend                             │
│  3. Return HTTP response to client                                  │
└─────────────────────────────────────────────────────────────────────┘

```

---

## 📊 Data Source Summary

### **CACHED DATA (Redis) - No API Calls**

| Data Type | Cache Key | TTL | Source | When Refreshed |
|-----------|-----------|-----|--------|----------------|
| **Player Database** | `sleeper:players:nba` | 48 hours | Sleeper API | Startup + manual refresh |
| **League Details** | `sleeper:league:{id}` | 1 hour | Sleeper API | On cache miss |
| **Rosters** | `sleeper:rosters:{id}` | 30 min | Sleeper API | On cache miss |
| **Matchups** | `sleeper:matchups:{id}:{week}` | 1 hour | Sleeper API | On cache miss |
| **NBA Schedule** | `nba:schedule:{date}` | 24 hours | NBA API | On cache miss |

### **LIVE API CALLS (On-Demand)**

| Function Tool | API Endpoint | When Called | Cache Strategy |
|---------------|--------------|-------------|----------------|
| `search_available_players()` | Check roster cache first | User asks about waivers | Uses cached player data + roster data |
| `get_opponent_roster()` | Check roster cache first | User asks about opponent | Falls back to live API if cache miss |
| `get_recent_transactions()` | **ALWAYS LIVE** | User asks about recent activity | `sleeper.get_league_transactions()` |
| `get_all_league_rosters()` | Check roster cache first | User asks about standings | Falls back to live API if cache miss |
| `search_player_details()` | **ALWAYS CACHE** | User asks about a player | `player_cache.get_cached_players()` |

---

## 🔍 Detailed Tool Behavior

### 1️⃣ **search_available_players(position, limit)**
```
Cache First Strategy:
1. Get rosters → Try cache, fallback to API
2. Get all players → Always from cache (48hr)
3. Filter logic → In-memory (no API)

API Calls: 0-1 (only if roster cache miss)
Response Time: ~50ms (cached) or ~500ms (with API)
```

**Example Query:** "Who's available at point guard?"
- **Cache Usage:** Player data (cached), Rosters (may hit API)
- **Live API:** Only if rosters not cached

---

### 2️⃣ **get_opponent_roster(team_name)**
```
Cache First Strategy:
1. Get rosters → Try cache, fallback to API
2. Get league details → Try cache, fallback to API
3. Get player data → Always from cache

API Calls: 0-2 (if both rosters and league miss cache)
Response Time: ~100ms (cached) or ~800ms (with API)
```

**Example Query:** "What does Team Alpha's roster look like?"
- **Cache Usage:** Player data (cached), may need roster/league API
- **Live API:** If rosters or league details expired

---

### 3️⃣ **get_recent_transactions(limit)**
```
ALWAYS LIVE - No Cache:
1. Call sleeper.get_league_transactions(league_id)
2. Get player names from cache
3. Format results

API Calls: 1 (always)
Response Time: ~600ms
```

**Example Query:** "What's happened in the league this week?"
- **Cache Usage:** Player names only
- **Live API:** Transaction data (always fresh)

---

### 4️⃣ **get_all_league_rosters()**
```
Cache First Strategy:
1. Get rosters → Try cache, fallback to API
2. Get league details → Try cache, fallback to API
3. Sort by wins/points → In-memory

API Calls: 0-2 (if cache misses)
Response Time: ~100ms (cached) or ~800ms (with API)
```

**Example Query:** "Show me the league standings"
- **Cache Usage:** Rosters + league details
- **Live API:** Only if cache expired

---

### 5️⃣ **search_player_details(player_name)**
```
ALWAYS CACHE - No API:
1. Search player_cache.get_cached_players()
2. Fuzzy match on player name
3. Return player info

API Calls: 0 (always)
Response Time: ~10ms
```

**Example Query:** "Tell me about LeBron James"
- **Cache Usage:** Player database (cached)
- **Live API:** Never

---

## ⚡ Performance Characteristics

### **Typical Chat Response Times**

| Scenario | Data Source | Typical Latency |
|----------|-------------|-----------------|
| Simple roster question | Cache only | 1-2 seconds |
| Waiver wire search (cached) | Cache only | 2-3 seconds |
| Waiver wire search (cache miss) | Cache + 1 API | 3-4 seconds |
| Recent transactions | 1 Live API | 3-4 seconds |
| Multiple tool calls | Mixed | 5-8 seconds |

### **Cache Hit Rates (Expected)**

- **Player Data:** ~99% (rarely changes)
- **Rosters:** ~80% (30min TTL, frequent checks)
- **League Details:** ~90% (1hr TTL, stable data)
- **Matchups:** ~70% (1hr TTL, weekly updates)

---

## 🎯 Key Design Decisions

### **Why Cache-First for Most Data?**
1. **Faster responses** - Redis lookup ~5ms vs API call ~500ms
2. **Rate limit protection** - Sleeper API has rate limits
3. **Reliability** - Works even if Sleeper API is slow/down
4. **Cost** - Reduces external API calls

### **Why Live API for Transactions?**
1. **Data freshness** - Transactions change frequently
2. **User expectation** - "What happened today?" needs real-time data
3. **Not in cache** - Transactions aren't part of roster/league cache

### **Why 48-Hour Player Cache?**
1. **Stability** - Player metadata (names, teams) rarely changes
2. **Volume** - 2000+ players, large dataset
3. **Efficiency** - One API call serves all users for 48 hours

---

## 🔄 Cache Refresh Strategy

### **Automatic Refresh**
- **Startup:** Fetch player database immediately
- **Background:** None (on-demand only)

### **On-Demand Refresh**
- **Cache Miss:** When user requests data and cache expired
- **Pre-warming:** Before building context (ensures data available)

### **Manual Refresh**
- **Admin Endpoint:** `/api/admin/refresh-cache` (if needed)
- **Health Check:** Shows cache status and TTLs

---

## 💡 Example Conversations

### **Example 1: Waiver Wire Question (Mostly Cached)**
```
User: "Who are the best available centers?"

Data Flow:
1. Static context built from cache (1-2 API calls if cache miss)
2. LLM decides to call: search_available_players(position="C", limit=10)
3. Tool execution:
   - Get rosters: CACHE HIT (30 rosters, TTL 28min)
   - Get players: CACHE HIT (2008 players, TTL 45hrs)
   - Filter/sort: In-memory
4. Return: 10 available centers with stats
5. LLM: Generates personalized recommendation

Total API Calls: 0 (if cache fresh) or 1-2 (if cache miss on startup)
Response Time: ~2-3 seconds
```

---

### **Example 2: Recent Activity Question (Live API)**
```
User: "What trades happened this week?"

Data Flow:
1. Static context built from cache
2. LLM decides to call: get_recent_transactions(limit=20)
3. Tool execution:
   - LIVE API: sleeper.get_league_transactions(league_id)
   - Get player names: CACHE HIT
   - Format results
4. Return: List of 20 recent transactions
5. LLM: Summarizes trades and adds analysis

Total API Calls: 1 (always - transactions are live)
Response Time: ~3-4 seconds
```

---

### **Example 3: Multi-Step Analysis (Mixed)**
```
User: "Should I trade for player X? Compare to my roster and see who's available"

Data Flow:
1. Static context: Your roster (cache)
2. LLM calls: search_player_details("player X")
   - Source: CACHE (instant)
3. LLM calls: search_available_players(position="", limit=15)
   - Source: CACHE + possible API for rosters
4. LLM analyzes:
   - Your roster needs (from static context)
   - Player X details (from tool call #2)
   - Alternative options (from tool call #3)
5. LLM: Generates comprehensive trade analysis

Total API Calls: 0-1 (roster cache miss)
Response Time: ~4-6 seconds (multiple LLM rounds)
```

---

## 🚀 Optimization Opportunities

### **Future Improvements**
1. **Predictive Pre-warming:** Load rosters/matchups during off-hours
2. **Transaction Cache:** Cache recent transactions for 5 minutes
3. **Smart Invalidation:** Webhook from Sleeper to invalidate cache
4. **User-Specific Cache:** Cache user's roster separately for faster access
5. **Compressed Context:** Summarize static context to reduce LLM tokens

---

## 📝 Summary

| Question Type | Primary Data Source | Fallback | Typical API Calls |
|---------------|---------------------|----------|-------------------|
| "Who's on my roster?" | Cache (static context) | N/A | 0 |
| "Who should I start?" | Cache (static context) | N/A | 0 |
| "Who's available at PG?" | Cache (player data + rosters) | Live API for rosters | 0-1 |
| "What's happening in the league?" | Live API (transactions) | N/A | 1 (always) |
| "Show me Team X's roster" | Cache (rosters + league) | Live API if expired | 0-2 |
| "League standings?" | Cache (rosters + league) | Live API if expired | 0-2 |
| "Tell me about LeBron" | Cache (player database) | N/A | 0 |

**Average API Calls Per Chat:** 0-2
**Cache Hit Rate:** ~85% overall
**Typical Response Time:** 2-4 seconds

