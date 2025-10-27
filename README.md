# Fantasy Basketball League Manager

A FastAPI-based fantasy basketball league management system with Sleeper API integration and AI-powered trade negotiations using AutoGen multi-agent framework.

## Project Description

The Fantasy Basketball League Manager is an intelligent system that integrates with Sleeper fantasy sports platform to manage fantasy basketball teams, rosters, and trades. Users can access their existing Sleeper leagues and rosters through a simple username-based flow, eliminating the need for traditional authentication. The system uses AI agents to facilitate trade negotiations between teams, ensuring fair and strategic trades while maintaining roster composition rules and salary cap constraints.

## New Sleeper-First Workflow

1. **Username Entry**: Enter your Sleeper username to create a session
2. **League Selection**: View and select from your Sleeper fantasy basketball leagues
3. **Roster Display**: View detailed rosters with player names, positions, and team information
4. **Trade Negotiations**: Use AI-powered agents for intelligent trade negotiations (optional authentication for trade history)

## Prerequisites

- **Python 3.11+**: Required for the backend application
- **Neon PostgreSQL Account**: Cloud PostgreSQL database for data storage
- **Ollama**: Local AI model server for agent functionality (optional for basic features)

## Setup Instructions

### 1. Clone and Setup Environment

```bash
# Navigate to the project directory
cd fantasy-basketball-league

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit .env file with your configuration
nano backend/.env
```

**Required Configuration:**
- Replace `DATABASE_URL` with your actual Neon PostgreSQL connection string from your Neon dashboard
- **Redis Configuration**: Update `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PASSWORD` if using a remote Redis instance
- Adjust other settings as needed (API ports, CORS origins, etc.)

### 3. Redis Setup (Optional for Sleeper Integration)

Redis is used for caching NBA player data from Sleeper API. While optional, it improves performance.

```bash
# Option 1: Using Docker (Recommended)
docker run --name fantasy-redis -p 6379:6379 -d redis:alpine

# Option 2: Using Homebrew (macOS)
brew install redis
brew services start redis

# Option 3: Manual installation
# Follow Redis installation guide for your OS
```

### 4. Database Setup

```bash
# Navigate to backend directory
cd backend

# Run database seeding with hardcoded data
python seed_data.py --reset

# OR: Use Sleeper API data (requires Redis)
python seed_data.py --reset --use-sleeper
```

### 5. Start the Server

```bash
# Start the FastAPI server
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 3002
```

The API will be available at:
- **API Base**: http://localhost:3002
- **Interactive Docs**: http://localhost:3002/docs
- **Health Check**: http://localhost:3002/health

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Neon PostgreSQL connection string | Required |
| `API_HOST` | API server host | 0.0.0.0 |
| `API_PORT` | API server port | 3002 |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | localhost:3000,3001,5173 |
| `SALARY_CAP` | Team salary cap in dollars | 100000000 ($100M) |
| `LOG_LEVEL` | Logging level | INFO |
| `OLLAMA_HOST` | Ollama server URL | http://localhost:11434 |
| `OLLAMA_MODEL` | AI model name | llama2 |
| `REDIS_HOST` | Redis server host for caching | localhost |
| `REDIS_PORT` | Redis server port | 6379 |
| `SLEEPER_API_BASE_URL` | Sleeper API base URL | https://api.sleeper.app/v1 |
| `SLEEPER_DEFAULT_SEASON` | Default NBA season year for API calls | 2024 |
| `SLEEPER_SEASON_CACHE_TTL` | Cache duration for season lookups (seconds) | 86400 (24 hours) |

## Database Schema

### Teams Table
- **id**: Unique team identifier
- **name**: Team name (Lakers, Warriors, Celtics)
- **total_salary**: Sum of all player salaries
- **created_at**: Team creation timestamp

### Players Table
- **id**: Unique player identifier  
- **name**: Player name
- **team_id**: Foreign key to teams table
- **position**: Player position (PG, SG, SF, PF, C)
- **salary**: Player salary in dollars
- **Statistical fields**: PPG, RPG, APG, SPG, BPG, TOV, FG%, 3PT%

### Trade Preferences Table
- **id**: Unique preference identifier
- **team_id**: Foreign key to teams table
- **improve_rebounds/assists/scoring**: Boolean flags for trade focus
- **reduce_turnovers**: Boolean flag for reducing turnovers
- **notes**: Additional preference notes

### Trades Table
- **id**: Unique trade identifier
- **session_id**: Unique session for trade negotiation
- **status**: Current trade status
- **team1_id, team2_id**: Participating teams
- **created_at, completed_at**: Timestamps

## API Endpoints

### New Sleeper Integration Endpoints

#### POST /api/sleeper/session
Create a session using a Sleeper username.

**Request:**
```json
{
  "sleeper_username": "your_username"
}
```

**Response:**
```json
{
  "user_id": "1145917800104538112",
  "username": "your_username",
  "display_name": "Your Display Name",
  "avatar": "avatar_hash"
}
```

#### GET /api/sleeper/leagues
Get fantasy leagues for a user. Season parameter is optional and defaults to current season.

**Query Parameters:**
- `user_id` (required): Sleeper user ID
- `season` (optional): Season year, defaults to `SLEEPER_DEFAULT_SEASON` setting

**Response:**
```json
[
  {
    "league_id": "1145865745969213440",
    "name": "My Fantasy League",
    "season": "2024",
    "total_rosters": 10,
    "sport": "nba",
    "status": "complete",
    "settings": { ... }
  }
]
```

#### GET /api/sleeper/rosters/{league_id}
Get rosters for a specific league.

**Response:**
```json
[
  {
    "roster_id": 1,
    "owner_id": "user_id",
    "players": ["player_id1", "player_id2"],
    "starters": ["player_id1"],
    "settings": {
      "wins": 9,
      "losses": 12,
      "fpts": 8568.42
    }
  }
]
```

#### GET /api/sleeper/players/{player_id}
Get player details by Sleeper player ID.

**Response:**
```json
{
  "player_id": "4046",
  "full_name": "LeBron James",
  "position": "SF",
  "team": "LAL",
  "status": "Active"
}
```

### Core Endpoints

#### GET /health
Health check endpoint to verify API and database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "database_connected": true,
  "timestamp": "2025-10-10T20:00:00.000Z",
  "version": "1.0.0"
}
```

### GET /api/teams
Retrieve all teams with basic information.

**Response:**
```json
{
  "teams": [
    {
      "id": 1,
      "name": "Lakers",
      "total_salary": 99000000,
      "player_count": 13
    }
  ],
  "total_count": 3
}
```

### GET /api/teams/{team_id}/players
Get all players for a specific team with detailed statistics.

**Response:**
```json
{
  "players": [
    {
      "id": 1,
      "name": "LeBron James",
      "team_id": 1,
      "position": "PG",
      "salary": 44200000,
      "stats": {
        "points_per_game": 28.5,
        "rebounds_per_game": 8.2,
        "assists_per_game": 8.8,
        "steals_per_game": 1.3,
        "blocks_per_game": 0.8,
        "turnovers_per_game": 3.2,
        "field_goal_percentage": 0.525,
        "three_point_percentage": 0.365
      }
    }
  ],
  "team_name": "Lakers"
}
```

### Sleeper API Integration Endpoints

The system includes integration with Sleeper API for real NBA player data with Redis caching.

#### POST /api/sleeper/sync-players
Manually synchronize NBA player data from Sleeper API to Redis cache.

**Authentication:** Requires admin privileges  
**Cache TTL:** 24 hours per Sleeper API recommendations

**Response:**
```json
{
  "success": true,
  "message": "Player data synchronized successfully",
  "player_count": 2847,
  "cache_size_mb": 5.2
}
```

#### GET /api/sleeper/cache-status
Check the status of the Sleeper player cache.

**Response:**
```json
{
  "cached": true,
  "player_count": 2847,
  "cache_size_mb": 5.2,
  "ttl_seconds": 82800,
  "expires_at": "2025-10-14T12:00:00Z"
}
```

#### DELETE /api/sleeper/cache
Clear the Sleeper player cache.

**Authentication:** Requires admin privileges

**Response:**
```json
{
  "success": true,
  "message": "Cache cleared successfully"
}
```

#### GET /api/sleeper/players/{player_id}
Get individual player data from cache.

**Response:**
```json
{
  "name": "LeBron James",
  "team": "LAL",
  "positions": ["SF", "PG"],
  "status": "Active",
  "injury_status": null
}
```

## Roster Rules

Each team must maintain a roster of exactly **13 players** with the following composition:

### Position Requirements (Minimum)
- **1 Point Guard (PG)**: Primary ball handler and playmaker
- **1 Shooting Guard (SG)**: Perimeter scorer and defender  
- **1 Small Forward (SF)**: Versatile wing player
- **1 Power Forward (PF)**: Interior presence and rebounder
- **2 Centers (C)**: Rim protection and post presence

### Additional Roster Spots
- **7 Utility/Bench Players**: Can be any position to provide depth and flexibility

### Financial Constraints
- **Salary Cap**: $100,000,000 per team
- Teams cannot exceed the salary cap when making trades
- All player salaries are based on realistic NBA contract values

## Next Steps

### Phase 1: Trade Agent System (Upcoming)
- Implement AI agents for automated trade negotiations
- Multi-agent conversations using AutoGen framework
- Trade proposal generation and evaluation

### Phase 2: Web Frontend (Future)
- React-based dashboard for team management
- Real-time trade negotiation viewer
- Interactive roster management tools

### Phase 3: Advanced Features (Future)
- Salary cap projections and analytics
- Player performance predictions
- Historical trade analysis

## Features

### 🤖 AI Trade Assistant (NEW)
Get AI-powered analysis of proposed trades with detailed insights and recommendations.

**Key Features:**
- **Favorability Scoring**: 0-100 scale rating trade value for your team
- **Pros & Cons Analysis**: Detailed breakdown of trade impacts
- **AI Recommendations**: Accept, Reject, or Consider guidance from GPT-4
- **Matchup Simulation**: Project impact on upcoming weeks
- **Analysis History**: Review past trade evaluations
- **Recent Trades Reference**: See what's happening in your league

**How to Use:**
1. Navigate to your roster view
2. Click "Trade Assistant" button
3. Enter opponent's roster ID
4. Select players you're trading away
5. Select players you're receiving
6. Click "Analyze Trade"
7. View AI-powered analysis in 10-15 seconds

**Technical Implementation:**
- **Backend**: FastAPI with background task processing
- **AI Engine**: OpenAI GPT-4 for natural language analysis
- **Data Sources**: NBA MCP server for real-time stats, Sleeper API for league context
- **Database**: SQLite with session persistence
- **Frontend**: React with real-time polling and responsive UI

See `TRADE_ASSISTANT_COMPLETE.md` for full documentation.

### NBA Stats Integration
The system integrates with NBA.com's official CDN and the `nba_api` Python library to provide comprehensive game schedule and player biographical data.

#### Data Sources
- **NBA CDN**: Free, public API for game schedules and live scores
  - Schedule endpoint: `https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json`
  - Scoreboard endpoint: `https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json`
  - No authentication required
- **nba_api Library**: Python wrapper for stats.nba.com
  - Player biographical information (height, weight, draft info, etc.)
  - Team assignments and jersey numbers

#### Caching Strategy
- **Game Schedule**: 12-hour Redis cache + PostgreSQL persistence
- **Player Info**: 24-hour Redis cache + PostgreSQL persistence
- **Automatic Fallback**: Redis → Database → Live Fetch
- **Cache Invalidation**: Admin endpoints to clear stale data

#### Player ID Mapping
The system links Sleeper player IDs to NBA person IDs using these priority mappings:
1. `sportradar_id` (highest priority)
2. `espn_id`
3. `yahoo_id`

This enables combining Sleeper roster data with NBA biographical information seamlessly.

#### Configuration
Enable NBA stats integration in `.env`:
```bash
# NBA Stats Integration
NBA_STATS_ENABLED=true
NBA_CDN_BASE_URL=https://cdn.nba.com/static/json
NBA_CDN_TIMEOUT=10
NBA_SCHEDULE_CACHE_TTL=43200  # 12 hours
NBA_PLAYER_INFO_CACHE_TTL=86400  # 24 hours
NBA_SCHEDULE_REFRESH_HOUR=2  # UTC
NBA_PLAYER_INFO_REFRESH_HOUR=3  # UTC
NBA_CURRENT_SEASON=2024
```

#### NBA API Endpoints

**Admin/Sync Operations:**
- `POST /api/nba/sync-schedule` - Sync full season schedule from NBA CDN
- `POST /api/nba/sync-player-info` - Sync player bio data for specified player IDs

**Schedule Queries:**
- `GET /api/nba/schedule?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&season=2024` - Get games by date range
- `GET /api/nba/schedule/today` - Get today's games with live scores
- `GET /api/nba/schedule/team/{tricode}?start_date=...&end_date=...` - Get team schedule

**Player Information:**
- `GET /api/nba/player-info/{player_id}` - Get bio data for single player (Sleeper ID)
- `POST /api/nba/player-info/bulk` - Get bio data for multiple players (batch)

**Cache Management:**
- `GET /api/nba/cache-status` - View cache statistics and status
- `DELETE /api/nba/cache/schedule` - Invalidate schedule cache
- `DELETE /api/nba/cache/player-info?player_id=...` - Invalidate player info cache (all or specific player)

#### Example Usage

```bash
# Sync current season schedule
curl -X POST "http://localhost:3002/api/nba/sync-schedule"

# Get today's games
curl "http://localhost:3002/api/nba/schedule/today"

# Get Lakers schedule for next 7 days
curl "http://localhost:3002/api/nba/schedule/team/LAL?start_date=2024-10-20&end_date=2024-10-27"

# Sync player info for specific players
curl -X POST "http://localhost:3002/api/nba/sync-player-info" \
  -H "Content-Type: application/json" \
  -d '{"player_ids": ["6794", "8261", "8567"]}'

# Get player bio information
curl "http://localhost:3002/api/nba/player-info/6794"

# Check cache status
curl "http://localhost:3002/api/nba/cache-status"
```

### Sleeper API Integration
- **Real NBA Data**: Fetch live player data from Sleeper API (~5MB JSON response)
- **Redis Caching**: 24-hour TTL caching for optimal performance
- **Graceful Fallbacks**: System continues working if Sleeper/Redis unavailable
- **Manual Sync**: Admin endpoints for cache management
- **Future Scheduler**: Automated cache refresh (planned for later phase)

### Database Seeding Options
- **Hardcoded Data**: Reliable fallback with pre-defined player stats
- **Sleeper Integration**: `--use-sleeper` flag fetches real NBA data
- **Hybrid Approach**: Uses cached Sleeper data, supplements with hardcoded when needed

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: Neon PostgreSQL with SQLModel ORM
- **Caching**: Redis with connection pooling and JSON serialization
- **External APIs**: 
  - Sleeper API for fantasy roster data
  - NBA CDN for game schedules and live scores
  - nba_api library for player biographical information
- **AI Agents**: AutoGen framework with Ollama
- **API Documentation**: Automatic OpenAPI/Swagger generation
- **Development**: Hot reload, comprehensive logging, error handling

## Contributing

This project follows the repository pattern with clear separation of concerns:
- **Models**: Database schema definitions (`session/models.py`)
- **Repository**: Data access layer with session management (`session/repository.py`)
- **Services**: Business logic and external API integrations (`services/`)
- **API**: RESTful endpoints with proper error handling (`main.py`)
- **Configuration**: Environment-based settings management (`config.py`)
- **Dependencies**: Dependency injection for services (`dependencies.py`)

For questions or contributions, please refer to the codebase structure and existing patterns.