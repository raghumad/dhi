import numpy as np
from src.core.storage import StorageEngine

import os
from dotenv import load_dotenv

load_dotenv()

# Global Storage (Lazy loaded)
_storage = None

def get_storage():
    global _storage
    if _storage is None:
        dataset_name = os.getenv("DATASET_NAME", "rigveda")
        _storage = StorageEngine(dataset_name=dataset_name)
    return _storage

def retrieve(query_vector, kb=None, top_k=5):
    """
    Retrieve top_k chunks using HNSW Storage Engine.
    'kb' arg is deprecated/unused but kept for signature compatibility if needed.
    """
    if kb:
        print("Warning: 'kb' argument in retrieve() is deprecated. Using StorageEngine.")
    
    storage = get_storage()
    if not storage:
        return []
        
    return storage.search(query_vector, top_k=top_k)

