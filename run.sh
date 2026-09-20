#!/usr/bin/env bash
# Dhi: set up the environment, build the dataset from manifests, serve the API.
#
#   ./run.sh            set up env + build (if needed) + serve on :8000
#   ./run.sh --build    force a full rebuild, then serve
#   ./run.sh --no-build serve only (fails fast if data/ is empty)
set -euo pipefail
cd "$(dirname "$0")"

# --- system dependency: poppler (plate extraction) -----------------------
if ! command -v pdftoppm >/dev/null 2>&1; then
    echo "error: pdftoppm not found. Plate extraction needs poppler:" >&2
    echo "  sudo apt install poppler-utils   # Debian/Ubuntu" >&2
    echo "  brew install poppler             # macOS" >&2
    exit 1
fi

# --- python environment ---------------------------------------------------
UV=""
if command -v uv >/dev/null 2>&1; then
    UV=uv
elif [ -x "$HOME/.local/bin/uv" ]; then
    UV="$HOME/.local/bin/uv"
fi

if [ ! -x .venv/bin/python ]; then
    echo "creating .venv ..."
    if [ -n "$UV" ]; then
        "$UV" venv .venv
    else
        python3 -m venv .venv
    fi
fi
PY=.venv/bin/python

# Ensure project deps are installed (also repairs venvs created before
# the pipeline dependencies were declared).
if ! "$PY" -c "import yaml, PIL, numpy, scipy, fastapi" 2>/dev/null; then
    echo "installing dependencies ..."
    if [ -n "$UV" ]; then
        "$UV" sync
    else
        "$PY" -m pip install -e .
    fi
fi

# --- build + serve ---------------------------------------------------------
if [ "${1:-}" = "--build" ]; then
    rm -rf data/artifacts/plates data/figures data/records
    shift || true
fi

if [ "${1:-}" != "--no-build" ]; then
    # Build only what is missing; each stage is idempotent.
    "$PY" ingest/build.py
fi

exec "$PY" -m uvicorn api.main:app --host 127.0.0.1 --port 8000
