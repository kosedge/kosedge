# NFL Season Engine — Harden & Validate (v1.4.1)

**Date:** 2026-08-03  
**Branch:** `feat/nfl-season-engine-harden` → `deploy-vercel`  
**Engine version before:** `nfl-season-engine-v1.4-survivor`  
**Engine version after:** `nfl-season-engine-v1.4.1-hardened`  
**Scope:** Trustworthiness + inspectability (no new modeling features / no UI)

Artifacts: `data/ops/nfl-season-engine-harden-20260803/`  
Contract: `data/ops/nfl-season-engine-api-contract-20260803.md`

## What was hardened / fixed

1. **Dual-form player name matching** — `Christian McCaffrey` now resolves to demo/DB `C.McCaffrey` (initial.last ↔ First Last + last-name uniqueness). Previously injury paths silently no-oped with `player_not_found_on_roster`.
2. **Team alias** — `LAR` → `LA` in injury path parse/match.
3. **`include_diagnostics`** — Optional structured explain payloads (usage shares, share integrity, injury adjustments, bye teams). Game-boxes default **off**; simulate/survivor default **on**.
4. **Leaner game-boxes notes** — Removed opaque stringified share dumps from default `notes`; moved to diagnostics.
5. **NaN / finite guards** — Season aggregate distributions drop non-finite samples.
6. **Missing-team guards** — `build_game_script` uses league-average placeholder; `evolve_after_game` no-ops if a club is absent (no KeyError).
7. **Empty / thin rosters** — Empty usage returns `[]`; residual **other** absorbs volume when RB2 missing.
8. **Survivor bye documentation** — Explicit `bye_handling` in formula notes + `bye_teams_this_week` in diagnostics; bye teams excluded from `ranked_picks`.
9. **Share integrity helper** — `share_integrity_summary` asserts modeled shares + residual other = 1.0.
10. **Regression tests** — `tests/test_nfl_season_engine_harden.py` (name match, CMC realloc, thin roster, BUF@KC bounds, win spread, survivor bye/used, diagnostics flag).
11. **Validation CLI** — `scripts/nfl/harden_validate_season_engine.py`.

## Numerical deltas (demo, seed=2026)

| Check | Result | Notes |
| --- | --- | --- |
| Season win means (40 sims) | min **5.63**, max **10.85**, spread **5.23**, σ **1.48**, sum **272.0** | Not collapsed; no NaNs |
| BUF@KC Cook rush | **54.1** yds | Within Cook/Rice-style v1.3 bounds (<110) |
| BUF@KC Rice rec | **54.3** yds | <120 |
| BUF@KC Mahomes pass | **243.8** yds | In GAME_SANITY QB band |
| CMC full-name match | **matched** → `C.McCaffrey` | Was broken before |
| Mason rush share Δ (CMC out) | **+0.45** absolute share | Role-aware RB2 sink |
| Mason rush yds Δ (boxes) | **+45.4** | Healthy → CMC-out week 2 |
| CMC rush when out | **0.0** | Outside week range: no-op |
| Survivor already_used | KC/BUF excluded | Pass |
| Demo byes | 0 | Round-robin; documented |

**Modeling knobs unchanged** (efficiency, script matrix, strength evolution, survivor scoring weights). Numerical box/season means match v1.4 within MC noise — this pass is defensive/observability.

## Validation checklist

- [x] Season win distributions not collapsed / no NaNs  
- [x] Box scores: no inflated WR/RB (Cook/Rice bounds)  
- [x] Injury multi-week: in-range applies; outside no-op  
- [x] Thin roster / missing RB2: no crash; residual other  
- [x] Survivor: already_used excluded; bye handling documented  
- [x] Response field naming consistency (`engine_version`, `point_estimate`, `ranked_picks`, …)  
- [x] Tests green; harden regression suite added  

## Remaining risks

1. Demo round-robin schedule ≠ real 2026 byes/matchups — always check `mode` / `schedule_match`.  
2. Last-name-only injury matches can collide on common surnames (Johnson) — prefer `player_key`.  
3. Survivor heuristics still not multi-entry EV / field-aware.  
4. Strength evolution still placeholder drift (calibrated, not walk-forward fitted).  
5. QB rush (Allen) still light vs career — known thin Layer-3/4 prior.  
6. HTTP `n_sims` still capped at 500; heavy runs via CLI.  
7. No auto injury-report ingest.

## Files changed (high level)

- `services/model-service/src/services/nfl_season_engine/*` (calibration version, injury match, game_query diagnostics, season_sim finite stats, survivor bye notes, player_usage integrity, game_script/team_strength guards)
- `services/model-service/src/routes/nfl.py` (`include_diagnostics`, contract pointer on status)
- `services/model-service/tests/test_nfl_season_engine_harden.py` + version assertion updates
- `scripts/nfl/harden_validate_season_engine.py`
- `data/ops/nfl-season-engine-api-contract-20260803.md`
- `data/ops/nfl-season-engine-harden-validate-20260803.md` (this file)
- `data/ops/nfl-full-model-foundation-report.md`
- `data/ops/nfl-season-engine-harden-20260803/*` artifacts

## How to re-run

```bash
cd services/model-service && python3 -m pytest tests/test_nfl_season_engine*.py -q
python3 scripts/nfl/harden_validate_season_engine.py --demo --n-sims 40
```
