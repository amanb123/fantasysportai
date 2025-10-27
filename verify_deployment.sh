#!/bin/bash

# Verify Deployment Setup
# Checks that staging and production environments are correctly configured

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Verifying Deployment Configuration${NC}"
echo ""

# URLs
STAGING_BACKEND="https://fantasysportai-staging.up.railway.app"
PROD_BACKEND="https://fantasysportai-production.up.railway.app"
PROD_FRONTEND="https://fantasysportai.vercel.app"

echo -e "${BLUE}Testing Backend Health Endpoints...${NC}"

# Test staging backend
echo -n "Staging backend ($STAGING_BACKEND/health): "
if curl -s -f "$STAGING_BACKEND/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    echo "  Make sure Railway staging environment is deployed"
fi

# Test production backend
echo -n "Production backend ($PROD_BACKEND/health): "
if curl -s -f "$PROD_BACKEND/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    echo "  Make sure Railway production environment is deployed"
fi

echo ""
echo -e "${BLUE}Testing Frontend Deployments...${NC}"

# Test production frontend
echo -n "Production frontend ($PROD_FRONTEND): "
if curl -s -f "$PROD_FRONTEND" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️  Check manually${NC}"
fi

echo ""
echo -e "${BLUE}Checking Git Configuration...${NC}"

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -n "Current branch: "
if [ "$CURRENT_BRANCH" = "dev" ]; then
    echo -e "${GREEN}$CURRENT_BRANCH ✅${NC} (correct for development)"
elif [ "$CURRENT_BRANCH" = "main" ]; then
    echo -e "${YELLOW}$CURRENT_BRANCH ⚠️${NC} (switch to dev for development)"
else
    echo -e "${RED}$CURRENT_BRANCH ❌${NC} (should be dev or main)"
fi

# Check for uncommitted changes
echo -n "Working directory: "
if git diff-index --quiet HEAD --; then
    echo -e "${GREEN}Clean ✅${NC}"
else
    echo -e "${YELLOW}Has uncommitted changes ⚠️${NC}"
fi

# Check if dev branch exists locally
echo -n "Dev branch exists: "
if git show-ref --verify --quiet refs/heads/dev; then
    echo -e "${GREEN}✅ Yes${NC}"
else
    echo -e "${RED}❌ No${NC} (run: git checkout -b dev)"
fi

# Check if dev branch exists remotely
echo -n "Dev branch on GitHub: "
if git ls-remote --heads origin dev | grep -q dev; then
    echo -e "${GREEN}✅ Yes${NC}"
else
    echo -e "${RED}❌ No${NC} (run: git push -u origin dev)"
fi

echo ""
echo -e "${BLUE}Environment Files Check...${NC}"

# Check for required files
FILES=(
    ".env.development"
    ".env.production.template"
    "frontend/.env.staging"
    "frontend/.env.production"
    "dev_workflow.sh"
)

for file in "${FILES[@]}"; do
    echo -n "$file: "
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ Exists${NC}"
    else
        echo -e "${RED}❌ Missing${NC}"
    fi
done

echo ""
echo -e "${BLUE}📋 Environment URLs Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${YELLOW}Local Development:${NC}"
echo "  Backend:  http://localhost:3002"
echo "  Frontend: http://localhost:5173"
echo ""
echo -e "${YELLOW}Staging (dev branch):${NC}"
echo "  Backend:  $STAGING_BACKEND"
echo "  Frontend: https://fantasysportai-git-dev-*.vercel.app"
echo ""
echo -e "${YELLOW}Production (main branch):${NC}"
echo "  Backend:  $PROD_BACKEND"
echo "  Frontend: $PROD_FRONTEND"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo -e "${BLUE}🚀 Quick Commands${NC}"
echo "  Start local dev:    ./start_local_dev.sh"
echo "  Deploy to staging:  git push origin dev"
echo "  Promote to prod:    ./dev_workflow.sh"
echo "  Check this setup:   ./verify_deployment.sh"

echo ""
echo -e "${GREEN}✨ Setup verification complete!${NC}"
