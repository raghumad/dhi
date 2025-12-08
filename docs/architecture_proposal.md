# Architecture Proposal: "The Research Interface" (Local Scripture Research Engine)

## Executive Summary
This document outlines the technical architecture for a privacy-first, on-device application that allows users to research massive scripture files (PDF/TXT) using natural language. It solves for **Indic script complexity**, **Modern Bias**, and **Offline Privacy**.

## 1. The Data Pipeline (Local RAG)
*Goal: Turn `Rigveda.pdf` into a searchable brain.*

### A. Ingestion Layer
*   **Tool**: `PyMuPDF` (Python).
*   **Why**: Superior handling of native PDF text extraction compared to `pypdf`.
*   **Logic**:
    1.  User drags & drops PDF.
    2.  Extract text page-by-page.
    3.  **Heuristic Cleaning**: Remove headers/footers using coordinate analysis (PyMuPDF allows this).

### B. The "Universal Script" Normalization
*   **Tool**: `aksharamukha` (Python).
*   **Why**: User might search "Agni" (Roman) but text is "అగ్ని" (Telugu).
*   **Pipeline**:
    *   **Step 1**: Detect script of incoming chunk.
    *   **Step 2**: Store *two* versions in the database:
        *   `raw_text`: Original (for display).
        *   `canonical_text`: Transliterated to **ISO-15919 Roman** (for search matching).

### C. Storage Engine: "WORM + Pointers"
*Goal: Zero-Copy, Memory-Mapped access similar to FlexBuffers.*
1.  **Immutability**: The core `Rigveda.txt` is **WORM** (Write Once, Read Many). We never modify it.
2.  **File 1: The Blob ([rigveda_normalized.txt](file:///home/raghu/src/dhi/rigveda_normalized.txt))**
    *   A massive, contiguous UTF-8 text file.
    *   **Mapped**: Python `mmap` allows specific byte-range reads without loading 50MB into RAM.
3.  **File 2: The Index (`index.bin`)**
    *   A custom binary format (or lightweight SQLite) storing:
        *   `ID` (int)
        *   `Vector` (3072 floats)
        *   `Offset` (Start Byte)
        *   `Length` (Byte Count)
4.  **User Notes**: Stored in a separate `notes.jsonl` (Append-Only).
    *   Format: `{"target_id": "verse_10", "note": "Check commentary..."}`.
    *   This separates static "Truth" from dynamic "UserData".
5.  **The "Portable Book" (`.dhi` Package)**:
    *   Since `rigveda.txt` and `index.bin` are immutable, they can be zipped into a single file.
    *   **Benefit**: "Compute Once, Run Everywhere".

### D. Optimization Strategy (Linux Kernel Tuning)
*   **Problem**: RAG retrieval is inherently **random access**. Reading chunk #42, then #105, then #7 causes disk thrashing if the OS tries to "read ahead" sequentially.
*   **Solution**:
    1.  **Global Policy**: `madvise(MADV_RANDOM)` on the memory maps. This disables the kernel's aggressive sequential readahead, saving I/O.
    2.  **Active Prefetch**: When HNSW returns a batch of IDs (e.g., top 5), we issue `madvise(MADV_WILLNEED)` for those specific byte ranges *before* reading them. This triggers parallel async page-ins.

## 2. On-Device Intelligence (The Brain)
*   **Engine**: `llama.cpp` (running as a Python subprocess via `llama-cpp-python`).
*   **Model**: `Llama-3-8B-Instruct-v2` (Quantized q4_k_m, ~4GB).
    *   **Why**: Smart enough to follow complex "Persona" instructions ("Be a Historian", "Be a Debater").
*   **RAG Workflow**:
    1.  User Query: "What does Rigveda say about gambling?"
    2.  Lookup: Retrieve top 5 chunks from ChromaDB (using LaBSE embeddings).
    3.  Prompt: "Context: [Chunk 1, Chunk 2...] Question: [User Query]. Answer as [Persona]."

## 3. The "Multi-Lens" UI (Bias Mitigation)
*   **Framework**: Next.js (Static Export) + Python Flask (Local Host).
*   **Features**:
    *   **Lens Toggle**:
        *   **🔎 Historian**: Pure context (1500 BCE norms).
        *   **⚖️ Literal**: Word-for-word translation.
        *   **🔥 Debater**: Eric Cartman style argumentative quotes.
    *   **Pronunciation Button**: Uses `gTTS` (Telugu/Sanskrit) for the visible shloka.

## 4. Hardware Requirements
*   **RAM**: 8GB Minimum (4GB for System + 4GB for LLM).
*   **Storage**: ~6GB (Models + App).
*   **GPU**: Optional (Accelerates inference, but runs on CPU).

## 5. Evaluation of Alternatives
### Why not "nanochat" (Andrej Karpathy)?
The user asked to evaluate `nanochat` as the inference engine.
*   **Verdict**: **Not recommended for this specific use case.**
*   **Reasoning**:
    *   `nanochat` (and `llama2.c`) is primarily an **educational** project designed to teach how LLMs work from scratch.
    *   It lacks the robust **ecosystem** of `llama.cpp` (GGUF file format support, broad quantization options, bindings for Python/Node.js).
    *   `llama.cpp` is battle-tested for **production edge inference** with support for the specific models (Llama 3, Mistral) and embeddings (BERT/LaBSE) we need.

### What about "Gemini Nano" (Android/Chrome)?
The user asked about "gemini3" (likely referring to the **Gemini Nano** edge ecosystem).
*   **Verdict**: **Excellent for "Native" Apps, but fragmented.**
*   **Pros**:
    *   **Zero Download**: Model ships with the OS (Android/Chrome). User doesn't download 4GB.
    *   **Hardware Acceleration**: Native NPU usage via AICore.
*   **Cons**:
    *   **Availability**: Only on high-end Androids (Pixel 9, S24) and Desktop Chrome (Dev Channel).
    *   **Control**: Harder to inject custom context (RAG) compared to `llama.cpp`.
*   **Recommendation**:
    *   **Phase 1 (Prototype)**: Stick to `llama.cpp` for guaranteed performance on *any* machine.
    *   **Phase 2 (Mobile App)**: Use Gemini Nano via Google AI Edge SDK for the Android version.

### Can we convert IndicXlit to use with llama.cpp?
The user asked about theoretically converting the Fairseq (Encoder-Decoder) models to Decoder-only for use in `llama.cpp`.
*   **The Theory**: Yes, you can technically retrain/distill the 11M parameter transliteration logic into a small Decoder-only model (like a tiny GPT-2).
*   **The "Advantage" (Pros)**: 
    *   **Unified Runtime**: You would only need `llama.cpp` effectively removing the Python/Fairseq dependency.
    *   **Deployment**: Simpler single-binary distribution.
*   **The "Reality" (Cons)**:
    *   **Overhead**: `llama.cpp` is optimized for multi-gigabyte models. Running an 11MB model inside it incurs significant overhead (loading, context switching) compared to a specialized runtime.
    *   **Quality Risk**: Encoder-Decoder models are historically better for character-level tasks where the *entire* input word must be "seen" before generating output. A Decoder-only model might struggle with "future" characters in a word context without heavy attention tuning.
*   **Verdict**: **Not worth the engineering effort.** The hybrid Python pipeline is standard industry practice.

## 6. The "Unified Runtime" Strategy (Future-Proofing)
The user expressed a strong desire to unify everything under `llama.cpp` to avoid "model inventory hell."

**The Golden Rule**: *If a general-purpose model can do it well enough, delete the specialized model.*

### Can Llama-3 replace IndicXlit?
Instead of converting `IndicXlit`, we can simply **ask Llama-3 to transliterate**.
*   **Prompt**: *"Transliterate the following Roman text to Telugu: 'Om bhur bhuva svaha'"*
*   **Pros**: 
    1.  **Zero Extra Dependencies**: You strictly use `llama.cpp` for *everything* (Chat, Search, Transliteration).
    2.  **Future Proof**: As Llama-4/5 come out, your transliteration gets better automatically.
*   **Cons**:
    1.  **Latency**: Llama-3-8B is slower (tokens/sec) than a tiny 11M specialized model for simple word-swaps.
    2.  **Accuracy**: Specialized models (IndicXlit) are trained on millions of word pairs and are currently more accurate for strict transliteration than general LLMs.

**Recommendation**:
Start with **Hybrid** (for accuracy), but test **Llama-3 Transliteration** in parallel. If Llama-3 is "good enough," we **delete IndicXlit** and achieve your dream of a single unified runtime.

### Technical FAQ: Why can't `indicxlit` run in `llama.cpp`?
The user asked if there is a fundamental reason (like dataset) preventing this.
*   **The Mismatch is Math, not Data**:
    *   **Llama.cpp (Decoder-Only)**: Designed like "Autocomplete". It sees `A B C` and predicts `D`. It only has a "Decoder" half.
    *   **IndicXlit (Encoder-Decoder)**: Designed like a "Translator". It has a dedicated "Encoder" (reads input) and "Decoder" (writes output).
    *   **The Gap**: `llama.cpp` literally lacks the C++ code ("kernels") to run the *Encoder* part of the neural network efficiently, although support for architectures like T5 is slowly being added.
*   **Can we fork it?**: Yes, but you'd have to write C++ GPU kernels for Fairseq-style attention layers.
*   **Is it worth it?**: No. `llama.cpp` saves you RAM on *huge* (8GB+) models. `IndicXlit` is 0.04GB (40MB). It runs instantly on any CPU. Optimizing it is optimizing <1% of your app.

### Technical FAQ: Where are the Encoder-Decoder Edge Engines?
The user asked why "Fairseq Edge" doesn't exist.
*   **They DO exist!**: They just aren't called "Fairseq Engine".
    *   **CTranslate2**: This is the industry standard "Edge Engine" for NMT (Translation) models. It is highly optimized for Encoder-Decoder models (like Fairseq/Marian).
    *   **ONNX Runtime**: The general-purpose engine. You export Fairseq -> ONNX -> Edge.
*   **Why strict `llama.cpp` focus?**: The user wants *one* single binary. Adding `CTranslate2` adds another dependency.
*   **The "Meta" Answer**: Meta moved to **PyTorch Mobile** (now **ExecuTorch**) as their "Universal Edge Engine". They don't build separate engines for separate model architectures anymore; they build one runtime that executes computation graphs.

### Technical FAQ: Can `CTranslate2` run EVERYTHING?
The user asked if `CTranslate2` can replace `llama.cpp` entirely (Unified Runtime).
*   **The Problem**: `CTranslate2` is amazing for Linux/NVIDIA, but it **lacks Apple Metal (MPS) support**.
*   **The Consequence**: If you use `CTranslate2` on a Mac, your 8GB Llama-3 model runs on the **CPU**. It will be incredibly slow compared to `llama.cpp` which uses the Mac's GPU.
*   **Conclusion**: `llama.cpp` is the *only* engine that unifies Mac (Metal), Android (Vulkan/NPU), and Linux (CUDA). `CTranslate2` cannot do this yet.

### What about Apple Devices (iOS/macOS)?
The user asked about options for Apple devices.
*   **The "Native" Option: Apple Intelligence**:
    *   **Pros**: Built-in privacy, highly optimized for Apple Silicon (Neural Engine).
    *   **Cons**: Restricted to iPhone 15 Pro+ / M1+ Macs. API access (Writing Tools/Genmoji) is high-level, hard to fine-tune for "Debate Persona".
*   **The "Researcher" Option: MLX**:
    *   **Verdict**: Fantastic for macOS research (like PyTorch for Mac).
    *   **Cons**: Less mature for deployment on iOS compared to CoreML/llama.cpp.
*   **The "Production" Option: llama.cpp (Metal)**:
    *   **Verdict**: **Best for our Cross-Platform App.**
    *   **Why**: It supports **Metal** acceleration out of the box. You write code once (Python/C++) and it runs fast on Mac, Linux, and Android.
    *   **Recommendation**: Use `llama.cpp` with Metal build flag (`LLAMA_METAL=1`) for Mac users.

### Technical FAQ: Hardware Support Grid
The user asked about Metal (Mac), ROCm (AMD), and TPU (Google) specifically.

| Feature | `llama.cpp` | `CTranslate2` | Verdict |
| :--- | :--- | :--- | :--- |
| **Metal (Mac)** | ✅ **Native Support** (Fast) | ❌ No Support (CPU Only) | **llama.cpp** wins by a landslide. |
| **ROCm (AMD)** | ✅ **Native Support** (HIP) | ✅ Supported | Tie (Both work well). |
| **TPU (Edge)** | ⚠️ Experimental/Hard | ❌ No Support | **llama.cpp** (has partial support via forks). |
| **CUDA (NVIDIA)**| ✅ Native Support | ✅ Native Support | Tie. |

**Final Hardware Verdict**:
Since you care about **Metal** and **ROCm**, `llama.cpp` is your *only* safe choice. `CTranslate2` would cripple your Mac performance.

### Technical FAQ: What about `Ollama` and `vLLM`?
The user asked where these fit in.
*   **Ollama**: It is a legitimate option! It is effectively a user-friendly wrapper around `llama.cpp`.
    *   **Pros**: Easiest setup. Great CLI.
    *   **Cons**: It adds a "Server" layer (Go) on top of the C++ engine. For a tightly integrated app, calling `llama.cpp` directly (via Python) is slightly more efficient and gives you more control.
*   **vLLM**: It is a **Server Engine** (like Nginx for LLMs).
    *   **Use Case**: When you have 1000 users hitting your model at once (PagedAttention).
    *   **Device Fit**: It is primarily built for NVIDIA GPUs in Cloud Centers. It is **terrible** for local Mac/Android use compared to `llama.cpp`.

## 7. Further Reading (Resources)
*   **Official Repo**: [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp)
*   **Quantization Explained**: [Understanding GGUF & Quantization](https://medium.com/@mlbloging/local-llm-inference-with-llama-cpp-68693c04870e)
*   **Python Bindings**: [llama-cpp-python Documentation](https://llama-cpp-python.readthedocs.io/)
*   **Community**: [/r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/) (The best place for latest benchmarks).

## 8. Web App Design & UX Strategy ("The Face")
*Goal: A "High Contrast" Interface. No distractions, no bias, just the data.*

### A. Core Philosophy: "The Laboratory"
1.  **Typography**: High-readability Serif (Merriweather) for text, **Hurmit Nerd Font** for metadata and stats (The User's Choice).
2.  **Branding**: Polyglot header `धी / ధీ / ಧೀ / ധീ / Dhī`. The Roman script explicitly uses the macron (`ī`) for strict phonetic accuracy (ISO-15919).
3.  **No Clutter**: No ornaments. No glows. Just sharp lines and high contrast.
4.  **Color Palette**: "Obsidian & Steel".
    *   **Primary**: Pure Black (`#050505`).
    *   **Text**: Sharp White (`#E5E5E5`).
    *   **Metadata**: Neutral Grey (`#737373`).

### B. The "Search -> Insight" Flow
1.  **The Landing**: A command-line inspired search input. "Query the Archive...".
    *   *Micro-interaction*: Immediate response. No fade-ins. Instant snap.
2.  **The Result Card**:
    *   **Left Border**: A sharp white line (The Truth).
    *   **Content**: Raw text prioritized.
    *   **Footer**: Technical metadata (Vector distance, Source ID) exposed like a HUD.
3.  **The Lens Toggle (UX)**:
    *   Simple, functional radio buttons. "Historian | Literal | Debater".

### C. Accessibility & Technology
1.  **Mobile First**: Design for thumb-scrolling. Most users will be on phones.
2.  **PWA (Progressive Web App)**: The site handles offline caching.
3.  **React Stack**:
    *   **Framework**: Next.js 14 (App Router).
    *   **Styling**: Tailwind CSS (for rapid bespoke design).
    *   **State**: React Context (simple global state for "Lens").
    *   **Motion**: Framer Motion (for "smooth" slow-fade animations).
