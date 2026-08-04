# Full CFB Model: Foundation → Roster + QB (v0.2)

**Branch:** `feat/cfb-roster-qb` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.2-roster-qb`  
**Date:** 2026-08-04  
**Status:** Hierarchical foundation standing; Layers 1–2 deepened so they visibly drive project-game / season-sim. Calibration intentionally thin. Additive vs NFL engine and CFB markets-only Edge Board.

## Goal

Stand up an NFL-caliber *structure* for CFB 2026 that we can run the season through and evaluate next summer — without pretending historical team ratings alone are enough.

Design constraints (2026 reality):

- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity
- QB situation disproportionately important
- Early-season uncertainty very high

**v0.2 focus:** Make roster construction and QB situation the real drivers (transparent formulas, inspectable components, material projection deltas). See `data/ops/cfb-roster-qb-20260804.md`.

## Architecture (layers + feed order)

```
roster_construction ──┐  roster_strength
qb_situation ─────────┼──► team_projection ──► project-game / season_sim
position_groups ──────┘  qb_situation_index
                                  │
                                  └─► player_hooks (thin attach)
priors / early_season_uncertainty ──► widens W1–W4 margins + softens separation
```

| Layer | Module | Responsibility | Solid vs approximate |
| --- | --- | --- | --- |
| 1 Roster construction | `roster_construction.py` | Snap/start-weighted returning production, portal net, recruiting, experience → **roster_strength** | **Formula solid.** Packaged numerics **approximate**. Live feeds **gap**. |
| 2 QB situation | `qb_situation.py` | Incumbent / portal / open competition / true freshman + OL/weapons → **qb_situation_index** | **Classification + class multipliers solid.** Named talent **approximate**. |
| 3 Position groups | `position_groups.py` | OL, skill, front seven, secondary (+ ST) | Soft fills from roster/QB when missing (**placeholder**). Packaged grades **approximate**. |
| 4 Team projection | `team_projection.py` | Compose → O/D indices; analytic game projection | Weights inspectable; roster_strength + qb_situation **primary**. Win probs **approximate**. |
| Season sim | `season_sim.py` | Path-coherent team W/L skeleton | Structure solid; evolution + schedule sample **approximate / placeholder**. |
| Player hooks | `player_hooks.py` | Thin QB/skill identity attach | Wiring solid; identities thin. |
| Priors | `priors.py` / `calibration.py` | League env + early-season uncertainty (CFB-wider than NFL) | Explicitly approximate. |

Package root: `services/model-service/src/services/cfb_season_engine/`

## Data sources

| Source | Role | Fidelity |
| --- | --- | --- |
| `data/cfb_fbs_team_priors_2026.json` | Packaged FBS team priors (curated + placeholder rows); snap/start + portal value fields | Approximate / placeholder curated-estimated |
| `data/cfb_sample_schedule_2026.json` | Illustrative sample slate for sims | Placeholder — not official full FBS schedule |
| CFB Edge Board (`apps/web` markets-only) | Unchanged; no KEI invent | Markets-only |
| Live portal / recruiting / returning-production DB | **Not wired** | Gap |
| CollegeFootballData / cfbfastR | Noted for next pass; not required this pass | Gap |

## Entry points

```bash
# Status / honesty contract (includes roster_strength ladder + layer examples)
python scripts/cfb/run_hierarchical_season_sim.py --status-only

# Packaged demo: season paths + sample game
python scripts/cfb/run_hierarchical_season_sim.py --demo --n-sims 50 --sample-game UGA@ALA --week 1 --neutral
```

HTTP (model-service; additive):

- `GET  /cfb/season-engine/status`
- `POST /cfb/season-engine/project-game` (alias: `game-preview`)
- `POST /cfb/season-engine/simulate` (skeleton)

Tests: `services/model-service/tests/test_cfb_season_engine.py`  
Ops detail: `data/ops/cfb-roster-qb-20260804.md`

## What is solid vs approximate

**Solid**

- Layer boundaries and composition feed order
- Roster strength formula (snap/start + portal net + recruiting + experience)
- QB classification rules + class→offense multipliers
- `roster_strength` + `qb_situation_index` as primary projection drivers
- Early-season uncertainty posture (inspectable diagnostics)
- API / CLI / ops honesty contract
- Additive isolation (does not modify NFL season engine or CFB Edge Board markets-only)

**Approximate**

- Packaged roster snap/start / portal / recruiting numerics
- Named QB talent and depth identities
- Position group grades / supporting cast
- Game win probabilities / spreads / totals
- In-path strength evolution

**Placeholder / deferred**

- Official full 2026 FBS schedule
- Live portal + returning production feeds
- Player box production path
- CFP / conference standings
- Market-grade calibration / KEI fair lines on Edge Board

## Sample contrasts (v0.2)

Matchup family: power incumbent vs portal rebuild vs true freshman, same opponent (BALL), week 5 neutral — see ops note for full table.

| Home | qb_class | home_win_prob vs BALL |
| --- | --- | --- |
| UGA | incumbent | ≈ 0.92 |
| FSU | portal | ≈ 0.83 |
| COLO | true_freshman | ≈ 0.73 |

Near-coin-flip UGA@ALA in week 1 under early-season inflate remains expected — not a market claim. Layer snapshots include `roster_strength`, `qb_situation_index`, and component breakdowns.

## Remaining gaps / next passes

1. Wire real 2026 FBS schedule (CFBD or packaged full slate)
2. Ingest portal + returning production + recruiting capital feeds (replace packaged numerics)
3. Deepen player hooks → usage/production path (skill + QB)
4. Conference standings + CFP bracket skeleton on season_sim
5. Calibration pass against 2022–2025 FBS results
6. Optional Pro hub stub / Edge Board KEI only after calibrated fair lines exist

## Railway / deploy

Pushing model-service paths to `deploy-vercel` triggers `.github/workflows/deploy-railway.yml`.  
Live check after deploy: `GET /cfb/season-engine/status` on the Railway model-service URL — expect `engine_version: cfb-season-engine-v0.2-roster-qb`.
