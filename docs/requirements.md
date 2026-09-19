# Dhi — Requirements (DRAFT)

*Status: working draft, 2026-09-19. Scope: Phase 1 (seed ingestion pipeline,
record core, read API) plus standing constraints that apply to all phases.
Later phases get their own requirements when they are planned.*

Phase 1 delivers one vertical slice on real data: the Vats 1940 "Tabulation
of Seals" is fetched once, parsed into records, and served over HTTP. The
requirements below describe what that slice must guarantee; they are
deliberately silent on deployment, licensing, and collaboration, which are
open decisions listed at the end.

## 1. Data

- R-D1: Each seal record has a unique identifier, assigned once, never changed afterwards.
- R-D2: Each seal record contains: site of discovery, physical description, and a source citation (author, title, year, page/plate/figure). Material and measurements are included when the source states them.
- R-D3: Records without images are valid. Records with images reference the image artifact.
- R-D4: Source artifacts (scans, OCR text, transcriptions) are stored byte-identical to what was fetched. They are never edited in place.
- R-D5: Every derived field in a record identifies the source artifact and the extraction rule that produced it.
- R-D6: Artifact records, once written, are never modified in place. Corrections are recorded as new versions; previous versions remain retrievable.
- R-D7: Records contain no interpretive claims (no decipherment, no cultural attribution beyond what the source states).

## 2. Ingestion

- R-I1: Importing data is done by a repeatable command, not by manual file editing.
- R-I2: Re-running the import over unchanged sources reproduces identical derived records.
- R-I3: The import records, per record, which source artifact it came from.
- R-I4: Source fields with no mapping in the record schema are preserved with the record as unmapped key-value pairs, not discarded.
- R-I5: Records the importer distrusts (OCR damage, ambiguous classification) are marked with machine-readable flags for human review. Flagged records are never silently dropped and never silently repaired.

## 3. API

- R-A1: HTTP API provides: paginated record listing, record retrieval by identifier, filtering by site, filtering by material, and full-text search over descriptions.
- R-A2: Every API response for a record includes its identifier and its source citation.
- R-A3: Read access requires no authentication.
- R-A4: All records are exportable in bulk as JSON and as CSV.

## 4. Out of scope for Phase 1

- User accounts, annotations, and collaboration features.
- Entity disambiguation pages.
- Map and timeline views.
- Image hosting and IIIF-style image services.
- Scheduled ingestion (Phase 1 import is on-demand via R-I1; scheduling arrives in Phase 2).

## Open decisions

- Backend language and framework. Phase 1 is implemented in Python/FastAPI as
  the working choice; the HTTP+JSON contract is what clients depend on, so the
  implementation remains replaceable.
- License for derived factual data and for the codebase (no license terms are
  asserted by these requirements).
- Form of the transactional store for later phases (embedded database file vs.
  single-writer log).
- Deployment: containerization, backups, TLS, and hosting for the personal
  domain. Phase 1 runs as a local process; production deployment requirements
  will be written when hosting is chosen.
- Review-queue representation: Phase 1 uses free-form `parse_flags`; a formal
  review workflow is a later-phase design task.
