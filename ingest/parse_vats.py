#!/usr/bin/env python3
"""PoC parser: Vats 1940 'Tabulation of Seals' -> JSONL records.

Reads the OCR text of the archive.org scan (stored byte-identical under
data/artifacts/), locates the tabulation pages, and parses one row per
illustrated artifact: figure_no, size, depth below surface, type, material
cells, mound/area, field no.

Row layout in the OCR (each table cell on its own line):
    <figure_no> <size> <depth> <type> <material x1-3> <mound> <field_no>
Within one tabulation page the figure numbers form a near-consecutive
increasing sequence, which anchors row boundaries. Rows whose anchors were
too mangled are recovered by split heuristics; anything still unparseable
is preserved raw in `unmapped`, never discarded. Records that need human
review carry `parse_flags` (merged-row-suspect, duplicate-seal-no,
field-no-suspect).

Numbering note: the book's first column is headed "Plate No.", but its
values are the *figure* numbers of the illustrations on Plates LXXXV-CI in
Volume II (figures 1-713, numbered continuously across plates), not plate
numbers. The record field is therefore `figure_no`; the plate is derived
from the figure-range map below (verified against the plate scans).

Caveat: the tabulation covers the illustrated seals and sealings only.
Vats notes 974 seals and sealings were recovered in total, but duplicates
were omitted from the illustrations, so the tabulation is intentionally
smaller than 974.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

# Paths resolve from this file, not the process CWD: `python ingest/parse_vats.py`
# works wherever it is started from (R-I1: a repeatable command).
ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "data/artifacts/vats1940_djvu.txt"
OUT = ROOT / "data/records/vats1940_seals.jsonl"

# Figure ranges per plate, read off the Volume II plate scans
# (archive.org in.ernet.dli.2015.358923, scan pages n91-n107). Figure numbers
# run continuously 1-713 across Plates LXXXV-CI.
PLATE_FIGURES = [
    ("LXXXV", 1, 15), ("LXXXVI", 16, 37), ("LXXXVII", 38, 67),
    ("LXXXVIII", 68, 105), ("LXXXIX", 106, 167), ("XC", 168, 225),
    ("XCI", 226, 260), ("XCII", 261, 302), ("XCIII", 303, 328),
    ("XCIV", 329, 367), ("XCV", 368, 428), ("XCVI", 429, 496),
    ("XCVII", 497, 580), ("XCVIII", 581, 613), ("XCIX", 614, 650),
    ("C", 651, 692), ("CI", 693, 713),
]


def plate_for_figure(n: int) -> str:
    """Roman numeral of the plate illustrating figure n ('' if unknown)."""
    for plate, lo, hi in PLATE_FIGURES:
        if lo <= n <= hi:
            return plate
    return ""

COLOURS = re.compile(
    r"white|greenish|bluish|green|yellow|red|grey|gray|black|blue|brown|pink|buff",
    re.I,
)
# Bare material sub-column names, without any colour text. A cell holding only
# one of these is a material cell, never a field number or unmapped junk.
MATERIAL_NAMES = {"steatite", "faience", "pottery"}

# A figure-number line is 1-4 chars, all digits or common OCR confusions.
# Depth lines contain ' or ", sizes contain x/X -- both excluded here.
FIGURENO_RE = re.compile(r"^[0-9OISBlA?*^.\-]{1,4}$")
OCR_FIX = str.maketrans({"O": "0", "S": "3", "I": "1", "l": "1", "B": "8", "A": "4"})


def norm_figureno(line: str) -> int | None:
    s = line.strip()
    if not FIGURENO_RE.fullmatch(s):
        return None
    t = re.sub(r"[^0-9OISBlA]", "", s).translate(OCR_FIX)
    if not t.isdigit() or not (1 <= int(t) <= 1500):
        return None
    return int(t)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def longest_chain(cands):
    """Longest subsequence with 1 <= diff <= 4. cands: [(linepos, value, raw)]."""
    n = len(cands)
    if not n:
        return []
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        vi = cands[i][1]
        for j in range(i):
            d = vi - cands[j][1]
            if 1 <= d <= 4 and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    i = max(range(n), key=lambda k: dp[k])
    chain = []
    while i != -1:
        chain.append(cands[i])
        i = prev[i]
    chain.reverse()
    return chain


TYPE_RE = re.compile(r"^[a-z]{1,2}$")
MOUND_RE = re.compile(r"^[A-Z]{1,2}$")
PLACEHOLDER_RE = re.compile(r"^[\s.\-•*'\"]+$")
COLOUR_FIX = {"Hed": "Red", "Greenukh": "Greenish", "Bed": "Red"}

# Running page headers leak into the OCR mid-table; drop them.
RUNNING_HEAD_RE = re.compile(
    r"^(EXCAVATIONS|HARAPPA|MO[H]?ENJO|SEALS AND SEAL|TABULATION)", re.I
)


def parse_row(cells: list[str]) -> dict:
    """Content-based classification of a tabulation row's cells.

    Print order is figure_no, size, depth, type, material(steatite, faience,
    pottery), mound, field_no -- but OCR drops lines, so classify by content.
    Anything unclassified is kept in `unmapped`, never dropped.
    """
    body = cells[1:]  # cells[0] is the figure_no anchor
    # drop running page headers that leak into the OCR mid-table
    body = [c.replace("©", "e") for c in body
            if not RUNNING_HEAD_RE.match(c)]
    size = depth = type_ = mound = field_no = ""
    sizes_seen = depths_seen = 0
    material_cells: list[str] = []
    unmapped: list[str] = []
    for c in body:
        if re.search(r"[xX×]|diam", c):
            sizes_seen += 1
            size = size or c
        elif "'" in c or "spoil" in c.lower() or "surface" in c.lower():
            depths_seen += 1
            depth = depth or c
        elif not type_ and TYPE_RE.fullmatch(c):
            type_ = c
        elif COLOURS.search(c):
            material_cells.append(c)
        elif c.strip().rstrip(".").lower() in MATERIAL_NAMES:
            material_cells.append(c)  # bare material name, no colour text
        elif not mound and MOUND_RE.fullmatch(c):
            mound = c
        elif c.strip() == "?":
            size = size or c  # lone '?' in this table = unknown size
        elif PLACEHOLDER_RE.fullmatch(c):
            material_cells.append(c)  # empty material sub-column: keep position
        else:
            unmapped.append(c)
    # field_no is the trailing alphanumeric code. Real field numbers in this
    # book always contain digits ("H 5974", "1154c"); a trailing word without
    # any digit is OCR junk or a swallowed header cell, not a field number.
    flags = []
    if unmapped and re.fullmatch(r"[A-Za-z0-9()\-/ ]{1,12}", unmapped[-1]):
        if re.search(r"\d", unmapped[-1]):
            field_no = unmapped.pop()
        else:
            flags.append("field-no-suspect")
    colour = ""
    for mc in material_cells:
        m = COLOURS.search(mc)
        if m:
            w = m.group(0).capitalize()
            colour = COLOUR_FIX.get(w, w)
            break
    material = ""
    names = ["steatite", "faience", "pottery"]
    for i, mc in enumerate(material_cells):
        bare = mc.strip().rstrip(".").lower()
        if bare in MATERIAL_NAMES:
            material = bare
            break
        if COLOURS.search(mc) and i < 3:
            material = names[i]
            break
    if sizes_seen > 1 or depths_seen > 1:
        # two rows likely merged: the seal-no anchor between them was
        # unreadable. Quarantined for review instead of silently kept.
        flags.append("merged-row-suspect")
    return {"size_raw": size, "depth_raw": depth, "type_raw": type_,
            "material": material, "material_cells_raw": material_cells,
            "colour": colour, "mound": mound, "field_no": field_no,
            "unmapped": unmapped, "parse_flags": flags}


LOOSE_FIGURENO_RE = re.compile(r"^[0-9OISBlA?*^.\-■]{1,4}$")
SIZE_LIKE_RE = re.compile(r"[xX×]|diam")


def loose_figureno(cell: str) -> int | None:
    tok = cell.strip().split(" ")[0]
    if not LOOSE_FIGURENO_RE.fullmatch(tok):
        return None
    t = re.sub(r"[^0-9OISBlA]", "", tok).translate(OCR_FIX)
    if not t.isdigit() or not (1 <= int(t) <= 1500):
        return None
    return int(t)


def _restore_hundreds(value: int, prev: int) -> int:
    """Best-effort repair for OCR-dropped leading digits ('368' -> '68').

    Only valid because this tabulation's numbering is one continuous
    sequence: a value that goes backwards against `prev` is assumed to have
    lost hundreds. Callers must guard the result with independent evidence
    (see split_merged); never apply blindly to sources whose numbering may
    legitimately restart.
    """
    v = value
    while v <= prev:
        v += 100
    return v


def split_merged(figure_no: int, cells: list[str]) -> list[tuple[int, list[str]]]:
    """Recover rows whose figure-no anchor was too mangled for the chain.

    A later row's cells got appended to this row; its number survives as an
    ordinary cell. Split there, guarded so field numbers can't false-trigger:
    either a size-like cell follows the candidate (a new row is starting),
    or the current row already looks complete (size+depth+mound seen).
    """
    seen_size = seen_depth = seen_mound = False
    for i in range(1, len(cells)):
        c = cells[i]
        if SIZE_LIKE_RE.search(c) or c.strip() == "?":
            seen_size = True
        elif "'" in c or "spoil" in c.lower():
            seen_depth = True
        elif MOUND_RE.fullmatch(c):
            seen_mound = True
        v = loose_figureno(c)
        if v is None:
            continue
        v = _restore_hundreds(v, figure_no - 3)
        if v != figure_no and abs(v - figure_no) <= 2:
            follows = any(SIZE_LIKE_RE.search(x) or x.strip() == "?"
                          for x in cells[i + 1:i + 4])
            complete = seen_size and seen_depth and seen_mound
            head, tail = cells[:i], cells[i:]
            # both parts must have enough cells to be real rows; this also
            # stops field numbers (row-final codes) from false-splitting
            if (follows or complete) and len(head) >= 5 and len(tail) >= 5:
                if v > figure_no:
                    return [(figure_no, head)] + split_merged(v, tail)
                return [(v, head)] + split_merged(figure_no, tail)
    return [(figure_no, cells)]


# Tabulation page headers, OCR-mangled in various ways ("TABULATION OP
# SEALS", "TABULATIOZST OF SEALS", ...). The table of contents also mentions
# the tabulation once; heads[0] is that entry and is skipped below.
HEADER_RE = re.compile(r"TABULA\w*\s+O[PF]\s+SEAL")


def main() -> None:
    lines = ARTIFACT.read_text(encoding="utf-8", errors="replace").splitlines()
    digest = sha256(ARTIFACT)

    heads = [i for i, l in enumerate(lines) if HEADER_RE.search(l.upper())]
    ch13 = next(i for i, l in enumerate(lines)
                if l.strip() == "CHAPTER XIII." and i > heads[-1])
    pages = []
    for p in range(1, len(heads)):
        end = heads[p + 1] if p + 1 < len(heads) else ch13
        pages.append((heads[p], min(end, ch13)))

    anchored: list[tuple[int, list[str]]] = []
    for start, end in pages:
        chunk = [l.strip() for l in lines[start:end] if l.strip()]
        cands = [(li, v, chunk[li]) for li, l in enumerate(chunk)
                 if (v := norm_figureno(l)) is not None]
        chain = longest_chain(cands)
        if not chain:
            print("warning: no figure-number chain on page", start, file=sys.stderr)
            continue
        for k in range(len(chain)):
            a = chain[k][0]
            b = chain[k + 1][0] if k + 1 < len(chain) else len(chunk)
            cells = chunk[a:b]
            if len(cells) >= 5:
                anchored.append((chain[k][1], cells))

    # split rows that swallowed a following row whose anchor was too
    # mangled for the figure-number chain
    rows: list[tuple[int, list[str]]] = []
    for figure_no, cells in anchored:
        rows.extend(split_merged(figure_no, cells))

    # dedupe byte-identical rows; disambiguate genuine duplicate numbers
    seen_cells: set[tuple[int, tuple[str, ...]]] = set()
    seen_no: dict[int, int] = {}
    records = []
    for figure_no, cells in rows:
        if not 1 <= figure_no <= 713:
            # OCR garbage (e.g. a field number chained as a figure); the
            # cells are preserved in `unmapped` of the nearest real row only
            # if they were merged there, otherwise dropped here and counted.
            print(f"warning: dropping out-of-range figure_no {figure_no}",
                  file=sys.stderr)
            continue
        key = (figure_no, tuple(cells))
        if key in seen_cells:
            continue
        seen_cells.add(key)
        rec_id = f"vats1940-{figure_no}"
        row = parse_row(cells)
        n = seen_no.get(figure_no, 0)
        if n:
            # 2nd occurrence -> "b", 3rd -> "c", ...
            rec_id += chr(ord("a") + n)
            row["parse_flags"].append("duplicate-seal-no")
        seen_no[figure_no] = n + 1

        records.append({
            "id": rec_id,
            "figure_no": figure_no,
            "plate": plate_for_figure(figure_no),
            "site": "Harappa",
            "size_raw": row["size_raw"],
            "depth_raw": row["depth_raw"],
            "type_raw": row["type_raw"],
            "material": row["material"],
            "material_cells_raw": row["material_cells_raw"],
            "colour": row["colour"],
            "mound": row["mound"],
            "field_no": row["field_no"],
            "unmapped": row["unmapped"],
            "parse_flags": row["parse_flags"],
            "provenance": {
                "source": "Vats, M.S. Excavations at Harappa, Vol. I, 1940. "
                          "Tabulation of Seals (Pls. LXXXV-CI). Public domain.",
                "artifact": "archive.org in.ernet.dli.2015.210462",
                "artifact_sha256": digest,
                "extraction": "parse_vats.py tabulation-row parser (PoC)",
            },
        })

    records.sort(key=lambda r: r["figure_no"])

    # Stub records for illustrated figures whose tabulation row did not
    # survive OCR well enough to parse. Every figure 1-713 gets a record so
    # the seal image is always browsable; stubs carry no table data and are
    # flagged table-row-unparsed for human review. They are honest placeholders,
    # not parsed data.
    have = {r["figure_no"] for r in records}
    for n in range(1, 714):
        if n in have:
            continue
        records.append({
            "id": f"vats1940-{n}",
            "figure_no": n,
            "plate": plate_for_figure(n),
            "site": "Harappa",
            "size_raw": None,
            "depth_raw": None,
            "type_raw": None,
            "material": "unknown",
            "material_cells_raw": [],
            "colour": None,
            "mound": None,
            "field_no": None,
            "unmapped": [],
            "parse_flags": ["table-row-unparsed"],
            "provenance": {
                "source": "Vats, M.S. Excavations at Harappa, Vol. I, 1940. "
                          "Tabulation of Seals (Pls. LXXXV-CI). Public domain.",
                "artifact": "archive.org in.ernet.dli.2015.210462",
                "artifact_sha256": digest,
                "extraction": "stub: tabulation row not recovered from OCR; "
                              "figure number and plate only",
            },
        })

    records.sort(key=lambda r: r["figure_no"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"parsed {len(records)} records -> {OUT}")
    if records:
        print(f"figure_no range: {records[0]['figure_no']}..{records[-1]['figure_no']}")


if __name__ == "__main__":
    sys.exit(main())
