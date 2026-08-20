# Phase 3B prod rematerialize — confirmed (2026-08-20)

**Status:** prod/worker DB on Phase 3B means  
**Code:** `#267` (3B knobs) + `#268` (worker `REPO_ROOT` crash fix)  
**Spine:** `player-production-v3-phase3b`  
**LIVE:** still `false`

## Incident during rematerialize

1. Merge `#267` → Railway deploy left **worker+beat Crashed** (`parents[5]` IndexError under path-as-root).
2. Ops curl rebuilds without `weeks=` only rematerialized **week 22** and nearly wiped season features (2023: 21 rows; 2024: 0).
3. Fixed via `#268`; worker Online; then **direct rematerialize against Railway public Postgres** (Celery queue was backlogged / unreliable for 54-week jobs).

## Prod coverage after rematerialize

| Season | Features | Baselines (w1–18+) |
|--------|----------|---------------------|
| 2023 | 5628 | 5402 |
| 2024 | 5568 | 5313 |
| 2025 | 5612 | 5612 |

## 3B prod baseline (cap-17 pool, season 2025)

| Metric | Local 3B (ops) | **Prod after remat** |
|--------|----------------|----------------------|
| Max QB pass | 4591 | **4590** |
| QBs ≥ 4000 | 5 | **4** |
| Pass↔rec gap | 0.172 | **0.170** |

Equality: props == fantasy on prod sample (`spine_unify_phase1_equality.py` season=2025 week=1).

## Ops note for future rebuilds

Always pass explicit weeks:

```bash
curl -X POST ".../nfl/ops/rebuild-props-layers?season=2025&weeks=1,2,...,18&model_version=nfl-player-v1"
```

Bare `season=` alone resolves to `MAX(week)` only.

## C1 readiness

Gap still ~0.17 → **Phase 3C recouple** is in scope. Do not start C1 against laptop-only DB; this file is the prod baseline.
