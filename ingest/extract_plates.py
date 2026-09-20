#!/usr/bin/env python3
"""Extract plate scans from a source's plates PDF.

Reads the plate_extraction section of ingest/sources.yaml for the given
source id:
    - scans: explicit list of archive.org leaf numbers, or
      scan_start/scan_end: inclusive range of leaf numbers
    - scan_plates: optional leaf -> plate numeral map, for filename
      patterns using {plate}
    - pdf_page_offset: PDF page = leaf + offset
    - dpi, output_dir, filename_pattern ("plate_n{scan}.jpg" or
      "plate_{plate}.jpg")

Renders each page with pdftoppm and saves it as a grayscale JPEG.
Deterministic: re-running over an unchanged PDF reproduces identical
plates. Idempotent: existing outputs are skipped.

Requires: pdftoppm (poppler-utils), Pillow.

Usage:
    python ingest/extract_plates.py            # vats1940 (default)
    python ingest/extract_plates.py marshall1931
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
# critical invariant is rendering at the configured (native) DPI.
JPEG_QUALITY = 95


def load_config(source_id: str) -> dict:
    with open(SOURCES_YAML, encoding="utf-8") as f:
        sources = yaml.safe_load(f)["sources"]
    for s in sources:
        if s["id"] == source_id:
            return s
    raise SystemExit(f"{source_id} not found in sources.yaml")


def main() -> None:
    source_id = sys.argv[1] if len(sys.argv) > 1 else "vats1940"
    cfg = load_config(source_id)
    ex = cfg.get("plate_extraction")
    if not ex:
        raise SystemExit(f"{source_id}: no plate_extraction in sources.yaml")
    out_dir = ROOT / ex["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    if "scans" in ex:
        scans = ex["scans"]
    else:
        scans = list(range(ex["scan_start"], ex["scan_end"] + 1))
    scan_plates = ex.get("scan_plates", {})

    kind = ex.get("kind", "pdf")
    if kind == "pdf":
        extract_pdf(cfg, ex, scans, scan_plates, out_dir)
    elif kind == "jp2zip":
        extract_jp2zip(cfg, ex, scans, scan_plates, out_dir)
    else:
        raise SystemExit(f"{source_id}: unknown plate_extraction kind {kind!r}")
    print(f"plate extraction complete: {source_id}")


def plates_artifact(cfg: dict) -> dict:
    artifacts = {a["name"]: a for a in cfg["artifacts"]}
    name = cfg["plate_extraction"].get("artifact", "plates-pdf")
    if name not in artifacts:
        raise SystemExit(f"{cfg['id']}: no {name!r} artifact in sources.yaml")
    return artifacts[name]


def out_path_for(out_dir: Path, pattern: str, scan: int, plate) -> Path:
    return out_dir / pattern.format(scan=scan, plate=plate)


def save_plate_jpeg(im: Image.Image, out_path: Path) -> None:
    if out_path.is_file():
        print(f"  ok (cached) {out_path.name}")
        return
    im.convert("L").save(out_path, "JPEG", quality=JPEG_QUALITY)
    with Image.open(out_path) as check:
        print(f"  ok {out_path.name} {check.size[0]}x{check.size[1]}")


def extract_pdf(cfg, ex, scans, scan_plates, out_dir) -> None:
    if not shutil.which("pdftoppm"):
        raise SystemExit(
            "pdftoppm not found (poppler-utils). Install it first:\n"
            "  apt install poppler-utils   # Debian/Ubuntu\n"
            "  brew install poppler        # macOS")
    pdf = ROOT / plates_artifact(cfg)["path"]
    if not pdf.is_file():
        raise SystemExit(f"plates PDF not found: {pdf}\n"
                         f"Run: python ingest/fetch.py {cfg['id']}")
    for scan in scans:
        pdf_page = scan + ex["pdf_page_offset"]
        plate = scan_plates.get(scan, scan)
        out_path = out_path_for(out_dir, ex["filename_pattern"], scan, plate)
        if out_path.is_file():
            print(f"  ok (cached) {out_path.name}")
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
                save_plate_jpeg(im, out_path)


def extract_jp2zip(cfg, ex, scans, scan_plates, out_dir) -> None:
    """Extract leaves from an archive.org *_jp2.zip of full-res scans."""
    import io
    import re
    import zipfile
    zip_path = ROOT / plates_artifact(cfg)["path"]
    if not zip_path.is_file():
        raise SystemExit(f"plates JP2 zip not found: {zip_path}\n"
                         f"Run: python ingest/fetch.py {cfg['id']}")
    with zipfile.ZipFile(zip_path) as z:
        members = {}
        for name in z.namelist():
            m = re.search(r"(\d+)\.jp2$", name)
            if m:
                members[int(m.group(1))] = name
        for scan in scans:
            plate = scan_plates.get(scan, scan)
            out_path = out_path_for(out_dir, ex["filename_pattern"],
                                    scan, plate)
            if out_path.is_file():
                print(f"  ok (cached) {out_path.name}")
                continue
            if scan not in members:
                raise SystemExit(
                    f"leaf {scan} not found in {zip_path.name} "
                    f"(members like {next(iter(members.values()), None)!r})")
            with z.open(members[scan]) as fh:
                im = Image.open(io.BytesIO(fh.read()))
                im.load()
            save_plate_jpeg(im, out_path)


if __name__ == "__main__":
    main()
