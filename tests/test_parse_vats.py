"""Tests for ingest/parse_vats.py.

Covers the content-classification rules (parse_row), the seal-number chain
helpers, and the determinism/integrity guarantees the requirements demand:
re-running ingestion over unchanged sources reproduces identical records
(R-I2), every derived field names its source artifact (R-D5), and nothing
unmapped is silently dropped (R-I4).
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from ingest import parse_vats as pv

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "data" / "artifacts" / "vats1940_djvu.txt"
RECORDS = ROOT / "data" / "records" / "vats1940_seals.jsonl"


# --- seal-number helpers -------------------------------------------------


def test_norm_figureno_plain():
    assert pv.norm_figureno("368") == 368
    assert pv.norm_figureno(" 60 ") == 60


def test_norm_figureno_ocr_confusions():
    # common OCR misreads of digits are repaired
    assert pv.norm_figureno("l23") == 123  # lowercase L -> 1
    assert pv.norm_figureno("B68") == 868  # B -> 8


def test_norm_figureno_rejects_non_number_lines():
    assert pv.norm_figureno("1.0 x 0.9") is None  # size
    assert pv.norm_figureno("6' 10\"") is None  # depth
    assert pv.norm_figureno("abcde") is None  # too long / not digits
    assert pv.norm_figureno("") is None


def test_longest_chain_skips_outliers():
    cands = [(0, 60, "60"), (1, 61, "61"), (2, 9999, "9999"), (3, 62, "62")]
    chain = pv.longest_chain(cands)
    assert [v for _, v, _ in chain] == [60, 61, 62]


def test_restore_hundreds():
    # dropped leading digit: 68 after 367 must be 368
    assert pv._restore_hundreds(68, 367) == 368
    # already forward: untouched
    assert pv._restore_hundreds(369, 367) == 369


# --- row classification --------------------------------------------------


def test_parse_row_clean():
    cells = ["251", "1.15 x 1.0", "7' 3\"", "a",
             "White", "--", "--", "F", "H 5974"]
    row = pv.parse_row(cells)
    assert row["size_raw"] == "1.15 x 1.0"
    assert row["depth_raw"] == "7' 3\""
    assert row["type_raw"] == "a"
    assert row["material"] == "steatite"
    assert row["colour"] == "White"
    assert row["mound"] == "F"
    assert row["field_no"] == "H 5974"
    assert row["unmapped"] == []
    assert row["parse_flags"] == []


def test_parse_row_bare_material_name():
    # material sub-column with no colour text: still a material, never a field no
    cells = ["102", "1.0 x 0.9", "5' 0\"", "a",
             "--", "--", "Pottery", "F", "1154c"]
    row = pv.parse_row(cells)
    assert row["material"] == "pottery"
    assert row["field_no"] == "1154c"
    assert "Pottery" not in row["unmapped"]


def test_parse_row_trailing_word_without_digit_is_not_field_no():
    # regression: "Pottery" once leaked into field_no on a header-contaminated row
    cells = ["101", "1 x 1", "6' 10\"", "a",
             "White", "--", "--", "F", "Pottery"]
    row = pv.parse_row(cells)
    assert row["field_no"] == ""
    assert row["material"] == "steatite"


def test_parse_row_garbage_trailing_cell_flagged_not_silent():
    cells = ["210", "1 x 1", "5' 0\"", "a",
             "White", "--", "--", "F", "Afiie"]
    row = pv.parse_row(cells)
    assert row["field_no"] == ""
    assert "field-no-suspect" in row["parse_flags"]
    assert "Afiie" in row["unmapped"]  # preserved, not discarded


def test_parse_row_merged_row_suspect():
    cells = ["300", "1 x 1", "2 x 2", "5' 0\"", "6' 0\"", "a",
             "White", "F", "H 1"]
    row = pv.parse_row(cells)
    assert "merged-row-suspect" in row["parse_flags"]


def test_split_merged_recovers_swallowed_row():
    # seal 102's anchor survived only as an ordinary cell inside 101's row
    cells = ["101", "1 x 1", "5' 0\"", "a", "White", "--", "--", "F", "H 1",
             "102", "1.2 x 1.1", "6' 0\"", "a", "Greenish", "--", "--", "F",
             "H 2"]
    parts = pv.split_merged(101, cells)
    assert len(parts) == 2
    assert parts[0][0] == 101
    assert parts[1][0] == 102
    assert len(parts[0][1]) >= 5 and len(parts[1][1]) >= 5


def test_split_merged_does_not_split_on_field_numbers():
    # a numeric-looking field number at row end must not split the row
    cells = ["101", "1 x 1", "5' 0\"", "a", "White", "--", "--", "F", "102"]
    assert pv.split_merged(101, cells) == [(101, cells)]


# --- determinism and record integrity ------------------------------------


def _run_parser():
    subprocess.run([sys.executable, "ingest/parse_vats.py"],
                   cwd=ROOT, check=True,
                   capture_output=True, text=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ingest_is_deterministic():
    """R-I2: re-running over unchanged sources reproduces identical records."""
    committed = RECORDS.read_bytes()
    _run_parser()
    once = RECORDS.read_bytes()
    _run_parser()
    twice = RECORDS.read_bytes()
    assert _sha256(RECORDS) == hashlib.sha256(once).hexdigest() == \
        hashlib.sha256(twice).hexdigest()
    assert once == committed  # matches the snapshot in the repo


def test_parser_is_cwd_independent(tmp_path):
    """R-I1: the ingest command works wherever it is started from."""
    committed = RECORDS.read_bytes()
    subprocess.run([sys.executable, str(ROOT / "ingest/parse_vats.py")],
                   cwd=tmp_path, check=True,
                   capture_output=True, text=True)
    assert RECORDS.read_bytes() == committed


def test_artifact_stored_byte_identical():
    """The committed OCR artifact is what the records cite."""
    recs = [json.loads(line) for line in
            RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert recs, "no records parsed"
    digest = _sha256(ARTIFACT)
    for r in recs:
        assert r["provenance"]["artifact_sha256"] == digest


def test_records_have_stable_ids_and_schema():
    recs = [json.loads(line) for line in
            RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [r["id"] for r in recs]
    assert len(ids) == len(set(ids)), "duplicate record ids"
    for r in recs:
        assert re.fullmatch(r"vats1940-\d+[a-z]?", r["id"])
        assert isinstance(r["figure_no"], int)
        assert r["site"] == "Harappa"
        assert isinstance(r["parse_flags"], list)
        assert isinstance(r["unmapped"], list)
        assert "Tabulation of Seals" in r["provenance"]["source"]


def test_no_field_no_is_a_bare_material_word():
    recs = [json.loads(line) for line in
            RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]
    bad = [r["id"] for r in recs
           if (r["field_no"] or "").strip().lower() in pv.MATERIAL_NAMES]
    assert bad == []


def test_flagged_records_are_quarantined_not_silent():
    """Every record the parser distrusted says so in parse_flags."""
    recs = [json.loads(line) for line in
            RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]
    flagged = [r for r in recs if r["parse_flags"]]
    assert flagged, "expected some quarantined records on real OCR"
    for r in flagged:
        assert r["parse_flags"], r["id"]
