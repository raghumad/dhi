import argparse
import sys
import numpy as np
import os
from llama_cpp import Llama
from src.core.retrieval import retrieve
from dotenv import load_dotenv

load_dotenv()

def search_loop(model_path, verify_query=None):
    # Load Model
    print(f"Loading Llama model from {model_path}...")
    try:
        n_threads = int(os.getenv("N_THREADS", "4"))
        n_ctx = int(os.getenv("N_CTX", "8192"))
        llm = Llama(model_path=model_path, embedding=True, n_threads=n_threads, n_ctx=n_ctx, verbose=False)
        print(f"Model loaded successfully.")
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # -- Interactive Mode --
    print("\n--- Dhi Search (HNSW Index from 'out/rigveda') ---")
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
        out = llm.create_embedding(query)
        emb = out['data'][0]['embedding']
        vec = np.array(emb)
        if vec.ndim > 1: vec = np.mean(vec, axis=0) # Mean pool
        
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
    parser.add_argument("--model", type=str, default="models/llama-3.2-3b-instruct-q4km.gguf", help="Path to .gguf model file")
    parser.add_argument("--query", type=str, help="Run single query and exit")
    
    args = parser.parse_args()
    search_loop(args.model, args.query)
