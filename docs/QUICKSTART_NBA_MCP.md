# 🚀 NBA MCP Integration - Quick Start

## ✅ What's Been Done

I've integrated **obinopaul/nba-mcp-server** (a FREE NBA MCP server) into your project!

### Files Created/Modified:
- ✅ `backend/services/nba_mcp_client.py` - MCP protocol client
- ✅ `backend/services/nba_mcp_service.py` - High-level NBA service
- ✅ `backend/config.py` - Added NBA_MCP_SERVER_PATH config
- ✅ `backend/.env` - Updated with NBA MCP settings
- ✅ `setup_nba_mcp.sh` - Automated setup script
- ✅ `NBA_MCP_SETUP.md` - Comprehensive documentation

## 🎯 What You Need To Do (2 Steps!)

### Step 1: Run the Setup Script

From your project root:

```bash
./setup_nba_mcp.sh
```

This will:
1. Clone the nba-mcp-server repository
2. Install Python dependencies (mcp, nba-api, pandas, fastmcp)
3. Give you the server path

### Step 2: Update Your .env File

The setup script will tell you the exact path. Update `backend/.env`:

```properties
NBA_MCP_ENABLED=true
NBA_MCP_SERVER_PATH=/full/path/shown/by/setup/script/nba_server.py
```

### Step 3: Restart Your Backend

```bash
pkill -f run_backend.py
python3 run_backend.py
```

## 🎉 What You Get (All FREE!)

### 1. **Live NBA Game Data**
- Real-time scores
- Box scores
- Play-by-play action

### 2. **NBA Schedule**
- Games for any date
- Replaces your SQLite schedule system
- Always up-to-date

### 3. **Player Statistics**
- Career stats
- Game logs
- Player information
- All active players

### 4. **Team Data**
- Current standings
- Team game logs
- Team statistics

## 🔍 Example Usage

Once integrated, your LLM will be able to:

```
User: "When is my next game?"
LLM: "Your next game is on October 22, 2025. Buddy Hield (GSW) and 
      Austin Reaves (LAL) will face each other at 7:00 PM PT."

User: "How has Buddy Hield been performing?"
LLM: "Buddy Hield is averaging 18.5 PPG this season with 45% from 
      three-point range in his last 10 games..."
```

## 📊 Architecture

```
Your Backend
    ↓
NBAMCPService (backend/services/nba_mcp_service.py)
    ↓
NBAMCPClient (backend/services/nba_mcp_client.py)
    ↓
[JSON-RPC over stdio]
    ↓
nba_server.py (obinopaul/nba-mcp-server)
    ↓
Official NBA API (via nba_api library)
```

## ⚠️ Important Notes

1. **No API Key Required** - This is completely free!
2. **Python 3.8+** - Make sure your Python version is compatible
3. **Internet Connection** - Needed to fetch live NBA data
4. **Subprocess** - The MCP server runs as a subprocess of your backend

## 🐛 Troubleshooting

If you encounter issues:

1. **Check the path**: Make sure NBA_MCP_SERVER_PATH points to the actual file
   ```bash
   ls -la /path/you/set/nba_server.py
   ```

2. **Test the server manually**:
   ```bash
   cd /path/to/nba-mcp-server
   python3 nba_server.py
   # Should see startup message
   ```

3. **Check backend logs**:
   ```bash
   tail -f backend.log
   # Look for "NBA MCP client initialized successfully"
   ```

4. **Verify dependencies**:
   ```bash
   pip list | grep -E "mcp|nba-api|fastmcp"
   ```

## 📚 Full Documentation

See `NBA_MCP_SETUP.md` for complete documentation including:
- All available MCP tools
- Detailed troubleshooting
- Comparison with previous approach
- API references

## 🚀 Ready to Go!

Run `./setup_nba_mcp.sh` and you're 2 minutes away from having free, real-time NBA data in your fantasy basketball league!

---

**Questions?** Check `NBA_MCP_SETUP.md` or the logs in `backend.log`
