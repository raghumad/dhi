## What changes

## Validation (all required before review)

- [ ] CI is green (`test` and `smoke` jobs)
- [ ] Boot check: `uv run uvicorn api.main:app` — `/` redirects to `/docs`,
      `/seals`, `/seals/{id}`, `/search`, `/export` all respond
- [ ] `docs/` updated if any behavior, endpoint, or requirement changed
- [ ] No credentials, private notes, or vision material in the diff

## Notes for the reviewer
