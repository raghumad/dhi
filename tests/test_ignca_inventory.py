"""Tests for the SITE-5 IGNCA/IA inventory (ingest/ignca_inventory.yaml).

The inventory is generated from a snapshot of IA's in.gov.ignca.* metadata
(data/ignca_inventory.json, gitignored). These tests enforce the report's
contract and its reproducibility: re-running the match must yield the same
report byte-for-byte, so a stale or hand-edited inventory fails loudly.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
INGEST = REPO / "ingest"
REPORT = INGEST / "ignca_inventory.yaml"
SNAPSHOT = REPO / "data" / "ignca_inventory.json"

sys.path.insert(0, str(REPO))
from ingest.ignca_inventory import LOOSE, WANT, matches, norm  # noqa: E402


@pytest.fixture(scope="module")
def report():
    assert REPORT.exists(), "ingest/ignca_inventory.yaml missing - run match"
    return REPORT.read_text()


def test_report_header_names_query_and_date(report):
    assert "identifier:in.gov.ignca*" in report
    assert re.search(r"snapshot: \d{4}-\d{2}-\d{2}", report)


def test_entries_have_hit_or_miss_status(report):
    # Strip the leading comment lines, then parse as YAML.
    body = "\n".join(
        ln for ln in report.splitlines() if not ln.startswith("#"))
    data = yaml.safe_load(body)
    assert data, "inventory report is empty"
    for sid, entry in data.items():
        assert entry.get("status", "").startswith(("hit", "miss")), \
            f"{sid}: bad status {entry.get('status')!r}"
        if entry["status"].startswith("hit"):
            for cand in entry.get("candidates", []):
                assert cand["id"].startswith("in.gov.ignca."), \
                    f"{sid}: bad candidate id {cand['id']!r}"


def test_report_is_reproducible_from_snapshot():
    if not SNAPSHOT.exists():
        pytest.skip("no local IA snapshot; run "
                    "python ingest/ignca_inventory.py fetch")
    before = REPORT.read_text()
    r = subprocess.run(
        [sys.executable, str(INGEST / "ignca_inventory.py"), "match"],
        capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, r.stderr
    assert REPORT.read_text() == before, \
        "ignca_inventory.yaml is stale or was hand-edited - re-run match"


# --- Matcher semantics: the rules that keep hits honest --------------------

def test_word_keywords_need_word_boundaries():
    # "ur" must not match "culture" — the classic false positive.
    assert not matches(norm("Culture of the Indus seals"), [], ["ur"])
    assert not matches(norm("agriculture in antiquity"), [], ["ur"])
    assert matches(norm("Seals of Ancient Indian style found at Ur"),
                   [], ["ur"])
    assert matches(norm("Ur excavations"), [], ["ur"])


def test_must_keywords_are_substrings_all_required():
    assert matches(norm("Lothal excavations, S.R. Rao"), ["lothal", "rao"], [])
    assert not matches(norm("Lothal excavations"), ["lothal", "rao"], [])
    assert not matches(norm("Rao on Harappa"), ["lothal", "rao"], [])


def test_hit_miss_semantics(report):
    # Misses are exactly "miss" with no candidates; hits carry candidates.
    body = "\n".join(
        ln for ln in report.splitlines() if not ln.startswith("#"))
    data = yaml.safe_load(body)
    for sid, entry in data.items():
        status = entry.get("status", "")
        if status == "miss":
            assert "candidates" not in entry, f"{sid}: miss with candidates"
        else:
            assert status.startswith("hit ("), f"{sid}: bad status {status!r}"
            cands = entry.get("candidates", [])
            assert cands, f"{sid}: hit with no candidates"


def test_rule_ids_are_unique():
    sids = [sid for sid, _, _ in WANT + LOOSE]
    assert len(sids) == len(set(sids)), "duplicate rule id in WANT/LOOSE"
