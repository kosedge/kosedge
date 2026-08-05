# CFB Player ↔ Team Total Coherence (v0.8.3)

**Date:** 2026-08-05  
**Engine:** `cfb-season-engine-v0.8.3-player-coherence`  
**Branch:** `feat/cfb-player-coherence` → `deploy-vercel`  
**Scope:** Tightening pass on player hooks so QB/skill rows stay reconciled with team pools and respond to projected game script. Team scores / spreads / totals / WP unchanged. Tracking (v0.8.2) intact.

## Rules

### Consistency

1. **Allocation-only** — Player yards/TDs are role-share allocations of team pools derived from expected points. They never feed back into team expected scores, spread, total, or win probability.
2. **Named ≤ pool** — For each side: named QB pass yards ≤ team pass yards; named rush yards ≤ team rush yards; named receiving yards ≤ team pass yards. Residual `"other"` absorbs the rest.
3. **Star soft-caps** (excess → residual, not renormed onto other named players):
   - Rush: single RB ≤ 48% of team rush yards
   - Rec: single skill ≤ 30% of team pass yards
   - Pass: QB soft-cap relative to named pass pool (backup already depth-capped)
4. **Aggregate scale** — If rounding would push named sum over the pool, scale that field down and record a `coherence.adjustments` entry.

### Game-script awareness

Script is derived from **projected** margin (`own_exp − opp_exp`) and side win probability — not a drive sim.

| Detail | Margin (pts) | Allocation effect |
| --- | --- | --- |
| `large_lead` | ≥ +14 | Lower pass_rate; RB1 (+ depth) rush share up; WR1 trim / WR depth up |
| `small_lead` | ≥ +4 | Milder lead effects |
| `neutral` | (−4, +4) | Baseline role shares |
| `small_deficit` | ≤ −4 | Milder trail effects |
| `large_deficit` | ≤ −14 | Higher pass_rate; WR1 + RB checkdown share up; QB designed-rush share down |

Pass-rate deltas apply **only** to the player allocation pool (yards split), not to team projected points.

### Diagnostics

Visible on `POST /cfb/season-engine/project-game`:

- `drivers.player_projections.by_team.<TEAM>.game_script` — detail, intensity, pass_rate_delta
- `drivers.player_projections.by_team.<TEAM>.coherence` — `applied`, `adjustments[]`, `aggregates_within_pools`
- Top-level `coherence_adjustments_applied` / `script_aware`
- UI `/pro/cfb/project-game` shows script label + “coherence caps applied” when relevant

## Before / after examples

### Same team pool, script contrast (UGA hooks, 35 expected pts)

| | Neutral (28–27) | Large lead (42–14) |
| --- | --- | --- |
| Allocation pass yards | higher | lower |
| Allocation rush yards | lower | higher |
| RB1 `rush_share` | baseline | ↑ |
| WR1 `rec_share` | baseline | ↓ |
| WR2 `rec_share` | baseline | ↑ |
| Team expected score | **unchanged** | **unchanged** |

### Live project-game — UGA vs BALL · Week 5

Favorite tagged `large_lead`; named pass/rush/rec aggregates ≤ team pools; `does_not_modify_team_totals: true`. Close rivalry (OSU–MICH) keeps milder script detail while the same reconcile rules hold.

### MICH @ OSU · Week 1 (spot-check)

Player layer still allocation-only vs `project_game` baseline (scores/spread/total/WP identical). Residual other remains.

## Files

- `services/model-service/src/services/cfb_season_engine/player_hooks.py` — script signal, soft-caps, reconcile, diagnostics
- `services/model-service/src/services/cfb_season_engine/priors.py` — version + knobs
- `services/model-service/tests/test_cfb_season_engine.py` — coherence + blowout vs close
- `apps/web/components/pro/cfb/CfbProjectGameClient.tsx` — script / coherence labels

## Remaining gaps

- No drive-by-drive or clock-phase sim (single projected-script snapshot)
- Soft-caps are transparent priors, not prop-calibrated
- Residual “other” still large when packaged depth is thin
- No completions / air yards / RZ micro-model
- Tracking lake schema unchanged (v0.8.2)

## Tests

```bash
cd services/model-service && python -m pytest \
  tests/test_cfb_season_engine.py \
  tests/test_cfb_real_roster.py \
  tests/test_cfb_performance_tracking.py -q
```

## Deploy / smoke

1. Merge PR → `deploy-vercel`
2. Railway model-service: `GET /cfb/season-engine/status` → `engine_version` contains `v0.8.3-player-coherence`
3. `POST /cfb/season-engine/project-game` UGA@BALL → `drivers.player_projections.by_team.UGA.game_script.script_detail == large_lead`
4. `https://www.kosedge.com/pro/cfb/project-game` — player table + script label
5. Tracking endpoints still healthy; Edge Board CFB markets-only
