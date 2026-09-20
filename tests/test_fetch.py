"""Tests for ingest/fetch.py: hash-verified artifact acquisition."""
import hashlib
import re
from pathlib import Path

import pytest
import yaml

from ingest import fetch as fv

ROOT = Path(__file__).resolve().parent.parent


def test_sha256_of():
    p = ROOT / "ingest" / "sources.yaml"
    assert fv.sha256_of(p) == hashlib.sha256(p.read_bytes()).hexdigest()


def test_sources_yaml_manifest_valid():
    sources = fv.load_sources()
    assert sources, "no sources declared"
    ids = [s["id"] for s in sources]
    assert len(ids) == len(set(ids)), "duplicate source ids"
    for s in sources:
        assert s.get("parser"), f"{s['id']}: no parser declared"
        for a in s.get("artifacts", []):
            assert a.get("url", "").startswith("https://"), f"{a.get('name')}: bad url"
            assert re.fullmatch(r"[0-9a-f]{64}", a.get("sha256", "").lower()), \
                f"{a.get('name')}: sha256 must be 64 hex chars"
            assert a.get("path"), f"{a.get('name')}: no path"


def test_fetch_skips_cached_matching_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(fv, "ROOT", tmp_path)
    dest = tmp_path / "data" / "a.txt"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"hello")
    digest = hashlib.sha256(b"hello").hexdigest()
    got = fv.fetch_artifact({"name": "t", "url": "https://example.invalid/x",
                             "sha256": digest, "path": "data/a.txt"})
    assert got == dest  # no download attempted


def test_fetch_rejects_hash_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(fv, "ROOT", tmp_path)
    dest = tmp_path / "data" / "a.txt"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"tampered")
    with pytest.raises(SystemExit):
        fv.fetch_artifact({"name": "t", "url": "https://example.invalid/x",
                           "sha256": "0" * 64, "path": "data/a.txt"})
