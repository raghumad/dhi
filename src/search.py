import argparse
import sys
import json
import numpy as np
import os
from llama_cpp import Llama

def cosine_similarity(v1, v2):
    a = np.array(v1)
    b = np.array(v2)
    if a.ndim > 1: a = a.flatten()
    if b.ndim > 1: b = b.flatten()
    # Debugging if needed
    # if a.shape != b.shape: print(f"Shape mismatch: {a.shape} vs {b.shape}")
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def load_knowledge_base():
    kb_path = "out/knowledge_base.json"
    if not os.path.exists(kb_path):
        return []
    with open(kb_path, "r") as f:
        return json.load(f)

def retrieve(query_vector, kb, top_k=3):
    scores = []
    for item in kb:
        vec = item['vector']
        score = cosine_similarity(query_vector, vec)
        scores.append((score, item))
    
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[:top_k]

def search_loop(model_path, verify_query=None):
    # Load KB
    kb = load_knowledge_base()
    print(f"Loaded Knowledge Base: {len(kb)} chunks.")

    print(f"Loading Llama model from {model_path}...")
    try:
        # Resource Control: Benchmark showed 4 threads is optimal.
        n_threads = 4
        # Context Window
        n_ctx = 8192
        # Load with embedding=True
        llm = Llama(model_path=model_path, embedding=True, n_threads=n_threads, n_ctx=n_ctx, verbose=False)
        print(f"Model loaded successfully ({n_threads} threads, {n_ctx} ctx).")
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # -- Verify Retrieval Mode --
    if verify_query:
        print(f"Verifying retrieval for: '{verify_query}'")
        # Mean pool query
        out = llm.create_embedding(verify_query)
        token_matrix = np.array(out['data'][0]['embedding'])
        if token_matrix.ndim > 1:
            q_vec = np.mean(token_matrix, axis=0)
        else:
            q_vec = token_matrix
        
        results = retrieve(q_vec, kb, top_k=1)
        if results:
            score, item = results[0]
            print(f"Top Result: {item['text']}")
            print(f"Score: {score:.4f}")
        else:
            print("No results found.")
        return

    # -- Interactive Mode --
    print("\n--- Dhi Search (RAG Enabled) ---")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nQuery > ")
        if query.lower().strip() == "exit":
            break
            
        print(f"Processing: {query}", flush=True)
        
        # 1. Embed Query (Mean pool)
        out = llm.create_embedding(query)
        token_matrix = np.array(out['data'][0]['embedding'])
        if token_matrix.ndim > 1:
            q_vec = np.mean(token_matrix, axis=0)
        else:
            q_vec = token_matrix
        
        # 2. Retrieve
        results = retrieve(q_vec, kb, top_k=2)
        
        context_str = ""
        if results:
            print(f"[RAG] Found context (Score: {results[0][0]:.2f})")
            context_str = "\n".join([f"- {r[1]['text']}" for r in results])
        
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
        # Parse out just the answer if needed, but echo=True shows context
        print("Answer:", output['choices'][0]['text'].split("Answer:")[-1].strip())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dhi Search CLI")
    parser.add_argument("--model", type=str, required=True, help="Path to .gguf model file")
    parser.add_argument("--verify-retrieval", type=str, help="Run retrieval verification for a specific query and exit")
    
    args = parser.parse_args()
    search_loop(args.model, args.verify_retrieval)
