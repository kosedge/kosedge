# NFL Awards + Sleepers — drop editorial August 11 chrome — 2026-09-03

**Follow-up to PR 421** (Guillotine) and **PR 419** (props). Same stale launch date on Awards + Sleepers.

## Bug

Live `/pro/nfl/awards` and `/pro/nfl/fantasy/sleepers` still showed leftover editorial chrome:

`Date: August 11, 2026` via `KOSEDGE_DATE`

Paying-subscriber chrome: a dated launch stamp on a live Week 1 product looks like a leftover, not a market as-of.

## Fix (chrome only)

- Drop `KOSEDGE_DATE` / `Date: August 11` from Awards and Sleepers headers
- Awards: keep `NFL_AWARDS_SOURCE_STAMP` + real model lineage as-of (already on the page)
- Sleepers: keep ADP source / freshness labels when ADP is joined
- No other NFL pro/fantasy pages still rendered this `KOSEDGE_DATE` header chrome

## Out of scope

Tiles stay. No product build. No KEI mint, remat, paywall, hide. No writer-desk / season-preview markdown rewrites.

## Tests / docs

- `apps/web/__tests__/lib/pro-sport-ia.test.ts` — Sleepers + Awards assert no Aug 11 / `KOSEDGE_DATE` / `Date: {`
- This ops note (skip `project-log.md` merge fight)

**Do not merge** — CoS merges.
