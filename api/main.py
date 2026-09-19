#!/usr/bin/env python3
"""Dhi PoC API: serves Vats 1940 seal records.

Endpoints (per docs/requirements.md R-A1..R-A4):
  GET /seals            paginated listing + filters (material, colour, mound, type, site)
  GET /seals/{id}      single record, with provenance
  GET /search?q=...    full-text search over record fields
  GET /export          bulk export, format=json (default) or csv
  GET /stats           facet counts per dimension

Storage: records live in data/records/*.jsonl (immutable, written by ingest).
Indexes are built in memory at startup: one inverted index per categorical
dimension + one full-text token index. Raw records are never modified.
"""
import csv
import io
import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

app = FastAPI(title="Dhi PoC", version="0.1.0")

UI_DIR = Path(__file__).resolve().parent / "ui"

# Resolve data paths from this file's location, not the process CWD, so
# `uvicorn api.main:app` works wherever it is started from.
ROOT = Path(__file__).resolve().parent.parent

RECORDS: dict[str, dict] = {}
# dimension -> value -> [record ids]
DIM_INDEX: dict[str, dict[str, list[str]]] = {}
# token -> {record id: hit count}
TEXT_INDEX: dict[str, dict[str, int]] = {}

DIMS = ("site", "material", "colour", "mound", "type_raw")
TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def record_text(r: dict) -> str:
    return " ".join(str(r.get(k, "")) for k in (
        "seal_no", "site", "size_raw", "depth_raw", "type_raw", "material",
        "colour", "mound", "field_no") + tuple(r.get("unmapped", [])))


def load() -> None:
    for path in sorted((ROOT / "data" / "records").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            RECORDS[r["id"]] = r
    for dim in DIMS:
        idx: dict[str, list[str]] = {}
        for rid, r in RECORDS.items():
            v = (r.get(dim) or "?").strip().lower() or "?"
            idx.setdefault(v, []).append(rid)
        DIM_INDEX[dim] = idx
    for rid, r in RECORDS.items():
        for t in tokens(record_text(r)):
            TEXT_INDEX.setdefault(t, {}).setdefault(rid, 0)
            TEXT_INDEX[t][rid] += 1


load()


def apply_filters(material, colour, mound, type_, site) -> list[str]:
    sets = []
    for dim, val in (("material", material), ("colour", colour),
                     ("mound", mound), ("type_raw", type_), ("site", site)):
        if val:
            sets.append(set(DIM_INDEX[dim].get(val.strip().lower(), [])))
    if not sets:
        return sorted(RECORDS)
    return sorted(set.intersection(*sets))


@app.get("/", include_in_schema=False)
def root():
    # Humans get the record browser; developers can still reach /docs.
    return RedirectResponse("/ui")


@app.get("/ui", include_in_schema=False)
def ui():
    return FileResponse(UI_DIR / "index.html")


@app.get("/seals")
def list_seals(
    limit: int = Query(20, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    material: str | None = None,
    colour: str | None = None,
    mound: str | None = None,
    type_: str | None = Query(None, alias="type"),
    site: str | None = None,
):
    ids = apply_filters(material, colour, mound, type_, site)
    page = ids[offset:offset + limit]
    return {"total": len(ids), "limit": limit, "offset": offset,
            "records": [RECORDS[i] for i in page]}


@app.get("/seals/{seal_id}")
def get_seal(seal_id: str):
    r = RECORDS.get(seal_id)
    if r is None:
        raise HTTPException(404, "no such record")
    return r


@app.get("/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=200)):
    toks = tokens(q)
    if not toks:
        raise HTTPException(400, "empty query")
    postings = [TEXT_INDEX.get(t, {}) for t in toks]
    if any(not p for p in postings):
        return {"query": q, "total": 0, "records": []}
    common = set(postings[0])
    for p in postings[1:]:
        common &= set(p)
    scored = sorted(common, key=lambda rid: sum(p[rid] for p in postings),
                     reverse=True)
    return {"query": q, "total": len(scored),
            "records": [RECORDS[i] for i in scored[:limit]]}


@app.get("/stats")
def stats():
    out: dict = {"total": len(RECORDS),
                 "flagged": sum(1 for r in RECORDS.values()
                                if r.get("parse_flags"))}
    for dim in DIMS:
        out["by_" + dim] = {v: len(ids)
                            for v, ids in sorted(DIM_INDEX[dim].items())}
    return out


@app.get("/export")
def export(format: str = Query("json", pattern="^(json|csv)$")):
    recs = [RECORDS[i] for i in sorted(RECORDS)]
    if format == "json":
        buf = io.StringIO()
        for r in recs:
            buf.write(json.dumps(r, ensure_ascii=False) + "\n")
        buf.seek(0)
        return StreamingResponse(iter([buf.read()]),
                                 media_type="application/x-ndjson",
                                 headers={"Content-Disposition":
                                          "attachment; filename=dhi-seals.jsonl"})
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "seal_no", "site", "size_raw", "depth_raw", "type_raw",
                "material", "colour", "mound", "field_no", "source"])
    for r in recs:
        w.writerow([r["id"], r["seal_no"], r["site"], r["size_raw"],
                    r["depth_raw"], r["type_raw"], r["material"], r["colour"],
                    r["mound"], r["field_no"],
                    r["provenance"]["source"]])
    buf.seek(0)
    return StreamingResponse(iter([buf.read()]), media_type="text/csv",
                             headers={"Content-Disposition":
                                      "attachment; filename=dhi-seals.csv"})
