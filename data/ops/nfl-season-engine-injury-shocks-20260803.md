# NFL Season Engine — Injury & Availability Path Shocks

**Date:** 2026-08-03  
**Branch:** `feat/nfl-season-engine-injury-shocks` → `deploy-vercel`  
**Base:** `nfl-season-engine-v1.1-calibrated` (PR #72)  
**Engine version after:** `nfl-season-engine-v1.2-injury-shocks`  
**Scope:** Additive injury/availability paths inside `nfl_season_engine` only. Edge Board / Model-vs-KEI (#70) untouched. No survivor outputs; no major recalibration.

## Goal

Answer: **“what happens if Player X misses Weeks 4–8?”** by propagating availability through the four-layer hierarchy:

1. **team_strength** — temporary offense-index shock (value-weighted)
2. **game_script** — responds via adjusted O/D (win prob / totals / pass bias)
3. **player_usage** — injured role scaled; teammates absorb freed volume
4. **production** — new usage + script → box scores / season totals

## Representation

Explicit `InjuryPath` structs (`injury_paths.py`):

| Field | Meaning |
| --- | --- |
| `player_key` / `player_name` | Identity (key preferred; name fallback) |
| `team` | Club code |
| `status` | `out` \| `limited` \| `returning` |
| `week_start` / `week_end` | Inclusive week range |
| `availability` | Limited fixed fraction (default 0.50); returning ramp start (default 0.40) |
| `severity` | Optional 0–1 metadata; mildly reduces limited availability |

**Availability math**

- Outside range → `1.0` (unaffected)
- `out` → `0.0`
- `limited` → fixed fraction (severity optional nudge)
- `returning` → linear ramp from start availability → `1.0` across the range

Known current injuries and hypothetical future paths use the same struct; both are applied week-by-week inside season sims and for the query week in game-boxes.

## Team-strength impact (documented)

```
offense_delta = −player_offense_value(role) × (1 − availability)
offense_index' = clamp(offense_index + sum(deltas), …)   # cap ±0.22 / team / week
defense_index unchanged
```

`player_offense_value` (healthy full role):

| Role | Approx value |
| --- | --- |
| QB1 | 0.12 |
| RB workhorse | ~0.03–0.08 from rush/target shares |
| WR1 | ~0.04 from target share |
| TE1 | ~0.03 from target share |

Pass-rate bias nudges: RB missing → slightly more pass; WR1/QB1 missing → slight pass down.

**Path evolution:** injury shocks are *temporary overlays* for the game week. `evolve_after_game` still updates the unshocked path strength book.

## Usage reallocation rules

Freed volume = `role_share × (1 − availability)`. Of that freed volume:

- **~10%+ residual** stays in the calibration **“other”** bucket (same absolute-share philosophy as cal-v1 — do not inflate sparse backups to 100%).
- Remainder is position-aware:

| Injured | Absorption |
| --- | --- |
| **RB** | Rush → RB2/committee by depth × existing rush share. Targets → 70% other RBs / 30% WR+TE |
| **WR** | Targets → WR corps 70% / TE 20% / RB 10% |
| **TE** | Targets → TE2 35% / WR corps 65% |
| **QB** | Snap → QB2; most designed-rush value lost to other; small rush spill to RB1 |

Snaps / routes / red-zone shares follow the same spirit (same-position first).

`limited` and `returning` scale the *same* machinery by availability (e.g. 50% limited → half shock, half reallocation).

## API / CLI (optional; non-breaking)

```http
GET  /nfl/season-engine/status          # engine_version includes v1.2-injury-shocks
POST /nfl/season-engine/simulate        # optional body.injury_paths
GET  /nfl/season-engine/game-boxes      # unchanged (no paths)
POST /nfl/season-engine/game-boxes      # optional body.injury_paths
```

Body shape:

```json
{
  "injury_paths": [
    {
      "player_name": "C.McCaffrey",
      "team": "SF",
      "status": "out",
      "week_start": 4,
      "week_end": 8
    }
  ]
}
```

CLI:

```bash
python scripts/nfl/run_hierarchical_season_sim.py --demo --sample-game SEA@SF --week 6 \
  --injury-paths '[{"player_name":"C.McCaffrey","team":"SF","status":"out","week_start":4,"week_end":8}]'
```

## With / without example (demo universe)

Artifact: `data/ops/nfl-season-engine-injury-shocks-20260803/with_without_cmc.json`  
Scenario: **C.McCaffrey OUT weeks 4–8**; sample game **SEA @ SF, week 6**, 300 reps, seed 2026.

### Game boxes (week 6)

| Metric | Healthy | CMC out |
| --- | --- | --- |
| SF home win prob | **0.628** | **0.588** |
| Expected total | 44.59 | 43.14 |
| CMC rush yds / carries | **62.6 / 14.3** | **2.3 / 0.5** |
| CMC targets | 5.6 | 0.0 |
| J.Mason rush yds / carries | **23.4 / 5.9** | **70.3 / 16.9** |

Week 3 (outside range) CMC rush identical with/without path: **60.4**.

### Season (30 paths, seed 2026)

| Metric | Healthy | CMC out W4–8 |
| --- | --- | --- |
| SF mean wins | **10.93** | **9.63** |
| CMC rush / rec yds | **1065 / 528** | **769 / 391** |
| Mason rush yds | **412** | **637** |

## Files

| Path | Role |
| --- | --- |
| `…/nfl_season_engine/injury_paths.py` | Structs, availability, reallocation, strength shock |
| `…/season_sim.py` / `game_query.py` | Week-aware apply before Layers 2–4 |
| `…/calibration.py` | `ENGINE_VERSION = nfl-season-engine-v1.2-injury-shocks` |
| `…/routes/nfl.py` | Optional body + POST game-boxes |
| `scripts/nfl/run_hierarchical_season_sim.py` | `--injury-paths` |
| `tests/test_nfl_season_engine_injury_paths.py` | Required coverage |

## Tests

```bash
cd services/model-service && python3 -m pytest tests/test_nfl_season_engine*.py -q
# 20 passed
```

Coverage:

- out for week range zeros/reduces injured usage
- teammates absorb volume
- team strength shifts when star out
- limited vs full out differ
- week outside range unaffected
- game boxes + season totals respect paths

## Remaining limitations

1. Tiny Dirichlet residual can leave &lt;1 carry on a fully-out RB (alpha floor); practically near-zero.
2. No automatic ingest of live injury reports into paths (caller supplies JSON).
3. Strength values are transparent priors, not fitted win-probability deltas.
4. No depth-chart auto-promotion beyond share reallocation (no new phantom players).
5. Defense / special-teams injuries not modeled.
6. Returning ramp is linear (no practice-participation curve).

## Railway

Model-service `/nfl/season-engine/*` reads `DEFAULT_SEASON_ENGINE_VERSION`. Deploy the `kosedge` Railway service after merge (project `joyful-clarity`) so live HTTP serves `v1.2-injury-shocks`. Smoke:

```bash
curl -sS "$MODEL_SERVICE_URL/nfl/season-engine/status"
# POST game-boxes with/without injury_paths body and compare SF CMC week 6
```
