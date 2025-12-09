import sys
import os
import random
from pathlib import Path

def validate_text(text_path):
    """
    Validates that the text file contains coherent text, not transliteration artifacts.
    """
    if not os.path.exists(text_path):
        print(f"❌ File not found: {text_path}")
        return False

    with open(text_path, 'r', encoding='utf-8') as f:
        # Read a sample (first 10KB)
        content = f.read(10000)

    if not content.strip():
        print(f"❌ File is empty: {text_path}")
        return False

    # 1. Check for "Gibberish" artifacts (Schwa insertion explosion)
    # Words ending in 'a' indiscriminately is a sign of bad transliteration
    # e.g. "manuala", "ritualasa", "taranasalationa"
    
    words = content.split()
    if not words:
        return False
        
    ends_with_a = sum(1 for w in words if w.lower().endswith('a'))
    blocks_of_gibberish = sum(1 for w in words if "taranasalation" in w.lower() or "olivelale" in w.lower())
    
    ratio = ends_with_a / len(words)
    
    print(f"📄 Validation Report for {os.path.basename(text_path)}")
    print(f"   - Word Count (Sample): {len(words)}")
    print(f"   - Ends-with-'a' Ratio: {ratio:.2f}")
    
    # Normal English is ~5-10%. Sanskrit is higher. 
    # But "taranasalationa" (English words + 'a') is a dead giveaway.
    
    if blocks_of_gibberish > 0:
        print("❌ FAILED: Detected known transliteration artifacts (e.g. 'taranasalationa')")
        return False
        
    if ratio > 0.5:
        # If > 50% of words end in 'a', and it's supposedly English context... likely bad.
        # But if it's pure Sanskrit, this might be valid.
        # We need to context switch based on expectation.
        print("⚠️  WARNING: High frequency of words ending in 'a'. Potentially over-transliterated.")
        # Only failing on explicit garbage keywords for now.
        
    print("✅ Text looks coherent.")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_ingest.py <path_to_txt>")
        sys.exit(1)
        
    path = sys.argv[1]
    if validate_text(path):
        sys.exit(0)
    else:
        sys.exit(1)
