# Dhi (धी) // The Intellect

> "Nec verbum verbo curabis reddere, fidus Interpres"  
> — Horace

Dhi is a local, privacy-first, scripture research engine powered by **Llama 3** (The Brain) and **Next.js** (The Face).

## 🚀 Quick Start

One command to rule them all:
```bash
./scripts/start.sh
```
This will ignite:
1.  **The Spine (API)** on port 8000.
2.  **The Face (UI)** on port 3000.

### Setup (First Time)
If you are pulling this for the first time:
```bash
./scripts/setup.sh
```
This installs Python (Backend) and Node.js (Frontend) dependencies.

---

## 🧪 Testing

### API Tests (BDD)
Verify the brain is healthy.
```bash
source .venv/bin/activate
behave features/api_integration.feature
```

### UI Tests (E2E)
Verify the interface is responsive.
```bash
cd src/web
npx playwright test
```

## 🏗 Architecture
- **Frontend**: Next.js 14, Tailwind CSS (Obsidian/Steel Theme).
- **Backend**: FastAPI, Uvicorn, Llama-cpp-python.
- **Data**: JSON Vector Store (Rigveda), Hurmit Nerd Fonts.
- **Model**: Llama-3-8B-Quantized (GGUF).
