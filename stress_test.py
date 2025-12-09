import os
from llama_cpp import Llama
from src.core.storage import StorageEngine
import struct

# Mock Env
os.environ["N_CTX"] = "8192"
os.environ["N_THREADS"] = "4"

MODEL_PATH = "models/llama-3.2-3b-instruct-q4km.gguf"

def stress_test():
    print("1. Loading Model...")
    llm = Llama(model_path=MODEL_PATH, embedding=True, n_ctx=8192, verbose=False)
    
    print("2. Loading Storage...")
    storage = StorageEngine(dataset_name="rigveda")
    
    query = "who is marut"
    print(f"3. Embedding: '{query}'")
    embed_resp = llm.create_embedding(query)
    q_vec = embed_resp['data'][0]['embedding']
    
    print("4. Retrieving...")
    results = storage.search(q_vec, top_k=3)
    print(f"   Found {len(results)} chunks.")
    
    context_text = "\n\n".join([r['text'] for r in results])
    
    print("5. Generating...")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {query}"}
    ]
    
    resp = llm.create_chat_completion(messages=messages, max_tokens=128)
    print("6. Result:", resp['choices'][0]['message']['content'])
    print("✅ Success!")

if __name__ == "__main__":
    stress_test()
