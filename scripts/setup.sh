#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}   Dhi (धी) Environment Setup${NC}"
echo -e "${GREEN}===========================================${NC}"

# 1. Check for Python 3.12
echo -e "\n[+] Checking for Python 3.12..."
if command -v python3.12 &> /dev/null; then
    PY_CMD=python3.12
    echo "    Found python3.12 command."
elif command -v python3 &> /dev/null; then
    # Check if python3 is actually 3.12
    VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ "$VER" == "3.12" ]; then
        PY_CMD=python3
        echo "    Found python3 (version 3.12)."
    else
        echo -e "${RED}Error: python3 is version $VER. We strictly require Python 3.12.${NC}"
        echo "Please install Python 3.12 or use 'python3.12' executable."
        exit 1
    fi
else
    echo -e "${RED}Error: Python 3 not found.${NC}"
    exit 1
fi

# 2. Check/Create Virtual Environment
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ] && [ -x "$VENV_DIR/bin/python" ] && [ -x "$VENV_DIR/bin/pip" ]; then
    echo -e "\n[+] Valid virtual environment '$VENV_DIR' found."
else
    if [ -d "$VENV_DIR" ]; then
         echo -e "\n[!] Virtual environment '$VENV_DIR' is broken or incomplete. Recreating..."
         rm -rf "$VENV_DIR"
    fi
    echo -e "\n[+] Creating virtual environment in '$VENV_DIR'..."
    $PY_CMD -m venv $VENV_DIR --without-pip || true
    
    # Check if pip exists, if not, bootstrap it
    if [ ! -x "$VENV_DIR/bin/pip" ]; then
        echo -e "\n[!] 'ensurepip' failed (Debian/Ubuntu issue?). Bootstrapping pip manually..."
        curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        $VENV_DIR/bin/python get-pip.py
        rm get-pip.py
    fi
fi

# 3. Install/Sync Dependencies
echo -e "\n[+] Installing dependencies..."
# Resolve Project Root (one level up from this script)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
# We use the pip inside the venv directly to ensure we install there
PIP_CMD="$VENV_DIR/bin/pip"

$PIP_CMD install --upgrade pip
$PIP_CMD install -r requirements.txt
if [ -f "src/api/requirements.txt" ]; then
    echo -e "\n[+] Installing API dependencies..."
    $PIP_CMD install -r src/api/requirements.txt
fi

# 4. Frontend Setup
if [ -d "src/web" ]; then
    echo -e "\n[+] Installing Frontend dependencies..."
    if command -v npm &> /dev/null; then
        cd src/web && npm install && cd ../..
    else
        echo -e "${RED}Error: npm not found. Install Node.js to run the frontend.${NC}"
    fi
fi

# 4. Setup Complete
echo -e "\n${GREEN}===========================================${NC}"
echo -e "${GREEN}   Setup Complete!${NC}"
echo -e "${GREEN}===========================================${NC}"
