# CFB Season Sim + Early Uncertainty (v0.4)

**Date:** 2026-08-04  
**Engine:** `cfb-season-engine-v0.4-season-sim`  
**Branch:** `feat/cfb-season-sim` → `deploy-vercel`  
**Package:** `services/model-service/src/services/cfb_season_engine/`

## What shipped

1. **Full-season path sims** on densified packaged schedule (~12 games/team, weeks 1–14)
2. **Win distributions** (mean/std/p10/p50/p90), ranking-ish standings, week-by-week sample path
3. **Optional conference standings** from approximate affiliation map
4. **Week-indexed early-season uncertainty** (wide W1–W4, narrows thereafter) on project-game + season diagnostics
5. **project-game `drivers` + `uncertainty` blocks** surfacing roster_strength, qb_situation_index, unit grades
6. **Score coherence** — `total = home + away`, `spread = away - home`, `wp_home + wp_away = 1`

NFL season engine and CFB Edge Board markets-only are untouched.

## Schedule honesty

| Item | Status |
| --- | --- |
| Official 2026 FBS schedule in-repo | **No** |
| Packaged sample seed (`cfb_sample_schedule_2026.json`) | Curated approximate matchups |
| Densify (`schedule.densify_schedule`) | Synthetic paths; `schedule_source=packaged_sample_densified` |
| Conference map | Approximate packaged affiliations |

Do **not** treat densified paths or conference standings as official.

## Early-season uncertainty

| Week | Active | margin_sd_mult (base 16.5) | Notes |
| --- | --- | --- | --- |
| 1 | yes | 1.38 | Widest priors + identity noise |
| 2 | yes | 1.26 | |
| 3 | yes | 1.16 | |
| 4 | yes | 1.08 | |
| 5+ | no | 1.00 | Base priors |

Also: separation soften W1–W4, score noise inflate, mild extra strength-evolution noise on paths.

## Example: project-game with uncertainty (ALA vs UGA, neutral)

Illustrative packaged run (approximate — not market-grade):

| Week | home_wp | spread_home | total | margin_sd | early active |
| --- | --- | --- | --- | --- | --- |
| 1 | ~0.49 | ~+0.5 | ~53.6 | ~23.9 | yes |
| 5 | ~0.49 | ~+0.6 | ~53.7 | ~17.3 | no |

Drivers (both weeks; layer inputs unchanged by week):

- ALA: roster_strength ≈ 69.8, qb_situation_index ≈ 1.55 (incumbent), strong unit grades
- UGA: roster_strength ≈ 69.7, qb_situation_index ≈ 1.55 (incumbent), strong unit grades

Near-coin-flip under early inflate is expected — honesty label `fidelity=approximate`.

## Example: season sim summary (n_sims≈20, seed=2026)

- Games/path ≈ densified full slate (~780 after alias collapse; ~12 gpt)
- Teams with positive mean wins: all packaged FBS codes (aliases like TXAM/OLE collapsed)
- Illustrative top (approximate / SOS-sensitive, densified slate): ALA, PSU, PUR, FSU, MEM, CLEM, HOU, ND, UNLV, TEX
- SEC standings head (approx conf wins): ALA, TEX, MISS, TAMU, UGA
- Treat ranking-ish output as **not a poll** — densified SOS still moves the board
- Week-by-week sample: full path-0 game list with scores + early_season flag

## What is still approximate

- Densified schedule (not official FBS slate)
- Packaged roster / QB / unit numeric priors
- Win probs / spreads / totals (no market calibration)
- In-path strength evolution
- Conference affiliations + standings
- Season win totals / ranking-ish order (SOS-sensitive)

## Deferred

- Official full 2026 schedule feed (CFBD / packaged slate)
- Live portal / returning-production DB
- Calibrated unit grades (SP+ class)
- Player box production path
- CFP bracket
- KEI / Edge Board fair lines

## Entry points

```bash
python scripts/cfb/run_hierarchical_season_sim.py --status-only
python scripts/cfb/run_hierarchical_season_sim.py --demo --n-sims 25 --sample-game UGA@ALA --week 1 --neutral
```

- `GET /cfb/season-engine/status`
- `POST /cfb/season-engine/project-game`
- `POST /cfb/season-engine/simulate`

Tests: `services/model-service/tests/test_cfb_season_engine.py`
