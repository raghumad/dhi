#!/usr/bin/env python3
"""Validate data/seals.json against the expected schema."""
import json
import sys
from pathlib import Path

REQUIRED = ["id", "site", "description", "source", "public_domain"]
root = Path(__file__).resolve().parent.parent
path = root / "data" / "seals.json"

data = json.loads(path.read_text())
errors = []
ids = set()
for i, s in enumerate(data):
    for f in REQUIRED:
        if f not in s:
            errors.append(f"entry {i}: missing '{f}'")
    if s.get("id") in ids:
        errors.append(f"entry {i}: duplicate id {s.get('id')}")
    ids.add(s.get("id"))
    if not s.get("public_domain"):
        errors.append(f"entry {i} ({s.get('id')}): public_domain must be true")

if errors:
    print("FAILED:")
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(data)} seals validated.")
