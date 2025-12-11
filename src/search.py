import argparse
import sys
import numpy as np
import os
from llama_cpp import Llama
from src.core.retrieval import retrieve
from dotenv import load_dotenv

load_dotenv()

def search_loop(model_path, verify_query=None):
    # Load Model (Generation)
    print(f"Loading Llama model (Generation) from {model_path}...")
    try:
        n_threads = int(os.getenv("N_THREADS", "4"))
        n_ctx = int(os.getenv("N_CTX", "8192"))
        verbose = os.getenv("VERBOSE", "False").lower() == "true"
        # Load Llama WITHOUT embedding (saves RAM, prevents crash)
        llm = Llama(model_path=model_path, embedding=False, n_threads=n_threads, n_ctx=n_ctx, verbose=verbose)
        print(f"Generation Model loaded.")
    except Exception as e:
        print(f"Failed to load generation model: {e}")
        return

    # Load Embedder
    provider = os.getenv("EMBEDDING_PROVIDER", "llama").lower()
    print(f"Embedding Provider: {provider.upper()}")
    embed_fn = None
    
    if provider == "netra" or provider == "sentence-transformers":
        try:
            from transformers import AutoModel, AutoTokenizer
            import torch
            print("Loading NetraEmbed (Transformers)...")
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
            print(f"Failed to load NetraEmbed: {e}")
            return
    else:
        # Legacy Llama Embedding
        # We need a separate Llama instance with embedding=True? 
        # Or re-use 'llm' if initialized with embedding=True?
        # To avoid crash, let's keep them separate or handle carefully.
        # For CLI, let's use a separate instance to be safe.
        print("Loading Llama (Embedding Mode)...")
        llm_embed = Llama(model_path=model_path, embedding=True, verbose=False)
        
        def llama_embed(text):
            out = llm_embed.create_embedding(text)
            mat = np.array(out['data'][0]['embedding'])
            return np.mean(mat, axis=0) if mat.ndim > 1 else mat
        embed_fn = llama_embed

    # -- Interactive Mode --
    print("\n--- Dhi Search (HNSW Index) ---")
    print("Type 'exit' to quit.")
    
    while True:
        if verify_query:
             query = verify_query
        else:
             query = input("\nQuery > ")
             
        if query.lower().strip() == "exit":
            break
            
        print(f"Processing: {query}", flush=True)
        
        # 1. Embed
        vec = embed_fn(query)
        
        # 2. Retrieve
        results = retrieve(vec, top_k=3)
        
        context_str = ""
        if results:
            print(f"[RAG] Found top result (Score: {results[0]['score']:.4f})")
            context_str = "\n".join([f"- {r['text']}" for r in results])
        else:
            print("[RAG] No results found.")
            context_str = "No specific verses found."
        
        if verify_query:
            # Just print results and exit
            print("\n----- Context Found -----")
            print(context_str)
            break

        # 3. Generate
        prompt = f"""Context from Rigveda:
{context_str}

Question: {query}
Answer: """
        
        output = llm(
            prompt, 
            max_tokens=128, 
            stop=["Question:", "\n"], 
            echo=True
        )
        print("Answer:", output['choices'][0]['text'].split("Answer:")[-1].strip())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dhi Search CLI")
    
    default_model = os.getenv("MODEL_PATH", "models/llama-3.2-3b-instruct-q4km.gguf")
    parser.add_argument("--model", type=str, default=default_model, help="Path to .gguf model file")
    parser.add_argument("--query", type=str, help="Run single query and exit")
    
    args = parser.parse_args()
    search_loop(args.model, args.query)
