# Dhi (धी) — Harappan Seals Open Catalog

**Dhi** ("Intellect" or "Understanding" in Sanskrit) is a free, searchable
catalog of Harappan / Indus seals built from **first-hand, public-domain
excavation records** — not someone else's interpretation. For enthusiasts,
students, and the curious.

> **A note on this repo's history:** Dhi began as a scripture search engine
> built to democratize the Rigveda. Along the way it became clear that the
> Harappan seals deserve the greater attention, so the project has been
> refocused. The earlier Rigveda prototype is preserved in git history and on
> the `master_debater` branch.

## ⚡ One-command start

```bash
./run.sh
```

Then open **http://localhost:8000** in your browser. That's it — a local web
server with instant search, no accounts, no paywalls.

Set a custom port with:

```bash
PORT=8080 ./run.sh
```

## What's inside

- `site/` — the searchable web app (static HTML/CSS/JS, no build step)
- `data/seals.json` — the catalog data. Each entry has:
  `id, site, find_no, mound, material, size_in, type, motif, plate,
  description, source, public_domain`
- `data/SOURCES.md` — where every entry comes from
- `scripts/` — helpers to grow the catalog from public-domain sources

## The vision

Everything lives in GitHub. Anyone can:

1. Clone the repo
2. Run `./run.sh`
3. Feed their curiosity — search by motif (unicorn, bull…), material, mound, or free text

No gatekeeping. If you can add a seal from a public-domain source, open a PR.

## Data policy

- **Only public-domain or openly licensed sources.** The seed data comes from
  ASI reports in the public domain: Daya Ram Sahni (1926) and
  Madho Sarup Vats, *Excavations at Harappa* (1940).
- **No copyrighted photo corpora.** The CISI volumes (Parpola et al.) are the
  gold standard but are copyrighted — we link to them, we don't copy them.
- Every entry cites its source verbatim. Interpretations and decipherment
  claims don't belong here — just the dig records.

## Contribute

1. Find a seal in a public-domain report (see `data/SOURCES.md`)
2. Add it to `data/seals.json` following the existing schema
3. Run `./run.sh` and check it renders
4. Open a pull request

## Roadmap

- [ ] Import all plates from Vats (1940) Vol. II — public domain
- [ ] Import Marshall (1931) *Mohenjo-daro and the Indus Civilization* seals
- [ ] Add thumbnail images from public-domain plate scans (archive.org)
- [ ] Filters for period/level, advanced search
- [ ] GitHub Pages deployment for a live demo

## License

Code: MIT. Data: public domain to the best of our knowledge — see
`data/SOURCES.md` for provenance of each entry.
