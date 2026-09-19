# Dhi — Architecture (Phase 1)

## The problem in one paragraph

Researchers need structured, citable facts about Harappan seals: which seal,
where it was found, what it is made of, and exactly which publication says
so. The raw material is 1930s excavation reports — long books, printed
tables, noisy OCR. Dhi's job is to turn those into records a computer can
filter and search, without ever losing track of where each fact came from.

## The pipeline

```
source artifact (immutable file)
        │  ingest/parse_vats.py  (deterministic, re-runnable)
        ▼
records (JSONL snapshot, one object per line)
        │  loaded at startup
        ▼
in-memory indexes (one per filter dimension + full-text)
        │  api/main.py  (thin HTTP layer)
        ▼
HTTP+JSON API  →  any client (Phase 1: curl; later: PWA)
```

Each stage is deliberately dumb, and each stage's output is inspectable on
disk. If the API ever returns something surprising, you can open the JSONL
file and the OCR text it came from and see exactly why.

## Why files instead of a database (Phase 1)

A database is a program that owns your data and answers queries. For Phase 1
that buys little and costs much: another server to install, back up, and keep
running, plus a schema-migration story for every change. Files buy three
things that matter more right now:

1. **Byte-identical sources.** The OCR text is stored exactly as fetched, with
   a SHA-256 hash recorded in every derived record. "Which bytes produced this
   fact?" is always answerable.
2. **Deterministic rebuilds.** The parser is a pure function of the artifact:
   re-running it must reproduce the records byte-for-byte. A test enforces
   this. Version control then gives us history for free.
3. **Zero operational burden.** There is nothing to install except Python.

The honest tradeoff: files don't do concurrent writes, transactions, or
efficient updates. The moment researchers start annotating and correcting
records concurrently, Phase 1's "regenerate the world" model stops working
and a transactional store becomes necessary. That decision is explicitly
deferred to Phase 2 (see requirements, open decisions). The record format is
designed so the migration is additive, not a rewrite.

## Why Python, and why FastAPI

Python is the working language for one reason: this project's hardest code is
data munging — OCR cleanup, table parsing, text normalization — and Python
has the richest ecosystem and the shortest path from idea to working parser
for that kind of work. The API itself is almost trivial by comparison.

Given Python, the API needs a way to turn Python functions into HTTP
endpoints. The options:

- **Flask**: the minimal classic. You write a function, decorate it with a
  URL, and return a dict. Less built-in validation; you hand-check query
  parameters.
- **Django**: a full framework — ORM, admin, auth — built for database-backed
  sites. Far more machinery than a read API over files needs.
- **FastAPI**: like Flask, but function signatures *are* the contract. Declare
  `limit: int = Query(20, ge=1, le=200)` and invalid requests are rejected
  automatically, with interactive documentation generated for free.

FastAPI was chosen because a public data API lives or dies on its contract:
what parameters exist, what shapes responses take, what errors mean. Getting
that validation and documentation without hand-writing it is worth the
slightly younger ecosystem. If Python ever stops fitting, the HTTP+JSON
contract is the boundary clients depend on — the implementation behind it is
replaceable without breaking anyone.

Alternatives outside Python (Go, Rust, Node) would serve HTTP faster, but
speed is not Phase 1's bottleneck — parsing 1930s OCR is. Optimizing the
wrong layer is the classic mistake; the slow part here is I/O and text, where
language choice barely matters at this scale.

## Why a web client first (later phase)

Citations need stable URLs, and nothing in the requirements needs phone
hardware (camera, GPS, Bluetooth). A web app gives every record an address,
works on every device, and can be installed as a PWA with offline reading.
Native apps remain possible later precisely because they would talk to the
same HTTP+JSON API — no backend changes required.

## What "quarantine" means

The parser does not pretend the OCR is clean. When a row looks wrong — two
sizes where one should be, a field number with no digits, a swallowed table
header — the record is kept, the suspicious part is preserved raw, and a
`parse_flags` entry marks it for human review. This is the system's answer to
untrustworthy input: never silently drop, never silently repair. The review
interface itself is a later phase; Phase 1 only guarantees the flags exist
and are queryable.

## Deliberate non-goals for Phase 1

No user accounts, no annotations, no image serving, no maps or timelines, no
scheduled ingestion, no production deployment story. Each is a real need, each
would double the design surface, and none is required to prove the core loop:
artifact → record → query.
