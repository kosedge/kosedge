# CFB Position Groups + Team Projection (v0.3)

**Branch:** `feat/cfb-position-projection` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.3-position-projection`  
**Date:** 2026-08-04  
**Base:** `cfb-season-engine-v0.2-roster-qb` (PR #96)

## Goal

Make **position groups** real, distinct projection drivers and tighten **team projection** / `project-game` so unit grades visibly move spreads, totals, and win probs — without regressing roster/QB contrasts (UGA > FSU > COLO).

## How position groups are calculated

Each unit (OL, skill/WR-TE-RB, front seven, secondary) is an inspectable composite:

```
unit_grade = 0.50 * talent + 0.30 * experience + 0.20 * portal_impact
```

| Component | Meaning | Provenance |
| --- | --- | --- |
| `talent` | Unit talent composite (recruiting / depth quality) | Packaged approximate; soft-fill from QB OL/weapons or recruiting when thin |
| `experience` | Unit experience / continuity | Blend of roster experience + returning production |
| `portal_impact` | Portal contribution to the unit | Blend of portal_in + unit talent prior |

**Headline rule:** When packaged JSON ships an explicit unit score (`ol: 90`), that headline is authoritative for projection. Components are still exposed for diagnostics and recompose near the headline.

**Thin / placeholder rule:** Flat all-50 placeholder rows are *not* treated as real grades. Runtime (and packaged enrichment) replaces them with distinct roster-derived unit fills so OL ≠ skill ≠ F7 ≠ secondary.

Special teams remain thin (optional ±1.5% total nudge only).

### Packaged enrichment (v0.3)

`cfb_fbs_team_priors_2026.json` now includes per-unit `components.{talent,experience,portal_impact}` for all 136 FBS rows. Curated (~74) headlines stay distinct; placeholder flats were rewritten to roster-derived distinct grades.

## How they drive team projection

### Offense compose

```
offense_score =
    0.34 * roster_strength
  + 0.30 * qb_situation_score
  + 0.18 * skill
  + 0.18 * ol

offense_index = score_to_index(offense_score)
offense_index = (1 - 0.40) * offense_index + 0.40 * (offense_index * qb_situation_index)
offense_index = (1 - 0.16) * offense_index + 0.16 * (offense_index * ol_index)
offense_index = (1 - 0.12) * offense_index + 0.12 * (offense_index * skill_index)
```

### Defense compose

```
defense_score =
    0.20 * roster_strength
  + 0.38 * front_seven
  + 0.32 * secondary
  + 0.10 * experience_index

defense_index = score_to_index(defense_score)
def_unit = 0.55 * f7_index + 0.45 * secondary_index
defense_index = (1 - 0.22) * defense_index + 0.22 * (defense_index * def_unit)
```

Historical team ratings are **not** primary.

## Updated project-game behavior

Clean pipeline:

```
strength indices
  → expected points (unit-aware matchup)
  → margin
  → spread_home / total / home_wp
```

```
pts = league_ppg * (off/def)^response
        * ol_skill_boost          # ±10% from OL+skill
        * opp_def_dampen          # ±12% from opponent F7+secondary
        * pace
        + HFA

spread_home = away_exp - home_exp   # neg = home favorite
total       = home_exp + away_exp (+ thin ST nudge)
home_wp     = Φ(margin / margin_sd)
```

Diagnostics on every projection:

- `home_layers.position_groups` / `away_layers.position_groups` (with components)
- `notes.method` / `notes.formula` / matchup boost-dampen terms
- `projection_formula` block on the HTTP dict
- `early_season_uncertainty` still explicit; W1–W4 `margin_sd` inflated

## Impact examples (packaged priors)

### Ablation (roster/QB fixed)

| Lever | Holding fixed | Effect |
| --- | --- | --- |
| OL 45 → 88 | roster + portal QB | offense_index ↑ ≥ 0.04; home WP ↑ ≥ 0.03 vs fixed opp |
| Secondary 50 → 90 | roster + incumbent QB | defense_index ↑ ≥ 0.05 |
| Front seven 45 → 92 | roster + incumbent QB | opponent expected points ↓ ≥ 2.0; home WP ↑ ≥ 0.04 |

### Profile contrasts vs BALL (week 5 neutral)

| Home | Profile | home_win_prob | approx score |
| --- | --- | --- | --- |
| UGA | elite units + incumbent | ≈ 0.96 | ≈ 45.6 – 15.0 |
| FSU | good units + portal QB | ≈ 0.92 | ≈ 44.1 – 18.8 |
| COLO | mixed units + true freshman | ≈ 0.86 | ≈ 39.8 – 20.2 |

Ordering **UGA > FSU > COLO** preserved (roster/QB still material; units amplify separation via defense dampen + offense boost).

## Fidelity

**Solid (structure)**

- Unit grade formula + component keys
- Composition weights + unit index blends
- project-game formula (strength → margin → lines/WP)
- Ablation-tested material unit effects
- Early-season uncertainty posture

**Approximate (numbers)**

- Packaged unit talent composites and component fills
- Win probs / spreads / totals
- In-path strength evolution

**Thin / gap**

- Special teams (nudge only)
- Placeholder mid-majors still share similar roster priors → unit fills cluster
- No live SP+/PFF-class unit feeds
- No market-grade calibration / KEI fair lines (Edge Board CFB stays markets-only)

## Entry points

```bash
python scripts/cfb/run_hierarchical_season_sim.py --status-only
python scripts/cfb/run_hierarchical_season_sim.py --demo --n-sims 50 --sample-game UGA@ALA --week 1 --neutral
```

- `GET  /cfb/season-engine/status` — examples include position_groups + breakdown
- `POST /cfb/season-engine/project-game` — layers + projection_formula
- `POST /cfb/season-engine/simulate`

Tests: `services/model-service/tests/test_cfb_season_engine.py`  
Foundation report: `data/ops/cfb-full-model-foundation-report.md`
