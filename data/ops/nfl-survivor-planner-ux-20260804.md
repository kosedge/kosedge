# NFL Survivor Planner UX — ops note

**Date:** 2026-08-04  
**Engine:** `nfl-season-engine-v1.12-survivor-planner-ux`  
**Capability:** `survivor_planner_ux` (keeps `survivor_planner`)  
**UI:** `/pro/nfl/survivor?mode=planner`  
**APIs:**
- `POST /nfl/season-engine/survivor/plan` (slate metrics + matchup enrichment)
- `POST /nfl/season-engine/survivor/suggest-paths` (heuristic AI paths)
- BFF mirrors under `/api/nfl/season-engine/survivor/...`

**UI default sims:** `120` (BFF timeout 120s). Ops curls below use `80` for speed.

## What changed (feel)

| Before | After |
| --- | --- |
| Clear looked broken (stale server lock) | Clear / Reset fully clears picks, URL, localStorage |
| Chip: `SEA 61% · .38` | Chip: `SEA 61% vs ARI` (favorite highlighted; no pick_now clutter) |
| Hero = joint path survival → ~0% on 17 picks | Hero = slate grade + avg weekly WP + danger weeks + best left |
| Dry spreadsheet energy | Command strip, lock flash, one-click AI paths |

## Hero metrics (formulas)

Documented in `PATH_FORMULA_NOTES` (`survivor.py`):

1. **avg_locked_wp** — mean of each locked pick’s marginal week WP (`wins_in_week / n_sims`).
2. **danger_weeks** — count of locked picks with WP &lt; 55%.
3. **best_remaining_equity** — max chalk WP among unused teams still playing in open weeks (`null` / “Full” when slate complete).
4. **slate_grade** — letter from avg WP (A≥70%, B≥62%, C≥55%, D≥48%, else F), downgraded one letter per two danger weeks.
5. **slate_score** — `round(100 * avg_locked_wp) - 4 * danger_weeks` (floor 0).

**Joint path survival** remains in the payload and UI under “Advanced” — honest, but demoted because a 17-leg parlay collapses toward ~0.

## AI suggested paths

`suggest_survivor_paths` runs the **same** team W/L season matrix (not an LLM) and fills unused weeks with three heuristics:

| ID | Label | Rule |
| --- | --- | --- |
| `chalk` | Chalk | Each week: max `win_rate` among unused |
| `balanced` | Balanced | Each week: max `pick_now_score` |
| `contrarian_save` | Contrarian save | Among WP≥55% (else all), min `save_score` |

UI loads a path with one click; user can edit any week afterward.

## Smoke

```bash
# Planner + new metrics
curl -sS -X POST "$MODEL/nfl/season-engine/survivor/plan" \
  -H "content-type: application/json" -H "x-kosedge-secret: $SECRET" \
  -d '{"season":2026,"n_sims":80,"seed":42,"picks":{"1":"SEA"},"top_n":5}' \
  | jq '{engine_version, slate_grade, avg_locked_wp, danger_weeks, best_remaining_equity, path_survival}'

# Suggested paths
curl -sS -X POST "$MODEL/nfl/season-engine/survivor/suggest-paths" \
  -H "content-type: application/json" -H "x-kosedge-secret: $SECRET" \
  -d '{"season":2026,"n_sims":80,"seed":42}' \
  | jq '.paths[] | {id, label, pick_count, slate_grade, avg_locked_wp}'

# Status capability
curl -sS "$MODEL/nfl/season-engine/status" \
  | jq '{engine_version, caps: [.capabilities[] | select(test("survivor"))]}'
```

## Mobile (no regression vs PR #94)

- Sticky hero under `--kos-pro-header-h`
- Week rows `scroll-mt` accounts for sticky metrics
- Controls keep `min-h-11` (~44px) touch targets
- Verify at 390×844: Clear, pick SEA sees vs ARI, metrics update, Load Chalk

## Limits

1. Suggested paths are greedy heuristics — not pool-aware EV.
2. Underlying Layers 1–4 / cal-v2 knobs unchanged from v1.11.
3. Edge Board / KEI untouched.
