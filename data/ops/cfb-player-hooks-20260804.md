# CFB Player Hooks — QB + Skill (v0.7)

**Date:** 2026-08-04  
**Engine:** `cfb-season-engine-v0.7-player-hooks`  
**Branch:** `feat/cfb-player-hooks` → `deploy-vercel`  
**Scope:** First player-level projection layer on project-game. Team scores / spreads / totals unchanged. Edge Board CFB stays markets-only.

## What player hooks produce

For each side of a project-game matchup:

| Output | Who | Notes |
| --- | --- | --- |
| Pass yards / pass TDs / INTs | QB depth (QB1 dominates) | Allocated from team pass pool |
| Rush yards / rush TDs | RB1/RB2 (+ small QB rush) | Feature vs committee label when clear |
| Rec yards / rec TDs | WR1/WR2, TE1/TE2, RB checkdowns | Role priors × usage share |
| Residual "other" | Unnamed depth | Named shares sum **≤** team totals |

Response fields on `POST /cfb/season-engine/project-game`:

- `player_projections` (canonical)
- `players` (alias)
- `player_hooks` (identity summaries with `role`)
- `drivers.player_projections` (team totals + residual diagnostics)

## Methodology (transparent)

1. **Team pool** from expected points (already projected by Layers 1–4):
   - `total_yards ≈ expected_points × 14.2`
   - Pass/rush split from `pass_rate = league_pass_rate + pass_rate_bias`
   - Offensive TDs ≈ `points / 7.2`; pass vs rush TD share follows pass rate
   - INTs ≈ pass attempts × base INT rate, tempered by QB situation index + supporting cast
2. **Identity** from ESPN packaged roster snapshot v0.6 (`packaged_espn_roster_2026`) — real names, depth order within position.
3. **Role shares**
   - QB: depth-1 soft-capped to lead; residual pass volume for backup + other
   - RB: usage/depth weights inside rush pool; QB rush share tied to situation/talent
   - Receiving: WR1 > WR2 > TE1 > RB1 priors × usage; residual other
4. **Does not feed back** into team expected scores, spread, total, or win probability.

## Example game — MICH @ OSU · Week 1

Packaged universe, engine `cfb-season-engine-v0.7-player-hooks`:

| Field | Value |
| --- | --- |
| Projected score | 31.85 – 36.93 (Away – Home) |
| Spread / total / home WP | OSU −5.08 / 68.78 / 59.6% |
| Team totals unchanged | Player layer is allocation-only |

**OSU team pool:** pass 388 / rush 136 yds · 3.0 pass TD / 2.1 rush TD · residual pass 15.5 / rush 13.6

| Player | Role | Pass | pTD | INT | Rush | Rec |
| --- | --- | --- | --- | --- | --- | --- |
| Julian Sayin | QB1 | 344.6 | 2.67 | 1.03 | 15.1 | — |
| Justyn Martin | QB2 | 27.9 | 0.22 | 0.08 | 1.3 | — |
| Ja'Kobi Jackson | RB1 (feature) | — | — | — | 59.5 | 46.0 |
| Bo Jackson | RB2 | — | — | — | 46.8 | 26.8 |
| Brandon Inniss | WR1 | — | — | — | — | 99.7 |
| David Adolph | WR2 | — | — | — | — | 69.0 |
| Bennett Christian | TE1 | — | — | — | — | 53.7 |

**MICH team pool:** pass 335 / rush 118 yds · Bryce Underwood QB1 **297** pass yds / 2.3 pTD; John Volker RB1; Anthony Simpson WR1 **86** rec yds.

Always check `drivers.player_projections.by_team.*.team_totals` + `residual` for the live allocation math.

## Limitations

- Approximate role shares — **not** a calibrated prop / box-score engine
- Packaged depth is thin (≈2 players per skill position); residual "other" is intentional
- Usage shares in the snapshot are production-depth proxies, not measured snap%
- No completions, air yards, routes, or red-zone micro-model
- Team scoring still approximate (v0.6.1 calibration); player yards inherit that
- No Edge Board KEI / market-grade player props

## UI

`/pro/cfb/project-game` — scannable QB + skill table under the market card (mobile horizontal scroll). Labeled **approximate**.

## Tests

`services/model-service/tests/test_cfb_season_engine.py`:

- Engine version `cfb-season-engine-v0.7-player-hooks`
- QB1 pass yards > QB2
- Named pass/rush/rec shares ≤ team pools
- Team scores/spread/total/WP unchanged vs pre-attach baseline
- Depth order assigned within position from ESPN list order

## Deploy

1. Merge PR → `deploy-vercel` (Vercel web + model-service image path used by Railway when that branch is live)
2. Smoke: `GET /cfb/season-engine/status` → `engine_version` contains `v0.7-player-hooks`
3. Smoke: `POST /cfb/season-engine/project-game` MICH@OSU → `player_projections` present
4. Smoke: `https://www.kosedge.com/pro/cfb/project-game` shows player table under market card
5. Confirm `/edge-board/cfb` still markets-only
