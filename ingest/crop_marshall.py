#!/usr/bin/env python3
"""Crop individual seal figures from Marshall 1931 Vol. III plates.

Reads the 18 seal plate scans (data/artifacts/plates-marshall/plate_{CI..CXVIII}.jpg),
detects figure bounding boxes, and writes:
  - data/figures/marshall1931-{PLATE}-{NN}.jpg : the seal crop
  - data/figures/_review/marshall_contact_{PLATE}.jpg : boxes+indices for review
  - data/figures/marshall1931_boxes.json : box coordinates + provenance

Figure identity: the printed plates letter their sub-figures (a, b, c...),
but the printed letters are NOT in pure reading order on every plate, so
guessing them from detection order would bake in wrong labels. Crops use
positional indices (01, 02, ...) in reading order; mapping to the printed
letters (and to the Vol. II tabulation records) is pending human review.
The manifest records this explicitly -- indices are not letters.

A plate is cropped only if detection finds a plausible figure count
(>=3); sparse plates use connected components, dense ones grid projection.
Contact sheets make verification cheap: the reviewer reads the printed
letters off the plate and records the index->letter map.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from detect import detect_components, detect_grid

ROOT = Path(__file__).resolve().parent.parent
PLATES = ROOT / "data/artifacts/plates-marshall"
OUT = ROOT / "data/figures"
REVIEW = OUT / "_review"
MANIFEST = OUT / "marshall1931_boxes.json"

# (scan leaf, plate roman, method, ksize, threshold)
# Photo plates are the odd leaves; even leaves are blank versos.
# ksize/threshold tuned per plate family on 2026-09-20:
#   photo plates (CII-CXVI): ksize=8, threshold=180 -- Marshall's
#     continuous-tone photos are lighter than Vats' halftones, so the
#     default 128 misses pale figures; ksize=8 avoids merging neighbours.
#   line-drawing plates (CXVII copper tablets, CXVIII sealings):
#     ksize=15, threshold=128 -- the larger close thickens thin ink
#     lines into solid blobs so the area filter keeps them.
PLATES_MAP = [
    (179, "CII", "components", 8, 180),
    (181, "CIII", "components", 8, 180),
    (183, "CIV", "components", 8, 180),
    (185, "CV", "components", 8, 180),
    (187, "CVI", "components", 8, 180),
    (189, "CVII", "components", 8, 180),
    (191, "CVIII", "components", 8, 180),
    (193, "CIX", "components", 8, 180),
    (195, "CX", "components", 8, 180),
    (197, "CXI", "components", 8, 180),
    (199, "CXII", "components", 8, 180),
    (201, "CXIII", "components", 8, 180),
    (203, "CXIV", "components", 8, 180),
    (205, "CXV", "components", 8, 180),
    (207, "CXVI", "components", 8, 180),
    (209, "CXVII", "components", 15, 128),
    (211, "CXVIII", "components", 15, 128),
]

# Padding around each crop, scaled for the ~2480-px-wide Marshall plates.
PAD = 15


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    problems: list[str] = []

    for scan, roman, method, ksize, threshold in PLATES_MAP:
        src = PLATES / f"plate_{roman}.jpg"
        if not src.exists():
            problems.append(f"{roman}: missing {src}")
            continue
        if method == "components":
            figs = detect_components(src, ksize, threshold)
        else:
            figs = detect_grid(src)
        if len(figs) < 3:
            problems.append(
                f"{roman}: {method} found only {len(figs)} figures; skipping")
            continue
        im = Image.open(src)
        W, H = im.size
        thumb = im.copy().convert("RGB")
        thumb.thumbnail((900, 1300))
        sx, sy = thumb.size[0] / W, thumb.size[1] / H
        draw = ImageDraw.Draw(thumb)
        for idx, b in enumerate(figs, start=1):
            x0 = max(0, b[0] - PAD); y0 = max(0, b[1] - PAD)
            x1 = min(W, b[2] + PAD); y1 = min(H, b[3] + PAD)
            key = f"marshall1931-{roman}-{idx:02d}"
            im.crop((x0, y0, x1, y1)).save(OUT / f"{key}.jpg", quality=88)
            draw.rectangle([x0 * sx, y0 * sy, x1 * sx, y1 * sy],
                           outline="red", width=3)
            draw.text((x0 * sx + 4, y0 * sy + 4), str(idx), fill="red")
            manifest[key] = {
                "plate": roman, "plate_scan": f"leaf{scan}",
                "index": idx,
                "printed_letter": None,
                "box": [x0, y0, x1, y1], "method": method,
                "crop_file": f"{key}.jpg",
                "review": ("auto-detected, awaiting human review; "
                           "index is positional, not the printed letter"),
            }
        thumb.save(REVIEW / f"marshall_contact_{roman}.jpg", quality=75)
        print(f"{roman}: {len(figs)} figures via {method}")

    MANIFEST.write_text(json.dumps(manifest, indent=1))
    if problems:
        print("\nPROBLEMS:", file=sys.stderr)
        for p in problems:
            print(" -", p, file=sys.stderr)
    print(f"\nmanifest: {len(manifest)} figures")


if __name__ == "__main__":
    main()
