#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Resolve Project Root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}      Dhi (धी) // The Intellect            ${NC}"
echo -e "${GREEN}===========================================${NC}"

# Function to kill processes on exit
cleanup() {
    echo -e "\n${YELLOW}[!] Shutting down...${NC}"
    if [ -n "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    if [ -n "$WEB_PID" ]; then
        kill $WEB_PID 2>/dev/null || true
    fi
    exit 0
}

# Trap Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

# 1. Start API (The Spine)
echo -e "\n${BLUE}[+] Igniting The Spine (FastAPI)...${NC}"
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
echo "    -> API PID: $API_PID"

# Wait for API to be healthy? (Optional, but nice)
# sleep 2

# 2. Start Frontend (The Face)
echo -e "\n${BLUE}[+] Awakening The Face (Next.js)...${NC}"
cd src/web
npm run dev &
WEB_PID=$!
echo "    -> Web PID: $WEB_PID"

echo -e "\n${GREEN}System Is Live.${NC}"
echo -e "Web: http://localhost:3000"
echo -e "API: http://localhost:8000"
echo -e "${YELLOW}Press Ctrl+C to stop.${NC}"

# Wait forever
wait
