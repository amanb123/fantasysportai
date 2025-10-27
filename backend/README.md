# Fantasy Basketball League Backend

This is the backend API for the Fantasy Basketball League application, built with FastAPI.

## Features

### Roster Assistant Chat

The Roster Assistant provides AI-powered roster advice and player analysis using existing Sleeper and NBA APIs (no MCP servers needed).

**Capabilities:**
- Analyze current roster strengths and weaknesses
- Provide lineup optimization advice based on lock-in rules
- Suggest waiver wire pickups and drops
- Analyze matchup advantages for upcoming week
- Answer historical stats questions ("what was LeBron's average in 2022?")
- Explain Sleeper lock-in mechanics and league-specific scoring

**Key Features:**
- Real-time chat interface with WebSocket support
- On-demand historical stats fetching using nba_api
- League-specific context (scoring settings, roster positions, lock-in rules)
- Current roster analysis with injury status
- Upcoming schedule awareness
- Recent performance tracking

### Roster Chat Endpoints

**`POST /api/roster-chat/start`** - Start new chat session
- Creates a new roster chat session
- Optionally accepts initial message
- Returns session_id for WebSocket connection

**`POST /api/roster-chat/{session_id}/message`** - Send message and get response
- Sends user message to chat session
- LLM generates response with full context
- Automatically fetches historical stats if query detected
- Broadcasts response via WebSocket

**`GET /api/roster-chat/{session_id}/history`** - Get full chat history
- Retrieves all messages for a session
- Returns complete conversation with timestamps

**`GET /api/roster-chat/sessions`** - Get user's chat sessions
- Lists all chat sessions for a Sleeper user
- Optional filter by league_id
- Returns session metadata

**`DELETE /api/roster-chat/{session_id}`** - Archive session
- Archives a chat session (soft delete)
- Preserves history for future reference

**`WS /ws/roster-chat/{session_id}`** - WebSocket for real-time updates
- Real-time message delivery
- Bi-directional communication
- Automatic reconnection support

### Historical Stats Integration

The LLM can fetch historical NBA stats on-demand when users ask historical questions.

**Capabilities:**
- Player career stats (all seasons)
- Season averages (specific season)
- Game logs (individual games)
- Date range queries ("around this time last year")

**Data Sources:**
- `nba_api` library for historical data
- Sleeper API for current rosters and leagues
- NBA CDN for schedules

**Caching Strategy:**
- Historical data cached for 7 days (doesn't change)
- 0.6s delay between nba_api requests (rate limiting)
- Redis caching for frequently requested data

**Example Historical Queries:**
- "What was Giannis's scoring average in 2022?"
- "How did LeBron perform around this time last year?"
- "Show me Curry's career stats"
- "What were Anthony Davis's stats last season?"

### League Rules Context

The LLM understands Sleeper league rules by fetching league settings from the Sleeper API.

**League Settings Fetched:**
- Scoring settings: Point values for each stat category (pts, reb, ast, stl, blk, tov, etc.)
- Roster positions: Required position slots (PG, SG, SF, PF, C, G, F, UTIL, BENCH)
- Lock-in mode mechanics: One game per week per player, must lock before next game
- Waiver rules, trade deadlines, playoff structure

**Context Building:**
- League rules formatted as markdown for LLM
- Current roster with player positions and injury status
- Upcoming schedule (next 7 days)
- Recent performance (last 2 weeks)
- Dynamically includes historical stats when relevant

**Token Management:**
- Max context: ~3000 tokens
- Prioritization: league rules > roster > historical stats > schedule > performance
- Automatic truncation if context exceeds limit

## Environment Variables

### Roster Chat Configuration

```bash
# Max messages to include in LLM context (manages token usage)
ROSTER_CHAT_MAX_HISTORY_MESSAGES=10

# Estimated max tokens for context (league rules + roster + historical stats)
ROSTER_CHAT_MAX_CONTEXT_TOKENS=3000

# Enable on-demand historical stats fetching when user asks historical questions
ROSTER_CHAT_ENABLE_HISTORICAL_STATS=true

# Max seasons to fetch for historical queries (prevents excessive API calls)
ROSTER_CHAT_HISTORICAL_STATS_MAX_SEASONS=3
```

### NBA Historical Stats Configuration

```bash
# Historical data doesn't change, cache for 7 days (604800 seconds)
NBA_HISTORICAL_STATS_CACHE_TTL=604800

# Redis key prefix for historical stats
NBA_HISTORICAL_STATS_CACHE_KEY_PREFIX=nba:historical

# Delay between nba_api requests to avoid rate limiting (0.6 seconds)
NBA_API_REQUEST_DELAY=0.6
```

## Usage Examples

### Starting a Roster Chat Session

```bash
curl -X POST http://localhost:3002/api/roster-chat/start \
  -H "Content-Type: application/json" \
  -d '{
    "league_id": "123456789",
    "roster_id": 1,
    "sleeper_user_id": "987654321",
    "initial_message": "Who should I start this week?"
  }'
```

### Sending a Chat Message

```bash
curl -X POST http://localhost:3002/api/roster-chat/{session_id}/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What was LeBron James scoring average in 2022?",
    "include_historical": true
  }'
```

### Example Questions

**Current Roster:**
- "Who should I start this week?"
- "What are my team's weaknesses?"
- "Should I pick up Player X?"
- "Who should I drop?"

**Historical Stats:**
- "What was Giannis's scoring average in 2022?"
- "How did Curry perform last season?"
- "Show me LeBron's career stats"
- "What were Dame's stats around this time last year?"

**League Rules:**
- "How does lock-in mode work?"
- "What's my league's scoring system?"
- "When do I need to lock my lineup?"
- "What positions am I required to fill?"

**Matchup Analysis:**
- "Analyze my matchup this week"
- "Which players have favorable schedules?"
- "Who has the most games this week?"
- "Should I bench anyone for their matchup?"

## Architecture

### Components

1. **RosterContextBuilder** (`backend/services/roster_context_builder.py`)
   - Builds comprehensive context for LLM
   - Fetches league settings, roster data, schedules
   - Handles historical stats queries
   - Manages token budget

2. **NBAStatsService** (`backend/services/nba_stats_service.py`)
   - Historical stats methods using nba_api
   - Player search by name
   - Career stats, season averages, game logs
   - Date range queries

3. **RosterChatSession/Message Models** (`backend/session/models.py`)
   - Database models for chat persistence
   - Session tracking and message history
   - Metadata storage for context tracking

4. **WebSocket Manager** (`backend/websocket_manager.py`)
   - Real-time message delivery
   - Connection management for chat sessions
   - Broadcast support for multiple clients

5. **Agent Factory** (`backend/agents/agent_factory.py`)
   - Creates specialized roster advisor agent
   - Configures LLM with context
   - Handles conversation management

### Data Flow

```
User → Frontend → API → Context Builder → [League Cache, NBA Stats, Player Cache]
                                           ↓
User ← WebSocket ← LLM ← Agent Factory ← Context (League Rules + Roster + Historical Stats)
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (see `.env.example`)

3. Initialize database:
```bash
python run_backend.py
```

## Development

### Adding New Context Sources

To add new data sources to the roster context:

1. Add fetching method to `RosterContextBuilder`
2. Add formatting method for markdown output
3. Update `build_roster_context()` to include new data
4. Manage token budget in `_truncate_context_if_needed()`

### Historical Stats Queries

Historical stats are fetched on-demand when:
- User query contains year keywords (2022, 2023, etc.)
- User asks about "last season", "career", etc.
- Query includes "average in", "stats in", etc.

The system automatically:
1. Detects historical query keywords
2. Extracts player name from query
3. Determines appropriate stats endpoint
4. Fetches and caches data
5. Formats as markdown for LLM context

## Testing

### Test Roster Chat

```bash
# Start a session
curl -X POST http://localhost:3002/api/roster-chat/start \
  -H "Content-Type: application/json" \
  -d '{"league_id": "test", "roster_id": 1, "sleeper_user_id": "test"}'

# Send a message
curl -X POST http://localhost:3002/api/roster-chat/{session_id}/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Who should I start?"}'

# Get history
curl http://localhost:3002/api/roster-chat/{session_id}/history
```

## Troubleshooting

### Chat Session Not Found
- Verify session_id is correct UUID format
- Check database for session existence
- Ensure session status is "active"

### Historical Stats Not Fetching
- Check `ROSTER_CHAT_ENABLE_HISTORICAL_STATS=true`
- Verify nba_api is installed
- Check request delay setting (`NBA_API_REQUEST_DELAY`)
- Review logs for nba_api errors

### WebSocket Connection Issues
- Verify WebSocket URL format
- Check CORS settings for WebSocket
- Ensure session_id is valid
- Review browser console for errors

### Context Too Large
- Reduce `ROSTER_CHAT_MAX_HISTORY_MESSAGES`
- Adjust `ROSTER_CHAT_MAX_CONTEXT_TOKENS`
- Limit schedule days (`days_ahead` parameter)
- Reduce performance weeks tracked

## License

MIT
