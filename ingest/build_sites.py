"""Build ingest/sites.geojson from the per-field evidence source of truth.

Source of truth:
  ingest/site_sources.yaml   - source registry (id -> citation, category)
  ingest/sites/<site_id>.yaml - one file per site; every asserted field carries
                                 its own value kind, review state, and evidence.

Output:
  ingest/sites.geojson        - generated; do not hand-edit. The API and the map
                               read this file.

Run:  .venv/bin/python ingest/build_sites.py
"""
import json
import sys
import yaml
from pathlib import Path

INGEST = Path(__file__).resolve().parent
FIELD_ORDER = ["name", "coordinates", "periods", "size_class",
               "excavation_status", "notes", "harappan_connection"]


def load_registry():
    return yaml.safe_load((INGEST / "site_sources.yaml").read_text())["sources"]


def load_sites():
    sites = []
    for path in sorted((INGEST / "sites").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        assert doc["site_id"] == path.stem, f"{path}: site_id mismatch"
        sites.append(doc)
    return sites


def derive_review_status(fields):
    states = [f["state"] for f in fields.values()]
    if all(s == "verified" for s in states):
        return "verified"
    if any(s == "verified" for s in states):
        return "partial"
    return "unverified"


def compile_sources(fields, registry):
    out, seen = [], set()
    for fname in FIELD_ORDER:
        for e in fields[fname].get("evidence", []):
            item = f"{registry[e['source']]['citation']} - {e['locator']}"
            if item not in seen:
                seen.add(item)
                out.append(item)
    return out


def authority_note(site_id, fields):
    lines = []
    for fname in FIELD_ORDER:
        f = fields[fname]
        bits = [f["state"], f["kind"]]
        if fname == "coordinates" and "uncertainty_m" in f:
            bits.append(f"±{f['uncertainty_m']}m")
        ev = "; ".join(f"{e['source']}: {e['locator']}"
                       for e in f.get("evidence", [])) or "no evidence"
        lines.append(f"- {fname}: {f['state']} [{', '.join(bits[1:])}] ({ev})")
        if f.get("note"):
            lines.append(f"  note: {f['note']}")
    unverified = [n for n in FIELD_ORDER if fields[n]["state"] != "verified"]
    tail = ("All fields verified." if not unverified
            else f"UNVERIFIED FIELDS: {', '.join(unverified)} - values shown are provisional or absent.")
    return "Per-field review:\n" + "\n".join(lines) + "\n" + tail


def build_feature(doc, registry):
    fields = doc["fields"]
    coords = fields["coordinates"]
    props = {
        "site_id": doc["site_id"],
        "affiliation": doc["affiliation"],
        "review_status": derive_review_status(fields),
        "uncertainty_m": coords.get("uncertainty_m"),
        "coordinate_provenance": coords.get("method"),
        "authority_note": authority_note(doc["site_id"], fields),
        "sources": compile_sources(fields, registry),
        "field_evidence": fields,
    }
    for fname in FIELD_ORDER:
        if fname == "coordinates":
            continue
        props[fname] = fields[fname]["value"]
    # keep 'name' first-ish for readability; dict order: site_id, name, ...
    ordered = {"site_id": props.pop("site_id"), "name": props.pop("name")}
    ordered.update(props)
    return {
        "type": "Feature",
        "geometry": {"type": "Point",
                     "coordinates": coords["value"]},
        "properties": ordered,
    }


def build():
    registry = load_registry()
    sites = load_sites()
    fc = {"type": "FeatureCollection",
          "features": [build_feature(d, registry) for d in sites]}
    out = INGEST / "sites.geojson"
    out.write_text(json.dumps(fc, indent=2, ensure_ascii=False) + "\n")
    by_status = {}
    for d in sites:
        by_status[derive_review_status(d["fields"])] = \
            by_status.get(derive_review_status(d["fields"]), 0) + 1
    print(f"wrote {out} ({len(sites)} sites: {by_status})")


if __name__ == "__main__":
    sys.exit(build())
