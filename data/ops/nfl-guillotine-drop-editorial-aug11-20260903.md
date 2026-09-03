# NFL Guillotine — drop editorial August 11 chrome — 2026-09-03

**Follow-up to PR 419** (props header honesty). Same stale launch date on Guillotine.

## Bug

Live `/pro/nfl/fantasy/guillotine` product copy is honest (educational stay-alive, no waivers) but still showed leftover editorial chrome:

`Date: August 11, 2026` via `KOSEDGE_DATE`

## Fix (chrome only)

- Drop `KOSEDGE_DATE` / `Date: August 11` from Guillotine header
- Keep educational stay-alive copy (PR leftover-copy honesty)
- Weekly Fantasy checked — no `KOSEDGE_DATE` / Aug 11 present; assert stays clean

## Out of scope

Tiles stay. No product build. No KEI mint, remat, paywall, hide. Sleepers / Awards Aug 11 chrome not in this PR.

## Tests / docs

- `apps/web/__tests__/lib/pro-sport-ia.test.ts` — Guillotine + Weekly Fantasy source asserts no Aug 11 / `KOSEDGE_DATE`
- This ops note + `project-log.md` row

**Do not merge** — CoS merges.
