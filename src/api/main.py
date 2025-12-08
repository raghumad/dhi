from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_cpp import Llama
import os
import numpy as np
from pathlib import Path
from src.core.retrieval import load_knowledge_base, retrieve

# --- Configuration ---
# Resolve absolute path to models/model.gguf
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = str(BASE_DIR / "models" / "model.gguf")
N_CTX = 8192
N_THREADS = 4

# --- Global State ---
llm_model = None
knowledge_base = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the Llama model into RAM on startup.
    This prevents the 5-10 second cold boot on every request.
    """
    global llm_model, knowledge_base
    
    # Load Knowledge Base
    print("📚 Loading Knowledge Base...")
    knowledge_base = load_knowledge_base()
    print(f"✅ KB Loaded: {len(knowledge_base)} chunks.")

    if os.path.exists(MODEL_PATH):
        print(f"🔥 Loading Agni (Llama) from {MODEL_PATH}...")
        try:
            llm_model = Llama(
                model_path=MODEL_PATH,
                n_ctx=N_CTX,
                n_threads=N_THREADS,
                embedding=True, # Enable embedding for retrieval
                verbose=False
            )
            print("✅ Model Loaded. Ready to Interpret.")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
    else:
        print(f"⚠️ Warning: Model not found at {MODEL_PATH}. Inference will fail.")
    
    yield
    
    # Cleanup (Optional)
    if llm_model:
        del llm_model
        print("❄️ Model Unloaded.")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Dhi API", lifespan=lifespan)

# Allow localhost:3000 (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
    return {"status": "ready", "model_loaded": llm_model is not None}

@app.post("/insight", response_model=InsightResponse)
def generate_insight(req: InsightRequest):
    """
    Generate an insight (interpretation) based on context.
    This is the "Interpreter" layer.
    """
    if not llm_model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # 1. Embed Query
        query_embed = llm_model.create_embedding(req.query)
        token_matrix = np.array(query_embed['data'][0]['embedding'])
        
        # Mean Pooling: (NumTokens, Dim) -> (Dim)
        if token_matrix.ndim > 1:
            q_vec = np.mean(token_matrix, axis=0)
        else:
            q_vec = token_matrix
        
        # 2. Retrieve Context (Real RAG)
        results = retrieve(q_vec, knowledge_base, top_k=3)
        
        context_str = ""
        if results:
            context_str = "\n".join([f"- {r[1]['text']}" for r in results])
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
