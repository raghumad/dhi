from llama_cpp import Llama
import numpy as np
import os

model_path = "models/llama-3.2-3b-instruct-q4km.gguf"
try:
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        exit(1)
        
    llm = Llama(model_path=model_path, embedding=True, verbose=False)
    # Important: llama-cpp-python < 0.2.23 might behave differently. 
    # Current version usually returns one vector.
    embed = llm.create_embedding("Test")
    vec = np.array(embed['data'][0]['embedding'])
    print(f"Model Embedding Dim: {vec.shape}")
except Exception as e:
    print(f"Error: {e}")
