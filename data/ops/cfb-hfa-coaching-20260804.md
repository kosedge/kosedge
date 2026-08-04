# CFB Variable HFA + Coaching Continuity (v0.5)

**Date:** 2026-08-04  
**Engine:** `cfb-season-engine-v0.5-hfa-coaching`  
**Branch:** `feat/cfb-hfa-coaching` → `deploy-vercel`  
**Package:** `services/model-service/src/services/cfb_season_engine/`

## What shipped

1. **Variable home-field advantage** — baseline ~2.0 pts; elite/strong/average/weak/poor buckets (not flat 3 pts)
2. **Night-game note** — optional +0.30 bump when `night_game=true` (thin; not a full night model)
3. **Coaching continuity / change** — explicit `new_hc` / `new_oc` / `new_dc` + returning flags
4. **Week-decayed penalties** — strongest W1–W4 (HC + DC largest), residual thereafter
5. **Wiring** — both layers flow into `project-game` and `season_sim` via `expected_team_points`
6. **Diagnostics** — HFA components + coaching flags/scores on drivers, layers, status examples

NFL season engine and CFB Edge Board markets-only are untouched. Roster / QB / position-group layers remain intact.

## Variable HFA formula

```
baseline = 2.0

bucket_points = {
  elite: 3.40, strong: 2.75, average: 2.00, weak: 1.25, poor: 0.70
}

hfa = 0                         if neutral_site or away
hfa = bucket_points             if home (day)
hfa = bucket_points + 0.30      if home and night_game
```

Team `env_score` (0–100) maps to bucket when bucket not explicit:

| env_score | bucket |
| --- | --- |
| ≥ 80 | elite |
| ≥ 65 | strong |
| ≥ 45 | average |
| ≥ 30 | weak |
| < 30 | poor |

**Sources (approximate):** curated venue / recent-home proxies (LSU Death Valley, Autzen, Beaver, etc.) or roster recruiting/experience soft proxy for the rest. Not live home ATS / scoring-margin splits.

## Coaching continuity formula

Week-1 scale penalties (points of expected scoring drag):

| Change | Offense | Defense | Uncertainty boost |
| --- | --- | --- | --- |
| New HC | 1.35 | 1.10 | +0.18 |
| New OC | 0.75 | — | +0.08 |
| New DC | — | 1.20 | +0.14 |
| All returning | +0.15 continuity bonus (offense) | — | 0 |

Week decay multiplier:

| Week | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8+ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Decay | 1.00 | 0.85 | 0.65 | 0.45 | 0.22 | 0.14 | 0.10 | ~0.05–0.08 |

Also at compose time: mild offense/defense index multipliers for new staff; uncertainty boost blends into `early_season_uncertainty` (interacts with existing W1–W4 inflate).

## Before / after examples (packaged approximate)

### HFA buckets (home vs WAKE, week 6, not neutral)

| Home | Bucket | HFA pts | home_wp | spread_home | Notes |
| --- | --- | --- | --- | --- | --- |
| LSU | elite | 3.40 | ~0.72 | ~−10.3 | Tiger Stadium / major environment |
| BALL | poor | 0.70 | ~0.09 | ~+23.8 | weak home proxy (talent gap also large) |

Elite vs poor HFA gap = **2.7 pts** on the home side. On a competitive board (TEX@OSU style), flipping elite↔poor HFA moves expected home score by ≥2 pts and WP by ≥4 pts.

### Coaching early vs mid (PSU new HC+OC+DC, neutral vs BALL)

| Week | Own scoring adj | home_wp | spread_home | Notes |
| --- | --- | --- | --- | --- |
| 1 | −2.10 | ~0.68 | ~−11.8 | Full early penalty (HC+OC offense) |
| 5 | −0.46 | ~0.88 | ~−21.4 | Decayed residual |
| 8 | −0.17 | ~0.88 | ~−22.0 | Near washed out |

UGA (all returning) W1 own adj = **+0.15** continuity bonus (vs PSU −2.10). Early-season uncertainty also higher for PSU (~0.49) than UGA (~0.16).

### Season sim

Path realization uses the same `expected_team_points` path → variable HFA + week-decayed coaching affect win distributions. Diagnostics flag `variable_hfa=true`, `coaching_continuity=true`.

## Honesty / limitations

| Item | Status |
| --- | --- |
| Bucket structure + decay schedule | **Solid** (inspectable) |
| Team env_scores / venues | **Approximate** curated proxies |
| Night-game bump | **Thin note** — not weather/TV/full night model |
| Coaching change flags | **Approximate** curated for notable regimes; most teams default returning (placeholder) |
| Live home-split / coaching feeds | **Gap** |
| Market calibration | **Deferred** |

## Entry points

- `GET /cfb/season-engine/status` — layers include `home_field` + `coaching_continuity`; examples expose both
- `POST /cfb/season-engine/project-game` — `drivers.matchup.hfa`, coaching adj, layer snapshots
- `POST /cfb/season-engine/simulate` — diagnostics include new layer flags
- CLI: `scripts/cfb/run_hierarchical_season_sim.py`

## Files

- `home_field.py`, `coaching_continuity.py` (new)
- `types.py`, `priors.py`, `team_projection.py`, `loaders.py`, `season_sim.py`, `__init__.py`
- `data/cfb_fbs_team_priors_2026.json` (enriched)
- `routes/cfb.py` (`night_game` body field)
- `tests/test_cfb_season_engine.py`
- Foundation report updated to v0.5
