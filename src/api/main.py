from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_cpp import Llama
import os
import numpy as np
from pathlib import Path
from src.core.retrieval import retrieve

# --- Configuration ---
# Resolve absolute path to models/model.gguf
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Allow override from env, but default to relative path resolved
DEFAULT_MODEL = str(BASE_DIR / "models" / "llama-3.2-3b-instruct-q4km.gguf")
MODEL_PATH = os.getenv("MODEL_PATH", DEFAULT_MODEL)
N_CTX = int(os.getenv("N_CTX", "8192"))
N_THREADS = int(os.getenv("N_THREADS", "4"))

# --- Global State ---
llm_model = None
embed_model = None # For Netra (AutoModel)
tokenizer = None   # For Netra (AutoTokenizer)
embed_fn = None    # Helper function

provider = os.getenv("EMBEDDING_PROVIDER", "llama").lower()
print(f"Embedding Provider: {provider.upper()}")
print("📚 Storage Engine: HNSW + Mmap (Lazy Loading)")

if provider == "netra" or provider == "sentence-transformers":
    try:
        from transformers import AutoModel, AutoTokenizer
        import torch
        print(f"🔥 Loading NetraEmbed (Transformers)...")
        model_name = "Cognitive-Lab/NetraEmbed"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        embed_model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        
        def netra_embed(text):
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=8192)
            with torch.no_grad():
                outputs = embed_model(**inputs)
                return outputs.last_hidden_state.mean(dim=1)[0].numpy()
                
        embed_fn = netra_embed
        
    except Exception as e:
        print(f"❌ Failed to load NetraEmbed: {e}")

    # 2. Load Llama for Generation ONLY
    if os.path.exists(MODEL_PATH):
        print(f"🔥 Loading Llama (Generation Only)...")
        try:
            llm_model = Llama(
                model_path=MODEL_PATH,
                n_ctx=N_CTX,
                n_threads=N_THREADS,
                embedding=False, 
                verbose=os.getenv("VERBOSE", "False").lower() == "true"
            )
            print("✅ Models Loaded (Hybrid Mode).")
        except Exception as e:
            print(f"❌ Failed to load Llama: {e}")

else:
    # Legacy Llama Mode
    if os.path.exists(MODEL_PATH):
        print(f"🔥 Loading Llama (Hybrid Embed+Gen)...")
        try:
            llm_model = Llama(
                model_path=MODEL_PATH,
                n_ctx=N_CTX,
                n_threads=N_THREADS,
                embedding=True, 
                verbose=os.getenv("VERBOSE", "False").lower() == "true"
            )
            embed_model = llm_model 
            
            def llama_embed(text):
                out = llm_model.create_embedding(text)
                mat = np.array(out['data'][0]['embedding'])
                if hasattr(llm_model, 'reset'): llm_model.reset()
                return np.mean(mat, axis=0) if mat.ndim > 1 else mat
                
            embed_fn = llama_embed
            print("✅ Model Loaded (Single Mode).")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")

from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Dhi API")

# Allow origins from env
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas ---
class InsightRequest(BaseModel):
    query: str

class InsightResponse(BaseModel):
    output: str
    token_usage: dict

# --- Endpoints ---

@app.get("/health")
def health():
    return {
        "status": "ready", 
        "provider": provider,
        "gen_loaded": llm_model is not None,
        "embed_loaded": embed_model is not None
    }

@app.get("/debug_gen")
async def debug_gen():
    """Test generation only"""
    if not llm_model: return {"error": "no model"}
    try:
        output = llm_model("Hello, my name is", max_tokens=10)
        return {"output": output}
    except Exception as e:
        return {"error": str(e)}

@app.post("/insight", response_model=InsightResponse)
async def generate_insight(req: InsightRequest):
    """
    Generate an insight (interpretation) based on context.
    This is the "Interpreter" layer.
    """
    if not llm_model:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        # 1. Embed Query
        q_vec = None
        if embed_fn:
            q_vec = embed_fn(req.query)
        else:
            raise HTTPException(status_code=500, detail="Embedding function not initialized")
        
        # 2. Retrieve Context (Real RAG)
        results = retrieve(q_vec, top_k=3)
        
        context_str = ""
        if results:
            context_str = "\n".join([f"- {r['text']}" for r in results])
        else:
            context_str = "No specific verses found. Answer from general knowledge."

        # 3. Construct Prompt
        prompt = f"""Context from Rigveda:
{context_str}

User Query: {req.query}

Insight (Be a faithful yet bold interpreter):
"""
        
        # 4. Generate
        output = llm_model(
            prompt,
            max_tokens=256,
            stop=["User Query:", "Context:"],
            echo=False
        )
        
        return {
            "output": output["choices"][0]["text"].strip(),
            "token_usage": output["usage"]
        }
    except Exception as e:
        import traceback
        error_msg = f"Server Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
