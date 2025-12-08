import os
import sys
import fitz  # PyMuPDF
from aksharamukha import transliterate
import numpy as np

def ingest_pdf(pdf_path, limit=None):
    """
    Reads a PDF and extracts text, normalizing it to a canonical script.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
        return

    print(f"Ingesting {pdf_path}...")
    
    # Open PDF
    doc = fitz.open(pdf_path)
    full_text = ""
    
    for page_num, page in enumerate(doc):
        text = page.get_text()
        full_text += text
    print(f"Extraction complete. Total characters: {len(full_text)}")
    
    # Normalize to IAST (International Alphabet of Sanskrit Transliteration)
    print("Normalizing to IAST...")
    normalized_text = transliterate.process('Devanagari', 'ISO', full_text)
    
    # --- RAG: Chunking & Embedding ---
    # --- RAG: Chunking & Embedding ---
    print("Chunking text...")
    import re
    # Robust splitting: Newline, optional whitespace, Newline
    chunks = [c.strip() for c in re.split(r'\n\s*\n', normalized_text) if len(c.strip()) > 20]
    
    if limit:
        print(f"Limiting to first {limit} chunks for testing.")
        chunks = chunks[:limit]
    
    print(f"Generated {len(chunks)} chunks. Loading model for embedding...")
    
    from llama_cpp import Llama
    import json
    
    # Load model with embedding=True
    model_path = "models/model.gguf" 
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")
    
    # Resource Control: Benchmark showed 4 threads is optimal (1.01s latency).
    # Higher threads (16/32/64) degraded performance significantly.
    n_threads = 4
    
    # Context Window: Set to 8192 (Default 512 is too small for chunks)
    n_ctx = 8192
    
    print(f"Loading model with {n_threads} threads and n_ctx={n_ctx}...")
    llm = Llama(model_path=model_path, embedding=True, n_threads=n_threads, n_ctx=n_ctx, verbose=False)
    
    knowledge_base = []
    print("Generating embeddings...")
    for i, chunk in enumerate(chunks):
        print(f"  Embedding chunk {i+1}/{len(chunks)}...", end="\r", flush=True)
        # Generate embedding (Mean Pooling)
        output = llm.create_embedding(chunk)
        # Check if output is (N, Dim)
        emb_data = output['data'][0]['embedding']
        token_matrix = np.array(emb_data)
        
        # If (N, Dim), mean pool across tokens
        if token_matrix.ndim > 1:
            mean_vec = np.mean(token_matrix, axis=0).tolist()
        else:
            mean_vec = token_matrix.tolist()
        
        knowledge_base.append({
            "id": f"chunk_{i}",
            "text": chunk,
            "vector": mean_vec,
            "source": pdf_path
        })
        if i % 10 == 0: print(f".", end="", flush=True)
            
    # Save Knowledge Base
    kb_path = "out/knowledge_base.json"
    with open(kb_path, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f)
        
    print(f"\nSaved {len(knowledge_base)} vectorized chunks to {kb_path}")
    
    # Also save the raw text for reference
    # Save to out/ directory
    os.makedirs("out", exist_ok=True)
    output_path = "out/rigveda_normalized.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(normalized_text)
    
    print(f"Successfully wrote {len(normalized_text)} chars to {output_path}")
    return normalized_text

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--limit", type=int, help="Limit number of chunks to process")
    args = parser.parse_args()
    
    ingest_pdf(args.pdf_path, args.limit)
