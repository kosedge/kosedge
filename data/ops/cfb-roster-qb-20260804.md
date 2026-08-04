# CFB Roster Construction + QB Situation (v0.2)

**Branch:** `feat/cfb-roster-qb` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.2-roster-qb`  
**Date:** 2026-08-04  
**Base:** `cfb-season-engine-v0.1-foundation` (PR #95)

## Goal

Deepen the two CFB-specific layers that should drive identity in 2026:

1. **Roster construction** → inspectable `roster_strength`
2. **QB situation** → first-class `qb_situation_index`

Both must **materially** move `project-game` and `season-sim`. Architecture, NFL engine, and Edge Board CFB markets-only stay intact.

## How roster construction is calculated

```
returning_production = 100 * (0.65 * returning_snap_share + 0.35 * returning_start_share)

portal_net = portal_in_value - 0.70 * portal_out_value + 35   # clamped 0–100

roster_strength =
    0.32 * returning_production
  + 0.26 * portal_net
  + 0.26 * recruiting_class_score
  + 0.16 * experience_index
```

| Field | Meaning | Provenance |
| --- | --- | --- |
| `returning_snap_share` | Prior-year snap share returning (0–1) | Curated/estimated in packaged JSON (not live SNAP%) |
| `returning_start_share` | Prior-year start share returning (0–1) | Curated/estimated |
| `portal_in_value` / `portal_out_value` | Portal talent in / production out | Approximate composites |
| `recruiting_class_score` | HS + transfer capital | Approximate composite |
| `experience_index` | Upperclass / starts distribution | Approximate |
| `roster_strength` | Layer-1 signal | Derived (formula solid; inputs approximate) |

Component breakdown is exposed on every team via `roster.components` in layer snapshots and `GET /cfb/season-engine/status` examples.

## How QB situation is calculated

```
supporting_cast = 0.55 * ol_support + 0.45 * weapons_support

talent_index = 1 + (qb_talent - 50) / 80
class_mult   = { incumbent: 1.10, portal: 0.96, open_competition: 0.88,
                 true_freshman: 0.80, unknown: 0.93 }
cast_mult    = 1 + 0.14 * (supporting_cast - 50) / 50

qb_situation_index = clamp(talent_index * class_mult * cast_mult, 0.55, 1.55)
qb_situation_score = 50 + (qb_situation_index - 1) * 80   # 0–100 mirror
```

Classification priority: explicit class → true freshman → open competition → portal → incumbent (if starts) → unknown.  
`portal_starter` is accepted as an alias for `portal`.

Uncertainty priors remain class-based (incumbent 0.18 … true_freshman 0.62), tempered slightly by supporting cast.

## How they drive team projection

Offense compose (primary drivers):

```
offense_score =
    0.40 * roster_strength
  + 0.36 * qb_situation_score
  + 0.14 * skill
  + 0.10 * ol

offense_index = score_to_index(offense_score)
offense_index = (1 - 0.42) * offense_index + 0.42 * (offense_index * qb_situation_index)
```

Defense still uses `roster_strength` plus front seven / secondary / experience. Historical team ratings are **not** primary.

## Team examples (packaged priors, mid-season week 5 neutral)

| Team | Profile | roster_strength | qb_class | qb_situation_index | offense_index |
| --- | --- | --- | --- | --- | --- |
| UGA | Stable power, incumbent QB, elite cast | ≈ 69.7 | incumbent | ≈ 1.55 | ≈ 1.55 |
| TEX | Blue-blood recruiting + incumbent | ≈ 69.6 | incumbent | ≈ 1.55 | ≈ 1.55 |
| FSU | Portal-heavy rebuild, portal QB | ≈ 55.0 | portal | ≈ 1.33 | ≈ 1.39 |
| COLO | Portal-heavy, true freshman QB | ≈ 57.0 | true_freshman | ≈ 1.10 | ≈ 1.20 |
| MICH | Open competition | ≈ 60.2 | open_competition | ≈ 1.16 | ≈ 1.28 |
| BALL | Placeholder mid-major | ≈ 50.8 | unknown | ≈ 0.93 | ≈ 0.95 |

### Projection deltas vs same opponent (BALL), week 5 neutral

| Matchup | home_win_prob | expected score |
| --- | --- | --- |
| UGA vs BALL | ≈ 0.92 | ≈ 43.4 – 18.6 |
| FSU vs BALL | ≈ 0.83 | ≈ 38.8 – 21.8 |
| COLO vs BALL | ≈ 0.73 | ≈ 33.3 – 22.2 |

UGA − COLO win-prob gap ≈ **0.19** under identical opponent — roster + QB layers, not a historical rating knob.

### Holding other inputs fixed (talent=75, cast=70)

| qb_class | qb_situation_index | offense_index |
| --- | --- | --- |
| incumbent | ≈ 1.53 | ≈ 1.55 |
| portal | ≈ 1.33 | ≈ 1.39 |
| open_competition | ≈ 1.22 | ≈ 1.29 |
| true_freshman | ≈ 1.11 | ≈ 1.20 |

Incumbent − true_freshman offense gap ≥ **0.10** by design.

## Fidelity notes

**Solid (structure)**

- Snap/start weighting, portal-net, roster_strength weights
- QB classification + class offense multipliers
- Composition order: roster_strength + qb_situation_index as primary drivers
- Status / diagnostics component breakdowns

**Approximate (numbers)**

- Packaged snap/start shares, portal values, recruiting scores
- Named QB talent and depth identities
- Unit grades / supporting cast
- Win probs, spreads, totals, season-sim win means

**Still a gap**

- Live portal / returning-production / recruiting DB feeds
- Official full 2026 FBS schedule
- Market-grade calibration / KEI fair lines (Edge Board CFB stays markets-only)

## Entry points

```bash
python scripts/cfb/run_hierarchical_season_sim.py --status-only
python scripts/cfb/run_hierarchical_season_sim.py --demo --n-sims 50 --sample-game UGA@ALA --week 1 --neutral
```

- `GET  /cfb/season-engine/status` — includes examples + roster_strength ladder
- `POST /cfb/season-engine/project-game`
- `POST /cfb/season-engine/simulate`

Tests: `services/model-service/tests/test_cfb_season_engine.py`
