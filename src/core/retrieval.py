import json
import numpy as np
import os
from pathlib import Path

# --- Configuration ---
# Resolve absolute path to knowledge base
BASE_DIR = Path(__file__).resolve().parent.parent.parent
KB_PATH = str(BASE_DIR / "out" / "knowledge_base.json")

def load_knowledge_base():
    if not os.path.exists(KB_PATH):
        print(f"⚠️ Knowledge Base not found at {KB_PATH}")
        return []
    with open(KB_PATH, "r") as f:
        return json.load(f)

def cosine_similarity(v1, v2):
    a = np.array(v1)
    b = np.array(v2)
    if a.ndim > 1: a = a.flatten()
    if b.ndim > 1: b = b.flatten()
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return np.dot(a, b) / (norm_a * norm_b)

def retrieve(query_vector, kb, top_k=3):
    """
    Retrieve top_k chunks from the KB similar to the query_vector.
    """
    if not kb:
        return []

    scores = []
    for item in kb:
        vec = item['vector']
        score = cosine_similarity(query_vector, vec)
        scores.append((score, item))
    
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[:top_k]
