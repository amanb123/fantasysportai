# 🚨 CORS Fix for Staging Environment

## Problem
You're getting `400 Bad Request` on OPTIONS requests from your staging frontend to staging backend because the CORS origins don't include the Vercel preview URLs.

## Root Cause
Vercel preview deployments use dynamic URLs like:
- `https://fantasysportai-git-dev-*.vercel.app`
- `https://fantasysportai-git-dev-amanb123.vercel.app`

These need to be allowed in Railway staging CORS configuration.

## 🔧 Solution: Update Railway Staging Environment Variables

### Go to Railway Dashboard:

1. Open: https://railway.app
2. Select your project
3. Switch to **staging** environment
4. Go to **Variables** tab

### Update CORS_ORIGINS Variable:

**Find**: `CORS_ORIGINS`

**Change to**:
```
https://fantasysportai.vercel.app,https://fantasysportai-git-dev-*.vercel.app,https://*.vercel.app
```

Or for more specific control:
```
https://fantasysportai.vercel.app,https://fantasysportai-git-dev-amanb123.vercel.app,https://*.vercel.app
```

### Alternative: Use Wildcard for Vercel (Staging Only)

Since this is staging and not production, you can be more permissive:

```
https://fantasysportai.vercel.app,https://*.vercel.app
```

This allows all Vercel deployments (previews and production).

## 🎯 Production vs Staging CORS

### Production Environment (main branch):
```
CORS_ORIGINS=https://fantasysportai.vercel.app
```
☝️ Strict - only production domain

### Staging Environment (dev branch):
```
CORS_ORIGINS=https://fantasysportai.vercel.app,https://*.vercel.app
```
☝️ Permissive - allows all Vercel deployments for testing

## 📝 Step-by-Step Fix

1. **Go to Railway**:
   - https://railway.app/project/[your-project]
   - Select **staging** environment

2. **Find CORS_ORIGINS variable**:
   - Click **Variables** tab
   - Look for `CORS_ORIGINS`

3. **Update the value**:
   ```
   https://fantasysportai.vercel.app,https://*.vercel.app
   ```

4. **Save** (Railway will auto-redeploy)

5. **Wait 30-60 seconds** for deployment

6. **Test again** - refresh your staging frontend

## 🧪 How to Test After Fix

### Method 1: Browser DevTools
```javascript
// Open staging frontend: https://fantasysportai-git-dev-*.vercel.app
// Open DevTools (F12) → Console
// Run this:
fetch('https://fantasysportai-staging.up.railway.app/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)

// Should work without CORS error
```

### Method 2: Check Network Tab
1. Open staging frontend
2. Open DevTools (F12) → Network tab
3. Try to create a session
4. Look for OPTIONS request - should return 200, not 400
5. The actual POST request should succeed

### Method 3: Command Line
```bash
# Test OPTIONS (preflight)
curl -X OPTIONS \
  -H "Origin: https://fantasysportai-git-dev-amanb123.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v \
  https://fantasysportai-staging.up.railway.app/api/sleeper/session

# Should return 200 with CORS headers
```

## 🔍 Verify Current CORS Settings

Check what Railway currently has:

```bash
# SSH into Railway (if you have access)
# Or check deployment logs for:
# "CORS Origins: [...]"
```

You can also add a debug endpoint to see current CORS:

```python
@app.get("/debug/cors")
async def debug_cors():
    return {"cors_origins": settings.cors_origins}
```

Then visit: `https://fantasysportai-staging.up.railway.app/debug/cors`

## ⚠️ Common Mistakes

### ❌ Wrong: Forgot the https://
```
CORS_ORIGINS=fantasysportai.vercel.app  # Missing https://
```

### ❌ Wrong: Trailing slash
```
CORS_ORIGINS=https://fantasysportai.vercel.app/  # Extra /
```

### ❌ Wrong: No comma separation
```
CORS_ORIGINS=https://fantasysportai.vercel.app https://*.vercel.app
```

### ✅ Correct:
```
CORS_ORIGINS=https://fantasysportai.vercel.app,https://*.vercel.app
```

## 🚀 Quick Fix Command

If you have Railway CLI installed:

```bash
# Set CORS for staging
railway variables set CORS_ORIGINS="https://fantasysportai.vercel.app,https://*.vercel.app" --environment staging

# Verify
railway variables --environment staging | grep CORS
```

## 📋 Full Railway Environment Variables for Staging

Here's what your staging should have:

```bash
# Environment
ENVIRONMENT=staging
DEBUG=true
LOG_LEVEL=DEBUG

# CORS - IMPORTANT!
CORS_ORIGINS=https://fantasysportai.vercel.app,https://*.vercel.app

# API
PORT=8080
HOST=0.0.0.0

# Database
DATABASE_URL=sqlite:///./staging_fantasy_db.db

# Redis (if using Railway Redis service)
REDIS_HOST=${REDIS_HOST}
REDIS_PORT=${REDIS_PORT}
REDIS_PASSWORD=${REDIS_PASSWORD}

# OpenAI
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_MODEL=gpt-4

# NBA
NBA_STATS_ENABLED=true
NBA_CURRENT_SEASON=2025
```

## 🆘 Still Not Working?

### Check these:

1. **Railway deployment finished**:
   - Check deployment logs
   - Look for "CORS Origins:" line

2. **Vercel URL is correct**:
   - Copy exact URL from Vercel deployment
   - Make sure it matches pattern in CORS_ORIGINS

3. **Clear browser cache**:
   - Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
   - Or open in incognito

4. **Check Railway logs**:
   ```bash
   railway logs --environment staging
   ```
   Look for CORS-related errors

5. **Temporary fix - use wildcard** (STAGING ONLY):
   ```
   CORS_ORIGINS=*
   ```
   This allows ALL origins - only use to debug, then revert to specific domains

## 📞 Need More Help?

Run these commands and share output:

```bash
# 1. Check what's deployed
curl https://fantasysportai-staging.up.railway.app/health

# 2. Test CORS
curl -X OPTIONS \
  -H "Origin: https://fantasysportai-git-dev-amanb123.vercel.app" \
  -v \
  https://fantasysportai-staging.up.railway.app/api/sleeper/session 2>&1 | grep -i "access-control"

# 3. Check Railway environment
railway variables --environment staging | grep CORS
```

---

**TL;DR**: Add `https://*.vercel.app` to CORS_ORIGINS in Railway staging environment! 🎯
