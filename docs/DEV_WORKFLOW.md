# Development Workflow Guide

## 🔄 Branch Strategy

This project uses a **Git Branch-Based Workflow** with automatic deployments:

- **`dev` branch** → Railway Staging Environment (for testing)
- **`main` branch** → Railway Production Environment (live)

## 🏗️ Initial Setup (One-Time)

### 1. Railway Environments Setup

You need to configure two separate Railway environments:

#### Create Staging Environment:
1. Go to [Railway Dashboard](https://railway.app)
2. Open your project
3. Click **"New Environment"** 
4. Name it: **"staging"**
5. Configure deployment settings:
   - **Branch:** `dev`
   - **Auto-deploy:** Enabled
6. Set environment variables (same as production but with staging-specific values):
   ```
   ENVIRONMENT=staging
   DEBUG=true
   LOG_LEVEL=DEBUG
   CORS_ORIGINS=https://fantasysportai-git-dev-*.vercel.app,https://fantasysportai-staging.vercel.app
   ```

#### Configure Production Environment:
1. Go to your existing Railway environment
2. Rename it to: **"production"** (if not already)
3. Ensure it's configured for:
   - **Branch:** `main`
   - **Auto-deploy:** Enabled
4. Environment variables:
   ```
   ENVIRONMENT=production
   DEBUG=false
   LOG_LEVEL=INFO
   ```

### 2. Vercel Deployment Setup

Configure Vercel to deploy from both branches:

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Open your project settings
3. Go to **Git** section
4. Enable deployments for both:
   - **Production Branch:** `main` → `fantasysportai.vercel.app`
   - **Preview Branch:** `dev` → `fantasysportai-git-dev-*.vercel.app`

### 3. Frontend Environment Configuration

Update frontend to use correct backend URLs:

**For Production** (`frontend/.env.production`):
```bash
VITE_API_URL=https://fantasysportai-production.up.railway.app
```

**For Staging** (`frontend/.env.staging` - create this):
```bash
VITE_API_URL=https://fantasysportai-staging.up.railway.app
```

## 📝 Daily Development Workflow

### Step 1: Start Working (Always on Dev)

```bash
# Make sure you're on dev branch
git checkout dev

# Pull latest changes
git pull origin dev

# Create a feature branch (optional but recommended)
git checkout -b feature/my-new-feature
```

### Step 2: Make Changes

```bash
# Edit code, test locally
./start_local_dev.sh

# Test your changes
curl http://localhost:3002/api/roster-ranking/1286111319551938560
```

### Step 3: Commit and Push to Dev

```bash
# Add your changes
git add .

# Commit with descriptive message
git commit -m "feat: add new trade analysis feature"

# If on feature branch, merge to dev first
git checkout dev
git merge feature/my-new-feature

# Push to dev (triggers staging deployment)
git push origin dev
```

**What happens:**
- ✅ Railway automatically deploys to **staging** environment
- ✅ Vercel creates a **preview deployment** for frontend
- ✅ You get a staging URL to test: `https://fantasysportai-git-dev-*.vercel.app`

### Step 4: Test in Staging

```bash
# Test staging backend
curl https://fantasysportai-staging.up.railway.app/health

# Test staging frontend
open https://fantasysportai-git-dev-*.vercel.app
```

### Step 5: Promote to Production (When Ready)

Use the helper script:

```bash
./dev_workflow.sh
# Select option 3: "Promote dev → prod"
```

Or manually:

```bash
# Switch to main branch
git checkout main

# Pull latest
git pull origin main

# Merge dev into main
git merge dev --no-ff -m "Promote dev to production - $(date +%Y-%m-%d)"

# Push to production (triggers prod deployment)
git push origin main
```

**What happens:**
- ✅ Railway automatically deploys to **production** environment
- ✅ Vercel deploys to **production** URL: `https://fantasysportai.vercel.app`

### Step 6: Return to Dev

```bash
# Always go back to dev for next feature
git checkout dev
```

## 🛠️ Quick Commands

### Using the Helper Script

```bash
./dev_workflow.sh
```

Options:
1. **Check current status** - See which branch you're on
2. **Setup dev branch** - Initial setup (already done)
3. **Promote dev → prod** - Automated promotion with safety checks
4. **Switch to dev branch** - Quick switch
5. **Switch to main branch** - Quick switch
6. **View deployment status** - Opens Railway dashboard

### Manual Commands

```bash
# Check current branch
git branch

# Switch branches
git checkout dev        # Development
git checkout main       # Production

# View recent commits
git log --oneline -10

# See what changed
git diff main dev       # Compare branches

# Emergency rollback (if prod is broken)
git checkout main
git revert HEAD
git push origin main
```

## 🔍 Environment URLs

### Development (Local)
- **Backend:** http://localhost:3002
- **Frontend:** http://localhost:5173

### Staging (Railway + Vercel)
- **Backend:** https://fantasysportai-staging.up.railway.app
- **Frontend:** https://fantasysportai-git-dev-*.vercel.app

### Production (Railway + Vercel)
- **Backend:** https://fantasysportai-production.up.railway.app
- **Frontend:** https://fantasysportai.vercel.app

## 📋 Best Practices

### ✅ DO:
- ✅ Always develop on `dev` branch
- ✅ Test thoroughly in staging before promoting
- ✅ Use descriptive commit messages
- ✅ Keep dev and main in sync (merge dev→main regularly)
- ✅ Use feature branches for large changes
- ✅ Review Railway logs after each deployment

### ❌ DON'T:
- ❌ Don't commit directly to `main` branch
- ❌ Don't push untested code to `dev`
- ❌ Don't skip staging - always test there first
- ❌ Don't force push (`git push -f`) to main or dev
- ❌ Don't merge main → dev (only merge dev → main)

## 🚨 Troubleshooting

### Staging deployment failed?
```bash
# Check Railway logs
railway logs --environment staging

# Check what you pushed
git log --oneline -5

# Rollback staging
git checkout dev
git revert HEAD
git push origin dev
```

### Production deployment broke?
```bash
# Quick rollback
git checkout main
git revert HEAD
git push origin main

# Or reset to last known good commit
git checkout main
git reset --hard HEAD~1
git push origin main --force-with-lease  # Only if necessary!
```

### Forgot which branch you're on?
```bash
git branch --show-current
```

### Dev and main diverged?
```bash
# This shouldn't happen if following workflow
# But if it does:
git checkout main
git pull origin main
git checkout dev
git rebase main  # Replay dev changes on top of main
```

## 🔐 Environment Variables

### Required in Railway (Both Environments)

**Shared Variables:**
```bash
OPENAI_API_KEY=<your-key>
OPENAI_MODEL=gpt-4
NBA_STATS_ENABLED=true
NBA_CURRENT_SEASON=2025
```

**Staging-Specific:**
```bash
ENVIRONMENT=staging
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///./staging_fantasy_db.db
```

**Production-Specific:**
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./fantasy_db.db
```

## 📊 Deployment Checklist

Before promoting dev → prod:

- [ ] All tests pass locally
- [ ] Code runs successfully in staging
- [ ] Frontend works with staging backend
- [ ] No errors in Railway staging logs
- [ ] Feature tested by team/QA
- [ ] Database migrations completed (if any)
- [ ] Environment variables updated (if needed)
- [ ] README/docs updated (if needed)

## 🎯 Example Full Workflow

```bash
# 1. Start new feature
git checkout dev
git pull origin dev
git checkout -b feature/improved-trade-analysis

# 2. Make changes
# ... edit files ...

# 3. Test locally
./start_local_dev.sh
# Test at http://localhost:3002

# 4. Commit and push to staging
git checkout dev
git merge feature/improved-trade-analysis
git push origin dev

# 5. Test in staging
# Visit: https://fantasysportai-git-dev-*.vercel.app
# Backend: https://fantasysportai-staging.up.railway.app

# 6. Promote to production
./dev_workflow.sh  # Option 3
# Or manually:
git checkout main
git merge dev --no-ff -m "Release: improved trade analysis"
git push origin main

# 7. Monitor production
# Check: https://fantasysportai.vercel.app
# Logs: railway logs --environment production

# 8. Back to dev
git checkout dev
```

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [Vercel Git Integration](https://vercel.com/docs/concepts/git)
- [Git Flow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)
- [Semantic Commit Messages](https://www.conventionalcommits.org/)

---

**Questions?** Check Railway logs, GitHub Actions, or Vercel deployment logs for details.
