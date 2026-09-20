#!/usr/bin/env python3
"""SITE-5: inventory the IGNCA-digitized ASI library on Internet Archive.

Queries IA advancedsearch for identifier:in.gov.ignca* (9,735 items as of
2026-09-20), saves the raw inventory snapshot, and matches titles against
the bounded authoritative corpus the site registry needs.

Usage:
    python ingest/ignca_inventory.py fetch     # download snapshot (slow, ~10 pages)
    python ingest/ignca_inventory.py match     # match snapshot against corpus

Outputs:
    data/ignca_inventory.json  (gitignored raw snapshot)
    ingest/ignca_inventory.yaml (committed: query, date, totals, hits/misses)
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "ignca_inventory.json"
REPORT = Path(__file__).resolve().parent / "ignca_inventory.yaml"

QUERY = "identifier:in.gov.ignca*"
FIELDS = ["identifier", "title", "date", "creator"]
ROWS = 1000

# (registry source id, must-have keywords, word-boundary keywords).
# must-have keywords match as substrings; word keywords need \b boundaries
# (so "ur" doesn't match "culture").
WANT = [
    ("rao1979", ["lothal", "rao"], []),
    ("lal2003", ["kalibangan", "lal"], []),
    ("bisht2015", ["dholavira", "bisht"], []),
    ("nath-rakhigarhi", ["rakhigarhi", "nath"], []),
    ("francfort1989", ["francfort"], ["shortughai", "shortugai", "oxus"]),
    ("gadd1932", ["gadd"], ["ur", "seal"]),
    ("legrain1951", ["legrain"], ["seal", "ur"]),
    # Broader sweep: any ASI memoir/report on our ten seed sites.
    ("corpus-harappa", ["harappa"], []),
    ("corpus-mohenjodaro", ["mohenjo"], []),
    ("corpus-dholavira", ["dholavira"], []),
    ("corpus-lothal", ["lothal"], []),
    ("corpus-kalibangan", ["kalibangan"], []),
    ("corpus-rakhigarhi", ["rakhigarhi"], []),
    ("corpus-ur", ["seals of ancient indian"], ["ur"]),
]

# Loose second-chance pass for the specific excavation reports we need:
# title-only keywords, author not required (cataloging varies).
LOOSE = [
    ("rao1979-loose", ["lothal"], []),
    ("lal2003-loose", ["kalibangan"], []),
    ("bisht2015-loose", ["dholavira"], []),
    ("nath-rakhigarhi-loose", ["rakhigarhi"], []),
    ("gadd1932-loose", ["seals of ancient indian"], []),
    ("legrain1951-loose", ["seal cylinders"], []),
    # Broad sweep, honestly named: any volume of Marshall 1931 — IA metadata
    # rarely records which volume a scan is, so this is not a "vol. 2" rule.
    ("marshall-volumes", ["mohenjo-daro and the indus civilization"], []),
]


def search(query: str, start: int) -> dict:
    params = {
        "q": query,
        "fl[]": FIELDS,
        "rows": ROWS,
        "start": start,
        "output": "json",
    }
    url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        params, doseq=True)
    last = None
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001 - transient network flakiness
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"IA search failed: {last}")


def cmd_fetch() -> None:
    # IA's relevance ranking drifts across deep pages and start is ignored
    # when a sort is given, so paginate by identifier prefix buckets instead:
    # each bucket query is small enough to be stable.
    docs, seen = [], set()
    expected = 0
    for d1 in "123456789":
        for d2 in "0123456789":
            query = f"identifier:in.gov.ignca.{d1}{d2}*"
            first = search(query, 0)
            total = first["response"]["numFound"]
            expected += total
            got = first["response"]["docs"]
            start = len(got)
            while start < total:
                page = search(query, start)
                batch = page["response"]["docs"]
                if not batch:
                    break
                got.extend(batch)
                start += len(batch)
            for d in got:
                if d["identifier"] not in seen:
                    seen.add(d["identifier"])
                    docs.append(d)
        print(f"  ... bucket {d1}x done: {len(docs)} unique", flush=True)
    print(f"expected ~{expected}, fetched {len(docs)} unique", flush=True)
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(
        {"query": QUERY, "fetched": time.strftime("%Y-%m-%d"),
         "numFound": total, "docs": docs}, indent=1))
    print(f"wrote {SNAPSHOT} ({len(docs)} docs)")


def norm(s) -> str:
    return (s or "").lower()


def matches(hay: str, must: list, words: list) -> bool:
    if not all(k in hay for k in must):
        return False
    return all(re.search(r"\b" + re.escape(w) + r"\b", hay) for w in words)


def cmd_match() -> None:
    snap = json.loads(SNAPSHOT.read_text())
    # IA deep pagination drifts: dedupe by identifier, keep first.
    seen, docs = set(), []
    for d in snap["docs"]:
        ident = d.get("identifier")
        if ident and ident not in seen:
            seen.add(ident)
            docs.append(d)
    report: dict = {}
    for sid, must, words in WANT + LOOSE:
        hits = []
        for d in docs:
            hay = norm(d.get("title")) + " " + norm(d.get("creator"))
            if matches(hay, must, words):
                hits.append(d)
        if hits:
            report[sid] = {
                "status": f"hit ({len(hits)} candidate(s))",
                "candidates": [
                    {"id": h["identifier"],
                     "title": (h.get("title") or "?")[:120],
                     "date": h.get("date")}
                    for h in hits[:10]
                ],
            }
            if len(hits) > 10:
                report[sid]["candidates_truncated"] = len(hits) - 10
        else:
            report[sid] = {"status": "miss"}
    header = (
        "# IGNCA/IA ASI-books inventory (SITE-5).\n"
        f"# Query: {snap['query']} | snapshot: {snap['fetched']} | "
        f"unique items scanned: {len(docs)}.\n"
        "# Hits are candidate pinned artifacts for SITE-2; misses stay on the\n"
        "# acquisition list. Generated by ingest/ignca_inventory.py - do not hand-edit.\n"
    )
    REPORT.write_text(header + yaml.safe_dump(
        report, sort_keys=False, allow_unicode=True, width=100))
    print(f"wrote {REPORT} ({len(docs)} unique items)")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("fetch", "match"):
        sys.exit("usage: ignca_inventory.py [fetch|match]")
    {"fetch": cmd_fetch, "match": cmd_match}[sys.argv[1]]()
