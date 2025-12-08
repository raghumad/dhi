#!/bin/bash

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Resolve Project Root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"



# Function to kill processes on exit
cleanup() {
    echo -e "\n${YELLOW}[!] Shutting down...${NC}"
    if [ -n "$API_PID" ]; then kill $API_PID 2>/dev/null || true; fi
    if [ -n "$WEB_PID" ]; then kill $WEB_PID 2>/dev/null || true; fi
    exit 0
}

# Function to kill existing ports
kill_port() {
    PORT=$1
    NAME=$2
    PID=$(lsof -t -i:$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
        echo -e "${YELLOW}[-] Found existing $NAME on Port $PORT (PID: $PID). Killing...${NC}"
        kill -9 $PID
        sleep 1
    fi
}

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}   धी / ధీ / ಧೀ / ധീ / Dhī   ${NC}"
echo -e "${GREEN}===========================================${NC}"

# 0. Cleanup Existing
kill_port 8000 "API"
kill_port 3000 "Web"

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
