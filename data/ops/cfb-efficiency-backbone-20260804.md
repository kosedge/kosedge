# CFB Efficiency Backbone (v0.8)

**Date:** 2026-08-04  
**Engine:** `cfb-season-engine-v0.8-efficiency`  
**Branch:** `feat/cfb-efficiency-backbone` → `deploy-vercel`  
**Scope:** Opponent-adjusted efficiency as a primary complementary driver beside roster / QB / units. Edge Board CFB stays markets-only.

## What changed

| Piece | Detail |
| --- | --- |
| New module | `efficiency.py` — `off_eff`, `def_eff`, `success_off/def`, `explosiveness` |
| Packaged data | `data/cfb_efficiency_snapshot_2025_carry_2026.json` (final-2025 SP+ carry) |
| Compose | Offense/defense scores blend efficiency + roster + QB + units |
| Anti double-count | Unit weights / index blends / game unit matchup scales reduced vs v0.7 |
| Drivers UI | Off Eff / Def Eff chips on `/pro/cfb/project-game` |
| Packager | `scripts/cfb/package_efficiency_2025_carry.py` (public SP+; CFBD optional) |

## Blend weights (inspectable)

**Offense (sum = 1.0):**

| Signal | Weight |
| --- | --- |
| `off_eff` | 0.28 |
| `roster_strength` | 0.24 |
| `qb_situation` | 0.26 |
| `skill` | 0.11 |
| `ol` | 0.11 |

Post-compose: `QB_INDEX_BLEND=0.28`, `OL=0.10`, `SKILL=0.08`, `EFF_OFF_INDEX_BLEND=0.08`.

**Defense (sum = 1.0):**

| Signal | Weight |
| --- | --- |
| `def_eff` | 0.30 |
| `roster_strength` | 0.14 |
| `front_seven` | 0.26 |
| `secondary` | 0.22 |
| `experience` | 0.08 |

Post-compose: `DEF_UNIT_BLEND=0.16`, `EFF_DEF_INDEX_BLEND=0.08`.  
Game-level unit boost/dampen scales: 0.07 / 0.09 (were 0.11 / 0.14).

## Data used (honesty)

- **Primary:** Final-2025 SP+ offense/defense (opponent-adjusted efficiency; Bill Connelly).
- **Normalization:** z-score → 0–100 (`off_eff`/`def_eff`); defense inverted so higher = better.
- **success_off/def / explosiveness:** SP+-correlated **proxies**, not true PBP success-rate / iso-explosiveness.
- **Not used:** Full play-by-play store (unavailable in-repo). CFBD `/ratings/sp` optional when `CFBD_API_KEY` set.
- **2026 preseason:** Prior-year carry + current roster/QB identity; labeled approximate. No live weekly SP+ refresh yet.

## Before / after (efficiency vs identity-only)

Holding roster/QB/units/HFA/coaching fixed and setting `off_eff=def_eff=50` isolates the backbone:

| Matchup | With efficiency spread | Identity-only (eff=50) | Δ |
| --- | --- | --- | --- |
| MICH @ OSU (W1) | ≈ −9.9 | ≈ −4.9 | efficiency widens OSU |
| BALL @ UGA (W5) | ≈ −34.8 | ≈ −21.3 | SP+ gap vs G5 material |
| OSU @ IU (W1 n) | ≈ +6.0 (OSU) | ≈ +7.2 | top SP+ peers stay close |

See `data/ops/cfb-efficiency-backbone-20260804/before_after.json` for live numbers.

Power-style ladder now surfaces SP+-strong sides (OSU / ORE / IU / MISS / ND) near the top **with** roster/QB still material — Indiana’s SP+ #1 does not erase Ohio State’s roster/QB identity.

## Limitations

- Approximate prior-year carry — not live 2026 EPA
- success/explosiveness are proxies
- Some packaged codes lack SP+ rows → league-average placeholder
- Soft ratio clamp still caps absurd 45-pt invents
- Not market-grade KEI / CLV

## Tests

`services/model-service/tests/test_cfb_season_engine.py`:

- efficiency moves projections when roster held fixed
- top SP+-ish teams rank high
- early-season uncertainty still widens
- player hooks still allocate from team totals
- drivers expose efficiency + blend weights

## UI

- `/pro/cfb/model` — efficiency fidelity copy + engine version
- `/pro/cfb/project-game` — **Off Eff** / **Def Eff** chips in driver strip
