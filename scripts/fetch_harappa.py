#!/usr/bin/env python3
"""
fetch_harappa.py — starter scraper for public-domain Harappa seal pages.

Harappa.com digitizes ASI (public-domain) descriptions. This script shows the
pattern for extracting structured entries; extend it page by page and always
verify against the original ASI report before committing.

Usage:
    python3 scripts/fetch_harappa.py > /tmp/new_seals.json
Then merge into data/seals.json by hand (keeps provenance review human).
"""
import json
import re
import urllib.request

PAGES = [
    # Add harappa.com excavation pages that transcribe ASI reports here.
    "https://www.harappa.com/excavations/1923-24-unearthing-mysteries-harappa/steatite-and-faience-seals-and-tablets",
]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "harappan-seals-catalog/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def main():
    print("Pages to process:")
    for p in PAGES:
        print(" -", p)
    print("\nThis is a starter scaffold. Page layouts vary; write per-page")
    print("parsers and cross-check every field against the ASI report scan.")

if __name__ == "__main__":
    main()
