# Full CFB Model: Foundation

**Branch:** `feat/cfb-full-model-foundation` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.1-foundation`  
**Date:** 2026-08-04  
**Status:** Hierarchical foundation standing. Calibration intentionally thin. Additive vs NFL engine and CFB markets-only Edge Board.

## Goal (this pass)

Stand up an NFL-caliber *structure* for CFB 2026 that we can run the season through and evaluate next summer — without pretending historical team ratings alone are enough.

Design constraints (2026 reality):

- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity
- QB situation disproportionately important
- Early-season uncertainty very high

## Architecture (layers + feed order)

```
roster_construction ──┐
qb_situation ─────────┼──► team_projection ──► project-game / season_sim
position_groups ──────┘           │
                                  └─► player_hooks (thin attach)
priors / early_season_uncertainty ──► widens W1–W4 margins + softens separation
```

| Layer | Module | Responsibility | Solid vs approximate |
| --- | --- | --- | --- |
| 1 Roster construction | `roster_construction.py` | Returning production, portal in/out, recruiting capital, experience, continuity | **Structure solid.** Packaged numerics **approximate**. Live feeds **gap**. |
| 2 QB situation | `qb_situation.py` | Incumbent / portal / open competition / true freshman + OL/weapons support | **Classification rules solid.** Named talent scores **approximate**. |
| 3 Position groups | `position_groups.py` | OL, skill, front seven, secondary (+ ST) | Soft fills from roster/QB when missing (**placeholder**). Packaged grades **approximate**. |
| 4 Team projection | `team_projection.py` | Compose → O/D indices; analytic game projection | Composition weights inspectable (**solid structure**). Win probs / spreads **approximate**. |
| Season sim | `season_sim.py` | Path-coherent team W/L skeleton | Structure solid; evolution + schedule sample **approximate / placeholder**. |
| Player hooks | `player_hooks.py` | Thin QB/skill identity attach | Wiring solid; identities thin. |
| Priors | `priors.py` / `calibration.py` | League env + early-season uncertainty (CFB-wider than NFL) | Explicitly approximate. |

Package root: `services/model-service/src/services/cfb_season_engine/`

## Data sources

| Source | Role | Fidelity |
| --- | --- | --- |
| `data/cfb_fbs_team_priors_2026.json` | Packaged FBS team priors (curated + placeholder rows) | Approximate / placeholder |
| `data/cfb_sample_schedule_2026.json` | Illustrative sample slate for sims | Placeholder — not official full FBS schedule |
| CFB Edge Board (`apps/web` markets-only) | Unchanged; no KEI invent | Markets-only |
| Live portal / recruiting / returning-production DB | **Not wired** | Gap |
| CollegeFootballData / cfbfastR | Noted for next pass; not required this foundation | Gap |

## Entry points

```bash
# Status / honesty contract
python scripts/cfb/run_hierarchical_season_sim.py --status-only

# Packaged demo: season paths + sample game
python scripts/cfb/run_hierarchical_season_sim.py --demo --n-sims 50 --sample-game UGA@ALA --week 1 --neutral
```

HTTP (model-service; additive):

- `GET  /cfb/season-engine/status`
- `POST /cfb/season-engine/project-game` (alias: `game-preview`)
- `POST /cfb/season-engine/simulate` (skeleton)

Tests: `services/model-service/tests/test_cfb_season_engine.py`

## What is solid vs approximate

**Solid**

- Layer boundaries and composition feed order
- QB classification rules
- Early-season uncertainty posture (inspectable diagnostics)
- API / CLI / ops honesty contract
- Additive isolation (does not modify NFL season engine or CFB Edge Board markets-only)

**Approximate**

- Packaged roster / portal / recruiting numerics
- Named QB talent and depth identities
- Position group grades
- Game win probabilities / spreads / totals
- In-path strength evolution

**Placeholder / deferred**

- Official full 2026 FBS schedule
- Live portal + returning production feeds
- Player box production path
- CFP / conference standings
- Market-grade calibration / KEI fair lines on Edge Board

## Sample team-level projection

Matchup: **UGA @ ALA**, week 1, neutral site (packaged priors).  
Artifact: `data/ops/cfb-season-engine-foundation-sample/run.json`

| Field | Value |
| --- | --- |
| home_win_prob (ALA) | ≈ 0.498 |
| expected score | UGA 28.6 @ ALA 28.6 |
| expected_total | ≈ 57.2 |
| spread_home | ≈ +0.1 |
| margin_sd (W1 inflate) | ≈ 23.9 |
| early_season_uncertainty.active | true |

Near-coin-flip is expected under W1 CFB uncertainty + approximate priors — not a market claim. Layer snapshots for both teams include `roster`, `qb`, and `position_groups`.

## Remaining gaps / next passes

1. Wire real 2026 FBS schedule (CFBD or packaged full slate)
2. Ingest portal + returning production + recruiting capital feeds (replace packaged numerics)
3. Deepen player hooks → usage/production path (skill + QB)
4. Conference standings + CFP bracket skeleton on season_sim
5. Calibration pass against 2022–2025 FBS results (not this foundation PR)
6. Optional Pro hub stub / Edge Board KEI only after calibrated fair lines exist

## Railway / deploy

Pushing model-service paths to `deploy-vercel` triggers `.github/workflows/deploy-railway.yml`.  
Live check after deploy: `GET /cfb/season-engine/status` on the Railway model-service URL.
