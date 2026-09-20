# Indus World Site Gazetteer

Citable site-level gazetteer for the dhi map and API. Two tiers:

- **affiliation `harappan`**: settlements of the Indus Civilization proper
  (the dots behind the Saraswati/Ghaggar-Hakra distribution argument).
- **affiliation `related`**: sites outside the Indus cultural zone with
  documented Harappan artifacts, trade contacts, or inscriptions
  (Gonur Tepe, Mesopotamian cities, Dilmun...). The "Indus world" scope.

## Schema

```json
{
  "site_id": "harappa",
  "name": "Harappa",
  "affiliation": "harappan",
  "latitude": 30.6357,
  "longitude": 72.8739,
  "uncertainty_m": 500,
  "size_class": "major_city",
  "periods": ["early", "mature", "late"],
  "excavation_status": "excavated",
  "harappan_connection": null,
  "sources": ["Vats 1940, Pl. I", "..."]
}
```

- `size_class`: `major_city` | `town` | `village` | `camp` | `unknown`
- `periods`: subset of `early` | `mature` | `late` (Harappan phases)
- `excavation_status`: `excavated` | `surveyed` | `unknown`
- `harappan_connection` (related sites only): free text, e.g.
  "Indus seals and carnelian beads excavated (Sarianidi)".
- Coordinates are representative site centers; `uncertainty_m` reflects
  how well the site location is pinned, not excavation precision.

## Sources

Site coordinates compiled from published archaeological literature.
Each entry cites its source. Corrections welcome — every coordinate is
falsifiable.
