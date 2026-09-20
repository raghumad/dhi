#!/usr/bin/env python3
"""Fetch Indus-world seals from the Metropolitan Museum of Art Collection API.

The Met's Collection API is public (no key) and every object used here is
flagged isPublicDomain by the Met, so images and metadata are free to reuse.
This module materializes the source's artifacts:

    data/artifacts/met_objects.json   - full object records for the query
    data/artifacts/images-met/<id>.jpg - primary image per object
    data/artifacts/met_manifest.json  - query, fetch date, per-file SHA-256

Unlike static-file artifacts (fetch.py), an API response cannot be hash-pinned
in advance: the manifest records the hashes at fetch time, and re-runs are
idempotent -- if the manifest's hash still matches the on-disk JSON, nothing
is re-downloaded. To force a re-fetch, delete met_objects.json + manifest.

Only objects with isPublicDomain=true AND a primary image are kept. Objects
whose culture is not Indus-related are still kept (the Met's "indus seal"
search also surfaces Mesopotamian and BMAC seals); each record carries its
museum-given culture label so the catalog never misattributes them.

Usage:
    python ingest/fetch_met.py
"""
import datetime
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://collectionapi.metmuseum.org/public/collection/v1"
QUERY = "indus seal"
SEARCH_URL = f"{API}/search?q={urllib.request.quote(QUERY)}"

OUT_JSON = ROOT / "data/artifacts/met_objects.json"
IMG_DIR = ROOT / "data/artifacts/images-met"
MANIFEST = ROOT / "data/artifacts/met_manifest.json"

CHUNK = 1024 * 1024
POLITENESS_DELAY = 0.2  # seconds between object requests


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "dhi-ingest/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "dhi-ingest/0.1"})
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as f:
        while True:
            chunk = resp.read(CHUNK)
            if not chunk:
                break
            f.write(chunk)
    tmp.replace(dest)


def main() -> None:
    # Idempotency: manifest pins the hashes we fetched last time.
    if MANIFEST.is_file() and OUT_JSON.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if manifest.get("objects_sha256") == sha256_of(OUT_JSON):
            print(f"  ok (cached) met_objects.json "
                  f"({manifest['kept']} objects)")
            return
        print("  met_objects.json changed since last fetch; re-fetching")

    print(f"  querying Met API: {QUERY!r} ...")
    search = get_json(SEARCH_URL)
    object_ids = search.get("objectIDs") or []
    print(f"  {len(object_ids)} object IDs returned")

    objects = []
    missing = []
    for i, oid in enumerate(object_ids):
        try:
            obj = get_json(f"{API}/objects/{oid}")
        except urllib.error.HTTPError as e:
            # Search index can be stale; a 404 means the object record is
            # gone. Record it and move on -- never fail the whole fetch.
            print(f"    [{i+1}/{len(object_ids)}] {oid} -> HTTP {e.code}, skipped")
            missing.append(oid)
            continue
        objects.append(obj)
        kept = "keep" if obj.get("isPublicDomain") and obj.get("primaryImage") else "skip"
        print(f"    [{i+1}/{len(object_ids)}] {oid} "
              f"{obj.get('title','?')[:50]!r} -> {kept}")
        time.sleep(POLITENESS_DELAY)

    kept_objs = [o for o in objects
                 if o.get("isPublicDomain") and o.get("primaryImage")]
    print(f"  kept {len(kept_objs)} public-domain objects with images")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(objects, indent=1, ensure_ascii=False),
                        encoding="utf-8")

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    images = {}
    for o in kept_objs:
        oid = o["objectID"]
        # Prefer the smaller web image; originals are multi-MB.
        url = o.get("primaryImageSmall") or o["primaryImage"]
        dest = IMG_DIR / f"met-{oid}.jpg"
        if dest.is_file():
            print(f"    ok (cached) {dest.name}")
        else:
            print(f"    downloading {dest.name} ...")
            download(url, dest)
            time.sleep(POLITENESS_DELAY)
        images[str(oid)] = {
            "file": f"images-met/met-{oid}.jpg",
            "sha256": sha256_of(dest),
            "source_url": url,
        }

    manifest = {
        "source": "met",
        "query": QUERY,
        "search_url": SEARCH_URL,
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "returned": len(object_ids),
        "missing": missing,
        "kept": len(kept_objs),
        "objects_sha256": sha256_of(OUT_JSON),
        "images": images,
        "note": ("Only isPublicDomain objects with a primary image are kept. "
                 "Culture labels are the Met's own; non-Indus cultures "
                 "(Mesopotamian, BMAC) are kept and labeled, not filtered."),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"  fetch complete: met ({len(kept_objs)} objects)")


if __name__ == "__main__":
    main()
