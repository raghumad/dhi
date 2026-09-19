"""Shared test setup: repo root on sys.path, cwd at root.

Both ingest/parse_vats.py and api/main.py use paths relative to the
repository root, so tests chdir there before importing them.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, ROOT)
os.chdir(ROOT)
