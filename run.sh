#!/usr/bin/env bash
# Dhi: build the dataset from manifests, then serve the API.
#
#   ./run.sh            build (if needed) + serve on :8000
#   ./run.sh --build    force a full rebuild, then serve
#   ./run.sh --no-build serve only (fails fast if data/ is empty)
set -euo pipefail
cd "$(dirname "$0")"

PY=python3
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; fi

if [ "${1:-}" = "--build" ]; then
    rm -rf data/artifacts/plates data/figures data/records
    shift || true
fi

if [ "${1:-}" != "--no-build" ]; then
    # Build only what is missing; each stage is idempotent.
    $PY ingest/build.py
fi

exec $PY -m uvicorn api.main:app --host 127.0.0.1 --port 8000
