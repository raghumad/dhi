import time
import os
from llama_cpp import Llama
import numpy as np

MODEL_PATH = "models/llama-3.2-3b-instruct-q4km.gguf"

if not os.path.exists(MODEL_PATH):
    print("Model not found")
    exit(1)

prompt = "Write a short poem about the sun."

def benchmark(n_threads):
    print(f"--- Benchmarking N_THREADS={n_threads} ---")
    start_load = time.time()
    llm = Llama(
        model_path=MODEL_PATH,
        n_threads=n_threads,
        n_ctx=2048,
        verbose=False
    )
    load_time = time.time() - start_load
    
    start_gen = time.time()
    output = llm(prompt, max_tokens=50)
    gen_time = time.time() - start_gen
    
    tokens = output['usage']['completion_tokens']
    tps = tokens / gen_time
    
    print(f"TPS: {tps:.2f} | Gen Time: {gen_time:.2f}s | Load Time: {load_time:.2f}s")
    return tps

best_tps = 0
best_n = 0

for n in [1, 2, 4, 8, 16, 32, 60]:
    tps = benchmark(n)
    if tps > best_tps:
        best_tps = tps
        best_n = n

print(f"\n🏆 Best Configuration: N_THREADS={best_n} (TPS: {best_tps:.2f})")
