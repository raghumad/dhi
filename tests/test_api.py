"""API smoke tests (docs/requirements.md R-A1..R-A4).

Exercises the HTTP contract a future PWA will build on: listing with
pagination and filters, single-record retrieval with provenance, search,
stats, and bulk export.
"""
import json

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_list_seals_paginates():
    r = client.get("/seals", params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 300
    assert len(body["records"]) == 5
    assert body["limit"] == 5 and body["offset"] == 0


def test_list_seals_offset():
    first = client.get("/seals", params={"limit": 1, "offset": 0}).json()
    second = client.get("/seals", params={"limit": 1, "offset": 1}).json()
    assert first["records"][0]["id"] != second["records"][0]["id"]


def test_filter_material_and_mound():
    r = client.get("/seals", params={"material": "faience", "mound": "F"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    for rec in body["records"]:
        assert rec["material"] == "faience"
        assert rec["mound"] == "F"


def test_get_seal_includes_provenance():
    r = client.get("/seals/vats1940-251")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "vats1940-251"
    assert body["seal_no"] == 251
    assert "artifact_sha256" in body["provenance"]


def test_get_seal_404():
    assert client.get("/seals/vats1940-99999").status_code == 404


def test_search_finds_material_terms():
    r = client.get("/search", params={"q": "steatite"})
    assert r.status_code == 200
    assert r.json()["total"] > 0


def test_search_motif_absent_from_tabulation():
    # motifs (unicorn, bull) live in the book's prose, not the tabulation:
    # honest zero, not a silent failure
    r = client.get("/search", params={"q": "unicorn"})
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_stats_consistent_with_listing():
    stats = client.get("/stats").json()
    listing = client.get("/seals", params={"limit": 1}).json()
    assert stats["total"] == listing["total"]
    assert stats["flagged"] > 0
    assert "by_material" in stats


def test_export_json_round_trips():
    r = client.get("/export", params={"format": "json"})
    assert r.status_code == 200
    lines = [ln for ln in r.text.splitlines() if ln.strip()]
    rec = json.loads(lines[0])
    assert rec["id"].startswith("vats1940-")
    assert len(lines) == client.get("/stats").json()["total"]


def test_export_csv_has_header():
    r = client.get("/export", params={"format": "csv"})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    header = r.text.splitlines()[0]
    assert header.startswith("id,seal_no,site,")
    # R-A2: full source citation per record, not truncated
    assert "Public domain." in r.text
