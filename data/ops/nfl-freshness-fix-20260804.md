# NFL freshness / connection errors fix — 2026-08-04

## Symptom
Pro NFL season-engine desks (`/pro/nfl/model`, `/game-boxes`, `/survivor`) showed **Data freshness degraded** (and felt like connection errors) even when the season engine was healthy.

## Root cause
1. Shared `NflDataFreshnessBanner` (via `SportProShell` on all `/pro/nfl/*`) probes Railway `GET /health/nfl-data-freshness`.
2. That probe runs DB-backed owned-data SLOs. With Railway Postgres unreachable (`/health/db` → 503 timeout), the health endpoint hangs (20s+ / no bytes).
3. www BFF aborted at ~8s → `freshness_fetch_failed` → amber **Data freshness degraded** banner.
4. Season engine itself was fine: `GET /nfl/season-engine/status` ~2.2–2.8s, `mode=real`, packaged 2026 schedule/depth, `engine_version=nfl-season-engine-v1.11-calibration`. Packaged fallback ≠ broken.

## Fix (web / deploy-vercel)
- Skip owned-data freshness banner on season-engine desk paths (`x-pathname` from `proxy.ts`).
- Treat transport/timeout freshness failures as `probe_unavailable` — do **not** show the degraded boards banner.
- Cap freshness probe timeout at 3s so other NFL pages do not stall on a hung DB probe.
- Season-engine status BFF budget → `UPSTREAM_TIMEOUT_MS.board` (12s) for 2–3s status latency.
- Surface **Using packaged 2026 schedule/depth** as informational when status sources are packaged.

## Confirmation (pre-merge prod snapshot)
| Check | Result |
|-------|--------|
| `/nfl/season-engine/status` | 200 ~2.2s, real + packaged |
| `/api/nfl/season-engine/status` | 200 ~2.8s |
| `/health/db` | 503 connection timeout |
| `/health/nfl-data-freshness` | hang / timeout |
| `/pro/nfl/model` | Ready for use + degraded banner (pre-fix) |

Post-merge: model/game-boxes/survivor should show ready/clean with packaged notice; no spurious degraded/connection banner when status is up.

## Note
Edge Board / KEI still use owned-data freshness when the probe returns real SLO blockers. Probe-unavailable no longer alarms those pages either (honest: we could not evaluate, not “data is stale”).
