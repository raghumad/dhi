#!/bin/bash
set -e

# Resolve Project Root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Idempotency: Auto-run setup if environment is missing
if [ ! -f ".venv/bin/behave" ]; then
    echo "⚠️  Environment not found. Running setup first..."
    ./scripts/setup.sh
fi

echo "xxx Running Dhi BDD Tests..."
.venv/bin/behave

echo ""
echo "==============================================="
echo "✅ Tests Completed."
echo "📊 Report Generated: $(pwd)/out/test_report.html"
echo "==============================================="
echo "To view the report, run: xdg-open out/test_report.html"
