# NFL Survivor Planner (17-week) — ops note

**Date:** 2026-08-04  
**Engine:** `nfl-season-engine-v1.10-survivor-planner`  
**Capability:** `survivor_planner`  
**UI:** `/pro/nfl/survivor` → **17-week planner** tab (single-week helper retained)  
**API:** `POST /nfl/season-engine/survivor/plan`  
**BFF:** `POST /api/nfl/season-engine/survivor/plan`

## How to use

1. Open `https://www.kosedge.com/pro/nfl/survivor` (or local `/pro/nfl/survivor`).
2. Stay on **17-week planner** (default). Single-week helper remains under the other tab.
3. Lock a team for a week via recommendation chips or the week dropdown.
4. Used teams disappear from other weeks; path survival updates after a short debounce (~450ms).
5. Clear a week or **Reset plan**. Picks persist in `localStorage` + `?picks=1:CHI,2:ATL,…` / `?mode=planner`.

Default planner sims: **250** (BFF). Ops example below used **80** for speed.

## Path survival formula

```
path_survival = (# season sims where every locked (week, team) wins) / n_sims
```

- Empty slate → `1.0` (vacuous) / band **Empty**.
- Same team W/L paths as single-week survivor (Layers 1–2; Layers 3–4 skipped).
- **path_strength** band from geometric mean of locked *marginal* week WPs:
  - Strong ≥ 0.68
  - OK ≥ 0.55
  - else Fragile

Inspectable notes also live in `PATH_FORMULA_NOTES` (`survivor.py`).

## Example (packaged 2026 schedule, seed=42, n_sims=80)

| Step | Locked slate | Path survival | Strength (geo) | Notes |
| --- | --- | --- | --- | --- |
| 0 | _(none)_ | **100%** | Empty | 18 REG weeks present |
| 1 | W1 **CHI** | **61.25%** | OK (0.61) | W1 top pick-now was CHI (DET higher raw WP) |
| 2 | + W2 **ATL** | **43.75%** | OK (0.67) | CHI excluded from later weeks |
| 3 | + W3 **CLE** | **26.25%** | Strong (0.68) | Joint drops; geo of chalk marginals stays high |

After three locks, Week 4 top remaining included BAL / NYG / CIN / KC / BUF (CHI/ATL/CLE removed).

Bye rejection: `{"5":"KC"}` → `400` / `ValueError`: *Team KC is on bye or not scheduled in week 5*.

## Limitations

1. Joint path survival ≠ multi-entry / field-aware pool EV.
2. Heuristic pick-now / save scores unchanged from v1.4; planner only adds joint survival + multi-week ranks.
3. HTTP sims capped; planner default 250 — heavier runs belong on CLI/worker.
4. Strength band uses marginal geo mean (can read Strong while joint % is modest after many locks).
5. Does not change Edge Board / KEI / box-score layers.

## Smoke checklist

```bash
# Model-service
curl -sS -X POST "$MODEL/nfl/season-engine/survivor/plan" \
  -H "content-type: application/json" -H "x-kosedge-secret: $SECRET" \
  -d '{"season":2026,"n_sims":80,"seed":42,"picks":{"1":"CHI","2":"ATL"},"top_n":5}'

# Status capability
curl -sS "$MODEL/nfl/season-engine/status" | jq '.engine_version, .capabilities | map(select(.=="survivor_planner"))'

# Web
open https://www.kosedge.com/pro/nfl/survivor?mode=planner
```
