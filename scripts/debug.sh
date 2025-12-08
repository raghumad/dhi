#!/bin/bash
set -e

# Resolve Project Root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== 🐛 Dhi Debug Pipeline ==="
echo "Working Directory: $(pwd)"

# 1. Environment Check
echo -e "\n[1/3] 🔍 Checking Environment..."
if [ ! -f ".venv/bin/python" ]; then
    echo "⚠️  Virtualenv missing. Running setup..."
    ./scripts/setup.sh
fi

# 2. Ingestion (Traceable)
echo -e "\n[2/3] 📚 Running Ingestion (Limit: 10 chunks)..."
echo "Command: src/ingest.py out/rigveda.pdf --limit 10"

INGEST_CMD=".venv/bin/python src/ingest.py out/rigveda.pdf --limit 10"

# Run Ingestion directly (Internal limits handle resource usage)
$INGEST_CMD

# 3. Search Verification
echo -e "\n[3/3] 🧠 Verifying Search Logic..."
echo "Query: 'Who is Agni?'"

.venv/bin/python src/search.py --model models/model.gguf --verify-retrieval "Who is Agni?"

echo -e "\n=== ✅ Debug Run Complete ==="
echo "Artifacts generated in out/"
