#!/usr/bin/env python3
"""Crop individual seal figures from the Vol. II plates (1999 ASI reprint).

Reads the 17 plate scans (data/artifacts/plates/plate_n{94..110}.jpg),
detects figure bounding boxes (connected components for sparse plates,
grid projection for dense plates), assigns figure numbers by reading order,
and writes:
  - data/figures/vats1940-fig{N}.jpg : the seal crop
  - data/figures/_review/contact_{plate}.jpg : boxes+numbers for human review
  - data/figures/boxes.json : box coordinates + provenance per figure

Figure ranges per plate are from PLATE_FIGURES (verified against scans).
GAPS lists figure numbers with no illustration on their plate (visually
confirmed; currently empty -- 568 was removed 2026-09-20 after the reprint
plate showed it does exist).
A plate is only cropped if the detected count matches the expected count;
mismatches are reported for human review, never silently accepted.

Detection itself lives in ingest/detect.py (shared with crop_marshall.py).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from detect import detect_components, detect_grid

ROOT = Path(__file__).resolve().parent.parent
PLATES = ROOT / "data/artifacts/plates"
OUT = ROOT / "data/figures"
REVIEW = OUT / "_review"

# (reprint scan leaf, plate roman, first figure, last figure, method, closing_ksize)
# Scan leaves 94-110 = plates LXXXV-CI (verified against the reprint's
# djvu.xml plate labels). Method/ksize retuned for the reprint's native
# 1500x2174 px plates; verified detected == expected.
PLATES_MAP = [
    (94, "LXXXV", 1, 15, "components", 6),
    (95, "LXXXVI", 16, 37, "components", 6),
    (96, "LXXXVII", 38, 67, "components", 8),
    (97, "LXXXVIII", 68, 105, "components", 6),
    (100, "XCI", 226, 260, "components", 8),
    (102, "XCIII", 303, 328, "components", 10),
    (103, "XCIV", 329, 367, "components", 10),
    (106, "XCVII", 497, 580, "grid", None),
]
# Remaining plates (LXXXIX, XC, XCII, XCV, XCVI, XCVIII, XCIX, C, CI)
# need manual box review; crops pending. Full plates are served regardless.
# Figure numbers with no illustration on their plate (verified visually).
# NOTE (2026-09-20): 568 was treated as a gap on Plate XCVII, but the 1999
# reprint plate clearly shows "568" printed with a figure -- the gap was an
# OCR/parsing artifact, not a real omission. GAPS stays empty until a gap
# is VISUALLY confirmed on the plate.
GAPS = set()

# Padding around each crop, scaled for the 1500-px-wide reprint plates
# (was 18 px on the 2788-px-wide 1940 DLI scan).
PAD = 10


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    problems: list[str] = []

    for page, roman, first, last, method, ksize in PLATES_MAP:
        src = PLATES / f"plate_n{page}.jpg"
        if not src.exists():
            problems.append(f"{roman}: missing {src}")
            continue
        expected = last - first + 1 - sum(1 for g in GAPS if first <= g <= last)
        if method == "components":
            figs = detect_components(src, ksize)
        else:
            figs = detect_grid(src)
        if len(figs) != expected:
            problems.append(
                f"{roman}: {method} gave {len(figs)}, expected {expected}; "
                "skipping")
            continue
        im = Image.open(src)
        W, H = im.size
        thumb = im.copy().convert("RGB")
        thumb.thumbnail((900, 1300))
        sx, sy = thumb.size[0] / W, thumb.size[1] / H
        draw = ImageDraw.Draw(thumb)
        figno = first
        for b in figs:
            while figno in GAPS:
                figno += 1
            x0 = max(0, b[0] - PAD); y0 = max(0, b[1] - PAD)
            x1 = min(W, b[2] + PAD); y1 = min(H, b[3] + PAD)
            im.crop((x0, y0, x1, y1)).save(OUT / f"vats1940-fig{figno}.jpg",
                                           quality=88)
            draw.rectangle([x0 * sx, y0 * sy, x1 * sx, y1 * sy],
                           outline="red", width=3)
            draw.text((x0 * sx + 4, y0 * sy + 4), str(figno), fill="red")
            manifest[str(figno)] = {
                "plate": roman, "plate_scan": f"n{page}",
                "box": [x0, y0, x1, y1], "method": method,
                "crop_file": f"vats1940-fig{figno}.jpg",
                "review": "auto-detected, awaiting human review",
            }
            figno += 1
        thumb.save(REVIEW / f"contact_{roman}.jpg", quality=75)
        print(f"{roman}: {len(figs)} figures via {method}")

    (OUT / "boxes.json").write_text(json.dumps(manifest, indent=1))
    if problems:
        print("\nPROBLEMS:", file=sys.stderr)
        for p in problems:
            print(" -", p, file=sys.stderr)
    print(f"\nmanifest: {len(manifest)} figures")


if __name__ == "__main__":
    main()
