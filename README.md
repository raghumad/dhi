# Dhi (धी) // The Intellect

> "Nec verbum verbo curabis reddere, fidus Interpres"  
> — Horace

Dhi is a local, privacy-first, scripture research engine powered by **Llama 3** (The Brain) and **Next.js** (The Face).

## 🚀 Quick Start

You need two terminals to run the full stack:

### 1. The Spine (API)
This loads the persistent Llama model into RAM.
```bash
# In Terminal 1 (Root of repo)
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
*Wait for "✅ Model Loaded" before starting the UI.*

### 2. The Face (UI)
The "Ruthless Truth" interface.
```bash
# In Terminal 2
cd src/web
npm run dev
```
Open [http://localhost:3000](http://localhost:3000).

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
