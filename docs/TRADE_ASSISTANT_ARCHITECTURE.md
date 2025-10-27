# Trade Assistant Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React)                            │
│                        Port 3001 (Vite)                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────┐      ┌──────────────────────┐             │
│  │  RosterDisplay     │─────▶│  TradeAssistant      │             │
│  │  (Entry Point)     │      │  (Main Component)    │             │
│  └────────────────────┘      └──────────────────────┘             │
│           │                            │                            │
│           │                            │                            │
│           ▼                            ▼                            │
│  ┌─────────────────────────────────────────────────┐              │
│  │          services/api.js                         │              │
│  │  • getRecentTrades()                            │              │
│  │  • startTradeAnalysis()                         │              │
│  │  • getTradeAnalysisResult()                     │              │
│  │  • simulateMatchup()                            │              │
│  │  • getUserTradeAnalyses()                       │              │
│  └─────────────────────────────────────────────────┘              │
│                          │                                          │
└──────────────────────────┼──────────────────────────────────────────┘
                           │ HTTP/REST
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                             │
│                      Port 3002 (Uvicorn)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                      main.py                                │   │
│  │  5 Trade Assistant Endpoints:                               │   │
│  │  • GET  /api/trade-assistant/recent-trades/{league_id}     │   │
│  │  • POST /api/trade-assistant/analyze                        │   │
│  │  • GET  /api/trade-assistant/analysis/{session_id}         │   │
│  │  • POST /api/trade-assistant/simulate                       │   │
│  │  • GET  /api/trade-assistant/sessions                       │   │
│  └────────────────────────────────────────────────────────────┘   │
│                          │                                          │
│                          ▼                                          │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              services/ (Business Logic)                     │   │
│  │                                                             │   │
│  │  ┌───────────────────────────────────────────────┐        │   │
│  │  │  TradeAnalysisService                          │        │   │
│  │  │  • analyze_trade()                             │        │   │
│  │  │  • _fetch_league_context()                     │        │   │
│  │  │  • _calculate_roster_stats_via_mcp()          │        │   │
│  │  │  • Enhanced JSON parsing ✨                   │        │   │
│  │  └───────────────────────────────────────────────┘        │   │
│  │           │              │              │                   │   │
│  │           ▼              ▼              ▼                   │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐       │   │
│  │  │ SleeperSvc   │ │ NBAMCPSvc    │ │ AgentFactory│       │   │
│  │  │ • get_league │ │ • get_player │ │ • GPT-4     │       │   │
│  │  │ • get_roster │ │   _stats()   │ │   Analysis  │       │   │
│  │  │ • get_trans  │ │ • get_scheds │ └─────────────┘       │   │
│  │  └──────────────┘ └──────────────┘                        │   │
│  │                                                             │   │
│  │  ┌───────────────────────────────────────────────┐        │   │
│  │  │  MatchupSimulationService                      │        │   │
│  │  │  • simulate_matchup()                          │        │   │
│  │  │  • _get_player_projection_via_mcp()           │        │   │
│  │  └───────────────────────────────────────────────┘        │   │
│  └────────────────────────────────────────────────────────────┘   │
│                          │                                          │
│                          ▼                                          │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              session/ (Data Layer)                          │   │
│  │                                                             │   │
│  │  ┌──────────────────┐      ┌──────────────────┐           │   │
│  │  │  Repository       │      │  Database        │           │   │
│  │  │  • CRUD ops       │─────▶│  (SQLite)        │           │   │
│  │  │  • Session mgmt   │      │  • Models        │           │   │
│  │  │  • Expunge fix ✨ │      │  • Persistence   │           │   │
│  │  └──────────────────┘      └──────────────────┘           │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Sleeper API  │  │  NBA MCP     │  │  OpenAI      │             │
│  │ • League data│  │  • Stats     │  │  • GPT-4     │             │
│  │ • Rosters    │  │  • Schedules │  │  • Analysis  │             │
│  │ • Trades     │  │  • Projections│  │              │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

DATA FLOW:
==========

1. USER ACTION: Click "Trade Assistant" on Roster Display
   ↓
2. NAVIGATE: React Router → /trade-assistant
   ↓
3. RENDER: TradeAssistant component with form
   ↓
4. INPUT: User enters opponent ID and player IDs
   ↓
5. SUBMIT: POST /api/trade-assistant/analyze
   ↓
6. BACKEND: FastAPI endpoint receives request
   ↓
7. DATABASE: Create TradeAnalysis session (status: analyzing)
   ↓
8. BACKGROUND: Start async analysis task
   │   ├─ Fetch league settings (Sleeper)
   │   ├─ Fetch rosters (Sleeper)
   │   ├─ Get player stats (NBA MCP)
   │   ├─ Generate AI analysis (OpenAI GPT-4)
   │   ├─ Parse JSON response (with fallback)
   │   └─ Update database (status: completed)
   ↓
9. RESPONSE: Return session_id to frontend
   ↓
10. POLL: Frontend polls GET /analysis/{session_id} every 2 seconds
   ↓
11. COMPLETE: Backend returns completed analysis
   ↓
12. DISPLAY: Show favorability score, pros/cons, recommendation
   ↓
13. HISTORY: Session saved in database for future reference

KEY FEATURES:
=============

✨ Enhanced JSON Parsing (Lines 68-134 in trade_analysis_service.py)
   - Logs raw LLM response
   - Removes markdown fences
   - Finds JSON boundaries
   - Provides structured fallback
   - Fills missing fields

✨ Session Expunge Fix (Lines 1900, 2010-2013 in repository.py)
   - Detaches SQLModel objects before returning
   - Prevents SQLAlchemy binding errors

✨ Real-time Polling (TradeAssistant.jsx)
   - Checks status every 2 seconds
   - Shows progress indicator
   - Stops on completion/failure

✨ Background Processing
   - Non-blocking API responses
   - FastAPI BackgroundTasks
   - Scalable architecture

TESTING:
========

Backend: python test_trade_assistant.py
   ✅ All 5 endpoints
   ✅ 8 sessions created
   ✅ JSON parsing working

Frontend: http://localhost:3001
   ✅ Component renders
   ✅ Form validation
   ✅ API integration
   ✅ Result display
