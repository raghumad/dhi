from llama_cpp import Llama
import numpy as np
import os
from src.core.retrieval import retrieve

# Simulate Main.py logic
MODEL_PATH = os.getenv("MODEL_PATH", "models/llama-3.2-3b-instruct-q4km.gguf")
query = "Who is Agni?"

print("1. Loading Model...")
llm = Llama(model_path=MODEL_PATH, embedding=True, verbose=True)

print(f"2. Embedding Query: '{query}'")
embed = llm.create_embedding(query)
token_matrix = np.array(embed['data'][0]['embedding'])
if token_matrix.ndim > 1:
    q_vec = np.mean(token_matrix, axis=0)
else:
    q_vec = token_matrix

print(f"   Shape: {q_vec.shape}")

print("3. Retrieving...")
results = retrieve(q_vec, top_k=3)
print(f"   Found {len(results)} results")
context_str = "\n".join([f"- {r['text'][:50]}..." for r in results])
print(f"   Context: {context_str}")

print("4. Generating Answer...")
prompt = f"Context: {context_str}\n\nQ: {query}\n\nA:"
output = llm(prompt, max_tokens=100)
print(f"   Answer: {output['choices'][0]['text']}")
print("✅ Done.")
