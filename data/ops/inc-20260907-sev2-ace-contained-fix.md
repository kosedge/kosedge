# INC-2026-09-07 SEV-2 — A+C+E contained fix (Ryan ACCEPT 1/2/3)

**Status:** Draft PR only — do not merge from this note. Independent review outside agent.

**Scope (only):**
- **A** — Stop persist-on-GET for model-service `/nfl/fair-lines`
- **C** — Narrow NFL live Edge Board assemble window; full-slate **governed snapshot or fail-closed** (no live `daysAhead=200`)
- **E** — GO-1c warm cron hits public cache path (no Auth CDN BYPASS)

**Explicitly out:** B/D snapshot spine / Odds dedupe · F pageData timeout raise · unseal/promote/KEI mint/PLAY expand

## A — Zero Postgres writes on customer GET

| Before | After |
| --- | --- |
| `persist` Query default **True** — bare GET wrote `odds_snapshots` via `_persist_nfl_odds_events_for_training` | Default **False**; `persist=0` still honored; `persist=1` opt-in for ops only |
| Page-data relied on web sending `persist=0` | Model-service page-data path default non-persisting even if caller omits param |

Warehouse persist remains worker/beat `pull_odds_snapshot` (idempotent, observable).

**Tests (must appear in PR Quality CI logs):**
- `tests/test_nfl_projection_endpoints.py::test_nfl_fair_lines_get_default_zero_persist_writes`
- `tests/test_tasks_persistence.py::test_pull_odds_snapshot_persists_rows`

**CI wire:** `.github/workflows/pr-check.yml` — DepthSot/NFL job includes both node ids; dedicated step `NFL fair-lines GET zero-persist + worker snapshot proofs` when `nfl_ms=1`.

## C — Live window + full-slate governance

| Surface | Behavior |
| --- | --- |
| `slate=week1` / live | Fair-lines window `daysAhead=10`, `includePastDays=2` (live assemble) |
| `slate=full` | **Governed snapshot only** (`data/processed/edge_board_full_slate_nfl.json`). **No** live `daysAhead=200` customer path. Missing snapshot → **503 fail closed**. |
| Cache keys | `/api/edge-board/nfl/assemble?slate=week1` ≠ `?slate=full` |
| pageData | `UPSTREAM_TIMEOUT_MS.pageData` stays **25s**; maxDuration 30 |

**Full-slate data source (document):** shipped governed artifact via `loadGovernedNflFullSlate` / `requireGovernedNflFullSlate`. B/D spine (writer that materializes the artifact) is follow-on — until that ships, Full tab is honestly unavailable (503), not a cold 15–16s live 200d assemble.

**Fail-closed path:** `requireGovernedNflFullSlate()` throws → `pageDataUpstreamErrorResponse` → HTTP 503 `private, no-store`.

## E — Warm cron public path (bandage)

| Before | After |
| --- | --- |
| Warm fetch forwarded `Authorization: Bearer CRON_SECRET` → CDN **BYPASS** | Auth on cron route only; assemble GET is public + `x-kosedge-warm` |
| — | Bounded paths: NFL week1 + CFB week1 only (no full-slate warm / Odds spend) |
| — | Observe hooks: `x-vercel-cache`, `age`, `alerts` (`cdn_bypass` / `origin_error` / `cache_miss`) |

## Rollback

1. Revert this PR (or restore `persist: Query(True)` + prior assemble/warm/CI files).
2. Web already sends `persist=0` on page-data — temporary safety net if model-service rolls back alone.
3. Warm Auth-forward regresses to BYPASS (perf only; correctness intact).
4. Full-slate live 200d path returns (undesired) if C is reverted alone.

## Prod smoke (after merge — CoS)

1. `GET` model `/nfl/fair-lines` (no persist) → `odds_persisted` zeros; warehouse ledger independent.
2. Beat/worker `pull_odds_snapshot` still inserts snapshots.
3. `/api/edge-board/nfl/assemble?slate=week1` 200 (narrow); `?slate=full` 503 until governed snapshot exists (never live 200d / never week1-as-full).
4. Cold → warm → repeated: warm cron `alerts` without `cdn_bypass`; HIT within 45s band.
5. Confirm no uncontrolled Odds spend from full-slate warm (path absent).

## CI receipt (HEAD `560d70e1`)

| Proof | Test node | Result | CI |
| --- | --- | --- | --- |
| 1 | `test_nfl_fair_lines_get_default_zero_persist_writes` | **1 passed** | [PR Quality run 34164442192](https://github.com/kosedge/kosedge/actions/runs/34164442192) · step `NFL fair-lines GET zero-persist + worker snapshot proofs` |
| 2 | `test_pull_odds_snapshot_persists_rows` | **1 passed** | same run · log: `INC-2026-09-07 proofs 1+2 PASSED` |
| Gate | Web typecheck + Next build | pass | [Production Gate twin 34164442196](https://github.com/kosedge/kosedge/actions/runs/34164442196) |
| HEAD | `560d70e1` | draft | PR https://github.com/kosedge/kosedge/pull/503 |

Log excerpt (proofs step):
```
INC-2026-09-07 proof 1: test_nfl_fair_lines_get_default_zero_persist_writes
1 passed, 1 warning in 1.12s
INC-2026-09-07 proof 2: test_pull_odds_snapshot_persists_rows
1 passed in 1.28s
INC-2026-09-07 proofs 1+2 PASSED
```
