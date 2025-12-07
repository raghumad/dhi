import os
import sys
import fitz  # PyMuPDF
from aksharamukha import transliterate

def ingest_pdf(pdf_path):
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
    
    # Save to out/ directory
    os.makedirs("out", exist_ok=True)
    output_path = "out/rigveda_normalized.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(normalized_text)
    
    print(f"Successfully wrote {len(normalized_text)} chars to {output_path}")
    return normalized_text

if __name__ == "__main__":
    # For testing, we can pass a dummy path or use command line args
    if len(sys.argv) > 1:
        ingest_pdf(sys.argv[1])
    else:
        print("Usage: python ingest.py <path_to_pdf>")
