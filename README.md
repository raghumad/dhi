# Dhi (धी) - Scripture Search Engine

**Dhi** ("Intellect" or "Understanding" in Sanskrit) is a privacy-first, on-device semantic search engine for ancient scriptures.

## The Goal: "Unified Runtime"
We aim to build a search engine that runs entirely on your local device (Linux/Mac/Android) with minimal dependencies.

### Architecture
*   **The Brain**: `llama.cpp` (Llama-3) for understanding context, debating, and answering questions.
*   **The Tongue**: `IndicXlit` (via `aksharamukha` / Python) for accurate transliteration of Indic scripts.
*   **The Glue**: Python bindings effectively creating a hybrid runtime.

## Setup

### 1. One-Click Setup
We provide an idempotent script to check your Python version, create the virtual environment, and install pinned dependencies.

```bash
# Run the setup script
./setup.sh

# Activate the environment
source .venv/bin/activate
```

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
