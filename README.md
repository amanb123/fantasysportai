# Fantasy Basketball League Manager

A FastAPI-based fantasy basketball league management system with AI-powered trade negotiations using AutoGen multi-agent framework.

## Project Description

The Fantasy Basketball League Manager is an intelligent system that manages fantasy basketball teams, rosters, and trades. The system uses AI agents powered by Ollama to facilitate trade negotiations between teams, ensuring fair and strategic trades while maintaining roster composition rules and salary cap constraints.

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
- Adjust other settings as needed (API ports, CORS origins, etc.)

### 3. Database Setup

```bash
# Navigate to backend directory
cd backend

# Run database seeding (creates tables and initial data)
python seed_data.py
```

### 4. Start the Server

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

### GET /health
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

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Database**: Neon PostgreSQL with SQLModel ORM
- **AI Agents**: AutoGen framework with Ollama
- **API Documentation**: Automatic OpenAPI/Swagger generation
- **Development**: Hot reload, comprehensive logging, error handling

## Contributing

This project follows the repository pattern with clear separation of concerns:
- **Models**: Database schema definitions
- **Repository**: Data access layer with session management
- **API**: RESTful endpoints with proper error handling
- **Configuration**: Environment-based settings management

For questions or contributions, please refer to the codebase structure and existing patterns.