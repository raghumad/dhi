#!/usr/bin/env python3
"""Generic artifact acquisition for Dhi ingestion.

Reads ingest/sources.yaml and materializes every declared artifact:
download from URL, verify SHA-256, write to its path. Fully generic --
there is no per-source code here. A new source is a new YAML entry.

Usage:
    python ingest/fetch.py            # fetch all sources
    python ingest/fetch.py vats1940   # fetch one source

Idempotent: artifacts already present with a matching hash are skipped.
A hash mismatch on an existing file is a hard error (never silently
overwrite); delete the file and re-run to re-fetch.
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCES_YAML = Path(__file__).resolve().parent / "sources.yaml"

CHUNK = 1024 * 1024


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest_tmp: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "dhi-ingest/0.1"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest_tmp, "wb") as f:
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            f.write(chunk)


def fetch_artifact(spec: dict) -> Path:
    dest = ROOT / spec["path"]
    want = spec["sha256"].lower()
    if dest.is_file():
        got = sha256_of(dest)
        if got == want:
            print(f"  ok (cached) {spec['name']} -> {spec['path']}")
            return dest
        raise SystemExit(
            f"HASH MISMATCH on existing {dest}\n"
            f"  expected {want}\n  got      {got}\n"
            f"Delete the file and re-run to re-fetch.")
    print(f"  downloading {spec['name']} ...")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    download(spec["url"], tmp)
    got = sha256_of(tmp)
    if got != want:
        tmp.unlink(missing_ok=True)
        raise SystemExit(
            f"HASH MISMATCH on downloaded {spec['name']}\n"
            f"  expected {want}\n"
            f"  got      {got}\n"
            f"The upstream file changed. Refusing to ingest.")
    tmp.rename(dest)
    print(f"  ok {spec['name']} -> {spec['path']}")
    return dest


def fetch_source(source: dict) -> None:
    print(f"source: {source['id']}")
    for spec in source.get("artifacts", []):
        fetch_artifact(spec)


def load_sources() -> list[dict]:
    with open(SOURCES_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def main(argv: list[str]) -> None:
    only = argv[1] if len(argv) > 1 else None
    sources = load_sources()
    if only:
        sources = [s for s in sources if s["id"] == only]
        if not sources:
            raise SystemExit(f"unknown source: {only}")
    for source in sources:
        fetch_source(source)
    print("fetch complete")


if __name__ == "__main__":
    main(sys.argv)
