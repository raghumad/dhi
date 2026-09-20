# Dhi Story Backlog

How we work: stories are discovered through discussion, listed here, prioritized,
then implemented most-important-first. After each implementation we revisit the
priorities. Anyone can propose a story; nothing gets built until it's on this list
and prioritized.

**Status values:** `proposed` · `prioritized` · `in progress` · `done`
**Priority values:** P0 (next) · P1 · P2 · P3 · P4 (later) · — (unranked)

---

## Site gazetteer

- **SITE-1 — Per-field evidence schema** · P0 · done (2026-09-20)
  Each asserted site field carries its own citation (source ID, full citation,
  page/plate/table) and review state; values labeled as source / normalized /
  derived / provisional. Motivated by Kalibangan: periods verified, coordinates
  not — one record-level flag can't express that.
  Implemented: `ingest/site_sources.yaml` (31 sources), `ingest/sites/*.yaml`
  (one file per site), `ingest/build_sites.py` compiles to `sites.geojson` with
  derived review_status (Kalibangan = partial), `tests/test_sites_schema.py`
  (7 tests; 67 green total). Map/API keys preserved.
- **SITE-2 — Source registry with pinned artifacts** · P0 · done 2026-09-20
  Every site citation points to a content-addressed artifact (scan/PDF, SHA-256)
  in the sources registry, so "verified" stays falsifiable when URLs rot.
  Extends the agreed seal-ingestion design to sites.
  Implemented: `ingest/fetch_site_artifacts.py` (fetch + hash-verify, same
  contract as `ingest/fetch.py`); 10 artifacts pinned across 6/31 sources
  (3 UNESCO docs, Shinde 2018, 2× Pleiades; Vats 1940 and Marshall 1931 Vol. III
  reference the seal pipeline's already-pinned files); `tests/test_site_artifacts.py`
  enforces the entry contract and re-hashes local artifacts. Remaining 25
  sources tracked for SITE-5 (IGNCA/IA inventory) and follow-up pinning.
- **SITE-3 — Corpus scoping** · P2 · proposed
  A bounded target site list seeded from authoritative lists (ASI records,
  Possehl's gazetteer, UNESCO listings), ordered excavated-first, so ingestion
  proceeds in a known order and gaps are visible.
- **SITE-4 — Batch site-ingestion pipeline** · P2 · proposed
  One file per site (`ingest/sites/<site_id>.yaml`); a build step compiles and
  validates them into `sites.geojson`; tests reject a "verified" field with no
  structured citation; new/changed entries stay quarantined until reviewed.
- **SITE-5 — IGNCA/IA ASI-books inventory** · P1 · proposed
  Query Internet Archive collection metadata for `in.gov.ignca.*` (the
  IGNCA-digitized ASI Central Archaeological Library; formerly
  asi.nic.in/asi_books, now link-rotted), match title-by-title against the corpus
  list, and record hits/misses in the source registry. Turns "maybe the reports
  are in there" into a known inventory; stable IA items become the pinned
  artifacts SITE-2 needs. Immediate payoff if found: Lal's Kalibangan memoir
  (MASI 98) would unblock its unverified coordinates.

## Map

- **MAP-1 — Map reads `/sites` as the single source of truth** · P1 · proposed
  The map page embeds its own copy of the site data, which goes stale whenever
  `sites.geojson` changes. Generate it from the API or build deterministically.
- **MAP-2 — Markers persist at all zooms** · P1 · proposed
  Site markers currently vanish at zoom 10+ even for sites with no detail layer.
  Markers should stay; detail layers (mound polygons) appear where they exist.
- **MAP-3 — Detail availability indicator** · P1 · proposed
  Visually distinguish sites with report-derived detail (mound polygons, plans)
  from representative-dot-only sites, so the map never implies precision it
  doesn't have.
- **MAP-4 — Per-seal pins via mound_location lookup** · P3 · proposed
  Find No. points into field registers not in the book, so exact per-seal pins
  aren't derivable from the publication; but 'Mound or Area' is coarsely mappable
  (Plate I georef → mound polygons, hundreds of meters) and 'Level below surface'
  gives the vertical. Parser joins on a mound_location table.

## Seal catalog

- **SEAL-1 — Rename `field_no` → `find_no`** · P3 · proposed
  The printed Vats column heading is "Find No."; the code should match the source.
- **SEAL-2 — Marshall 1931 Vol II tabulation parser** · P3 · proposed
  17 plates / 591 figures are ingested but quarantined with no records to attach
  to. A tabulation parser un-blocks them for review and publication.
- **SEAL-3 — Review queue for 65 crop-less figures + multi-view UX** · P4 · proposed
  Plates XCIII/XCIV/XCVII need human review; fig330 has 4 views but the detector
  cropped 1 — decide how multi-view figures are presented.
- **SEAL-4 — `seal_no` → `figure_no` stable-ID migration** · P4 · proposed
  IDs should follow the publication's figure numbering, not an internal sequence.
- **SEAL-5 — Investigate Vats record expansion (371 → 721)** · P4 · proposed
  Output grew from 371 to 721 records (figures 1–713) without an explained cause.
  Understand it before it corrupts downstream data.

## Georeferencing

- **GEO-1 — Review hand-traced mound polygons** · P4 · proposed
  Polygons B, C, D, G, H, J, P are unreviewed hand traces; verify against
  Plate I before they're treated as evidence.
- **GEO-2 — Plate I transform refinement** · P4 · proposed
  Current transform is preliminary (~1.26 m/pixel, 2.96° rotation, one OSM anchor,
  ~155 m village residual); Leaflet's image overlay ignores the rotation.
- **GEO-3 — Nearby search via polygon distance** · P4 · proposed
  `/seals/nearby` uses centroid Haversine distance, not polygon
  distance/intersection — misleading near polygon edges.
- **GEO-4 — Coordinate-aware DjVu XML parsing** · P4 · proposed
  OCR is currently flattened text; word coordinates from DjVu XML would improve
  figure/label association.

## Data quality

- **QUAL-1 — Human review of 288 auto-crops on master** · P4 · proposed
  Auto-crops ship unreviewed; the vats1940-330 "black blob" incident showed the
  source scan, not the cropper, can be at fault — review distinguishes the two.
- **QUAL-2 — "Mound P = Great Granary" claim review** · P4 · proposed
  The identification was promoted too strongly; check it against the source
  before it hardens into catalog fact.
- **QUAL-3 — Committed `plate-i.jpg` vs no-binaries policy** · P4 · proposed
  PR #8 committed a binary the ingestion policy forbids; resolve the conflict
  explicitly (exception with rationale, or move to build-time fetch).

---

## Log

- 2026-09-20: backlog created from discussion history; initial priorities proposed.
