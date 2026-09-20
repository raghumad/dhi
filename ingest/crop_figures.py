#!/usr/bin/env python3
"""Crop individual seal figures from Volume II plates.

Reads the 17 plate scans (data/artifacts/plates/plate_n{91..107}.jpg),
detects figure bounding boxes (connected components for sparse plates,
grid projection for dense plates), assigns figure numbers by reading order,
and writes:
  - data/figures/vats1940-fig{N}.jpg : the seal crop
  - data/figures/_review/contact_{plate}.jpg : boxes+numbers for human review
  - data/figures/boxes.json : box coordinates + provenance per figure

Figure ranges per plate are from PLATE_FIGURES (verified against scans).
Known numbering gaps (e.g. 568 skipped on Plate XCVII) are listed in GAPS.
A plate is only cropped if the detected count matches the expected count;
mismatches are reported for human review, never silently accepted.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
PLATES = ROOT / "data/artifacts/plates"
OUT = ROOT / "data/figures"
REVIEW = OUT / "_review"

# (archive page, plate roman, first figure, last figure, method, closing_ksize)
# Method/ksize tuned per plate at half resolution; verified detected == expected.
PLATES_MAP = [
    (91, "LXXXV", 1, 15, "components", 6),
    (92, "LXXXVI", 16, 37, "components", 6),
    (93, "LXXXVII", 38, 67, "components", 8),
    (94, "LXXXVIII", 68, 105, "components", 6),
    (97, "XCI", 226, 260, "components", 8),
    (99, "XCIII", 303, 328, "components", 10),
    (100, "XCIV", 329, 367, "components", 10),
    (103, "XCVII", 497, 580, "grid", None),
]
# Remaining plates (LXXXIX, XC, XCII, XCV, XCVI, XCVIII, XCIX, C, CI)
# need manual box review; crops pending. Full plates are served regardless.
# Figure numbers with no illustration on their plate (verified visually).
GAPS = {568}

PAD = 18


def detect_components(plate_path: Path, ksize: int = 25) -> list[list[int]]:
    """Sparse plates: connected components of dark regions."""
    im = Image.open(plate_path).convert("L")
    # work at half resolution for speed; scale boxes back up
    small = im.resize((im.size[0] // 2, im.size[1] // 2))
    a = np.array(small)
    binary = a < 128
    closed = ndimage.binary_closing(binary,
                                    structure=np.ones((ksize, ksize)))
    labeled, _ = ndimage.label(closed)
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(labeled)):
        if sl is None:
            continue
        y_sl, x_sl = sl
        h, w = y_sl.stop - y_sl.start, x_sl.stop - x_sl.start
        area = (labeled[y_sl, x_sl] == (i + 1)).sum()
        # thresholds for half-res (≈1/4 area)
        if w > 40 and h > 40 and area > 7500:
            boxes.append([x_sl.start * 2, y_sl.start * 2,
                          x_sl.stop * 2, y_sl.stop * 2])
    return _reading_order(boxes)


def detect_grid(plate_path: Path) -> list[list[int]]:
    """Dense plates: figure rows via horizontal projection, columns via vertical."""
    im = Image.open(plate_path).convert("L")
    a = np.array(im)
    binary = a < 128
    H, W = binary.shape
    hproj = binary.sum(axis=1)
    row_mask = hproj > (W * 0.03)
    bands, start = [], None
    for i, v in enumerate(row_mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start > 15:
                bands.append((start, i, "FIG" if i - start > 50 else "NUM"))
            start = None
    fig_rows, cur = [], []
    for s, e, typ in bands:
        if typ == "FIG":
            cur.append((s, e))
        elif cur:
            fig_rows.append((cur[0][0], cur[-1][1]))
            cur = []
    if cur:
        fig_rows.append((cur[0][0], cur[-1][1]))
    figs = []
    for (y0, y1) in fig_rows:
        vproj = binary[y0:y1, :].sum(axis=0)
        col_mask = vproj > ((y1 - y0) * 0.05)
        cols, cs = [], None
        for i, v in enumerate(col_mask):
            if v and cs is None:
                cs = i
            elif not v and cs is not None:
                if i - cs > 20:
                    cols.append((cs, i))
                cs = None
        for (x0, x1) in cols:
            cell = binary[y0:y1, x0:x1]
            ys, xs = np.where(cell)
            if len(xs) == 0:
                continue
            figs.append([int(x0 + xs.min()), int(y0 + ys.min()),
                         int(x0 + xs.max()), int(y0 + ys.max())])
    return _reading_order(figs)


def _reading_order(boxes: list[list[int]]) -> list[list[int]]:
    boxes.sort(key=lambda b: (b[1] + b[3]) / 2)
    rows: list[list[list[int]]] = []
    for b in boxes:
        yc = (b[1] + b[3]) / 2
        for row in rows:
            ryc = sum((x[1] + x[3]) / 2 for x in row) / len(row)
            if abs(yc - ryc) < 250:
                row.append(b)
                break
        else:
            rows.append([b])
    rows.sort(key=lambda r: sum((x[1] + x[3]) / 2 for x in r) / len(r))
    out = []
    for row in rows:
        row.sort(key=lambda b: b[0])
        out.extend(row)
    return out


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
