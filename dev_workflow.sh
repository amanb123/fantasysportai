#!/bin/bash

# Development Workflow Helper Script
# Helps manage dev → prod promotion

set -e  # Exit on error

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Fantasy Basketball League - Dev Workflow Manager${NC}"
echo ""

# Function to check current branch
check_branch() {
    CURRENT_BRANCH=$(git branch --show-current)
    echo -e "${BLUE}Current branch: ${GREEN}$CURRENT_BRANCH${NC}"
}

# Function to promote dev to prod
promote_to_prod() {
    echo -e "${YELLOW}📦 Promoting dev to production...${NC}"
    
    # Check if on dev branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "dev" ]; then
        echo -e "${RED}❌ You must be on the dev branch to promote${NC}"
        echo "Run: git checkout dev"
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        echo -e "${RED}❌ You have uncommitted changes${NC}"
        echo "Please commit or stash your changes first"
        exit 1
    fi
    
    # Make sure dev is up to date
    echo -e "${BLUE}Pulling latest dev changes...${NC}"
    git pull origin dev
    
    # Run tests (if you have them)
    echo -e "${BLUE}Running tests...${NC}"
    # Uncomment when you have tests:
    # pytest tests/ || { echo -e "${RED}❌ Tests failed!${NC}"; exit 1; }
    
    # Switch to main and merge
    echo -e "${BLUE}Switching to main branch...${NC}"
    git checkout main
    git pull origin main
    
    echo -e "${BLUE}Merging dev into main...${NC}"
    git merge dev --no-ff -m "Promote dev to production - $(date +%Y-%m-%d)"
    
    # Push to production
    echo -e "${YELLOW}Ready to push to production!${NC}"
    echo -e "This will trigger Railway deployment to production."
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin main
        echo -e "${GREEN}✅ Successfully promoted to production!${NC}"
        echo -e "${BLUE}Monitor deployment at: https://railway.app${NC}"
        
        # Switch back to dev
        git checkout dev
        echo -e "${GREEN}Switched back to dev branch${NC}"
    else
        echo -e "${YELLOW}Cancelled. You're still on main branch.${NC}"
        echo "Run 'git checkout dev' to go back to dev"
    fi
}

# Function to create dev branch if it doesn't exist
setup_dev_branch() {
    if git show-ref --verify --quiet refs/heads/dev; then
        echo -e "${GREEN}✅ Dev branch already exists${NC}"
    else
        echo -e "${YELLOW}Creating dev branch...${NC}"
        git checkout -b dev
        git push -u origin dev
        echo -e "${GREEN}✅ Dev branch created and pushed${NC}"
    fi
}

# Main menu
echo "Select an option:"
echo "1) Check current status"
echo "2) Setup dev branch (first time)"
echo "3) Promote dev → prod"
echo "4) Switch to dev branch"
echo "5) Switch to main branch"
echo "6) View deployment status"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        check_branch
        echo ""
        git status
        ;;
    2)
        setup_dev_branch
        ;;
    3)
        promote_to_prod
        ;;
    4)
        git checkout dev
        echo -e "${GREEN}✅ Switched to dev branch${NC}"
        ;;
    5)
        git checkout main
        echo -e "${GREEN}✅ Switched to main branch${NC}"
        ;;
    6)
        echo -e "${BLUE}Opening Railway dashboard...${NC}"
        open "https://railway.app"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
