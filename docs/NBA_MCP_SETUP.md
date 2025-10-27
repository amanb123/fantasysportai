# NBA MCP Integration

This project now uses **obinopaul/nba-mcp-server** for NBA data access - a **FREE**, open-source MCP server that uses the official NBA API.

## 🎉 What You Get (100% FREE!)

- ✅ **Live Game Data**: Real-time scores, box scores, play-by-play
- ✅ **Schedule Access**: Get games for any date
- ✅ **Player Stats**: Career statistics, game logs, player info
- ✅ **Team Data**: Standings, game logs, team stats
- ✅ **No API Key Required**: Uses official NBA API via `nba_api` Python library

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)

Run the setup script from the project root:

```bash
chmod +x setup_nba_mcp.sh
./setup_nba_mcp.sh
```

This will:
1. Clone the `obinopaul/nba-mcp-server` repository
2. Install required Python dependencies
3. Provide you with the server path

### Option 2: Manual Setup

1. **Clone the NBA MCP Server**:
   ```bash
   git clone https://github.com/obinopaul/nba-mcp-server.git
   cd nba-mcp-server
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Get the Server Path**:
   ```bash
   pwd
   # Copy the full path and append '/nba_server.py'
   ```

## ⚙️ Configuration

Update your `backend/.env` file:

```properties
# NBA MCP Configuration
NBA_MCP_ENABLED=true
NBA_MCP_SERVER_PATH=/full/path/to/nba-mcp-server/nba_server.py
```

**Example**:
```properties
NBA_MCP_SERVER_PATH=/Users/yourname/fantasy-basketball-league/nba-mcp-server/nba_server.py
```

## 🔄 Restart Backend

After configuration:

```bash
pkill -f run_backend.py
python3 run_backend.py
```

## 📚 Available NBA MCP Tools

The integration provides access to these NBA data tools:

### Live Game Data
- `nba_live_scoreboard` - Today's live scores
- `nba_live_boxscore` - Real-time box scores
- `nba_live_play_by_play` - Live play-by-play

### Schedule
- `nba_list_todays_games` - Get games for any specific date

### Player Data
- `nba_list_active_players` - All active NBA players
- `nba_common_player_info` - Player biographical info
- `nba_player_career_stats` - Career statistics
- `nba_player_game_logs` - Game-by-game logs

### Team Data
- `nba_team_standings` - Current standings
- `nba_team_game_logs_by_name` - Team game logs
- `nba_team_stats_by_name` - Team statistics
- `nba_all_teams_stats` - All teams stats

## 🔧 How It Works

1. **MCP Client** (`backend/services/nba_mcp_client.py`):
   - Launches `nba_server.py` as a subprocess
   - Communicates via JSON-RPC over stdio
   - Handles all NBA API calls

2. **MCP Service** (`backend/services/nba_mcp_service.py`):
   - High-level interface for your application
   - Transforms MCP responses to match existing code format
   - Maintains backward compatibility

3. **Integration Points**:
   - Roster context builder uses schedule data
   - LLM tools can access player stats
   - No changes needed to Sleeper data flow

## 🆚 Comparison with Previous Approach

| Feature | Previous (SQLite + nba_api) | New (MCP Server) |
|---------|---------------------------|------------------|
| **Cost** | Free | ✅ Free |
| **Setup** | Manual database sync | ✅ Automatic |
| **Data Freshness** | Manual updates | ✅ Real-time |
| **Live Games** | ❌ Not available | ✅ Available |
| **Maintenance** | High (sync schedule manually) | ✅ Low (automatic) |
| **Player Stats** | Limited | ✅ Comprehensive |

## 🐛 Troubleshooting

### Server Path Not Found
```bash
# Verify the file exists
ls -la /path/to/nba-mcp-server/nba_server.py

# Make sure you're using the absolute path
realpath /path/to/nba-mcp-server/nba_server.py
```

### MCP Server Won't Start
```bash
# Check Python dependencies
pip install mcp nba-api pandas fastmcp

# Test the server manually
cd nba-mcp-server
python3 nba_server.py
# Should see: "Starting MCP server 'nba_mcp_server'..."
```

### Connection Errors
- Ensure `NBA_MCP_ENABLED=true` in backend/.env
- Check backend logs: `tail -f backend.log`
- Verify Python executable can access nba_api: `python3 -c "import nba_api; print('OK')"`

## 📖 Resources

- **MCP Server Repository**: https://github.com/obinopaul/nba-mcp-server
- **NBA API Documentation**: https://github.com/swar/nba_api
- **MCP Protocol**: https://modelcontextprotocol.io/

## 🙏 Credits

- NBA MCP Server by [obinopaul](https://github.com/obinopaul)
- Built on [nba_api](https://github.com/swar/nba_api) by swar
- Uses [FastMCP](https://github.com/jlowin/fastmcp) framework
