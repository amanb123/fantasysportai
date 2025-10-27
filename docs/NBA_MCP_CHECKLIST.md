# ✅ NBA MCP Integration Checklist

## 📦 What I've Done For You

- [x] **Created MCP Client** (`backend/services/nba_mcp_client.py`)
  - Handles JSON-RPC communication with NBA MCP server
  - Manages subprocess for nba_server.py
  - Implements all NBA data retrieval methods

- [x] **Created MCP Service** (`backend/services/nba_mcp_service.py`)
  - High-level NBA data service
  - Backward compatible with existing code
  - Provides schedule, player stats, and team data

- [x] **Updated Configuration** (`backend/config.py`)
  - Added NBA_MCP_SERVER_PATH setting
  - Removed BALLDONTLIE_API_KEY (no longer needed)

- [x] **Updated Environment** (`backend/.env`)
  - Set NBA_MCP_ENABLED=true
  - Added NBA_MCP_SERVER_PATH placeholder
  - Added helpful comments with GitHub link

- [x] **Created Setup Script** (`setup_nba_mcp.sh`)
  - Automated clone and setup
  - Dependency installation
  - Path configuration help

- [x] **Created Documentation**
  - `QUICKSTART_NBA_MCP.md` - Quick 3-step guide
  - `NBA_MCP_SETUP.md` - Comprehensive documentation
  - `NBA_MCP_INTEGRATION_SUMMARY.md` - Technical summary

---

## 🎯 What You Need To Do

### Step 1: Run Setup Script ⏱️ 2 minutes

```bash
cd /Users/aman.buddaraju/fantasy-basketball-league
./setup_nba_mcp.sh
```

**What this does:**
- Clones https://github.com/obinopaul/nba-mcp-server
- Installs Python dependencies (mcp, nba-api, pandas, fastmcp)
- Shows you the server path to use

**Expected output:**
```
================================================
✅ Setup Complete!
================================================

Server path: /Users/aman.buddaraju/fantasy-basketball-league/nba-mcp-server/nba_server.py

Next steps:
1. Update your backend/.env file:
   NBA_MCP_SERVER_PATH=/Users/aman.buddaraju/fantasy-basketball-league/nba-mcp-server/nba_server.py
```

### Step 2: Update .env File ⏱️ 30 seconds

Open `backend/.env` and update:

```properties
# NBA MCP Configuration (obinopaul/nba-mcp-server - FREE!)
NBA_MCP_ENABLED=true
NBA_MCP_SERVER_PATH=/Users/aman.buddaraju/fantasy-basketball-league/nba-mcp-server/nba_server.py
```

👆 **Use the exact path from Step 1's output!**

### Step 3: Restart Backend ⏱️ 10 seconds

```bash
pkill -f run_backend.py
python3 run_backend.py
```

### Step 4: Verify It's Working ⏱️ 1 minute

Check the logs:

```bash
tail -f backend.log | grep "NBA MCP"
```

**You should see:**
```
NBA MCP client initialized successfully
NBA MCP service initialized
```

**Test in your app:**
Ask the LLM: "When is my next game?" or "How many games does Steph Curry have this week?"

---

## ✅ Verification Checklist

After completing the steps above, verify:

- [ ] `nba-mcp-server/` directory exists in your project root
- [ ] `nba-mcp-server/nba_server.py` file exists
- [ ] `backend/.env` has correct NBA_MCP_SERVER_PATH
- [ ] Backend restarts without errors
- [ ] Logs show "NBA MCP client initialized successfully"
- [ ] LLM can answer questions about NBA schedule
- [ ] LLM can provide player statistics

---

## 🎉 Success Indicators

You'll know it's working when:

1. **Backend logs show:**
   ```
   INFO: NBA MCP client initialized successfully
   INFO: NBA MCP service initialized
   INFO: Retrieved X games via MCP for date range
   ```

2. **LLM can answer:**
   - "When is my next game?" ✅
   - "How is LeBron James performing?" ✅
   - "What games are today?" ✅
   - "Who does GSW play next?" ✅

3. **No errors about:**
   - Missing API keys ❌
   - Database sync issues ❌
   - Schedule not found ❌

---

## 🚨 If Something Goes Wrong

### Setup Script Fails

**Problem**: Git clone fails
**Solution**:
```bash
# Clone manually
git clone https://github.com/obinopaul/nba-mcp-server.git
cd nba-mcp-server
pip install -r requirements.txt
```

**Problem**: Permission denied
**Solution**:
```bash
chmod +x setup_nba_mcp.sh
./setup_nba_mcp.sh
```

### Backend Won't Start

**Check 1**: Path is correct
```bash
ls -la /path/you/set/in/env/nba_server.py
# Should show the file exists
```

**Check 2**: Dependencies installed
```bash
pip list | grep -E "mcp|nba-api|fastmcp"
# Should show all three packages
```

**Check 3**: Test server manually
```bash
cd nba-mcp-server
python3 nba_server.py
# Should see: "Starting MCP server..."
# Press Ctrl+C to stop
```

### LLM Can't Access NBA Data

**Check logs**:
```bash
tail -100 backend.log | grep -E "NBA|MCP|error"
```

**Look for**:
- "NBA MCP client initialized successfully" ✅
- "Error initializing NBA MCP" ❌ (fix path)
- "No module named 'mcp'" ❌ (install dependencies)

---

## 📞 Getting Help

### Documentation Files:
1. **Start here**: `QUICKSTART_NBA_MCP.md`
2. **Detailed guide**: `NBA_MCP_SETUP.md`
3. **Technical details**: `NBA_MCP_INTEGRATION_SUMMARY.md`

### Check Logs:
```bash
# Full backend log
tail -f backend.log

# Just NBA MCP messages
tail -f backend.log | grep "NBA MCP"

# Errors only
tail -f backend.log | grep -i error
```

### External Resources:
- **MCP Server Repo**: https://github.com/obinopaul/nba-mcp-server
- **NBA API Docs**: https://github.com/swar/nba_api
- **MCP Protocol**: https://modelcontextprotocol.io/

---

## 🎯 Total Time Required

- ⏱️ **Setup Script**: 2 minutes
- ⏱️ **Update .env**: 30 seconds
- ⏱️ **Restart Backend**: 10 seconds
- ⏱️ **Verification**: 1 minute

**Total**: ~4 minutes to complete setup!

---

## 🎉 Ready to Start!

```bash
# Run this command to begin:
./setup_nba_mcp.sh
```

Then follow Steps 2-4 above. You'll have free, real-time NBA data in less than 5 minutes!

---

**Cost**: $0 (completely free!)
**API Keys**: None required
**Maintenance**: Automatic
**Data**: Real-time from official NBA API
