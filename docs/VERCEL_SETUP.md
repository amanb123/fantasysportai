# Vercel Configuration Guide

## 🎯 Goal
Configure Vercel to automatically deploy:
- **`dev` branch** → Preview/Staging deployment
- **`main` branch** → Production deployment

Each with the correct backend API URL.

## 📝 Step-by-Step Configuration

### Step 1: Access Vercel Project Settings

1. Go to https://vercel.com/dashboard
2. Find your project: **fantasysportai**
3. Click on the project
4. Click **Settings** tab

### Step 2: Configure Git Integration

1. In Settings, go to **Git** section
2. Verify these settings:
   ```
   Production Branch: main
   ✅ Automatically expose System Environment Variables
   ```

3. Under **Deploy Hooks**, ensure both branches can deploy:
   - `main` branch → Production
   - `dev` branch → Preview

### Step 3: Configure Environment Variables

This is the MOST IMPORTANT part! Go to **Settings** → **Environment Variables**

#### Add Production Variables (for `main` branch):

Click **Add New** and enter:

```
Key: VITE_API_URL
Value: https://fantasysportai-production.up.railway.app
Environment: Production ✅ (only)
```

#### Add Preview/Staging Variables (for `dev` branch):

Click **Add New** and enter:

```
Key: VITE_API_URL
Value: https://fantasysportai-staging.up.railway.app
Environment: Preview ✅ (only)
```

#### Optional: Add Development Variables (for local):

```
Key: VITE_API_URL
Value: http://localhost:3002
Environment: Development ✅ (only)
```

### Step 4: Configure Branch Deployments

1. Still in Settings, go to **Git** section
2. Scroll to **Ignored Build Step**
3. Leave it empty (or default) to deploy all branches

4. Under **Deploy Hooks** → **Production Branch**:
   - Ensure it's set to: `main`

5. Under **Branches** section:
   - **All branches** should be enabled for preview deployments

### Step 5: Add Vercel Configuration File (Optional but Recommended)

In your project root, you can create `vercel.json` for more control:

```json
{
  "buildCommand": "cd frontend && npm run build",
  "outputDirectory": "frontend/dist",
  "framework": "vite",
  "installCommand": "cd frontend && npm install",
  "git": {
    "deploymentEnabled": {
      "main": true,
      "dev": true
    }
  },
  "github": {
    "silent": false,
    "autoJobCancelation": true
  }
}
```

## 🔍 Verification Steps

### After Configuration, Test Each Branch:

#### Test Production (main branch):
1. Push to main: `git push origin main`
2. Go to Vercel dashboard
3. Check deployment logs
4. Visit: https://fantasysportai.vercel.app
5. Open browser console, check network tab
6. API calls should go to: `fantasysportai-production.up.railway.app`

#### Test Staging (dev branch):
1. Push to dev: `git push origin dev`
2. Go to Vercel dashboard → Deployments
3. Find the preview deployment
4. Click to get URL (e.g., `fantasysportai-git-dev-*.vercel.app`)
5. Open browser console, check network tab
6. API calls should go to: `fantasysportai-staging.up.railway.app`

## 🎨 Environment Variables Summary

Here's what your Vercel environment variables should look like:

| Variable | Production (main) | Preview (dev) | Development (local) |
|----------|------------------|---------------|---------------------|
| `VITE_API_URL` | `https://fantasysportai-production.up.railway.app` | `https://fantasysportai-staging.up.railway.app` | `http://localhost:3002` |

## 📱 Testing in Browser

### Check Production:
```javascript
// Open https://fantasysportai.vercel.app
// Open browser console and run:
console.log(import.meta.env.VITE_API_URL)
// Should show: "https://fantasysportai-production.up.railway.app"
```

### Check Staging:
```javascript
// Open https://fantasysportai-git-dev-*.vercel.app
// Open browser console and run:
console.log(import.meta.env.VITE_API_URL)
// Should show: "https://fantasysportai-staging.up.railway.app"
```

## 🔧 Troubleshooting

### Problem: Preview deployment uses production API

**Solution**: 
1. Go to Vercel → Settings → Environment Variables
2. Make sure `VITE_API_URL` for staging has **Preview** checked ONLY
3. Make sure production variable has **Production** checked ONLY
4. Redeploy: `git push origin dev --force-with-lease`

### Problem: Environment variable not updating

**Solution**:
1. Delete the old environment variable
2. Re-add it with correct environment selection
3. Go to Deployments → Click on latest → Click **Redeploy**

### Problem: Both environments use same backend

**Solution**:
1. Check that you have TWO separate `VITE_API_URL` variables:
   - One with "Production" ✅
   - One with "Preview" ✅
2. They should have different URLs
3. Clear and recreate if needed

### Problem: Can't find preview deployment URL

**Solution**:
1. Go to Vercel dashboard → Deployments tab
2. Look for deployments from `dev` branch
3. They'll be labeled as "Preview"
4. Click on one to get the URL
5. Or wait for GitHub PR comment (if you use PRs)

## 🚀 Deployment URLs

After proper configuration, you'll have:

### Production Deployment:
- **Branch**: `main`
- **Frontend URL**: https://fantasysportai.vercel.app
- **Backend URL**: https://fantasysportai-production.up.railway.app
- **Triggered by**: `git push origin main`

### Staging/Preview Deployment:
- **Branch**: `dev`  
- **Frontend URL**: https://fantasysportai-git-dev-*.vercel.app
- **Backend URL**: https://fantasysportai-staging.up.railway.app
- **Triggered by**: `git push origin dev`

### Local Development:
- **Frontend URL**: http://localhost:5173
- **Backend URL**: http://localhost:3002
- **Started by**: `./start_local_dev.sh`

## 📋 Quick Checklist

Before you're done, verify:

- [ ] Production branch is set to `main`
- [ ] `VITE_API_URL` exists with "Production" environment
- [ ] `VITE_API_URL` exists with "Preview" environment  
- [ ] Both variables have different backend URLs
- [ ] Test deployment from `dev` branch works
- [ ] Test deployment from `main` branch works
- [ ] Preview URL uses staging backend
- [ ] Production URL uses production backend

## 💡 Pro Tips

1. **Use Vercel CLI for testing**:
   ```bash
   npm i -g vercel
   vercel env ls  # List all environment variables
   ```

2. **Check build logs**:
   - Always check Vercel deployment logs
   - Look for "Using environment variable VITE_API_URL"

3. **Use deployment protection**:
   - In Settings → Deployment Protection
   - Enable protection for production deployments
   - Requires manual approval before going live

4. **Set up notifications**:
   - Settings → Notifications
   - Get notified of deployment failures

5. **Preview deployments for PRs**:
   - When you create a PR from `dev` to `main`
   - Vercel automatically creates a preview
   - Perfect for testing before merging!

## 🔗 Useful Vercel Links

- Dashboard: https://vercel.com/dashboard
- Environment Variables: https://vercel.com/docs/concepts/projects/environment-variables
- Git Integration: https://vercel.com/docs/concepts/git
- Deployment Docs: https://vercel.com/docs/concepts/deployments/overview

---

**Next Step**: After configuring Vercel, run `./verify_deployment.sh` to test everything!
