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
        # parser may be null for a source whose plates are ingested but
        # whose catalog records are not yet parsed (e.g. Marshall 1931:
        # plates done, Vol. II tabulation parser pending). Such sources
        # must not be served as catalog records until a parser exists.
        assert "parser" in s, f"{s['id']}: no parser key"
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


def test_download_retries_transient_500_then_succeeds(tmp_path, monkeypatch):
    import io
    import urllib.error
    calls = []

    class FakeResp:
        def __init__(self, data: bytes):
            self._buf = io.BytesIO(data)
        def read(self, n=-1):
            return self._buf.read(n)
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.HTTPError(req.full_url, 500, "Internal Server Error", {}, None)
        return FakeResp(b"data-bytes")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)  # no waiting in tests
    dest = tmp_path / "out.part"
    fv.download("https://example.invalid/x", dest)
    assert dest.read_bytes() == b"data-bytes"
    assert len(calls) == 3


def test_download_does_not_retry_404(tmp_path, monkeypatch):
    import urllib.error
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(1)
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(urllib.error.HTTPError):
        fv.download("https://example.invalid/x", tmp_path / "out.part")
    assert len(calls) == 1  # no retry on client errors


def test_download_gives_up_after_attempts(tmp_path, monkeypatch):
    import urllib.error
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(1)
        raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(urllib.error.HTTPError):
        fv.download("https://example.invalid/x", tmp_path / "out.part", attempts=2)
    assert len(calls) == 2
