import os
import sys
import fitz  # PyMuPDF
from aksharamukha import transliterate
import numpy as np
import hnswlib
import struct
from pathlib import Path

def ingest_pdf(pdf_path, limit=None, force=False):
    """
    Reads a PDF, extracts text, normalizes it, and builds:
    1. Text Blob (.txt)
    2. HNSW Index (.hnsw)
    3. Metadata Map (.bin)
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
        return

    # Derive Base Name (e.g., "Rigveda")
    base_name = Path(pdf_path).stem
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    
    txt_path = out_dir / f"{base_name}.txt"
    hnsw_path = out_dir / f"{base_name}.hnsw"
    bin_path = out_dir / f"{base_name}.bin"

    # Idempotency Check
    if not force and txt_path.exists() and hnsw_path.exists() and bin_path.exists():
        print(f"Artifacts exist for {base_name}. Skipping ingestion use --force to overwrite.")
        print(f"Found: {txt_path}, {hnsw_path}, {bin_path}")
        return

    print(f"Ingesting {pdf_path} -> {base_name}.* ...")
    
    # --- 1. Text Extraction & Normalization ---
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    
    print(f"Extraction complete. Total characters: {len(full_text)}")
    print("Normalizing to IAST (Auto-detect script)...")
    try:
        normalized_text = transliterate.process('autodetect', 'ISO', full_text)
    except Exception as e:
        print(f"Warning: Transliteration failed ({e}). Fallback to raw text.")
        normalized_text = full_text

    # --- 2. Chunking & Aligned Storage ---
    print("Chunking & Writing Aligned Text Blob...")
    import re
    import mmap
    PAGESIZE = mmap.PAGESIZE

    # Sliding Window Chunking
    chunk_size = int(os.getenv("CHUNK_SIZE", "1024")) # Characters
    overlap = int(os.getenv("CHUNK_OVERLAP", "100"))
    
    print(f"Chunking Strategy: Window={chunk_size}, Overlap={overlap}")
    
    raw_chunks = []
    text_len = len(normalized_text)
    start = 0
    
    while start < text_len:
        end = start + chunk_size
        
        # Don't split in the middle of a word if possible
        if end < text_len:
            # Look for space to break
            while end > start and normalized_text[end] not in (' ', '\n', '\u0964'): # Space, newline, or danda
                end -= 1
            if end == start: # Force split if no break found
                end = start + chunk_size
                
        chunk = normalized_text[start:end].strip()
        if len(chunk) > 20:
             raw_chunks.append(chunk)
             
        start = end - overlap
        
    print(f"Total Chunks: {len(raw_chunks)} (Size: ~{chunk_size} chars)")
    
    if limit:
        print(f"Limiting to first {limit} chunks.")
        raw_chunks = raw_chunks[:limit]

    test_path = out_dir / f"{base_name}.txt"
    chunk_metadata = [] 
    valid_chunks = []

    with open(test_path, "wb") as f:
        for i, chunk in enumerate(raw_chunks):
            # Encode
            chunk_bytes = chunk.encode('utf-8')
            
            # Calculate Padding for Alignment
            current_pos = f.tell()
            padding_needed = (PAGESIZE - (current_pos % PAGESIZE)) % PAGESIZE
            
            if padding_needed > 0:
                f.write(b'\0' * padding_needed)
            
            # Start of aligned chunk
            start_offset = f.tell()
            assert start_offset % PAGESIZE == 0, "Offset alignment failed"
            
            f.write(chunk_bytes)
            length = len(chunk_bytes)
            
            chunk_metadata.append({
                "id": len(valid_chunks),
                "offset": start_offset,
                "length": length,
                "text": chunk
            })
            valid_chunks.append(chunk)

    print(f"Valid chunks written: {len(valid_chunks)}")

    # --- 3. Embedding & Indexing ---
    from llama_cpp import Llama
    
    model_path = os.getenv("MODEL_PATH", "models/llama-3.2-3b-instruct-q4km.gguf")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")

    # Initialize Model
    from dotenv import load_dotenv
    load_dotenv()
    
    n_threads = int(os.getenv("N_THREADS", "4"))
    n_ctx = int(os.getenv("N_CTX", "8192"))
    verbose = os.getenv("VERBOSE", "False").lower() == "true"
    print(f"Loading model ({n_threads} threads, {n_ctx} ctx, verbose={verbose})...")
    # n_gpu_layers=-1 offloads all layers to GPU if available.
    # n_batch=512 speeds up prompt processing.
    llm = Llama(
        model_path=model_path, 
        embedding=True, 
        n_threads=n_threads, 
        n_ctx=n_ctx, 
        n_gpu_layers=-1,
        n_batch=512,
        verbose=verbose
    )

    # Detect Dimension
    test_emb = llm.create_embedding("test")
    # Handle list of lists (tokens) vs flat list (pooled)
    emb_data = test_emb['data'][0]['embedding']
    token_matrix = np.array(emb_data)
    
    if token_matrix.ndim > 1:
        # (Tokens, Dim)
        dim = token_matrix.shape[1]
    else:
        # (Dim)
        dim = token_matrix.shape[0]
        
    print(f"Detected Vector Dimension: {dim}")

    # Initialize HNSW Index
    # max_elements needs to be known or estimated. We know exact count.
    num_elements = len(valid_chunks)
    p = hnswlib.Index(space='cosine', dim=dim)
    p.init_index(max_elements=num_elements, ef_construction=200, M=16)

    # Embed Loop
    print("Generating embeddings & Indexing...")
    batch_vectors = []
    batch_ids = []
    
    for i, item in enumerate(chunk_metadata):
        print(f"  Processing {i+1}/{num_elements}...", end="\r")
        
        # Embed
        output = llm.create_embedding(item['text'])
        emb_data = output['data'][0]['embedding']
        token_matrix = np.array(emb_data)
        
        if token_matrix.ndim > 1:
            vec = np.mean(token_matrix, axis=0) # Mean Pool
        else:
            vec = token_matrix
            
        # Verify shape
        if len(vec) != dim:
            # Pad or truncate? Or just skip?
            # Creating a zero vector is safer than crashing
            print(f"\nWarning: Vector dim mismatch {len(vec)} vs {dim}. Zeroing.")
            vec = np.zeros(dim)
            
        p.add_items(vec, item['id'])

    print("\nEmbeddings complete.")

    # --- 4. Save Artifacts ---
    
    # Save HNSW
    p.save_index(str(hnsw_path))
    print(f"Saved Index: {hnsw_path}")
    
    # Save Metadata (Binary)
    # Format: 
    #   Header: MAGIC(4s) VERSION(I) COUNT(I)
    #   Rows:   OFFSET(Q) LENGTH(I)  (Q=unsigned long long 8B, I=unsigned int 4B)
    
    print(f"Saving Binary Metadata to {bin_path}...")
    with open(bin_path, "wb") as f:
        # Header
        f.write(b"DHIM") # Magic
        f.write(struct.pack("I", 1)) # Version
        f.write(struct.pack("I", len(chunk_metadata))) # Count
        f.write(struct.pack("I", dim)) # DIMENSION
        
        # Rows
        for item in chunk_metadata:
            # Pack: Offset (8 bytes), Length (4 bytes)
            f.write(struct.pack("Q I", item['offset'], item['length']))
            
    print("✅ Ingestion Complete.")
    print(f"Artifacts: {txt_path}, {hnsw_path}, {bin_path}")

    return normalized_text

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--limit", type=int, help="Limit number of chunks to process")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion even if artifacts exist")
    args = parser.parse_args()
    
    ingest_pdf(args.pdf_path, args.limit, args.force)
