# Dhi Project Makefile
# Use 'make help' to see available commands

.PHONY: help setup dev start stop test debug clean lint

# Colors
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# Shell settings
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

help: ## Show this help message
	@echo -e "${GREEN}Dhi (धी) Management Interface${NC}"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "${BLUE}%-15s${NC} %s\n", $$1, $$2}'

setup: ## Install all dependencies (Python + Node)
	@echo -e "${GREEN}[+] Setting up Environment...${NC}"
	@# 1. Check Python
	@if ! command -v python3.12 &> /dev/null; then echo -e "${RED}Error: Python 3.12 required.${NC}"; exit 1; fi
	@# 2. Create Venv (Check for bin/pip to ensure valid env)
	@if [ ! -f ".venv/bin/pip" ]; then \
		echo "    Creating .venv..."; \
		rm -rf .venv; \
		python3.12 -m venv .venv; \
	fi
	@# 3. Pip Install (Idempotent by default)
	@echo "    Installing Python Deps..."
	@.venv/bin/pip install --upgrade pip > /dev/null
	@.venv/bin/pip install -r requirements.txt
	@[ -f "src/api/requirements.txt" ] && .venv/bin/pip install -r src/api/requirements.txt || true
	@# 4. Node Install (Check for node_modules)
	@echo "    Installing Node Deps..."
	@if [ -d "src/web" ] && command -v npm &> /dev/null; then \
		if [ ! -d "src/web/node_modules" ]; then \
			cd src/web && npm install; \
		else \
			echo "    Node modules present. Skipping npm install."; \
		fi \
	else \
		echo -e "${YELLOW}    Skipping Node setup (src/web missing or npm not found).${NC}"; \
	fi
	@echo -e "${GREEN}[+] Setup Complete.${NC}"

dev: start ## Alias for start
start: ## Start API and Web servers concurrently
	@echo -e "${GREEN}[+] Igniting Dhi System...${NC}"
	@make stop
	@echo -e "${BLUE}API (Port 8000) | Web (Port 3000)${NC}"
	@# Trap SIGINT to kill background processes
	@trap 'kill 0' EXIT; \
	.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 & \
	cd src/web && npm run dev & \
	wait

stop: ## Kill processes on ports 8000 and 3000
	@echo -e "${YELLOW}[!] Stopping Services...${NC}"
	@lsof -t -i:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
	@lsof -t -i:3000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
	@echo -e "${GREEN}[+] Stopped.${NC}"

test: ## Run BDD Tests (Behave)
	@echo -e "${BLUE}[+] Running Tests...${NC}"
	@# Ensure API is ready for api tests - simpler to just run logic tests for now or rely on separate run
	@# For full integration tests, we need the API running.
	@# Run disjointly or assume user ran 'make dev' in another tab? 
	@# Let's mirror test.sh logic: spin up temp API if needed.
	@if ! lsof -i:8000 -t >/dev/null; then \
		echo -e "${YELLOW}    Starting temporary API for tests...${NC}"; \
		.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 & \
		PID=$$!; \
		echo "    Waiting for API..."; \
		sleep 5; \
		.venv/bin/behave || { kill $$PID; exit 1; }; \
		kill $$PID; \
	else \
		.venv/bin/behave; \
	fi

debug: ## Run ingestion verification script
	@echo -e "${GREEN}[+] Debugging Ingestion & Retrieval...${NC}"
	@.venv/bin/python src/ingest.py out/rigveda.pdf --limit 10 --force
	@echo -e "${BLUE}[?] Querying...${NC}"
	@.venv/bin/python src/search.py --model models/llama-3.2-3b-instruct-q4km.gguf --verify-retrieval "Who is Agni?"

ingest: ## Bulk ingest PDFs from DIR (default: out/)
	@echo -e "${GREEN}[+] Ingesting PDFs from $(DIR)${NC}"
	@# Default DIR to out if not specified
	$(eval DIR ?= out)
	@find $(DIR) -name "*.pdf" -print0 | xargs -0 -I {} bash -c \
		'echo "Processing {}..."; .venv/bin/python src/ingest.py "{}"'

ingest-debug: ## Ingest without systemd limits (VERBOSE=True)
	@echo -e "${YELLOW}[!] Running Ingestion in DEBUG mode (No Limits, Verbose)${NC}"
	@$(eval DIR ?= out)
	@export VERBOSE=True; find $(DIR) -name "*.pdf" -print0 | xargs -0 -I {} .venv/bin/python src/ingest.py "{}"

clean: ## Remove artifacts and temp files
	@echo -e "${YELLOW}[!] Cleaning Artifacts...${NC}"
	@# Wipe out/ but keep the source PDF so we can re-ingest
	@find out -type f -not -name '*.pdf' -delete
	@rm -rf __pycache__ .pytest_cache
	@find . -name "*.pyc" -delete
	@echo -e "${GREEN}[+] Clean.${NC}"


gpu: ## Re-install with ROCm (Vega 64 Support)
	@echo -e "${YELLOW}[!] Re-compiling for ROCm (Vega 64/GFX900)...${NC}"
	@# Force reinstall with HIP support and GFX900 targeting
	@CMAKE_ARGS="-DGGML_HIPBLAS=on -DAMDGPU_TARGETS=gfx900" \
	HSA_OVERRIDE_GFX_VERSION=9.0.0 \
	.venv/bin/pip install llama-cpp-python \
	--upgrade --force-reinstall --no-cache-dir
	@echo -e "${GREEN}[+] GPU Support Enabled.${NC}"

lint: ## Lint codebase (Optional)
	@.venv/bin/pip install pylint >/dev/null
	@.venv/bin/pylint src/ --disable=C,R,W0703 || true
