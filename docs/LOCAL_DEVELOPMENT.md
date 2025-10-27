# Local Development Setup

This guide explains how to run the Fantasy Basketball League application locally with a production-like configuration.

## Overview

Your local development environment is configured to match production:
- ✅ NBA MCP **disabled** (uses nba_api directly like production)
- ✅ Direct NBA.com API access
- ✅ Redis caching enabled
- ✅ All features working without MCP dependency

## Quick Start

### 1. Start Backend

```bash
# Option A: Use the automated script (recommended)
./start_local_dev.sh

# Option B: Manual start
export NBA_MCP_ENABLED=false nba_mcp_enabled=false
.venv/bin/python run_backend.py > backend.log 2>&1 &
```

The backend will start at **http://localhost:3002**

### 2. Start Frontend

```bash
cd frontend
npm run dev
```

The frontend will start at **http://localhost:5173** (or http://localhost:3000)

### 3. Verify Everything Works

- Health check: http://localhost:3002/health
- API docs: http://localhost:3002/docs
- Frontend: http://localhost:5173

## Configuration Files

### Backend (.env)
Located at project root. Key settings for production-like development:

```bash
# Disable NBA MCP (matches production)
NBA_MCP_ENABLED=false
nba_mcp_enabled=false
nba_mcp_server_path=

# Enable NBA Stats API (direct access)
NBA_STATS_ENABLED=true
nba_stats_enabled=true

# CORS for local frontend
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend (.env.development)
Located at `frontend/.env.development`. Points to local backend:

```bash
VITE_API_BASE_URL=http://localhost:3002
VITE_WS_BASE_URL=ws://localhost:3002
```

### Frontend (.env.local) - Optional
Located at `frontend/.env.local` (gitignored). Override settings as needed.

## Available Services

When running locally with production config:

| Service | Status | Notes |
|---------|--------|-------|
| ✅ Roster Ranking | Working | Uses nba_stats_service |
| ✅ Trade Analysis | Working | Uses nba_stats_service fallback |
| ✅ Roster Chat | Working | Requires OPENAI_API_KEY |
| ✅ League Data Cache | Working | Redis-backed |
| ✅ NBA Schedule | Working | Cached from NBA.com |
| ✅ Player Stats | Working | Direct nba_api access |
| ❌ NBA MCP | Disabled | Matches production |

## Logs and Debugging

```bash
# View backend logs (real-time)
tail -f backend.log

# Check last 50 lines
tail -50 backend.log

# Check for errors
grep -i error backend.log

# Check NBA services
grep -E "(NBA MCP|NBA stats|RosterRanking|TradeAnalysis)" backend.log
```

## Common Commands

```bash
# Stop backend
pkill -f run_backend.py

# Restart backend with fresh config
./start_local_dev.sh

# Clear Redis cache
redis-cli FLUSHALL

# Test API endpoints
curl http://localhost:3002/health
curl http://localhost:3002/api/roster-ranking/1286111319551938560 | jq
```

## Differences from Production

| Feature | Local Dev | Production (Railway) |
|---------|-----------|---------------------|
| Database | SQLite (file) | SQLite (container) |
| Redis | localhost:6379 | Railway Redis |
| Environment | development | production |
| CORS | localhost only | Vercel domains |
| Logs | backend.log file | Railway console |

## Testing Before Production Push

1. **Test all features locally**:
   - Login with Sleeper username
   - View roster rankings
   - Test trade analysis
   - Check roster chat

2. **Verify logs are clean**:
   ```bash
   grep -E "(ERROR|CRITICAL)" backend.log
   ```

3. **Commit only once per day**:
   ```bash
   git add <files>
   git commit -m "Feature: Description"
   git push origin main
   ```

4. **Railway auto-deploys** from main branch

## Troubleshooting

### Backend won't start
```bash
# Check if port 3002 is in use
lsof -i :3002

# Kill any stuck processes
pkill -9 -f run_backend.py
pkill -9 -f uvicorn
```

### NBA MCP still loading
Make sure `.env` has:
```bash
NBA_MCP_ENABLED=false
nba_mcp_enabled=false
nba_mcp_server_path=
```

Then restart:
```bash
./start_local_dev.sh
```

### Frontend can't connect to backend
Check CORS in `.env`:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Make sure backend is running:
```bash
curl http://localhost:3002/health
```

### Redis connection failed
Start Redis:
```bash
# macOS (Homebrew)
brew services start redis

# Or run directly
redis-server
```

## Production Deployment

When you're ready to deploy:

1. Test everything locally
2. Commit changes: `git commit -am "Description"`
3. Push once per day: `git push origin main`
4. Railway auto-deploys within ~2 minutes
5. Verify at https://fantasysportai.vercel.app

## Environment Variables Reference

### Required for Local Development
- `REDIS_HOST=localhost`
- `REDIS_PORT=6379`
- `NBA_MCP_ENABLED=false`
- `NBA_STATS_ENABLED=true`

### Optional but Recommended
- `OPENAI_API_KEY` - For AI chat features
- `LOG_LEVEL=INFO` - For debugging
- `CORS_ORIGINS` - For frontend connectivity

### Not Needed Locally
- `REDIS_URL` - Only for Railway
- `SECRET_KEY` - Dev default is fine locally
- `DATABASE_URL` - Defaults to local SQLite

## Resources

- Backend API Docs: http://localhost:3002/docs
- Backend Health: http://localhost:3002/health
- Frontend Dev: http://localhost:5173
- Production: https://fantasysportai.vercel.app
- Railway Dashboard: https://railway.app
- Vercel Dashboard: https://vercel.com

---

**🎯 Goal**: Develop locally with confidence that your code will work exactly the same in production!
