# NFL Season Engine — Public API Contract

**Engine version:** `nfl-season-engine-v1.9-real-2026`  
**Date:** 2026-08-03  
**Package:** `services/model-service/src/services/nfl_season_engine/`  
**Cutover note:** v1.9 defaults to the real 2026 REG schedule (272 games + byes). Modeling layers unchanged from v1.8 coaching. See `data/ops/nfl-season-engine-real-2026-20260803.md`.

Additive HTTP surface on model-service. Does **not** modify Edge Board, Model-vs-KEI (#70), or `nfl_market_projections`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/nfl/season-engine/status` | Version, mode, schedule_source, game count, layers, capabilities |
| `POST` | `/nfl/season-engine/simulate` | N path-coherent full-season sims |
| `GET` | `/nfl/season-engine/game-boxes` | Future-game player box distributions |
| `POST` | `/nfl/season-engine/game-boxes` | Same + optional `injury_paths` / diagnostics |
| `POST` | `/nfl/season-engine/survivor` | Survivor week rankings + path-value scores |

CLI: `scripts/nfl/run_hierarchical_season_sim.py`, `run_survivor_evaluate.py`, `harden_validate_season_engine.py`.

---

## Common fields

| Field | Meaning |
| --- | --- |
| `engine_version` | Semver-ish tag from `calibration.ENGINE_VERSION` |
| `mode` | `real` (default) or `demo` (explicit `demo=true` round-robin) |
| `schedule_source` | `nfl_dp_schedules` \| `packaged_wall_chart_2026` \| `demo_round_robin` |
| `schedule_game_count` | REG games loaded (expect 272 for 2026 real) |
| `roster_source` / `roster_as_of` | Depth identity source + freshness tag |
| `notes` | Short string map (sources, schedule_match, bye_handling, …) |
| `diagnostics` | Structured explain payload (see flag below) |
| `injury_paths` | Echo of applied path dicts when present |

### `include_diagnostics`

| Endpoint | Default | When true |
| --- | --- | --- |
| `game-boxes` | `false` | Usage shares, share integrity, injury adjustments, script summary, **`depth_structure`**, **`role_transitions`**, **`play_mix_home` / `play_mix_away` / `play_mix_sample`** (v1.6), **`red_zone` / `scoring_usage`** (v1.7), **`coaching_profile` / `tendency_effects`** (v1.8) |
| `simulate` | `true` | Win-mean spread/stdev, injury path echo, finite checks, **`depth_structure`**, **`role_transitions_sample`** |
| `survivor` | `true` | Scoring knobs, bye teams, used exclusions |

Query param and/or JSON body field. Default game-boxes responses stay lean; players always include `usage_role`, `personnel`, `point_estimate`, `distributions`.

---

## `GET /nfl/season-engine/status`

Returns `engine_version`, layer modules, `capabilities`, usage-role labels/rules, survivor formula notes, injury-path statuses, contract pointer.

---

## `POST /nfl/season-engine/simulate`

**Query:** `season`, `n_sims` (≤500 HTTP), `seed`, `demo`, `as_of_week`, `include_diagnostics`  
**Body (optional):** `{ "injury_paths": [...], "include_diagnostics": true }`

**Response (stable):**

```json
{
  "mode": "real|demo",
  "schedule_source": "packaged_wall_chart_2026",
  "schedule_game_count": 272,
  "season": 2026,
  "n_sims": 25,
  "games_per_season": 272,
  "engine_version": "nfl-season-engine-v1.9-real-2026",
  "notes": {},
  "diagnostics": {
    "mean_wins_sum": 272.0,
    "win_mean_min": 5.5,
    "win_mean_max": 11.2,
    "win_mean_spread": 5.7,
    "win_mean_stdev": 1.3,
    "injury_path_count": 0,
    "injury_paths": [],
    "depth_structure": {"DET": {"rb_structure": "committee", "wr_hierarchy": "clear"}},
    "role_transitions_sample": []
  },
  "injury_paths": [],
  "top_teams_by_wins": [{"team": "KC", "mean": 11.1, "p10": 8, "p50": 11, "p90": 14}],
  "top_players": [{"player_name": "P.Mahomes", "pass_yards_mean": 4100.0, "...": "..."}]
}
```

**Limitations:** HTTP caps `n_sims` at 500; demo schedule is round-robin (no byes); player totals are path aggregates not fantasy projections.

---

## `GET|POST /nfl/season-engine/game-boxes`

**Query:** `home_team`, `away_team`, `season`, `week`, `n_replicates`, `seed`, `demo`, `include_diagnostics`  
**POST body (optional):** `{ "injury_paths": [...], "include_diagnostics": true }`

**Player row (stable):**

| Field | Meaning |
| --- | --- |
| `player_key` / `player_name` / `team` / `position` | Identity |
| `usage_role` | Taxonomy label (QB1, RB1, WR2, …) |
| `personnel` | Inferred package (`pass_heavy` / `balanced` / `rush_heavy`) |
| `script` | Modal coarse script state observed in MC (`lead`/`trail`/`neutral`) |
| `script_detail` | Fine script detail when present (`large_lead` / `small_lead` / `neutral` / `small_deficit` / `large_deficit`) — v1.6 additive |
| `scoring_role` | RZ/scoring taxonomy when present (usually mirrors `usage_role`; may be `RB_GL`) — v1.7 additive |
| `point_estimate` | Mean of position-primary stats |
| `distributions` | `{stat: {mean, std, p10, p50, p90}}` |

Position-primary stats:

- QB: `pass_yards`, `pass_tds`, `ints`, `rush_yards`
- RB: `rush_yards`, `rush_tds`, `rec_yards`, `receptions`
- WR/TE: `rec_yards`, `receptions`, `rec_tds`

Volume counters (`pass_attempts` / `carries` / `targets`) always appear under `distributions`.

**Diagnostics (when requested):** `usage_shares_home/away`, `share_integrity_*`, `injury_adjustments`, `injury_paths`, `game_script_summary`, `schedule_match` (`on_loaded_schedule` vs `synthetic_matchup`), **`depth_structure`**, **`depth_structure_detail`**, **`role_transitions`** (v1.5), **`play_mix_home`**, **`play_mix_away`**, **`play_mix_sample`** (v1.6 — `pass_rate`, `early_down_pass_rate`, `hurry_up`, `script_detail`, `script_intensity`, `time_bucket`), **`red_zone`** / **`scoring_usage`** (v1.7 — team `rz_pass_rate_mean`, per-player `rz_carries_i20/i10`, `rz_targets_i20/i10`, `td_opportunity_share`, static scoring-role tables), **`coaching_profile`** / **`tendency_effects`** (v1.8 — team profile fields + applied pass/RZ/script-aggression deltas).

**Limitations:** Single-game marginal MC (strengths frozen; no in-path evolution). Matchups missing from the loaded schedule are synthesized. Demo skill cores are sparse — residual **other** absorbs unnamed volume (by design; prevents WR1/RB1 inflation).

---

## `POST /nfl/season-engine/survivor`

**Body:**

```json
{
  "season": 2026,
  "week": 5,
  "n_sims": 300,
  "seed": 42,
  "already_used": ["KC", "BUF"],
  "injury_paths": [],
  "demo": true,
  "as_of_week": 1,
  "top_n": 16,
  "include_diagnostics": true
}
```

**Response (stable):**

| Field | Meaning |
| --- | --- |
| `ranked_picks` | Remaining teams that **play** this week, ordered by `pick_now_score` |
| `all_teams_week` | Every team’s week row (incl. used / bye) |
| `already_used` | Normalized team codes (`LAR`→`LA`) |
| `formula` | Inspectable save / pick-now / bye notes |
| `win_rate` / `win_prob` | `wins_in_sims / n_sims` (bye → 0) |
| `save_score` / `future_value` | Future-value heuristic (aliases) |
| `pick_now_score` | This-week lean score |

**Bye handling:** `plays_this_week=false` → excluded from `ranked_picks`; future bye weeks skipped in save_score (not treated as losses). Demo round-robin has **no** byes; DB schedules may.

**Limitations:** Heuristic path value, not full multi-entry EV / field correlation. Layers 3–4 skipped (team W/L only).

---

## Injury path body schema

```json
{
  "team": "SF",
  "status": "out|limited|returning",
  "week_start": 4,
  "week_end": 8,
  "player_key": "optional",
  "player_name": "C.McCaffrey",
  "availability": 0.5,
  "severity": 0.0
}
```

Name matching: `player_key` preferred; otherwise dual-form names (`Christian McCaffrey` ↔ `C.McCaffrey`) and last-name uniqueness on team. `LAR` normalized to `LA`.

Statuses:

- `out` → availability 0 in range  
- `limited` → fixed availability (default 0.50)  
- `returning` → linear ramp from availability/default 0.40 → 1.0  

Weeks outside `[week_start, week_end]` leave roles/strengths unchanged.

---

## Naming consistency

Prefer these names in clients (do not invent aliases):

- `engine_version` (not `version`)
- `point_estimate` + `distributions` (game boxes)
- `ranked_picks` / `already_used` / `pick_now_score` / `save_score`
- `usage_role` (not `role_label`)
- `depth_structure` / `role_transitions` (diagnostics; v1.5 additive)
- `red_zone` / `scoring_usage` (diagnostics; v1.7 additive)
- `coaching_profile` / `tendency_effects` (diagnostics; v1.8 additive)
- `n_sims` / `n_replicates` (season vs game MC)

---

## Current limitations (contract-level)

1. Demo universe ≠ real 2026 schedule / depth charts  
2. Strength evolution is calibrated placeholder drift, not Bayesian  
3. INT / efficiency CVs are league-ish when baselines missing  
4. Survivor scores are inspectable heuristics, not pool EV  
5. No automatic injury-report ingest — callers supply `injury_paths`  
6. HTTP simulate capped; heavy runs use CLI  
