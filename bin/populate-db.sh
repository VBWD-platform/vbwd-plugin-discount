#!/bin/bash
# Populate Discount Database
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Discount Database Population           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

if ! docker compose ps 2>/dev/null | grep -q "api.*Up"; then
    echo -e "${RED}Error: api service is not running${NC}"
    echo "  Start with: make up"
    exit 1
fi

echo -e "${YELLOW}Populating discount demo data...${NC}"
echo ""

docker compose exec -T api python /app/plugins/discount/bin/run_populate.py

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}Discount Population Complete${NC}"
    echo -e "${GREEN}  Discounts + coupons created${NC}"
    exit 0
else
    echo -e "${RED}Failed to populate discount data${NC}"
    exit 1
fi
