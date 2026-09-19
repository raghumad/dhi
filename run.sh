#!/usr/bin/env bash
# One-command local web server for the Harappan Seals Open Catalog.
# Usage: ./run.sh  (then open http://localhost:8000 )
set -e
PORT="${PORT:-8000}"
echo "🏺 Harappan Seals — Open Catalog"
echo "→ Serving at http://localhost:${PORT}"
echo "→ Press Ctrl+C to stop"
# Serve repo root so both /site and /data resolve
python3 -m http.server "${PORT}" --directory "$(dirname "$0")"
