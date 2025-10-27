# Roster Chat System Architecture

## 🏗️ System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                             │
│                          http://localhost:3000                            │
├──────────────────────────────────────────────────────────────────────────┤
│  • TradeNegotiationView.jsx                                              │
│  • ConversationHistory.jsx                                               │
│  • WebSocket Client (real-time updates)                                  │
└────────────────┬─────────────────────────────────────┬───────────────────┘
                 │                                     │
                 │ HTTP (Chat Messages)                │ WebSocket (Live Updates)
                 │                                     │
┌────────────────▼─────────────────────────────────────▼───────────────────┐
│                       BACKEND (FastAPI)                                   │
│                    http://localhost:3002                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    API ENDPOINTS (main.py)                        │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │  POST /api/roster-chat/start                                     │   │
│  │    • Creates new chat session                                    │   │
│  │    • Generates welcome message                                   │   │
│  │                                                                   │   │
│  │  POST /api/roster-chat/{session_id}/message                      │   │
│  │    • Main chat endpoint ⭐                                        │   │
│  │    • Orchestrates entire flow                                    │   │
│  │                                                                   │   │
│  │  GET /api/roster-chat/{session_id}/history                       │   │
│  │    • Retrieves chat history                                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                            │
│                              ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              ORCHESTRATION LAYER                                  │   │
│  │                                                                   │   │
│  │  1️⃣ Validate Session                                             │   │
│  │  2️⃣ Save User Message                                            │   │
│  │  3️⃣ Pre-warm Caches (if needed)                                  │   │
│  │  4️⃣ Build Static Context                                         │   │
│  │  5️⃣ Initialize Tools                                             │   │
│  │  6️⃣ Create LLM Agent                                             │   │
│  │  7️⃣ Send to OpenAI                                               │   │
│  │  8️⃣ Execute Tool Calls (if requested)                            │   │
│  │  9️⃣ Save & Broadcast Response                                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                            │
│         ┌────────────────────┼────────────────────┐                     │
│         ▼                    ▼                    ▼                     │
│  ┌─────────────┐   ┌──────────────────┐   ┌──────────────┐            │
│  │  Database   │   │  Cache Services  │   │  LLM Agent   │            │
│  │   Layer     │   │      Layer       │   │    Layer     │            │
│  └─────────────┘   └──────────────────┘   └──────────────┘            │
│         │                    │                    │                     │
└─────────┼────────────────────┼────────────────────┼─────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
```

---

## 📦 Layer-by-Layer Breakdown

### **1️⃣ Database Layer**
```
┌─────────────────────────────────────────────────────────────┐
│                    SQLite Database                           │
│              (test_fantasy_db.db)                            │
├─────────────────────────────────────────────────────────────┤
│  Tables:                                                     │
│  • roster_chat_sessions                                      │
│    - session_id, league_id, roster_id, user_id              │
│    - status, created_at                                      │
│                                                              │
│  • roster_chat_messages                                      │
│    - message_id, session_id, role, content                   │
│    - timestamp, metadata                                     │
│                                                              │
│  Repository Pattern:                                         │
│  • session/repository.py                                     │
│  • Uses session.expunge() to prevent DetachedInstanceError   │
└─────────────────────────────────────────────────────────────┘
```

**Purpose:** Persist chat sessions and message history
**Data:** Chat messages, session metadata
**Access Pattern:** Read chat history, write new messages

---

### **2️⃣ Cache Services Layer**
```
┌──────────────────────────────────────────────────────────────────┐
│                      Redis Cache                                  │
│                 (localhost:6379)                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  PlayerCacheService                                         │  │
│  │  • Key: sleeper:players:nba                                 │  │
│  │  • TTL: 48 hours                                            │  │
│  │  • Data: {player_id: {name, team, positions, injury}}      │  │
│  │  • Size: ~2000 players                                      │  │
│  │  • Methods:                                                 │  │
│  │    - get_cached_players() → All players                    │  │
│  │    - get_players_bulk([ids]) → Specific players            │  │
│  │    - get_player_by_id(id) → Single player                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  LeagueDataCacheService                                     │  │
│  │  • Keys:                                                    │  │
│  │    - sleeper:league:{league_id} (TTL: 1hr)                 │  │
│  │    - sleeper:rosters:{league_id} (TTL: 30min)              │  │
│  │    - sleeper:matchups:{league_id}:{week} (TTL: 1hr)        │  │
│  │  • Methods:                                                 │  │
│  │    - get_cached_league_details(id) → League info           │  │
│  │    - get_cached_rosters(id) → All team rosters             │  │
│  │    - get_cached_matchups(id, week) → Weekly matchups       │  │
│  │    - cache_league_data(id) → Fetch & cache from API        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  NBACacheService                                            │  │
│  │  • Key: nba:schedule:{date} (TTL: 24hr)                    │  │
│  │  • Data: NBA game schedule                                  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

**Purpose:** Fast data access, reduce API calls
**Data:** Player info, league data, rosters, schedules
**Access Pattern:** Check cache first, fallback to API

---

### **3️⃣ Context Builder Layer**
```
┌──────────────────────────────────────────────────────────────────┐
│               RosterContextBuilder                                │
│         (services/roster_context_builder.py)                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  build_roster_context() → Builds static context string           │
│  │                                                                │
│  ├─ 1️⃣ _get_league_rules_context()                               │
│  │   • Scoring categories, roster positions                      │
│  │   • Source: league_cache.get_cached_league_details()          │
│  │                                                                │
│  ├─ 2️⃣ _get_roster_summary()                                     │
│  │   • Your starters, bench, record                              │
│  │   • Source: league_cache + player_cache                       │
│  │                                                                │
│  ├─ 3️⃣ _fetch_historical_stats_if_needed()                       │
│  │   • NBA historical stats (if user asks)                       │
│  │   • Source: nba_api → NBA.com                                 │
│  │                                                                │
│  ├─ 4️⃣ _get_schedule_context()                                   │
│  │   • Next 7 days of games                                      │
│  │   • Source: nba_cache                                         │
│  │                                                                │
│  ├─ 5️⃣ _get_injury_context()                                     │
│  │   • Injury report for rostered players                        │
│  │   • Source: player_cache                                      │
│  │                                                                │
│  └─ 6️⃣ _get_recent_performance_context()                         │
│      • Last 2 weeks fantasy scoring                              │
│      • Source: league_cache.get_cached_matchups()                │
│                                                                    │
│  📤 Output: ~1500 char formatted context string                  │
└──────────────────────────────────────────────────────────────────┘
```

**Purpose:** Prepare static context for LLM
**Data:** Aggregated info from all caches
**Access Pattern:** Called once per chat message

---

### **4️⃣ LLM Agent Layer**
```
┌──────────────────────────────────────────────────────────────────┐
│                    SimpleAssistantAgent                           │
│              (agents/agent_factory.py)                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  __init__(system_message, tools, tool_executor)                  │
│  │                                                                │
│  │  System Message:                                              │
│  │  • Static context (from RosterContextBuilder)                 │
│  │  • Instructions for using tools                               │
│  │  • Persona and guidelines                                     │
│  │                                                                │
│  │  Tools: [5 function definitions]                              │
│  │  • search_available_players()                                 │
│  │  • get_opponent_roster()                                      │
│  │  • get_recent_transactions()                                  │
│  │  • get_all_league_rosters()                                   │
│  │  • search_player_details()                                    │
│  │                                                                │
│  │  Tool Executor: RosterAdvisorTools instance                   │
│  │                                                                │
│  └─────────────────────────────────────────────────────────────  │
│                                                                    │
│  a_generate_reply(messages) → async LLM call                     │
│  │                                                                │
│  ├─ Try Ollama First (local, llama2)                             │
│  │  • POST http://localhost:11434/api/chat                       │
│  │  • No function calling support                                │
│  │  • Fallback if fails                                          │
│  │                                                                │
│  └─ OpenAI GPT-3.5-turbo (cloud, with function calling)          │
│     • POST https://api.openai.com/v1/chat/completions            │
│     • Supports function calling ⭐                                │
│     • Tool call loop (max 5 iterations)                          │
│     • Returns final response                                     │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

**Purpose:** Manage LLM interaction and function calling
**Data:** Messages, system context, tool calls
**Access Pattern:** Called once per chat message, may loop for tools

---

### **5️⃣ Tool Execution Layer**
```
┌──────────────────────────────────────────────────────────────────┐
│                   RosterAdvisorTools                              │
│                  (agents/tools.py)                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  __init__(league_id, roster_id, league_cache, player_cache,      │
│           sleeper_service)                                        │
│                                                                    │
│  execute_tool(tool_name, arguments) → Formatted string result    │
│  │                                                                │
│  ├─ search_available_players(position, limit)                    │
│  │  1. Get rostered players → Cache → API fallback               │
│  │  2. Get all players → Cache only                              │
│  │  3. Filter available → In-memory                              │
│  │  4. Return formatted list                                     │
│  │                                                                │
│  ├─ get_opponent_roster(team_name)                               │
│  │  1. Get all rosters → Cache → API fallback                    │
│  │  2. Get league details → Cache → API fallback                 │
│  │  3. Find matching team → In-memory                            │
│  │  4. Get player details → Cache only                           │
│  │  5. Return formatted roster                                   │
│  │                                                                │
│  ├─ get_recent_transactions(limit)                               │
│  │  1. Fetch transactions → ALWAYS API ⚠️                        │
│  │  2. Get player names → Cache only                             │
│  │  3. Format transaction list                                   │
│  │                                                                │
│  ├─ get_all_league_rosters()                                     │
│  │  1. Get all rosters → Cache → API fallback                    │
│  │  2. Get league metadata → Cache → API fallback                │
│  │  3. Sort by standings → In-memory                             │
│  │  4. Return formatted standings                                │
│  │                                                                │
│  └─ search_player_details(player_name)                           │
│     1. Search player database → Cache only                       │
│     2. Fuzzy match name → In-memory                              │
│     3. Return player info                                        │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

**Purpose:** Execute LLM-requested function calls
**Data:** Real-time Sleeper/cache data
**Access Pattern:** Called 0-5 times per chat message (on-demand)

---

### **6️⃣ External Services**
```
┌──────────────────────────────────────────────────────────────────┐
│                     External APIs                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Sleeper API (https://api.sleeper.app)                     │  │
│  │  • get_league(league_id)                                   │  │
│  │  • get_league_rosters(league_id)                           │  │
│  │  • get_matchups(league_id, week)                           │  │
│  │  • get_league_transactions(league_id)                      │  │
│  │  • get_nba_players() → All NBA players                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  NBA API (stats.nba.com) via nba_api library              │  │
│  │  • Player career stats                                     │  │
│  │  • Historical season stats                                 │  │
│  │  • Date range averages                                     │  │
│  │  • Used only for historical queries                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  OpenAI API (api.openai.com)                               │  │
│  │  • GPT-3.5-turbo (function calling)                        │  │
│  │  • Fallback from Ollama                                    │  │
│  │  • Requires API key                                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Ollama (localhost:11434) [Optional]                       │  │
│  │  • llama2 model (local LLM)                                │  │
│  │  • No function calling support                             │  │
│  │  • Tried first, fallback to OpenAI                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Message Flow Sequence

```
1. User types: "Who should I pick up from waivers?"
   │
   ▼
2. Frontend sends POST /api/roster-chat/{session_id}/message
   │
   ▼
3. Backend: Validate session (SQLite)
   │
   ▼
4. Backend: Save user message (SQLite)
   │
   ▼
5. Backend: Pre-warm caches
   ├─ Check league cache → HIT (fresh) ✓
   ├─ Check roster cache → MISS → API call → Cache
   └─ Check matchup cache → HIT (fresh) ✓
   │
   ▼
6. Backend: Build static context
   ├─ League rules (from cache)
   ├─ Your roster (from cache)
   ├─ Schedule (from cache)
   ├─ Injury report (from cache)
   └─ Recent performance (from cache)
   │
   ▼
7. Backend: Initialize tools
   └─ RosterAdvisorTools(league_cache, player_cache, sleeper_service)
   │
   ▼
8. Backend: Create LLM agent
   └─ SimpleAssistantAgent(system_message, tools, tool_executor)
   │
   ▼
9. Backend: Send to OpenAI GPT-3.5
   ├─ Messages: [system, history..., user_message]
   ├─ Tools: 5 function definitions
   └─ tool_choice: "auto"
   │
   ▼
10. OpenAI: Analyzes request
    └─ Decision: Need waiver wire data → Call search_available_players()
    │
    ▼
11. Backend: Execute tool call
    ├─ Get rostered players (from cache)
    ├─ Get all players (from cache)
    ├─ Filter available + position
    └─ Return top 10 available players
    │
    ▼
12. Backend: Send tool result back to OpenAI
    │
    ▼
13. OpenAI: Generate final response
    └─ "Based on your needs, I recommend: 1. John Collins..."
    │
    ▼
14. Backend: Save assistant message (SQLite)
    │
    ▼
15. Backend: Broadcast via WebSocket
    │
    ▼
16. Frontend: Display response in chat UI
```

**Total Time:** ~3-4 seconds
**API Calls:** 1 (roster cache miss) + 1-2 (OpenAI rounds)

---

## 📊 Data Flow Summary

| Step | Component | Data Source | API Calls |
|------|-----------|-------------|-----------|
| 1-4 | Message Handling | SQLite | 0 |
| 5 | Cache Pre-warming | Redis → Sleeper API | 0-3 |
| 6 | Context Building | Redis Cache | 0 |
| 7-8 | Tool Initialization | N/A | 0 |
| 9-10 | LLM Request | OpenAI API | 1 |
| 11 | Tool Execution | Redis → Sleeper API | 0-2 |
| 12-13 | LLM Response | OpenAI API | 1 |
| 14-16 | Response Handling | SQLite + WebSocket | 0 |

**Total:** 2-8 API calls per message (varies by cache state and tool usage)

