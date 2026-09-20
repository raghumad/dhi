# Site Gazetteer — source policy

## Authoritative-source rule (standing)

Site coordinates, periods, sizes, excavation status, and claimed Harappan
connections must be traceable to **authoritative sources**:

- Excavation reports and their published plans/tables
- National archaeological surveys (e.g. ASI reports)
- UNESCO World Heritage listings and nomination dossiers
- National heritage registries
- Peer-reviewed site gazetteers and survey publications

The following do **not** qualify: Wikipedia, journalism/magazines, general
reference works without citations, and model training-data memory.

## Per-field evidence schema (SITE-1)

The source of truth is **not** `sites.geojson` — it is generated. The truth lives in:

- `ingest/site_sources.yaml` — the source registry: every citable source gets an
  ID, a full citation, and a category (`excavation_report`, `excavation_project`,
  `peer_reviewed`, `unesco`, `gazetteer`, `course_material`, `official_record`,
  `expert_statement`). Pinned artifacts (SHA-256) arrive with SITE-2.
- `ingest/sites/<site_id>.yaml` — one file per site. Every asserted field
  (`name`, `coordinates`, `periods`, `size_class`, `excavation_status`, `notes`,
  `harappan_connection`) carries:
  - `value` — the asserted value (null only where not applicable)
  - `kind` — `source` (verbatim) / `normalized` (standardized) / `derived`
    (computed, e.g. georeferenced) / `provisional` (placeholder) / `na`
  - `state` — `verified` or `unverified`
  - `evidence` — list of `{source, locator}` with exact page/plate/table/plan
  - coordinates additionally carry `uncertainty_m` and `method`
  - optional `note` for caveats (e.g. variant spellings, rejected figures)

Rules enforced by `tests/test_sites_schema.py`:

- a `verified` field must cite ≥1 registered source with a non-empty locator
- an `unverified` field must be `kind: provisional` (no silent placeholders)
- `review_status` is **derived**, not asserted: `verified` if every field is
  verified, `partial` if mixed, `unverified` if none
- `ingest/sites.geojson` must be byte-identical to what `ingest/build_sites.py`
  regenerates — CI fails on a stale generated file

Rebuild: `.venv/bin/python ingest/build_sites.py`

## Pinned artifacts (SITE-2)

Every source in the registry may declare `artifacts` — immutable files fetched
once and addressed by SHA-256, following the same contract as the seal
pipeline's `ingest/sources.yaml` + `ingest/fetch.py`:

```yaml
artifacts:
  - name: periodic-report-138
    url: https://whc.unesco.org/document/164707
    sha256: 1321fa93599fcf8...
    path: data/artifacts/sites/unesco-whc/whc-164707.pdf
```

- `ingest/fetch_site_artifacts.py` downloads missing artifacts and verifies
  hashes (a mismatch is a hard error, never a silent overwrite). Some hosts
  (e.g. whc.unesco.org) require a browser User-Agent; the fetcher sets one.
- Artifacts live under `data/artifacts/sites/` (gitignored). Sources shared with
  the seal pipeline (Vats 1940, Marshall 1931 Vol. III) reference the same
  already-pinned files rather than duplicating them.
- `tests/test_site_artifacts.py` enforces the entry contract and re-hashes
  every locally present artifact against the registry.

Coverage as of 2026-09-20: 10 artifacts pinned across 6 of 31 sources
(unesco-whc ×3, vats1940 ×2, marshall1931 ×2, shinde2018, pleiades ×2).
The rest — excavation-report PDFs not yet digitized or located (Rao 1979,
Lal 2003, Bisht 2015, Nath's Rakhigarhi report, Francfort 1989, UE 10),
eGyankosh units, and web snapshots — are tracked for SITE-5 (IGNCA/IA
inventory) and follow-up pinning. An empty `artifacts: []` is honest: the
citation stands, the bytes aren't yet pinned.

## Review status

Every feature carries the derived `review_status`:

- `unverified` — provisional data, drawn from general knowledge. Do not cite.
  Shown on the map as a hollow dashed marker with an UNVERIFIED banner.
- `partial` — some fields verified, some provisional. The map shows which via
  the per-field `authority_note`.
- `verified` — every field traces to an authoritative source with
  page/plate/table locators. Shown solid.

## Verification log

| site_id | status | authoritative source | verified |
|---|---|---|---|
| harappa | verified | Vats 1940; HARP; Kenoyer 2008; IGNOU Unit 5 | 2026-09-20 |
| mohenjo-daro | verified | Marshall 1931; UNESCO WH property 138; IGNOU Unit 5 | 2026-09-20 |
| rakhigarhi | verified | ASI Nath report; Shinde et al. 2018; Lok Sabha Q.4977 | 2026-09-20 |
| kalibangan | partial (coords unverified) | Thapar 1975; ASI 2003 (MASI 98); IGNOU Unit 5 | 2026-09-20 |
| dholavira | verified | UNESCO 2021 dossier; Bisht 2015 (ASI); IGNOU Unit 5 | 2026-09-20 |
| lothal | verified | Rao 1979 (MASI 78); ASI site text; Frenez et al. 2005 | 2026-09-20 |
| shortugai (Shortughai) | verified | Francfort 1989; Possehl; Pleiades 717754049; Kenoyer 1998 | 2026-09-20 |
| gonur-tepe | verified | Kufterin & Dubova 2013; CISI 3.3; Parpola 2018; Pleiades | 2026-09-20 |
| ur | verified | CDLI; Gadd 1932; Legrain 1951 (UE 10) | 2026-09-20 |
| dilmun-bahrain (Qal'at al-Bahrain) | verified | UNESCO WH 1192ter dossier; Laursen & Steinkeller 2017 | 2026-09-20 |
