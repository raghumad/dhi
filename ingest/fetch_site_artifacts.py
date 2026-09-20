#!/usr/bin/env python3
"""Fetch pinned artifacts for the site-source registry.

Reads ingest/site_sources.yaml and materializes every declared artifact:
download from URL, verify SHA-256, write to its path. Same contract as
ingest/fetch.py (the seal pipeline), applied to site evidence.

Usage:
    python ingest/fetch_site_artifacts.py              # fetch all
    python ingest/fetch_site_artifacts.py unesco-whc    # fetch one source

Idempotent: artifacts already present with a matching hash are skipped.
A hash mismatch on an existing file is a hard error (never silently
overwrite); delete the file and re-run to re-fetch.

Artifacts live under data/artifacts/sites/ (gitignored, like all of data/).
"""
import hashlib
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = Path(__file__).resolve().parent / "site_sources.yaml"

CHUNK = 1024 * 1024
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest_tmp: Path, attempts: int = 4) -> None:
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r, \
                    open(dest_tmp, "wb") as f:
                while True:
                    chunk = r.read(CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
            return
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                raise RuntimeError(f"{url}: HTTP {e.code} (not retried)")
            last_exc = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_exc = e
        time.sleep(2 ** attempt)
    raise RuntimeError(f"{url}: failed after {attempts} attempts: {last_exc}")


def fetch_source(source_id: str, source: dict) -> None:
    for art in source.get("artifacts", []):
        dest = ROOT / art["path"]
        tmp = dest.with_suffix(dest.suffix + ".part")
        if dest.exists():
            if sha256_of(dest) == art["sha256"]:
                print(f"  ok (cached): {art['name']}")
                continue
            raise RuntimeError(
                f"{dest}: hash mismatch - refusing to overwrite; "
                "delete it and re-run to re-fetch")
        print(f"  fetching: {art['name']} <- {art['url']}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        download(art["url"], tmp)
        got = sha256_of(tmp)
        if got != art["sha256"]:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(
                f"{art['url']}: sha256 mismatch\n  expected {art['sha256']}\n"
                f"  got      {got}")
        tmp.rename(dest)
        print(f"  pinned: {dest} ({dest.stat().st_size} bytes)")


def main(argv: list[str]) -> int:
    registry = yaml.safe_load(REGISTRY.read_text())["sources"]
    only = argv[1] if len(argv) > 1 else None
    if only and only not in registry:
        print(f"unknown source: {only}", file=sys.stderr)
        return 1
    for sid, src in registry.items():
        if only and sid != only:
            continue
        print(f"{sid}:")
        fetch_source(sid, src)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
