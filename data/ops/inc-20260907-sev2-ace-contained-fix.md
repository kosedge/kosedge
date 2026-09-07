# INC-2026-09-07 SEV-2 — A+C+E contained fix (Ryan ACCEPT 1/2/3)

**Status:** Draft PR only — do not merge from this note. Independent review outside agent.

**Scope (only):**
- **A** — Stop persist-on-GET for model-service `/nfl/fair-lines`
- **C** — Narrow NFL live Edge Board assemble window; full-slate fail-closed honesty
- **E** — GO-1c warm cron hits public cache path (no Auth CDN BYPASS)

**Explicitly out:** B/D snapshot spine / Odds dedupe · F pageData timeout raise · unseal/promote/KEI mint/PLAY expand

## A — Zero Postgres writes on customer GET

| Before | After |
| --- | --- |
| `persist` Query default **True** — bare GET wrote `odds_snapshots` via `_persist_nfl_odds_events_for_training` | Default **False**; `persist=0` still honored; `persist=1` opt-in for ops only |
| Page-data relied on web sending `persist=0` | Model-service page-data path default non-persisting even if caller omits param |

Warehouse persist remains worker/beat `pull_odds_snapshot` (idempotent, observable).

**Tests:** `test_nfl_fair_lines_get_default_zero_persist_writes` · `test_pull_odds_snapshot_persists_rows`

## C — Live window + full-slate honesty

| Surface | Behavior |
| --- | --- |
| `slate=week1` / live | Fair-lines window `daysAhead=10`, `includePastDays=2` (not 200) |
| `slate=full` | Full window `daysAhead=200`; **fail closed** if a narrow live window would be labeled full; transport miss → 503/504 (never week1 rows as full) |
| Cache keys | `/api/edge-board/nfl/assemble?slate=week1` ≠ `?slate=full` (sport/window never mix) |
| pageData | `UPSTREAM_TIMEOUT_MS.pageData` stays **25s**; maxDuration 30 |

## E — Warm cron public path (bandage)

| Before | After |
| --- | --- |
| Warm fetch forwarded `Authorization: Bearer CRON_SECRET` → CDN **BYPASS** | Auth on cron route only; assemble GET is public + `x-kosedge-warm` |
| — | Bounded paths: NFL week1 + CFB week1 only (no full-slate warm / Odds spend) |
| — | Observe hooks: `x-vercel-cache`, `age`, `alerts` (`cdn_bypass` / `origin_error` / `cache_miss`) |

## Rollback

1. Revert this PR (or restore `persist: Query(True)` + prior assemble/warm files).
2. Web already sends `persist=0` on page-data — temporary safety net if model-service rolls back alone.
3. Warm cron Auth-forward regresses to BYPASS (perf only; correctness intact).

## Prod smoke (after merge — CoS)

1. `GET` model `/nfl/fair-lines` (no persist) → `odds_persisted` zeros; warehouse ledger independent.
2. Beat/worker `pull_odds_snapshot` still inserts snapshots.
3. `/api/edge-board/nfl/assemble?slate=week1` 200; `?slate=full` multi-week or 503 (never week1-sized full).
4. Cold → warm → repeated: warm cron `alerts` without `cdn_bypass`; HIT within 45s band.
5. Confirm no uncontrolled Odds spend from full-slate warm (path absent).
