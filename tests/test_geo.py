"""Georeferencing tests: plan transform, mound-area join, /seals/nearby.

Covers the geographic provenance added on the feature/seal-geolocation
branch: Vats 1940 Pl. I georeferenced via the 1000-ft survey grid, the
north arrow, and the OSM Harappa Museum building as anchor.
"""
import json
import math
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ingest"))

import georef
from api.main import app, haversine_km

client = TestClient(app)


# --- transform sanity -------------------------------------------------------
def test_transform_anchor_is_museum():
    lat, lon = georef.norm_to_wgs84(480, 829)
    assert abs(lat - 30.6247339) < 0.0005
    assert abs(lon - 72.8646927) < 0.0005


def test_transform_scale_matches_1000ft_grid():
    # 1000 ft of easting should span ~242 px -> ~304.8 m on the ground.
    lat1, lon1 = georef.plan_px_to_wgs84(500, 600)
    lat2, lon2 = georef.plan_px_to_wgs84(742, 600)
    dlat_m = (lat2 - lat1) * 110540
    dlon_m = (lon2 - lon1) * 111320 * math.cos(math.radians(lat1))
    dist = math.hypot(dlat_m, dlon_m)
    assert abs(dist - 304.8) < 15  # within 5%


def test_haversine_known_distance():
    # Museum to village node ~1.06 km (OSM).
    d = haversine_km(30.6247339, 72.8646927, 30.6330564, 72.8701682)
    assert abs(d - 1.06) < 0.05


# --- mound areas ------------------------------------------------------------
def test_areas_geojson_valid():
    fc = georef.load_areas_geojson()
    assert fc["type"] == "FeatureCollection"
    by_id = {f["properties"]["place_id"]: f["properties"] for f in fc["features"]}
    assert "harappa" in by_id  # site root
    for area in ("F", "P", "AB", "E", "D", "G", "J", "H"):
        pid = f"harappa:area:{area}"
        assert pid in by_id, pid
        assert by_id[pid]["level"] == "area"
        assert by_id[pid]["parent_id"] == "harappa"
    assert by_id["harappa"]["level"] == "site"
    for f in fc["features"]:
        p = f["properties"]
        if p["level"] == "area":
            ring = f["geometry"]["coordinates"][0]
            assert ring[0] == ring[-1]  # closed
            assert len(ring) >= 4
        lon, lat = p["centroid"]
        assert 30.60 < lat < 30.65
        assert 72.85 < lon < 72.88


def test_granary_centroid_near_mound_f():
    # "Mound P" is the Great Granary complex on Mound F: its centroid must
    # lie close to F's centroid (well within F's ~250 m uncertainty).
    fc = georef.load_areas_geojson()
    by_id = {f["properties"]["place_id"]: f["properties"] for f in fc["features"]}
    lon_f, lat_f = by_id["harappa:area:F"]["centroid"]
    lon_p, lat_p = by_id["harappa:area:P"]["centroid"]
    assert haversine_km(lat_f, lon_f, lat_p, lon_p) < 0.25


# --- record join --------------------------------------------------------------
def _vats_records():
    path = ROOT / "data" / "records" / "vats1940_seals.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_records_carry_location_block():
    recs = _vats_records()
    assert recs, "no vats records built"
    for r in recs:
        loc = r.get("location")
        assert loc is not None, r["id"]
        assert loc["level"] in georef.LEVELS, r["id"]
        assert loc["place_id"].startswith("harappa"), r["id"]
        assert isinstance(loc["latitude"], float)
        assert isinstance(loc["longitude"], float)
        assert loc["uncertainty_m"] > 0
        assert "georef.py" in loc["georef_source"]


def test_mound_p_records_resolve_to_granary():
    recs = [r for r in _vats_records() if r.get("mound") == "P"]
    assert recs, "expected some mound=P records"
    for r in recs:
        loc = r["location"]
        assert loc["level"] == "area"
        assert loc["place_id"] == "harappa:area:P"
        assert "Granary" in loc["place_name"]


def test_unmapped_mound_falls_back_to_site():
    recs = [r for r in _vats_records() if not r.get("mound")]
    assert recs
    for r in recs:
        assert r["location"]["level"] == "site"
        assert r["location"]["place_id"] == "harappa"


# --- /seals/nearby --------------------------------------------------------------
def test_nearby_returns_sorted_hits_with_distance():
    r = client.get("/seals/nearby", params={"lat": 30.6323, "lon": 72.8612,
                                            "radius_km": 0.5, "limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    dists = [rec["distance_km"] for rec in body["records"]]
    assert dists == sorted(dists)
    assert all(d <= 0.5 for d in dists)
    # closest hits should be granary (P) seals
    assert body["records"][0]["mound"] == "P"


def test_nearby_empty_radius():
    # mid-ocean: nothing within 1 km
    r = client.get("/seals/nearby", params={"lat": 0.0, "lon": 0.0, "radius_km": 1.0})
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_nearby_validates_params():
    r = client.get("/seals/nearby", params={"lat": 91.0, "lon": 0.0})
    assert r.status_code == 422
    r = client.get("/seals/nearby", params={"lat": 30.6})  # missing lon
    assert r.status_code == 422


def test_nearby_does_not_shadow_seal_id_route():
    # /seals/nearby must not be captured by /seals/{seal_id}
    r = client.get("/seals/nearby", params={"lat": 30.63, "lon": 72.86})
    assert r.status_code == 200
    assert "records" in r.json()
