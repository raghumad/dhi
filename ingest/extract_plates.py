#!/usr/bin/env python3
"""Extract seal plate scans from the Vats 1940 Vol. II PDF.

Reads the plate_extraction section of ingest/sources.yaml:
for each scan number, renders the corresponding PDF page with pdftoppm
and saves it as a grayscale JPEG. Deterministic: re-running over an
unchanged PDF reproduces identical plates.

Requires: pdftoppm (poppler-utils), Pillow.

Usage:
    python ingest/extract_plates.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCES_YAML = Path(__file__).resolve().parent / "sources.yaml"

# JPEG quality for plate scans. Content (not bytes) is what matters
# downstream; boxes.json coordinates are in absolute pixels, so the
# critical invariant is the 2788x3993 dimensions from 300 DPI.
JPEG_QUALITY = 95


def load_vats_config() -> dict:
    with open(SOURCES_YAML, encoding="utf-8") as f:
        sources = yaml.safe_load(f)["sources"]
    for s in sources:
        if s["id"] == "vats1940":
            return s
    raise SystemExit("vats1940 not found in sources.yaml")


def main() -> None:
    if not shutil.which("pdftoppm"):
        raise SystemExit(
            "pdftoppm not found (poppler-utils). Install it first:\n"
            "  apt install poppler-utils   # Debian/Ubuntu\n"
            "  brew install poppler        # macOS")
    cfg = load_vats_config()
    artifacts = {a["name"]: a for a in cfg["artifacts"]}
    pdf = ROOT / artifacts["plates-pdf"]["path"]
    if not pdf.is_file():
        raise SystemExit(f"plates PDF not found: {pdf}\nRun: python ingest/fetch.py vats1940")

    ex = cfg["plate_extraction"]
    out_dir = ROOT / ex["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    scans = range(ex["scan_start"], ex["scan_end"] + 1)
    for scan in scans:
        pdf_page = scan + ex["pdf_page_offset"]
        out_name = ex["filename_pattern"].format(scan=scan)
        out_path = out_dir / out_name
        if out_path.is_file():
            print(f"  ok (cached) {out_name}")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            prefix = str(Path(tmp) / "page")
            subprocess.run(
                ["pdftoppm", "-r", str(ex["dpi"]), "-gray",
                 "-f", str(pdf_page), "-l", str(pdf_page),
                 str(pdf), prefix],
                check=True, capture_output=True)
            pgm = next(Path(tmp).glob("*.pgm"), None)
            if pgm is None:
                raise SystemExit(f"pdftoppm produced no output for page {pdf_page}")
            with Image.open(pgm) as im:
                im.save(out_path, "JPEG", quality=JPEG_QUALITY)
        with Image.open(out_path) as im:
            print(f"  ok {out_name} {im.size[0]}x{im.size[1]}")
    print("plate extraction complete")


if __name__ == "__main__":
    main()
