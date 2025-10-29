# ✅ Dev → Prod Workflow Setup Complete!

## What Was Set Up

### 1. Git Branches Created
- ✅ **`dev` branch** - For development and staging
- ✅ **`main` branch** - For production (already existed)

Both branches are now on GitHub and ready for automatic deployments.

### 2. Files Added
```
.env.development              # Local dev environment config
.env.production.template      # Production config template
dev_workflow.sh              # Helper script for promotions
docs/DEV_WORKFLOW.md         # Complete workflow documentation
docs/QUICK_REFERENCE.md      # Quick command reference
frontend/.env.staging        # Staging frontend config
```

### 3. Documentation Created
- **[DEV_WORKFLOW.md](DEV_WORKFLOW.md)** - Full guide with examples
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - One-page cheat sheet
- Updated README.md with workflow links

## 🎯 Next Steps (Railway Setup)

You need to configure Railway to use the branch-based deployment:

### Step 1: Create Staging Environment in Railway

1. Go to https://railway.app
2. Open your project
3. Click **"New Environment"**
4. Configure:
   ```
   Name: staging
   Branch: dev
   Auto-deploy: ✅ Enabled
   ```

5. Copy all environment variables from production but change:
   ```bash
   ENVIRONMENT=staging
   DEBUG=true
   LOG_LEVEL=DEBUG
   ```

### Step 2: Rename Production Environment

1. In Railway, go to your existing environment
2. Rename it to: `production`
3. Ensure it's set to:
   ```
   Branch: main
   Auto-deploy: ✅ Enabled
   ```

### Step 3: Get Staging URL

After creating staging environment, Railway will give you a URL like:
```
https://fantasysportai-staging.up.railway.app
```

Copy this URL and update `frontend/.env.staging`:
```bash
VITE_API_URL=https://your-actual-staging-url.up.railway.app
```

### Step 4: Configure Vercel (Optional)

For Vercel preview deployments to use staging backend:

1. Go to Vercel project settings
2. Environment Variables
3. Add for **Preview** deployments:
   ```
   VITE_API_URL=https://your-staging-url.up.railway.app
   ```

## 🚀 How to Use (Starting Today)

### Your New Daily Workflow:

```bash
# 1. Always start on dev branch
git checkout dev

# 2. Make your changes
# ... edit code ...

# 3. Test locally
./start_local_dev.sh

# 4. Push to staging
git add .
git commit -m "feat: my new feature"
git push origin dev
# ⏳ Wait for Railway staging deployment

# 5. Test in staging
# Open: https://your-staging-url.up.railway.app

# 6. When ready, promote to production
./dev_workflow.sh
# Select option 3: "Promote dev → prod"

# This will:
# - Merge dev into main
# - Push to GitHub
# - Trigger Railway production deployment
# - Trigger Vercel production deployment
```

### Quick Helper Script Usage:

```bash
./dev_workflow.sh

Options:
1) Check current status      # See which branch you're on
2) Setup dev branch          # Already done!
3) Promote dev → prod        # Use this to go live
4) Switch to dev branch      # Quick switch
5) Switch to main branch     # Quick switch
6) View deployment status    # Opens Railway
```

## 📋 Important Rules

### ✅ DO:
- Work on `dev` branch for all development
- Test in staging before promoting
- Use `./dev_workflow.sh` for promotions
- Keep commits small and focused

### ❌ DON'T:
- Never commit directly to `main`
- Never skip staging testing
- Never force push to main or dev
- Never merge main into dev (only dev → main)

## 🔍 Deployment Flow

```
Local Development
    ↓ (git push origin dev)
Staging (Railway + Vercel)
    ↓ (test & verify)
    ↓ (git merge dev into main)
Production (Railway + Vercel)
    ↓
Live Users ✨
```

## 📚 Quick Reference

| Action | Command |
|--------|---------|
| Start working | `git checkout dev` |
| Deploy to staging | `git push origin dev` |
| Promote to prod | `./dev_workflow.sh` (option 3) |
| Check branch | `git branch --show-current` |
| Emergency rollback | `git revert HEAD && git push` |

## 🆘 Help & Resources

- Full workflow guide: `docs/DEV_WORKFLOW.md`
- Quick commands: `docs/QUICK_REFERENCE.md`
- Local dev setup: `docs/LOCAL_DEVELOPMENT.md`

## ✨ What You Get

- **Safe deployments**: Test in staging before going live
- **Easy rollbacks**: One command to undo production changes
- **Clear separation**: Development never affects production
- **Automatic deploys**: Push and Railway/Vercel handle the rest
- **Professional workflow**: Industry-standard branching strategy

---

**You're all set!** Just need to configure the Railway environments (Step 1-3 above), and you're ready to go! 🚀
