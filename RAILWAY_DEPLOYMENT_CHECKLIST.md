# Railway Deployment Checklist

## ✅ Completed Steps

### Code Fixes
- [x] Fixed PYTHONPATH environment variable (set in nixpacks.toml)
- [x] Made SECRET_KEY optional with default value
- [x] Added beautifulsoup4>=4.12.0 to requirements
- [x] Added lxml>=4.9.0 to requirements
- [x] Added email-validator>=2.0.0 to requirements
- [x] Added requests>=2.31.0 to requirements
- [x] All changes committed and pushed to GitHub

### Railway Configuration Files
- [x] nixpacks.toml (build configuration)
- [x] railway.toml (deployment configuration)
- [x] Procfile (process configuration)
- [x] runtime.txt (Python version)
- [x] requirements.txt (Python dependencies)

---

## 🔲 Next Steps

### 1. Monitor Railway Deployment
- [ ] Check Railway logs for successful startup
- [ ] Look for message: "Redis connection established successfully"
- [ ] Look for message: "Application startup complete"
- [ ] Verify no ModuleNotFoundError or ImportError

### 2. Add Redis to Railway
**Critical: Redis is REQUIRED for the app to function properly**

Railway Dashboard:
1. Click "+ New" → Database → Redis
2. Railway will automatically:
   - Create Redis instance
   - Generate REDIS_URL variable
   - Link it to your backend service

### 3. Configure Railway Environment Variables

Go to your backend service → **Variables** tab:

#### Required Variables:
```bash
# Redis (auto-generated when you add Redis service)
REDIS_URL=${{Redis.REDIS_URL}}

# OpenAI API Key (for AI agents)
OPENAI_API_KEY=sk-your-openai-api-key-here

# NBA MCP (disable for production)
NBA_MCP_ENABLED=false

# CORS Origins (add your Vercel domain)
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

#### Optional Variables (have defaults):
```bash
# SECRET_KEY - Has default, but set for production security
SECRET_KEY=your-secure-random-key-here

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

**To generate a secure SECRET_KEY:**
```bash
openssl rand -hex 32
```

### 4. Get Railway Backend URL

After deployment succeeds:
1. Go to backend service → **Settings** → **Networking**
2. Under "Public Networking" → **Generate Domain**
3. Copy the URL (e.g., `https://your-app.railway.app`)

### 5. Configure Vercel Frontend

In Vercel Dashboard → Your Project → **Settings** → **Environment Variables**:

Add for **Production**:
```bash
VITE_API_BASE_URL=https://your-app.railway.app
VITE_WS_BASE_URL=wss://your-app.railway.app
VITE_POLLING_INTERVAL=2000
VITE_TOKEN_STORAGE_KEY=fantasy_bb_token
```

Then redeploy: **Deployments** → **•••** → **Redeploy**

### 6. Test Full Application

#### Backend Health Check:
```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "environment": "production",
  "redis_connected": true,
  "timestamp": "2025-10-27T..."
}
```

#### API Documentation:
```
https://your-app.railway.app/docs
```

#### Frontend Testing:
1. Visit your Vercel URL
2. Enter Sleeper username
3. Select a league
4. Test features:
   - [ ] Roster Display
   - [ ] Roster Ranking
   - [ ] Roster Chat
   - [ ] Trade Assistant
   - [ ] Trade Negotiation

---

## 🐛 Troubleshooting

### If Backend Crashes:

1. **Check Railway Logs:**
   - Railway Dashboard → Backend Service → **Logs**
   - Look for error messages

2. **Common Issues:**
   - Missing Redis: Add Redis service
   - Missing REDIS_URL: Link Redis service to backend
   - Missing OPENAI_API_KEY: Add to environment variables
   - CORS errors: Update CORS_ORIGINS with Vercel domain

3. **Redis Connection Issues:**
   - Verify Redis service is running
   - Check REDIS_URL format: `redis://default:password@host:port`
   - App will log: "Redis connection failed - Sleeper caching will be unavailable"

4. **Module Import Errors:**
   - Check requirements.txt includes all dependencies
   - Look for "ModuleNotFoundError" in logs
   - Push updated requirements.txt to trigger redeploy

### If Frontend Can't Connect:

1. **Check CORS:**
   - Verify CORS_ORIGINS includes your Vercel domain
   - Format: `https://your-app.vercel.app,http://localhost:3000`

2. **Check API URL:**
   - Verify VITE_API_BASE_URL in Vercel environment variables
   - Must match Railway backend URL exactly

3. **Check Network Tab:**
   - Open browser DevTools → Network
   - Look for 502/503 errors (backend down)
   - Look for CORS errors (CORS_ORIGINS issue)

---

## 📊 Monitoring

### Railway Metrics:
- CPU usage
- Memory usage
- Network traffic
- Deployment history

### Application Logs:
Watch for:
- Redis connection status
- Player cache initialization
- NBA schedule cache status
- API request errors

### Cost Estimation:
- Backend (512MB RAM): ~$3-5/month
- Redis (256MB RAM): ~$2-3/month
- **Total: ~$5-8/month**

(First $5/month is free with Railway trial)

---

## 🎯 Success Criteria

- [ ] Railway backend deployed and running
- [ ] Redis service connected
- [ ] All environment variables configured
- [ ] Vercel frontend deployed
- [ ] Frontend can communicate with backend
- [ ] Sleeper username login works
- [ ] League selection works
- [ ] Roster ranking displays
- [ ] Roster chat functional
- [ ] Trade assistant works
- [ ] No errors in Railway logs
- [ ] No errors in browser console

---

## 📝 Notes

### Dependencies Added:
- beautifulsoup4 (web scraping)
- lxml (BeautifulSoup parser)
- email-validator (Pydantic email validation)
- requests (HTTP requests)

### Configuration Changes:
- SECRET_KEY made optional with default
- PYTHONPATH set to /app in nixpacks.toml
- Redis URL support added to config.py

### Optional Features (Disabled for Production):
- NBA_MCP_ENABLED=false (NBA MCP server not needed)
- SQLite database (not used - using Redis only)

### Data Storage:
- **Redis**: All caching (league data, player stats, roster rankings)
- **SQLite**: Session data (optional, primarily using Sleeper username sessions)

### Security:
- Set strong SECRET_KEY in production
- Keep OPENAI_API_KEY secret
- Use HTTPS for all communications
- CORS restricted to your domain
