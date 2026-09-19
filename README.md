# Dhi — Vats 1940 seal tabulation, end to end

Vertical slice proving the architecture: fetch once → parse → immutable
records → dimension indexes → query API.

## Layout

- `data/artifacts/vats1940_djvu.txt` — raw OCR from archive.org
  (`in.ernet.dli.2015.210462`), stored byte-identical, never edited.
- `ingest/parse_vats.py` — tabulation parser → `data/records/vats1940_seals.jsonl`
  (one JSON record per line, each with sha256 provenance of the artifact).
  The committed JSONL is a snapshot: re-running the parser over the unchanged
  artifact must reproduce it byte-identically (enforced by
  `tests/test_parse_vats.py::test_ingest_is_deterministic`).
- `api/main.py` — FastAPI: `/seals`, `/seals/{id}`, `/search`, `/stats`, `/export`.
- `tests/` — parser unit tests, ingestion determinism and record-integrity
  tests, API contract smoke tests.

## Rerun

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/
python3 ingest/parse_vats.py          # re-parse (deterministic)
.venv/bin/uvicorn api.main:app --port 8765
curl "localhost:8765/seals?material=faience&mound=F"
curl "localhost:8765/search?q=16"
curl "localhost:8765/export?format=csv"
```

## Result (2026-09-19)

371 records, seal figures 60–687. 98 carry `parse_flags` (quarantine for
human review: `merged-row-suspect`, `field-no-suspect`, `duplicate-seal-no`);
the rest parsed clean. Spot-checked against the print table.

Why 371 and not 974: Vats states 974 seals and sealings were recovered, but
duplicates "have been omitted from the illustrations" — the tabulation covers
the illustrated seals only, and this parse recovers the rows the OCR kept
readable.

## Known limitations (all quarantined, none silent)

- 1930s OCR noise: dropped lines, mangled numbers, split cells.
- Figure numbers occasionally lose a leading digit ("368" → "68"). The
  sequence-chain anchoring skips such anchors; the row is then either
  recovered by the split heuristic or swallowed into a neighbour, which gets
  `merged-row-suspect`. Dropped digits are *not* silently repaired.
- A trailing cell that looks like a field number but contains no digit
  ("Afiie", "Pottery") is kept in `unmapped` and flagged `field-no-suspect`;
  bare material words ("Pottery") are classified as material, never as a
  field number.
- Stray header lines can land in `unmapped` (preserved, never discarded).
- Motifs (unicorn, bull) live in the book's prose and plates, not in this
  tabulation — `/search?q=unicorn` honestly returns zero.
