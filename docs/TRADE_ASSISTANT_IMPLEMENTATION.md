# Trade Assistant Implementation Progress

## ✅ Completed Components (Backend)

### 1. Database Layer
- **File:** `backend/session/models.py`
  - Added `TradeAnalysisSessionModel` (lines 513-592)
  - Fields: session_id, rosters, players (in/out), analysis_result, favorability_score, simulation_result, status
  - Indexes on session_id, sleeper_user_id, league_id, created_at
  - `to_pydantic()` method for JSON parsing

- **File:** `backend/session/repository.py`
  - Added 5 trade analysis methods (lines 1823-2030):
    - `create_trade_analysis_session()` - Create new analysis
    - `get_trade_analysis_session()` - Retrieve by UUID
    - `update_trade_analysis_result()` - Save AI analysis
    - `update_trade_simulation_result()` - Save matchup simulation
    - `get_user_trade_analyses()` - Get user history

### 2. AI Agent Layer
- **File:** `backend/agents/agent_factory.py`
  - Added `create_trade_analyzer_agent()` method (lines 640-720)
  - Creates SimpleAssistantAgent for trade evaluation
  - Structured JSON output: pros, cons, favorability_score, reasoning, recommendation
  - Scoring guidelines: 0-30 (reject), 31-45 (unfavorable), 46-54 (fair), 55-70 (favorable), 71-100 (accept)

### 3. Business Logic Services
- **File:** `backend/services/trade_analysis_service.py` (NEW)
  - `analyze_trade()` - Main orchestration method
  - `build_trade_analysis_context()` - Builds comprehensive markdown context for LLM
  - `_format_league_scoring()` - Formats scoring settings as table
  - `_format_roster_with_trade()` - Shows before/after roster comparison
  - `_format_player_stats()` - Fetches player stats via NBA MCP
  - `_calculate_roster_stats_via_mcp()` - Gets season averages
  - `_get_upcoming_games_count_via_mcp()` - Schedule strength (next 7 days)

- **File:** `backend/services/matchup_simulation_service.py` (NEW)
  - `simulate_next_weeks()` - Main simulation (default 3 weeks)
  - `_calculate_projected_points_via_mcp()` - Fantasy points for roster
  - `_get_player_projection_via_mcp()` - Per-player projection
  - `_calculate_fantasy_points()` - Apply league scoring formula
  - `_calculate_win_probability()` - Logistic model for win probability

### 4. API Layer
- **File:** `backend/api_models.py`
  - Added 7 Pydantic models:
    - `RecentTradeResponse` - Recent completed trades
    - `TradeAnalysisStartRequest` - Request to start analysis
    - `TradeAnalysisStartResponse` - Analysis started response
    - `TradeAnalysisResultResponse` - Analysis result with AI output
    - `TradeSimulationRequest` - Request matchup simulation
    - `TradeSimulationResponse` - Simulation result
    - `TradeAnalysisSessionListResponse` - User's analysis history

- **File:** `backend/main.py`
  - Added 5 API endpoints (lines 1357-1709):
    1. `GET /api/trade-assistant/recent-trades/{league_id}` - Fetch recent trades for reference
    2. `POST /api/trade-assistant/analyze` - Start AI trade analysis
    3. `GET /api/trade-assistant/analysis/{session_id}` - Get analysis result
    4. `POST /api/trade-assistant/simulate` - Run matchup simulation
    5. `GET /api/trade-assistant/sessions` - Get user's analysis history

### 5. Dependency Injection
- **File:** `backend/dependencies.py`
  - Added `get_trade_analysis_service()` - Singleton TradeAnalysisService
  - Added `get_matchup_simulation_service()` - Singleton MatchupSimulationService
  - Both require NBA MCP service (graceful degradation if unavailable)

---

## ⏳ Pending Components (Frontend + Docs)

### Frontend (Not Started)
- [ ] `frontend/src/components/TradeAssistant.jsx` - Main UI component
  - Multi-step form (select rosters, input players, view analysis)
  - Recent trades section for reference
  - AI analysis display (pros/cons, score, recommendation)
  - Matchup simulation visualization
- [ ] `frontend/src/components/RosterDisplay.jsx` - Add "Trade Assistant" button
- [ ] `frontend/src/App.jsx` - Add `/trade-assistant` route
- [ ] `frontend/src/services/api.js` - Add 5 API functions:
  - `getRecentTrades(leagueId)`
  - `startTradeAnalysis(request)`
  - `getTradeAnalysisResult(sessionId)`
  - `simulateMatchup(sessionId, weeks)`
  - `getUserTradeAnalyses(sleeperUserId, leagueId)`

### Configuration & Documentation
- [ ] `backend/config.py` - Add Trade Assistant settings:
  - `TRADE_ANALYSIS_TIMEOUT` (default: 60 seconds)
  - `MAX_PLAYERS_PER_TRADE` (default: 4)
  - `SIMULATION_WEEKS` (default: 3)
- [ ] `.env.example` - Document new environment variables
- [ ] `backend/session/database.py` - Add migration helper:
  - `ensure_trade_analysis_tables()` - Create tables on startup
- [ ] `README.md` - Update documentation:
  - Trade Assistant overview section
  - API endpoint documentation
  - Usage examples
  - Architecture diagram
  - Limitations (Sleeper API doesn't expose pending trades)

---

## 🔧 Testing & Validation

### Backend Ready to Test
```bash
# 1. Ensure NBA MCP server is running
cd nba-mcp-server
python nba_server.py

# 2. Start backend
cd backend
python main.py

# 3. Test endpoints
curl -X GET "http://localhost:8000/api/trade-assistant/recent-trades/YOUR_LEAGUE_ID"

curl -X POST "http://localhost:8000/api/trade-assistant/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "league_id": "YOUR_LEAGUE_ID",
    "sleeper_user_id": "YOUR_USER_ID",
    "user_roster_id": 1,
    "opponent_roster_id": 2,
    "user_players_out": ["player_id_1"],
    "user_players_in": ["player_id_2"]
  }'

# 4. Get analysis result
curl -X GET "http://localhost:8000/api/trade-assistant/analysis/SESSION_ID"
```

### Known Dependencies
- **NBA MCP Server** - Must be running at path specified in `NBA_MCP_SERVER_PATH`
- **Redis** - Required for schedule cache
- **OpenAI API Key** - Required for AI agent (set in `.env`)

---

## 📊 Architecture Overview

```
User Input (Frontend)
    ↓
API Endpoints (main.py)
    ↓
Services Layer
    ├── TradeAnalysisService (builds context, calls AI)
    │   ├── NBAMCPService (player stats, schedule)
    │   ├── SleeperService (league settings, rosters)
    │   └── AgentFactory (creates trade analyzer agent)
    │       └── SimpleAssistantAgent (OpenAI GPT analysis)
    └── MatchupSimulationService (fantasy point projections)
        ├── NBAMCPService (schedule, stats)
        └── SleeperService (league scoring, rosters)
    ↓
Repository Layer (database.py)
    ↓
Database (SQLite)
    └── trade_analysis_sessions table
```

---

## 🎯 Key Features Implemented

1. **AI-Powered Analysis**
   - Evaluates trades from user's perspective
   - Considers league scoring weights
   - Analyzes player stats, schedule, injury status
   - Provides pros/cons with data-driven reasoning
   - Returns favorability score (0-100) and recommendation

2. **Matchup Simulation**
   - Projects fantasy points for next 3 weeks
   - Compares scenarios (with/without trade)
   - Calculates win probability using logistic model
   - Accounts for upcoming game schedule

3. **Recent Trades Reference**
   - Fetches completed trades from Sleeper API
   - Helps users understand league trade market
   - Note: Sleeper only exposes completed trades

4. **Session Management**
   - Persistent storage of all analyses
   - User can review historical trade evaluations
   - Filter by league and date

---

## 💡 Implementation Notes

### Why NBA MCP Instead of Sleeper Stats?
- Sleeper provides basic player info but no detailed stats
- NBA MCP offers career stats, game logs, recent performance
- Schedule cache enables "games played next week" analysis

### Trade Context Building
The LLM receives comprehensive context:
- League scoring settings (formatted table)
- Current roster composition
- Player season averages (PPG, RPG, APG, FG%, 3P%)
- Upcoming games in next 7 days
- Injury status
- Before/after roster comparison

### Background Task Pattern
- Analysis and simulation run async (can take 10-30 seconds)
- Immediate response with session_id
- Client polls `/api/trade-assistant/analysis/{session_id}` for results
- Status field: "analyzing" → "completed" / "failed"

### Error Handling
- Graceful degradation if NBA MCP unavailable
- Returns 503 with clear error message
- Failed analyses marked with status="failed"
- Stats fetch failures logged but don't block analysis

---

## 🚀 Next Steps

1. **Immediate (High Priority)**
   - Add `ensure_trade_analysis_tables()` to `database.py`
   - Update `.env.example` with trade assistant config
   - Test backend endpoints with Postman/curl

2. **Frontend Implementation**
   - Build TradeAssistant.jsx component
   - Add API integration functions
   - Design UI for analysis results display
   - Add route and navigation

3. **Documentation**
   - Update README.md with Trade Assistant section
   - Add API documentation with examples
   - Create user guide
   - Document limitations (Sleeper API)

4. **Enhancements (Future)**
   - Add trade proposal saving/sharing
   - Email/webhook notifications when analysis complete
   - Historical trade success tracking
   - League-wide trade market insights
   - Multi-player trade support (currently 1-for-1 to N-for-N)

---

## 📝 Changelog

**2024-12-XX - Backend Complete**
- ✅ Database models and repository methods
- ✅ AI agent for trade analysis
- ✅ Trade analysis service with NBA MCP integration
- ✅ Matchup simulation service
- ✅ API endpoints (5 endpoints)
- ✅ Dependency injection setup
- ✅ Error handling and logging
- ⏳ Frontend components (pending)
- ⏳ Documentation updates (pending)
