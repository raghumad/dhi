#!/usr/bin/env python3
"""Dhi ingestion pipeline: fetch -> extract -> crop -> parse.

Materializes the entire dataset from declarative manifests. Nothing under
data/ is committed to git; this script (re)builds it:

    python ingest/build.py              # full pipeline, all sources
    python ingest/build.py vats1940     # one source
    python ingest/build.py --skip-fetch # reuse already-fetched artifacts

Stages per source:
    1. fetch:    ingest/fetch.py            (generic: URL + SHA-256, no per-source code)
    2. extract:  source-specific (vats1940: PDF pages -> plate scans)
    3. crop:     ingest/crop_figures.py     (plate scans -> figure crops + boxes.json)
    4. parse:    ingest/parse_vats.py       (OCR text -> data/records/*.jsonl)

Each stage is idempotent: outputs already present are skipped, so re-running
is cheap. To force a stage, delete its outputs first.

Adding source #2: add its entry to sources.yaml, write its parser module,
and register its build steps in SOURCE_STEPS below. No framework changes.
"""
import runpy
import sys
from pathlib import Path

INGEST = Path(__file__).resolve().parent
ROOT = INGEST.parent
sys.path.insert(0, str(INGEST))

# source id -> ordered build steps after fetch.
# Each step is a module under ingest/ run as __main__.
SOURCE_STEPS: dict[str, list[str]] = {
    "vats1940": ["extract_plates", "crop_figures", "parse_vats"],
}


def run_step(module: str) -> None:
    print(f"--- step: {module} ---")
    runpy.run_module(module, run_name="__main__")


def build_source(source_id: str, skip_fetch: bool) -> None:
    import yaml
    with open(INGEST / "sources.yaml", encoding="utf-8") as f:
        ids = [s["id"] for s in yaml.safe_load(f)["sources"]]
    if source_id not in ids:
        raise SystemExit(f"unknown source: {source_id}")
    if not skip_fetch:
        import fetch
        fetch.main(["fetch.py", source_id])
    for step in SOURCE_STEPS.get(source_id, []):
        run_step(step)
    print(f"build complete: {source_id}")


def main(argv: list[str]) -> None:
    args = [a for a in argv[1:] if not a.startswith("--")]
    skip_fetch = "--skip-fetch" in argv[1:]
    if args:
        for sid in args:
            build_source(sid, skip_fetch)
    else:
        import yaml
        with open(INGEST / "sources.yaml", encoding="utf-8") as f:
            sources = yaml.safe_load(f)["sources"]
        for s in sources:
            build_source(s["id"], skip_fetch)


if __name__ == "__main__":
    main(sys.argv)
