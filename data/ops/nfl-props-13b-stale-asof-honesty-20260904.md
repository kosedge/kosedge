# NFL props 13b — Week 1 chrome + stale Jul as-of honesty — 2026-09-04

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-props-13b-stale-asof-honesty-bb2d`  
**Cite:** KOS-15 LOCKED (no silent stale fallback; §13b freshness = honesty only) · KOS-14 H-2 / remediation 13b · Phase A/B NFL-V2 · related C1 SSR as-of (PR 464) investigated, not copied

## Live bug (www)

`/pro/nfl/props?season=2026&week=1` showed:

- Period: `2026 · Week 1 REG`
- Stamp: `Board as of Jul 20, 2026, 7:21 PM EDT · stale` (`data-stale=true`)

Week 1 REG chrome could be read as a live/current board while vintage was Jul.

## Fix (honesty only)

| Surface | Was | Fix |
| --- | --- | --- |
| Period chrome | `2026 · Week 1 REG` alone | When board stamp is stale → `2026 · Week 1 REG · not live board` |
| Status | Stamp only (easy to miss vs Week chrome) | Amber `HonestStatusBanner` ties Week chrome to real as-of · stale |
| As-of stamp | Real Jul · stale | **Unchanged** — keep visible; never invent fresher |

## Locks

- No remat · no Celery · no PLAY · no Conf invent · no quarantine scrub · no desk fork · no props philosophy UI
- Do not hide Jul as-of; do not mint “as of now”

## Tests

- `__tests__/lib/nfl-props-header.test.ts` — period not-live + Jul stamp honesty
- `__tests__/lib/nfl-props-13b-stale-asof.test.ts` — source lock
