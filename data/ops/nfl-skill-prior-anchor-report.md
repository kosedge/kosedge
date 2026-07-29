# NFL Skill Prior-Anchor Calibration — Diagnosis & Result

Generated: 2026-07-29  
Bundle: `data/ops/nfl-preseason-sim-2026-20260729T160818Z`  
Team/futures MC: **unchanged** (100k). Player layer regenerated only.

## Root cause

Games projected were already **17** — undershoot was not an injury/games artifact.

Weekly baselines compressed established skill volume:

| Player | Prior REG peak (leakage-safe) | Model (pre-cal) | Gap |
| --- | ---: | ---: | ---: |
| J.Taylor | ~1431–1585 rush | 1307 | ~15–20% |
| J.Chase | ~1412–1708 rec | 1235 | ~15–25% |
| P.Nacua | ~1715 rec | 892 | severe |
| J.Jefferson | ~1533 (2024) | 840 | severe |

Contributing engine symptoms (already partially mitigated in weekly path, not fully
reflected in season CSVs): WR1 `role_confidence` often ~0.25–0.30 despite solid
`target_proxy`; talent/YPG factors under-correct elite ceilings.

## Fix (leakage-safe)

In `data_platform_nfl/player_season_totals.py` (synced to model-service copy):

1. `fetch_skill_prior_anchors` — REG weeks 1–18, seasons `season-1` and `season-2`
   only; ≥8 involvement games; take **max** rush/rec YPG per player.
2. `apply_skill_prior_anchor_calibration` — **upward-only** blend toward
   `prior_ypg × games_projected` with volume-tiered weights (e.g. prior season
   ≥1200 yd → blend 0.55). Scale TDs/receptions with yards. Never pulls down.
3. Applied after QB starter lock; playoffs derive from calibrated regular rates.
4. Publish floors **unchanged** (rush ≥1400, rec ≥1300, 3× WR ≥1200).

Regen: `scripts/nfl/regen_player_season_totals.py` (no 100k re-run).

## Post-calibration quality (honest)

| Gate | Before | After |
| --- | ---: | ---: |
| Top rush yards | 1307.5 (Taylor) | **1649.8** (Barkley) |
| Top rec yards | 1234.9 (Chase) | **1495.1** (Chase) |
| WR ≥1200 count | 1 | **5** |
| RB ≥1400 count | 0 | **3** |
| Dual 1000-yard RB rooms | 0 | **0** |
| Pass `publish_ready` | true | **true** |
| Skill `publish_ready_skill` | false | **true** |
| Overall `publish_ready` | false | **true** |

Players adjusted: **116** (of 380 prior anchors loaded). Rookies without prior
REG samples are left on model volume (no invented history).

## What this is / is not

- **Is:** structural season-total share/talent repair for hub publish boards.
- **Is not:** a weekly baseline rematerialization; weekly props path may still
  show compressed means until engine role/talent floors are rematerialized.
- **Is not:** a betting PLAY widen. Sides/ML/totals/props posture unchanged.
