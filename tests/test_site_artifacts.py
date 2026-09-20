"""Integrity tests for pinned site-evidence artifacts (SITE-2).

Each source in ingest/site_sources.yaml may declare artifacts:
{name, description, url, sha256, path, media_type, ...}. These tests enforce
the contract and verify that every locally present artifact still matches its
registered SHA-256. Artifacts not downloaded locally are skipped (CI does not
fetch multi-hundred-MB PDFs); run ingest/fetch_site_artifacts.py to materialize
them.
"""
import hashlib
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
INGEST = REPO / "ingest"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


@pytest.fixture(scope="module")
def registry():
    return yaml.safe_load((INGEST / "site_sources.yaml").read_text())["sources"]


@pytest.fixture(scope="module")
def artifacts(registry):
    out = []
    for sid, src in registry.items():
        for a in src.get("artifacts", []):
            out.append((sid, a))
    return out


def test_artifact_entries_wellformed(artifacts):
    assert artifacts, "no pinned artifacts in the registry"
    for sid, a in artifacts:
        for key in ("name", "description", "url", "sha256", "path",
                    "media_type"):
            assert a.get(key), f"{sid}/{a.get('name')}: missing {key}"
        assert HEX64.match(a["sha256"]), f"{sid}/{a['name']}: bad sha256"
        assert a["url"].startswith("http"), f"{sid}/{a['name']}: bad url"
        assert a["path"].startswith("data/artifacts/"), \
            f"{sid}/{a['name']}: path outside data/artifacts/"


def test_no_duplicate_artifact_paths(artifacts):
    paths = [a["path"] for _, a in artifacts]
    assert len(paths) == len(set(paths)), "duplicate artifact paths"


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def test_local_artifacts_match_registered_hashes(artifacts):
    checked, missing = 0, []
    for sid, a in artifacts:
        p = REPO / a["path"]
        if not p.exists():
            missing.append(f"{sid}/{a['name']}")
            continue
        assert _sha256_of(p) == a["sha256"], \
            f"{sid}/{a['name']}: LOCAL FILE HASH MISMATCH - evidence compromised"
        checked += 1
    print(f"\nhash-verified {checked} local artifacts; "
          f"{len(missing)} not downloaded (skipped)")
    assert checked > 0, "no pinned artifacts present locally to verify"
