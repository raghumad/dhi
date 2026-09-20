# Harappa Place Gazetteer

A citable gazetteer of archaeological places at Harappa, derived from
published excavation reports.  Each place can be referenced as
`<report> : <place>` — e.g., "Vats 1940, Pl. I : Mound F".

## Source reports

### Vats 1940 (primary)
- **Citation**: Vats, M. S. *Excavations at Harappa*. Delhi: Manager of
  Publications, 1940. 2 vols.
- **Spatial source**: Volume I, Plate I (site plan).  Scanned from the 1999
  ASI reprint (archive.org `dli.jZY9lup2kZl6TuXGlZQdjZM9k0Iy`,
  `TVA_BOK_0009128_Excavations_at_Harappa.pdf`, PDF p. 11).
- **Grid system**: 100-ft survey grid, squares designated by letters
  (J, K, M, …), each subdivided into 25 sub-squares.  The tabulation
  (Vol. II, "Tabulation of Seals") records the "Mound or Area" only;
  square designations appear in the Vol. I text (e.g., "Mound P,
  Great Granary Area, Square J 9/20").
- **Georeferencing**: see `ingest/georef.py`.  Scale from the 1000-ft grid
  (242 px / 1000 ft), rotation from the north arrow (2.96° E of up),
  anchored on the OSM Harappa Museum building.  Estimated accuracy
  ~100–200 m (mound-level, not trench-level).

## Places

| place_id          | level | name (as in report)              | defined_by          |
|-------------------|-------|----------------------------------|---------------------|
| `harappa`         | site  | Harappa                          | Vats 1940, Pl. I    |
| `harappa:area:F`  | area  | Mound F                          | Vats 1940, Pl. I    |
| `harappa:area:P`  | area  | Mound P (Great Granary complex)  | Vats 1940, Pl. I; Vol. I text |
| `harappa:area:AB` | area  | Mound AB                         | Vats 1940, Pl. I    |
| `harappa:area:E`  | area  | Mound E                          | Vats 1940, Pl. I    |
| `harappa:area:D`  | area  | Mound D                          | Vats 1940, Pl. I    |
| `harappa:area:J`  | area  | Mound J                          | Vats 1940, Pl. I    |
| `harappa:area:H`  | area  | Mound H                          | Vats 1940, Pl. I    |
| `harappa:area:G`  | area  | Mound G                          | Vats 1940, Pl. I    |
| `harappa:area:B`  | area  | Mound B                          | Vats 1940, Pl. I    |
| `harappa:area:C`  | area  | Mound C                          | Vats 1940, Pl. I    |

**Note on "Mound P"**: The tabulation lists "P" as a mound/area.  Vats Vol. I
identifies this as the Great Granary excavation complex, physically located
on Mound F ("Mound P, Great Granary Area, Square J 9/20").  It is modeled
as a separate `area` place nested within the site (not within Mound F),
because the report treats it as a distinct provenience unit.

## Referencing a location

To cite a seal's location, reference the gazetteer entry:

> Seal vats1940-258 was found in **Vats 1940, Pl. I : Mound P**
> (gazetteer `harappa:area:P`), georeferenced to (30.63226, 72.86117)
> ±250 m.

The `location` block in each record contains:
- `place_id`: the gazetteer ID (stable, citable)
- `level`: the provenience level (site/area/square/locus/point)
- `latitude`/`longitude`: representative point (centroid), WGS-84
- `uncertainty_m`: radius of uncertainty
- `derivation`: how the point was derived
- `georef_source`: the report and method

## Provenience levels

Standard archaeological hierarchy (coarsest → finest), cf. CIDOC CRM E53/P89:

- **site**: the settlement (Harappa)
- **area**: mound/area/operation (what the tabulation records)
- **square**: excavation grid square (e.g., "Square J") — *not yet in gazetteer*
- **locus**: stratigraphic context — *not in tabulation*
- **point**: exact 3D coordinate — *not recoverable from this report*

A record's `location` always references the **finest level actually known**
from the source.  The tabulation yields `area` level; `square` level
requires parsing Vol. I text (future work).

## Future: grid squares

Vats' 100-ft grid is a formal coordinate system.  The grid lines are visible
on Plate I; with the grid origin and labeling scheme calibrated, all squares
(e.g., `harappa:area:F:square:J`) can be generated mathematically rather
than hand-traced.  This would allow resolving square designations from the
Vol. I text (e.g., "Square J 9/20") to precise polygons.
