# 🚀 Quick Reference - Dev Workflow

## Branch Strategy
```
dev branch  → Railway Staging  → Test here first
main branch → Railway Production → Live users
```

## Daily Commands

### Start Working
```bash
git checkout dev
git pull origin dev
```

### Make Changes & Test Locally
```bash
# Start local server
./start_local_dev.sh

# Your changes...
git add .
git commit -m "feat: your feature description"
```

### Deploy to Staging
```bash
git push origin dev
# ✅ Auto-deploys to staging
# Test at: https://fantasysportai-git-dev-*.vercel.app
```

### Promote to Production (When Ready)
```bash
# Easy way
./dev_workflow.sh
# Select option 3

# Manual way
git checkout main
git merge dev --no-ff
git push origin main
# ✅ Auto-deploys to production

# Go back to dev
git checkout dev
```

## Quick Checks

```bash
# Which branch am I on?
git branch --show-current

# What changed since last commit?
git status

# View recent commits
git log --oneline -5
```

## URLs

| Environment | Backend | Frontend |
|-------------|---------|----------|
| **Local** | http://localhost:3002 | http://localhost:5173 |
| **Staging** | https://fantasysportai-staging.up.railway.app | https://fantasysportai-git-dev-*.vercel.app |
| **Production** | https://fantasysportai-production.up.railway.app | https://fantasysportai.vercel.app |

## Emergency Rollback

```bash
# If production breaks
git checkout main
git revert HEAD
git push origin main
```

## Rules
✅ **Always work on `dev` branch**  
✅ **Test in staging before promoting**  
❌ **Never commit directly to `main`**  
❌ **Never skip staging testing**

---
Full docs: [DEV_WORKFLOW.md](DEV_WORKFLOW.md)
