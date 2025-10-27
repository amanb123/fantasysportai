# Railway Deployment Guide

## Prerequisites

1. Railway account (sign up at [railway.app](https://railway.app))
2. GitHub repository connected

## Step 1: Create Railway Project

1. Go to [railway.app/new](https://railway.app/new)
2. Click **"Deploy from GitHub repo"**
3. Select your `fantasysportai` repository
4. Railway will create a new project

## Step 2: Add Redis Service

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"Add Redis"**
3. Railway will automatically provision a Redis instance
4. Note: Redis connection details will be available as environment variables

## Step 3: Configure Backend Service

### Set Root Directory

1. Go to your backend service settings
2. Under **"Service Settings"**:
   - **Root Directory**: `/backend`
   - **Build Command**: Will auto-detect from `railway.json`
   - **Start Command**: Will auto-detect from `railway.json`

### Add Environment Variables

Go to **"Variables"** tab and add:

#### Required Variables

```bash
# OpenAI API Key (required for AI agents)
OPENAI_API_KEY=sk-your-key-here

# Redis Configuration (automatically provided by Railway Redis service)
# These should auto-populate when you link Redis service
REDIS_HOST=${{Redis.REDIS_HOST}}
REDIS_PORT=${{Redis.REDIS_PORT}}
REDIS_PASSWORD=${{Redis.REDIS_PASSWORD}}

# Or if using Railway's REDIS_URL:
REDIS_URL=${{Redis.REDIS_URL}}

# Application Settings
NBA_MCP_ENABLED=false
DATABASE_URL=sqlite:///./fantasy_league.db

# CORS Origins (add your Vercel frontend URL)
CORS_ORIGINS=["https://your-app.vercel.app","http://localhost:3000"]

# JWT Secret (generate a secure random string)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### Optional Variables

```bash
# Environment
ENVIRONMENT=production

# Logging
LOG_LEVEL=INFO

# API Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

## Step 4: Link Redis to Backend

1. In your backend service, click **"Variables"**
2. Click **"+ New Variable"** → **"Add Reference"**
3. Select your Redis service
4. Add these references:
   - `REDIS_HOST` → `Redis.REDIS_HOST`
   - `REDIS_PORT` → `Redis.REDIS_PORT`
   - `REDIS_PASSWORD` → `Redis.REDIS_PASSWORD`

Or use the Redis URL directly:
   - `REDIS_URL` → `Redis.REDIS_URL`

## Step 5: Deploy

1. Railway will automatically deploy when you push to GitHub
2. Or click **"Deploy"** button manually
3. Monitor the build logs in the **"Deployments"** tab

## Step 6: Get Your Backend URL

1. Go to **"Settings"** tab
2. Under **"Networking"**, you'll see your public domain
3. Copy this URL (e.g., `https://your-app.railway.app`)

## Step 7: Update Frontend

Update your Vercel environment variables:

```bash
VITE_API_BASE_URL=https://your-app.railway.app
VITE_WS_BASE_URL=wss://your-app.railway.app
```

## Troubleshooting

### Build Fails

**Error: "Error creating build plan with Railpack"**
- ✅ Fixed with `railway.json` and `nixpacks.toml`
- Make sure **Root Directory** is set to `/backend`

**Error: "Module not found"**
- Check `requirements.txt` is in `/backend` directory
- Verify all dependencies are listed

### Redis Connection Issues

**Error: "Connection refused"**
- Make sure Redis service is running
- Verify environment variables are correctly linked
- Check Redis service is in the same Railway project

### Application Won't Start

**Check:**
1. Environment variables are set correctly
2. `PORT` variable is available (Railway provides this automatically)
3. Start command is correct: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### CORS Errors

Update `CORS_ORIGINS` to include your Vercel URL:
```bash
CORS_ORIGINS=["https://your-app.vercel.app","https://fantasysportai.vercel.app"]
```

## Monitoring

### View Logs
1. Go to your backend service
2. Click **"Deployments"** tab
3. Click on the latest deployment
4. View logs in real-time

### Metrics
Railway provides:
- CPU usage
- Memory usage
- Network traffic
- Request metrics

## Scaling

Railway automatically scales based on your plan:
- **Hobby Plan**: 512MB RAM, shared CPU
- **Pro Plan**: More resources available

## Cost Optimization

- Redis: ~$5/month (Hobby plan includes $5 credit)
- Backend: Based on usage (Hobby plan includes $5 credit)
- Total: ~$5-10/month for low traffic

## Files Created for Railway

- `backend/Procfile` - Process commands
- `backend/runtime.txt` - Python version
- `backend/railway.json` - Railway configuration
- `backend/nixpacks.toml` - Build configuration
- `backend/.railwayignore` - Files to ignore during deployment

## Next Steps

1. Deploy backend to Railway
2. Get backend URL
3. Update Vercel frontend environment variables
4. Test the full application

## Useful Commands

### Local Testing with Railway Environment

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Pull environment variables
railway variables

# Run locally with Railway environment
railway run python -m uvicorn main:app --reload
```
