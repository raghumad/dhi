#!/usr/bin/env python3
"""Parse Met Collection API objects -> JSONL records.

Reads data/artifacts/met_objects.json (written by fetch_met.py) and emits
one record per kept object to data/records/met_seals.jsonl.

Record contract (mirrors parse_vats.py where it applies):
  - id: "met-<objectID>" (stable; the Met never reuses object IDs)
  - image_url: served locally at /images/museum/met-<objectID>.jpg
  - provenance: museum, accession number, object URL, license, fetch manifest
  - provenance_type: "museum" (vs "excavation" for dig-published sources)

Culture labels are the Met's own words, passed through unedited -- the
catalog must not reclassify another institution's attributions. Objects
without an excavation context say so plainly (excavation: null) rather
than inheriting a site.

Light normalization for the catalog's facet dimensions:
  - material: "steatite"/"copper"/"gold"/etc. extracted from the medium
    string when unambiguous, else "unknown". This is a display aid; the
    verbatim medium is always kept in medium_raw.

Usage:
    python ingest/parse_met.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OBJECTS_JSON = ROOT / "data/artifacts/met_objects.json"
MANIFEST_JSON = ROOT / "data/artifacts/met_manifest.json"
OUT = ROOT / "data/records/met_seals.jsonl"


def norm_material(medium: str) -> str:
    """Best-effort single-word material for faceting; 'unknown' if unclear."""
    m = (medium or "").lower()
    for mat in ("steatite", "copper", "gold", "silver", "lapis", "carnelian",
                "agate", "ivory", "shell", "terracotta", "bronze", "lead",
                "chert", "jasper", "faience"):
        if mat in m:
            return mat
    return "unknown"


def main() -> None:
    objects = json.loads(OBJECTS_JSON.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))

    kept = [o for o in objects
            if o.get("isPublicDomain") and o.get("primaryImage")]
    print(f"  parsing {len(kept)} Met objects ...")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(OUT, "w", encoding="utf-8") as f:
        for o in kept:
            oid = o["objectID"]
            medium = o.get("medium") or ""
            dims = "; ".join(
                f"{m.get('elementName')}: "
                f"{', '.join(f'{k} {v}' for k, v in (m.get('elementMeasurements') or {}).items())}"
                for m in (o.get("measurements") or []) if m.get("elementMeasurements")
            ) or o.get("dimensions") or None
            rec = {
                "id": f"met-{oid}",
                "title": o.get("title"),
                "object_name": o.get("objectName"),
                "culture": o.get("culture") or None,
                "period": o.get("period"),
                "object_date": o.get("objectDate"),
                "medium_raw": medium or None,
                "material": norm_material(medium),
                "dimensions_raw": dims,
                "accession_number": o.get("accessionNumber"),
                "museum": "Metropolitan Museum of Art, New York",
                "museum_url": o.get("objectURL"),
                "excavation": o.get("excavation") or None,
                "site": None,  # museum objects: no trench context; do not guess
                "image_url": f"/images/museum/met-{oid}.jpg",
                "image_status": "museum",
                "license": "Public domain (Met Open Access)",
                "provenance_type": "museum",
                "provenance": {
                    "source": ("Metropolitan Museum of Art, New York. "
                               "Open Access collection."),
                    "artifact": "Met Collection API query 'indus seal'",
                    "artifact_sha256": manifest["objects_sha256"],
                    "fetched_at": manifest["fetched_at"],
                    "object_url": o.get("objectURL"),
                    "credit": o.get("creditLine"),
                    "extraction": "parse_met.py Met-API parser",
                },
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"  parsed {n} records -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
