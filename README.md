# Dhi (धी) - Scripture Search Engine

**Dhi** ("Intellect" or "Understanding" in Sanskrit) is a privacy-first, on-device semantic search engine for ancient scriptures.

## The Goal: "Unified Runtime"
We aim to build a search engine that runs entirely on your local device (Linux/Mac/Android) with minimal dependencies.

### Architecture
*   **The Brain**: `llama.cpp` (Llama-3) for understanding context, debating, and answering questions.
*   **The Tongue**: `IndicXlit` (via `aksharamukha` / Python) for accurate transliteration of Indic scripts.
*   **The Glue**: Python bindings effectively creating a hybrid runtime.

## Setup

### 1. One-Click Setup (Recommended)
This script is **idempotent** (safe to run multiple times). It creates the `.venv` and installs dependencies.
```bash
./scripts/setup.sh
```

### ✅ Running Tests
Run the BDD test suite (black-box tests).
**Note**: This script is also **idempotent**. It will auto-run setup if needed.
```bash
./scripts/test.sh
```
This will:
1.  Run all scenarios in `features/`.
2.  Generate a performance report at `test_report.html`.

### 2. Manual Setup (Alternative)
If the script fails, you can do it manually:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Ingestion (Prototype)
    ```bash
    python src/ingest.py
    ```

## Hardware Support
*   **Mac**: Native Metal (GPU) support via `llama.cpp`.
*   **Linux**: CUDA support.
*   **Android**: Future execution via Gemini Nano or llama.cpp (UserLAnd).
