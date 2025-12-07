import argparse
import sys
from llama_cpp import Llama

def search_loop(model_path):
    print(f"Loading Llama model from {model_path}...")
    try:
        llm = Llama(model_path=model_path, verbose=False)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    print("\n--- Dhi Search (Prototype) ---")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nQuery > ")
        if query.lower().strip() == "exit":
            break
            
        # Placeholder for Hybrid Logic
        # 1. Transliterate Query (Indic -> Roman)
        # 2. Embed Query
        # 3. Retrieve Context
        # 4. Generate Answer
        
        print(f"Processing: {query}")
        
        # Simple generation for now (Proof of Llama integration)
        output = llm(
            f"Q: {query} A: ", 
            max_tokens=64, 
            stop=["Q:", "\n"], 
            echo=True
        )
        print("Answer:", output['choices'][0]['text'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dhi Search CLI")
    parser.add_argument("--model", type=str, required=True, help="Path to .gguf model file")
    
    args = parser.parse_args()
    search_loop(args.model)
