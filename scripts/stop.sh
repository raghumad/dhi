#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping Dhi (धी)...${NC}"

# Function to kill port
kill_port() {
    PORT=$1
    NAME=$2
    
    # Check if anything is running on the port
    PID=$(lsof -t -i:$PORT 2>/dev/null)
    
    if [ -n "$PID" ]; then
        echo -e "${RED}[-] Killing $NAME on Port $PORT (PID: $PID)...${NC}"
        kill -9 $PID
    else
        echo -e "${GREEN}[*] No $NAME found on Port $PORT.${NC}"
    fi
}

# 1. Kill API
kill_port 8000 "API (The Spine)"

# 2. Kill Web
kill_port 3000 "Web (The Face)"

echo -e "\n${GREEN}System Stopped.${NC}"
