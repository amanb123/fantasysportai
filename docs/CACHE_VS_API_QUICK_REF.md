# Quick Reference: Cache vs API Data Sources

## 📋 At-a-Glance Summary

### **Static Context (Built Once Per Message)**
All from **CACHE** - checked before every message:

```
┌─────────────────────────┬──────────────┬─────────────┬──────────────────┐
│ Data Type               │ Source       │ Cache TTL   │ API Call If Miss │
├─────────────────────────┼──────────────┼─────────────┼──────────────────┤
│ League Rules & Scoring  │ Redis Cache  │ 1 hour      │ Yes (1 call)     │
│ Your Roster Players     │ Redis Cache  │ 30 minutes  │ Yes (1 call)     │
│ Player Names/Teams      │ Redis Cache  │ 48 hours    │ No (pre-loaded)  │
│ NBA Schedule (7 days)   │ Redis Cache  │ 24 hours    │ Yes (1 call)     │
│ Injury Statuses         │ Redis Cache  │ 48 hours    │ No (in players)  │
│ Recent Performance      │ Redis Cache  │ 30 minutes  │ Yes (with roster)│
│ Historical NBA Stats    │ NBA.com API  │ No cache    │ Yes (if asked)   │
└─────────────────────────┴──────────────┴─────────────┴──────────────────┘
```

**Total API calls for static context: 0-3** (only if caches expired)

---

### **Dynamic Tools (Called On-Demand by LLM)**

```
┌────────────────────────────────┬─────────────────┬──────────────────────┐
│ Tool Function                  │ Data Source     │ API Calls            │
├────────────────────────────────┼─────────────────┼──────────────────────┤
│ search_available_players()     │ Cache First     │ 0-1 (if roster miss) │
│   • Get rostered players       │ Redis → API     │                      │
│   • Get all NBA players        │ Redis (always)  │                      │
│   • Filter available           │ In-memory       │                      │
│                                │                 │                      │
│ get_opponent_roster()          │ Cache First     │ 0-2 (if miss)        │
│   • Get all rosters            │ Redis → API     │                      │
│   • Get league metadata        │ Redis → API     │                      │
│   • Get player details         │ Redis (always)  │                      │
│                                │                 │                      │
│ get_recent_transactions()      │ ALWAYS LIVE API │ 1 (always)           │
│   • Fetch transactions         │ Sleeper API     │                      │
│   • Get player names           │ Redis Cache     │                      │
│                                │                 │                      │
│ get_all_league_rosters()       │ Cache First     │ 0-2 (if miss)        │
│   • Get all rosters            │ Redis → API     │                      │
│   • Get league metadata        │ Redis → API     │                      │
│   • Sort standings             │ In-memory       │                      │
│                                │                 │                      │
│ search_player_details()        │ ALWAYS CACHE    │ 0 (never)            │
│   • Search player database     │ Redis (always)  │                      │
└────────────────────────────────┴─────────────────┴──────────────────────┘
```

---

## 🎯 Common Question Patterns

### **"What's on my roster?"**
- ✅ Static context only (pre-built)
- 📊 Data: Redis cache
- 🔧 API calls: 0
- ⏱️ Response time: 1-2 seconds

### **"Who should I pick up from waivers?"**
- ✅ Static context + `search_available_players()` tool
- 📊 Data: Redis cache (players + rosters)
- 🔧 API calls: 0-1 (only if roster cache expired)
- ⏱️ Response time: 2-4 seconds

### **"What trades happened recently?"**
- ✅ Static context + `get_recent_transactions()` tool
- 📊 Data: **LIVE Sleeper API** + Redis (player names)
- 🔧 API calls: 1 (always fresh)
- ⏱️ Response time: 3-5 seconds

### **"Show me the league standings"**
- ✅ Static context + `get_all_league_rosters()` tool
- 📊 Data: Redis cache (rosters + league)
- 🔧 API calls: 0-2 (if cache expired)
- ⏱️ Response time: 2-4 seconds

### **"Compare my team to Team Alpha"**
- ✅ Static context (your roster) + `get_opponent_roster("Team Alpha")` tool
- 📊 Data: Redis cache
- 🔧 API calls: 0-2 (if cache expired)
- ⏱️ Response time: 3-5 seconds

---

## 🔄 Cache Refresh Logic

### **Startup (Server Starts)**
```
1. Connect to Redis
2. Fetch ALL NBA players from Sleeper → Cache for 48 hours
3. Ready to serve requests
```

### **First Chat Message in a Session**
```
1. Check league cache → If MISS: API call + cache 1hr
2. Check roster cache → If MISS: API call + cache 30min
3. Check matchup cache → If MISS: API call + cache 1hr
4. Build static context from cached data
5. Ready for LLM
```

### **Subsequent Messages (Same Session)**
```
1. Reuse cached data (likely still fresh)
2. Only call API if cache expired
3. Tool calls may trigger additional API calls (on-demand)
```

### **Cache Miss Scenarios**
- **League expired (1hr):** 1 API call to refresh
- **Rosters expired (30min):** 1 API call to refresh
- **Players expired (48hr):** Already auto-refreshed at startup
- **Transactions:** ALWAYS fetch live (no cache)

---

## 💾 Redis Cache Keys

```bash
# Global player database (all users share this)
sleeper:players:nba → 2000+ players, TTL: 48hr

# League-specific data
sleeper:league:1234567890 → League details, TTL: 1hr
sleeper:rosters:1234567890 → All team rosters, TTL: 30min
sleeper:matchups:1234567890:1 → Week 1 matchups, TTL: 1hr

# NBA schedule data
nba:schedule:2025-10-16 → Games for that date, TTL: 24hr
```

---

## ⚡ Performance Optimization

### **Why Cache-First Strategy?**
1. **Speed:** Redis lookup = ~5ms vs API call = ~500ms (100x faster)
2. **Reliability:** Works even if Sleeper API is down/slow
3. **Rate Limits:** Sleeper API has rate limits (~1000 req/min)
4. **Cost:** Fewer external API calls = lower infrastructure cost

### **Why Live API for Transactions?**
1. **Freshness:** Users expect real-time transaction data
2. **Volatility:** Transactions happen frequently
3. **Small Dataset:** Only fetching recent transactions (not huge)

---

## 🎨 Typical Chat Flow Example

**User:** "Who are the best available point guards I should target?"

```
STEP 1: Build Static Context
├─ League rules ────────── CACHE (Redis) ✓
├─ Your roster ────────── CACHE (Redis) ✓
├─ Player database ────── CACHE (Redis) ✓
├─ Schedule ────────────── CACHE (Redis) ✓
└─ Recent performance ──── CACHE (Redis) ✓
                          📊 0 API calls

STEP 2: LLM Analyzes Question
├─ Identifies need for waiver wire data
├─ Decides to call: search_available_players(position="PG", limit=10)
└─ Sends tool call request

STEP 3: Execute Tool
├─ Get rostered players ── CACHE HIT (30min fresh) ✓
├─ Get all players ────── CACHE HIT (48hr fresh) ✓
├─ Filter by position PG ── In-memory
├─ Exclude rostered ────── In-memory
├─ Sort by relevance ───── In-memory
└─ Return top 10 ──────── String result
                          📊 0 API calls (cache hit)

STEP 4: LLM Generates Answer
├─ Analyzes your roster needs
├─ Reviews top 10 available PGs
├─ Compares to league scoring (blocks = 3pts, assists = 2pts)
└─ Recommends: "Tyus Jones - excellent assist numbers (2pts each)"

TOTAL: 0 API calls, ~2-3 seconds response time
```

---

## 📊 Expected Cache Hit Rates

Based on typical usage patterns:

| Cache Type | Expected Hit Rate | Reasoning |
|------------|-------------------|-----------|
| **Player Database** | ~99% | Refreshed every 48hrs, stable data |
| **Rosters** | ~80% | 30min TTL, checked every message |
| **League Details** | ~90% | 1hr TTL, rarely changes |
| **Matchups** | ~70% | 1hr TTL, weekly rotation |
| **NBA Schedule** | ~95% | 24hr TTL, stable schedule |

**Overall Cache Hit Rate: ~85%**

This means approximately **85% of chat messages require 0-1 API calls** total.

---

## 🚀 Future Optimizations

1. **Predictive Cache Warming**
   - Pre-fetch rosters during off-peak hours
   - Anticipate common queries (standings, waivers)

2. **User-Specific Cache**
   - Cache each user's roster separately
   - Faster context building for frequent users

3. **Smart Invalidation**
   - Webhook from Sleeper to invalidate on roster changes
   - Real-time cache updates when trades happen

4. **Compressed Context**
   - Summarize static context to reduce tokens
   - More room for tool responses

5. **Transaction Mini-Cache**
   - Cache transactions for 5 minutes
   - Reduce redundant API calls within same session

