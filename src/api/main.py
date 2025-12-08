from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from llama_cpp import Llama
import os

from pathlib import Path

# --- Configuration ---
# Resolve absolute path to models/model.gguf
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = str(BASE_DIR / "models" / "model.gguf")
N_CTX = 8192
N_THREADS = 4

# --- Global State ---
llm_model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the Llama model into RAM on startup.
    This prevents the 5-10 second cold boot on every request.
    """
    global llm_model
    if os.path.exists(MODEL_PATH):
        print(f"🔥 Loading Agni (Llama) from {MODEL_PATH}...")
        try:
            llm_model = Llama(
                model_path=MODEL_PATH,
                n_ctx=N_CTX,
                n_threads=N_THREADS,
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
    context: str
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
    
    # Simple Prompt Engineering
    prompt = f"""
    Context: {req.context}
    
    User Query: {req.query}
    
    Insight (Be a faithful yet bold interpreter):
    """
    
    output = llm_model(
        prompt,
        max_tokens=256,
        stop=["Context:", "User Query:"],
        echo=False
    )
    
    return {
        "output": output["choices"][0]["text"].strip(),
        "token_usage": output["usage"]
    }
