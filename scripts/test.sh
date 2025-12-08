#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Resolve Project Root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Idempotency: Auto-run setup if environment is missing
if [ ! -f ".venv/bin/behave" ]; then
    echo "⚠️  Environment not found. Running setup first..."
    ./scripts/setup.sh
fi

# Function to check if API is running
is_api_running() {
    lsof -i:8000 -t >/dev/null 2>&1
}

output_logs() {
    if [ -f api_test.log ]; then
        echo -e "\n${YELLOW}--- API Logs (Tail) ---${NC}"
        tail -n 20 api_test.log
    fi
}

STARTED_BY_SCRIPT=false

# 1. Ensure API is running
if is_api_running; then
    echo -e "${GREEN}[+] API is already running on port 8000.${NC}"
else
    echo -e "${YELLOW}[!] API not found using lsof 8000. Starting temporary instance...${NC}"
    source .venv/bin/activate
    # Run in background, redirect logs to file for debugging
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > api_test.log 2>&1 &
    API_PID=$!
    STARTED_BY_SCRIPT=true
    
    echo -e "${BLUE}[.] Waiting for API to come alive (this may take 10-20s for Model Load)...${NC}"
    
    # Wait loop
    MAX_RETRIES=30 # 30 seconds max
    COUNT=0
    while ! curl -s http://localhost:8000/docs > /dev/null; do
        sleep 1
        COUNT=$((COUNT+1))
        if [ $COUNT -ge $MAX_RETRIES ]; then
            echo -e "${RED}[!] API failed to start after $MAX_RETRIES seconds.${NC}"
            output_logs
            kill $API_PID 2>/dev/null || true
            exit 1
        fi
        echo -n "."
    done
    echo -e "\n${GREEN}[+] API is Ready!${NC}"
fi

# 2. Run Tests
echo -e "\n${BLUE}xxx Running Dhi BDD Tests...${NC}"
set +e # Allow test failure to not immediately exit so we can cleanup
.venv/bin/behave
TEST_EXIT_CODE=$?
set -e

# 3. Cleanup
if [ "$STARTED_BY_SCRIPT" = true ]; then
    echo -e "\n${YELLOW}[!] Stopping temporary API instance (PID: $API_PID)...${NC}"
    kill $API_PID 2>/dev/null || true
    # wait $API_PID 2>/dev/null || true
fi

echo ""
echo "==============================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Tests Completed Successfully.${NC}"
else
    echo -e "${RED}❌ Tests Failed.${NC}"
fi
echo "📊 Report Generated: $(pwd)/out/test_report.html"
echo "==============================================="

exit $TEST_EXIT_CODE
