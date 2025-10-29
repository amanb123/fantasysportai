# Vercel Environment Variables Quick Setup

## 🎯 What You Need to Configure

Go to: **Vercel Dashboard** → **Your Project** → **Settings** → **Environment Variables**

## ➕ Add These Two Variables:

### Variable #1: Production Backend (for main branch)

```
┌─────────────────────────────────────────────────────┐
│ Key: VITE_API_URL                                   │
├─────────────────────────────────────────────────────┤
│ Value:                                              │
│ https://fantasysportai-production.up.railway.app    │
├─────────────────────────────────────────────────────┤
│ Environments:                                       │
│ ☐ Development                                       │
│ ☑ Preview         ← UNCHECK THIS!                  │
│ ☑ Production      ← CHECK ONLY THIS!               │
└─────────────────────────────────────────────────────┘
```

Click **Save**

---

### Variable #2: Staging Backend (for dev branch)

```
┌─────────────────────────────────────────────────────┐
│ Key: VITE_API_URL                                   │
├─────────────────────────────────────────────────────┤
│ Value:                                              │
│ https://fantasysportai-staging.up.railway.app       │
├─────────────────────────────────────────────────────┤
│ Environments:                                       │
│ ☐ Development                                       │
│ ☑ Preview         ← CHECK ONLY THIS!               │
│ ☐ Production      ← UNCHECK THIS!                  │
└─────────────────────────────────────────────────────┘
```

Click **Save**

---

## ✅ Final Result

You should see TWO `VITE_API_URL` variables:

```
VITE_API_URL
  Production:  https://fantasysportai-production.up.railway.app
  Preview:     https://fantasysportai-staging.up.railway.app
```

## 🚀 How It Works

```
┌──────────────┐
│ git push     │
│ origin main  │
└──────┬───────┘
       │
       ├─→ Vercel reads: VITE_API_URL (Production)
       │   Value: fantasysportai-production.up.railway.app
       │
       └─→ Deploys to: https://fantasysportai.vercel.app


┌──────────────┐
│ git push     │
│ origin dev   │
└──────┬───────┘
       │
       ├─→ Vercel reads: VITE_API_URL (Preview)
       │   Value: fantasysportai-staging.up.railway.app
       │
       └─→ Deploys to: https://fantasysportai-git-dev-*.vercel.app
```

## 🔍 How to Verify

### After adding both variables:

1. **Trigger a deployment**:
   ```bash
   git push origin dev
   ```

2. **Check Vercel dashboard**:
   - Go to "Deployments" tab
   - Click on the latest deployment
   - Look in build logs for: `VITE_API_URL`

3. **Test the deployed site**:
   - Open preview URL
   - Open browser DevTools (F12)
   - Go to Network tab
   - Reload page
   - Check API calls - they should go to staging backend!

## ⚠️ Common Mistakes

### ❌ Wrong: Both checked for one variable
```
VITE_API_URL: https://fantasysportai-production.up.railway.app
☑ Preview
☑ Production  ← This means BOTH use production!
```

### ✅ Correct: Two separate variables
```
VITE_API_URL: https://fantasysportai-production.up.railway.app
☐ Preview
☑ Production

VITE_API_URL: https://fantasysportai-staging.up.railway.app
☑ Preview
☐ Production
```

## 🎯 Quick Test Commands

After configuration, test with these:

```bash
# Test staging
git push origin dev
# Wait for deployment, then visit preview URL
# Check browser console: should use staging backend

# Test production
git checkout main
git merge dev
git push origin main
# Wait for deployment, then visit fantasysportai.vercel.app
# Check browser console: should use production backend

# Back to dev
git checkout dev
```

---

**Questions?** See full guide: [VERCEL_SETUP.md](VERCEL_SETUP.md)
