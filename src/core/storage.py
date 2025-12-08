import hnswlib
import struct
import mmap
import os
from pathlib import Path

class StorageEngine:
    def __init__(self, dataset_name="Rigveda", base_dir="out"):
        self.base_dir = Path(base_dir)
        self.name = dataset_name
        
        self.txt_path = self.base_dir / f"{dataset_name}.txt"
        self.hnsw_path = self.base_dir / f"{dataset_name}.hnsw"
        self.bin_path = self.base_dir / f"{dataset_name}.bin"
        
        # Artifacts
        self.index = None
        self.metadata_map = None
        self.text_map = None
        self.count = 0
        
        self._load()

    def _load(self):
        if not (self.hnsw_path.exists() and self.bin_path.exists() and self.txt_path.exists()):
            print(f"⚠️ Storage artifacts for '{self.name}' not found in {self.base_dir}")
            return

        print(f"Loading Storage: {self.name}...")
        
        # 1. Map Metadata (Binary)
        # Header: MAGIC(4s) VERSION(I) COUNT(I) DIM(I)
        with open(self.bin_path, "rb") as f:
            self.metadata_map = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            # Optimize for random access (disable readahead)
            self.metadata_map.madvise(mmap.MADV_RANDOM)
        
        # Parse Header
        magic = self.metadata_map[:4]
        if magic != b"DHIM":
            raise ValueError("Invalid Magic in .bin file")
            
        self.count = struct.unpack("I", self.metadata_map[8:12])[0]
        try:
             # Try reading DIM
            self.dim = struct.unpack("I", self.metadata_map[12:16])[0]
            self.header_size = 16
        except Exception:
            # Fallback for old format if needed, but we just updated ingest.
            print("Warning: Could not read DIM from header. Defaulting to 3072.")
            self.dim = 3072
            self.header_size = 12

        self.row_size = 8 + 4 # 12 bytes

        # 2. Load HNSW Index
        try:
            self.index = hnswlib.Index(space='cosine', dim=self.dim)
            self.index.load_index(str(self.hnsw_path))
        except Exception as e:
            print(f"Failed to load index: {e}")
            return
        self.row_size = 8 + 4 # 12 bytes

        # 3. Map Text
        with open(self.txt_path, "r", encoding="utf-8") as f: # Open as text, but map bytes
             # mmap needs fileno. 
             # Python mmap on text file works if accessed as bytes.
             with open(self.txt_path, "rb") as f_bin:
                 self.text_map = mmap.mmap(f_bin.fileno(), 0, access=mmap.ACCESS_READ)
                 # Optimize for random access
                 self.text_map.madvise(mmap.MADV_RANDOM)

        print(f"✅ Storage Loaded. Count: {self.count}")

    def search(self, query_vector, top_k=5):
        if not self.index:
            return []
            
        # HNSW Query
        labels, distances = self.index.knn_query(query_vector, k=top_k)
        
        # --- Active Prefetching (MADV_WILLNEED) ---
        # We have the IDs (labels). Let's signal the kernel to page in the text data.
        # This allows parallel O/S paging while we process the first result.
        
        chunk_ids = labels[0]
        target_regions = []
        
        # 1. Resolve offsets first (Metadata Lookup is fast/cached mostly)
        # 1. Resolve offsets first (Metadata Lookup is fast/cached mostly)
        # We zip labels and distances to keep them paired even if we filter some out.
        for i, chunk_id in enumerate(chunk_ids):
            chunk_id = int(chunk_id)
            if chunk_id >= self.count: continue
            
            dist = distances[0][i]
            
            meta_pos = self.header_size + (chunk_id * self.row_size)
            row_bytes = self.metadata_map[meta_pos : meta_pos + self.row_size]
            offset, length = struct.unpack("Q I", row_bytes)
            # Store distance with the region info
            target_regions.append((chunk_id, offset, length, dist))
            
            # Prefetch Text (Offset is now page-aligned by ingestion)
            try:
                self.text_map.madvise(mmap.MADV_WILLNEED, offset, length)
            except Exception:
                pass
            
        # 2. Read Data
        results = []
        for chunk_id, offset, length, dist in target_regions:
            # Data should be paging in now...
            txt_bytes = self.text_map[offset : offset + length]
            text = txt_bytes.decode("utf-8")
            
            results.append({
                "id": chunk_id,
                "score": 1.0 - dist,
                "text": text
            })
            
        return results

    def get_text(self, chunk_id):
        # Kept for single lookup compatibility
        if chunk_id >= self.count:
            return ""
            
        meta_pos = self.header_size + (chunk_id * self.row_size)
        row_bytes = self.metadata_map[meta_pos : meta_pos + self.row_size]
        offset, length = struct.unpack("Q I", row_bytes)
        
        # Prefetch (Offset is page-aligned)
        try:
             self.text_map.madvise(mmap.MADV_WILLNEED, offset, length)
        except Exception:
             pass

        txt_bytes = self.text_map[offset : offset + length]
        return txt_bytes.decode("utf-8")

    def __del__(self):
        if self.metadata_map: self.metadata_map.close()
        if self.text_map: self.text_map.close()
