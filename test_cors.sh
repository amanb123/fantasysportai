#!/bin/bash

# Test CORS Configuration
# Tests both staging and production CORS settings

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Testing CORS Configuration${NC}"
echo ""

# URLs
STAGING_BACKEND="https://fantasysportai-staging.up.railway.app"
PROD_BACKEND="https://fantasysportai-production.up.railway.app"
STAGING_FRONTEND="https://fantasysportai-git-dev-amanb123.vercel.app"
PROD_FRONTEND="https://fantasysportai.vercel.app"

echo -e "${YELLOW}Testing Staging Backend CORS...${NC}"
echo "Backend: $STAGING_BACKEND"
echo "Origin: $STAGING_FRONTEND"
echo ""

# Test staging OPTIONS request
RESPONSE=$(curl -s -X OPTIONS \
  -H "Origin: $STAGING_FRONTEND" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -w "\nHTTP_STATUS:%{http_code}" \
  "$STAGING_BACKEND/api/sleeper/session" 2>&1)

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
CORS_HEADER=$(echo "$RESPONSE" | grep -i "access-control-allow-origin" || echo "NOT_FOUND")

echo -n "HTTP Status: "
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}$HTTP_CODE ✅${NC}"
else
    echo -e "${RED}$HTTP_CODE ❌${NC}"
fi

echo -n "CORS Header: "
if [[ "$CORS_HEADER" != "NOT_FOUND" ]]; then
    echo -e "${GREEN}Present ✅${NC}"
    echo "  $CORS_HEADER"
else
    echo -e "${RED}Missing ❌${NC}"
    echo -e "${YELLOW}  This is the problem! Railway staging needs CORS_ORIGINS updated.${NC}"
fi

echo ""
echo -e "${YELLOW}Testing Production Backend CORS...${NC}"
echo "Backend: $PROD_BACKEND"
echo "Origin: $PROD_FRONTEND"
echo ""

# Test production OPTIONS request
RESPONSE=$(curl -s -X OPTIONS \
  -H "Origin: $PROD_FRONTEND" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -w "\nHTTP_STATUS:%{http_code}" \
  "$PROD_BACKEND/api/sleeper/session" 2>&1)

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
CORS_HEADER=$(echo "$RESPONSE" | grep -i "access-control-allow-origin" || echo "NOT_FOUND")

echo -n "HTTP Status: "
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}$HTTP_CODE ✅${NC}"
else
    echo -e "${RED}$HTTP_CODE ❌${NC}"
fi

echo -n "CORS Header: "
if [[ "$CORS_HEADER" != "NOT_FOUND" ]]; then
    echo -e "${GREEN}Present ✅${NC}"
    echo "  $CORS_HEADER"
else
    echo -e "${RED}Missing ❌${NC}"
fi

echo ""
echo -e "${BLUE}📋 Recommendations:${NC}"
echo ""

if [ "$HTTP_CODE" != "200" ]; then
    echo -e "${YELLOW}⚠️  CORS Issue Detected!${NC}"
    echo ""
    echo "Fix in Railway:"
    echo "1. Go to: https://railway.app"
    echo "2. Select your project → staging environment"
    echo "3. Go to Variables tab"
    echo "4. Update CORS_ORIGINS to:"
    echo -e "   ${GREEN}https://fantasysportai.vercel.app,https://*.vercel.app${NC}"
    echo ""
    echo "For production:"
    echo -e "   ${GREEN}https://fantasysportai.vercel.app${NC}"
    echo ""
    echo "See docs/CORS_FIX_STAGING.md for complete guide"
else
    echo -e "${GREEN}✅ CORS looks good!${NC}"
fi

echo ""
echo -e "${BLUE}🔗 Useful Links:${NC}"
echo "  Railway: https://railway.app"
echo "  Docs: docs/CORS_FIX_STAGING.md"
