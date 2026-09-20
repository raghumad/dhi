"""Museum-source ingestion tests (source: met).

Covers the parse_met contract and the API's museum handling:
records are honestly labeled (provenance_type, culture passthrough),
images are served locally, and heterogeneous record shapes don't break
export or search.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
RECORDS = Path("data/records/met_seals.jsonl")


def _met_records():
    return [json.loads(ln) for ln in
            RECORDS.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_parse_met_records_have_stable_ids():
    recs = _met_records()
    assert len(recs) > 0
    ids = [r["id"] for r in recs]
    assert len(set(ids)) == len(ids)  # unique
    assert all(i.startswith("met-") for i in ids)


def test_parse_met_provenance_is_honest():
    for r in _met_records():
        assert r["provenance_type"] == "museum"
        assert r["museum"] == "Metropolitan Museum of Art, New York"
        assert r["museum_url"].startswith("https://www.metmuseum.org/")
        assert r["license"] == "Public domain (Met Open Access)"
        # no excavation context is invented
        assert r["site"] is None
        assert r["excavation"] is None
        # culture is the Met's label, passed through (None when the Met gives none)
        assert "culture" in r


def test_api_serves_met_record():
    recs = _met_records()
    rid = recs[0]["id"]
    r = client.get(f"/seals/{rid}")
    assert r.status_code == 200
    body = r.json()
    assert body["image_url"] == f"/images/museum/{rid}.jpg"
    assert body["image_status"] == "museum"


def test_api_serves_met_image():
    recs = _met_records()
    rid = recs[0]["id"]
    r = client.get(f"/images/museum/{rid}.jpg")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"


def test_api_rejects_met_image_traversal():
    r = client.get("/images/museum/../sources.yaml")
    assert r.status_code == 404
    r = client.get("/images/museum/met-nope.jpg")
    assert r.status_code == 404


def test_search_finds_met_records():
    # "bactria" appears in BMAC culture labels of the met source
    r = client.get("/search", params={"q": "bactria"})
    assert r.status_code == 200
    ids = [h["id"] for h in r.json()["records"]]
    assert any(i.startswith("met-") for i in ids)
