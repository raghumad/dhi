# Dhi (धी) // The Research Engine

> "Nec verbum verbo curabis reddere, fidus Interpres"  
> — Horace

Dhi is a local, privacy-first, scripture research engine powered by **Llama 3** (The Brain) and a custom **Native Binary Storage Engine** (The Memory).

## 🚀 Key Features
- **Zero-Wait Startup**: Boots instantly using memory-mapped (`mmap`) storage. No heavy JSON loading.
- **Zero-Copy Retrieval**: Kernels page in only the scripture verses needed for a query.
- **Vector Search**: HNSW indexing for semantic retrieval (`hnswlib`).
- **Privacy First**: Fully local inference using quantized GGUF models (`llama.cpp`).

---

## 🛠️ Quick Start (Makefile)

We use a standard `Makefile` for all operations.

### 1. Setup
Install Python (3.12) and Node.js dependencies.
```bash
make setup
```

### 2. Configuration
Copy the example environment file and adjust if needed (e.g., to increase Context Window).
```bash
cp .env.example .env
```
*   `N_CTX`: Context window size (Default: `8192`).
*   `DATASET_NAME`: Dataset identifier (Default: `rigveda`).

### 3. Run
Ignite the API (Port 8000) and Web UI (Port 3000).
```bash
make dev
```
*   **Web**: [http://localhost:3000](http://localhost:3000)
*   **API**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Stop
Kill background processes.
```bash
make stop
```

---

## 🧪 Development Workflow

| Command | Description |
| :--- | :--- |
| `make clean` | Wipes generated artifacts (`.hnsw`, `.bin`, `.txt`). **Keeps source PDF.** |
| `make test` | Runs the BDD validation suite (API, CLI, Storage). |
| `make debug` | Runs a traceable ingestion and search verification script. |

### Re-Ingesting Data
To process a new PDF or re-process `rigveda.pdf`:
1.  Place your PDF in `out/`.
2.  Run:
    ```bash
    make clean
    .venv/bin/python src/ingest.py out/YOUR_FILE.pdf
    ```
    *   (Or use `make debug` which defaults to `out/rigveda.pdf` with a 10-chunk limit).

---

## 🏗 Architecture

### 1. Storage Engine (Custom)
Instead of a database, Dhi uses specific binary artifacts optimized for OS-level caching:
*   `rigveda.txt`: Raw text blob, mapped into virtual memory.
*   `rigveda.bin`: Fixed-width binary metadata (Offset/Length) for O(1) lookups.
*   `rigveda.hnsw`: Hierarchical Navigable Small World graph for vector search.

### 2. Stack
*   **Frontend**: Next.js 14, Tailwind CSS (Obsidian/Steel Theme).
*   **Backend**: FastAPI, Uvicorn.
*   **LLM**: `Llama-3.2-3B-Instruct-Q4_K_M.gguf`.

---

## 🛡️ Security
- **Frontend**: Hardened dependencies (`eslint-config-next` v16) with 0 vulnerabilities.
- **Backend**: Strict CORS policies configurable via `.env`.
