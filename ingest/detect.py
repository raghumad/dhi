#!/usr/bin/env python3
"""Shared seal-figure detection for Dhi ingestion.

Both crop_figures.py (Vats 1940) and crop_marshall.py (Marshall 1931) use
these detectors. Thresholds are relative to image size (not absolute
pixels) so they survive source changes: the 1940 DLI scan, the 1999 ASI
reprint, and the Marshall IGNCA scan all have different native
resolutions, and absolute pixel thresholds do not transfer.

The relative values are derived from the thresholds originally tuned on
the 1940 DLI scan at half resolution (1394x1996):
    min side 40 px  -> 40/1394 ≈ 2.9% of the smaller half-res side
    min area 7500 px -> 7500/(1394*1996) ≈ 0.27% of half-res area
Each crop script verifies detected == expected per plate and reports
mismatches for human review; the thresholds are a starting point, not
a guarantee.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

# Fraction of half-res image area a blob must cover to count as a figure.
MIN_AREA_FRAC = 0.0027
# Fraction of the half-res smaller side a blob must span on each axis.
MIN_SIDE_FRAC = 0.029


def detect_components(plate_path, ksize: int = 25,
                      threshold: int = 128) -> list[list[int]]:
    """Sparse plates: connected components of dark regions.

    threshold: pixel values below this count as ink. Default 128 suits
        dark halftone plates; lighter continuous-tone photos may need
        a higher value to catch pale figures.
    """
    im = Image.open(plate_path).convert("L")
    # work at half resolution for speed; scale boxes back up
    small = im.resize((im.size[0] // 2, im.size[1] // 2))
    a = np.array(small)
    binary = a < threshold
    closed = ndimage.binary_closing(binary,
                                    structure=np.ones((ksize, ksize)))
    labeled, _ = ndimage.label(closed)
    h, w = a.shape
    min_side = min(h, w) * MIN_SIDE_FRAC
    min_area = h * w * MIN_AREA_FRAC
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(labeled)):
        if sl is None:
            continue
        y_sl, x_sl = sl
        bh, bw = y_sl.stop - y_sl.start, x_sl.stop - x_sl.start
        area = (labeled[y_sl, x_sl] == (i + 1)).sum()
        if bw > min_side and bh > min_side and area > min_area:
            boxes.append([x_sl.start * 2, y_sl.start * 2,
                          x_sl.stop * 2, y_sl.stop * 2])
    return _reading_order(boxes, h * 2)


def detect_grid(plate_path) -> list[list[int]]:
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
    return _reading_order(figs, H)


def _reading_order(boxes: list[list[int]], img_h: int) -> list[list[int]]:
    # Row-grouping tolerance scales with plate height (was 250 px on the
    # 3993-px-tall 1940 DLI scan ≈ 6.3% of height).
    row_tol = img_h * 0.063
    boxes.sort(key=lambda b: (b[1] + b[3]) / 2)
    rows: list[list[list[int]]] = []
    for b in boxes:
        yc = (b[1] + b[3]) / 2
        for row in rows:
            ryc = sum((x[1] + x[3]) / 2 for x in row) / len(row)
            if abs(yc - ryc) < row_tol:
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
