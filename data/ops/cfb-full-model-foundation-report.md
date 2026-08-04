# Full CFB Model: Foundation → Position Groups + Projection (v0.3)

**Branch:** `feat/cfb-position-projection` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.3-position-projection`  
**Date:** 2026-08-04  
**Status:** Hierarchical foundation standing; Layers 1–2 (roster/QB) material; Layer 3 position groups deepened with inspectable components and material projection deltas; Layer 4 project-game tightened (strength → margin → spread/total/WP). Calibration intentionally thin. Additive vs NFL engine and CFB markets-only Edge Board.

## Goal

Stand up an NFL-caliber *structure* for CFB 2026 that we can run the season through and evaluate next summer — without pretending historical team ratings alone are enough.

Design constraints (2026 reality):

- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity
- QB situation disproportionately important
- Position groups must be real drivers (not unused cosmetics)
- Early-season uncertainty very high

**v0.2 focus:** roster construction + QB situation as primary drivers.  
**v0.3 focus:** position groups (OL / skill / front seven / secondary) with talent/experience/portal_impact components; stronger team projection. See `data/ops/cfb-position-projection-20260804.md`.

## Architecture (layers + feed order)

```
roster_construction ──┐  roster_strength
qb_situation ─────────┼──► team_projection ──► project-game / season_sim
position_groups ──────┘  qb_situation_index + unit grades
                                  │
                                  └─► player_hooks (thin attach)
priors / early_season_uncertainty ──► widens W1–W4 margins + softens separation
```

| Layer | Module | Responsibility | Solid vs approximate |
| --- | --- | --- | --- |
| 1 Roster construction | `roster_construction.py` | Snap/start-weighted returning production, portal net, recruiting, experience → **roster_strength** | **Formula solid.** Packaged numerics **approximate**. Live feeds **gap**. |
| 2 QB situation | `qb_situation.py` | Incumbent / portal / open competition / true freshman + OL/weapons → **qb_situation_index** | **Classification + class multipliers solid.** Named talent **approximate**. |
| 3 Position groups | `position_groups.py` | OL, skill, front seven, secondary (+ thin ST); components talent/experience/portal_impact | **Formula solid.** Packaged talent **approximate**. Soft fills **placeholder**. |
| 4 Team projection | `team_projection.py` | Compose → O/D indices; unit-aware game projection | Weights inspectable; roster + QB + units drive. Win probs **approximate**. |
| Season sim | `season_sim.py` | Path-coherent team W/L skeleton | Structure solid; evolution + schedule sample **approximate / placeholder**. |
| Player hooks | `player_hooks.py` | Thin QB/skill identity attach | Wiring solid; identities thin. |
| Priors | `priors.py` / `calibration.py` | League env + early-season uncertainty (CFB-wider than NFL) | Explicitly approximate. |

Package root: `services/model-service/src/services/cfb_season_engine/`

## Data sources

| Source | Role | Fidelity |
| --- | --- | --- |
| `data/cfb_fbs_team_priors_2026.json` | Packaged FBS team priors; roster/QB/unit grades + unit components | Approximate / placeholder curated-estimated |
| `data/cfb_sample_schedule_2026.json` | Illustrative sample slate for sims | Placeholder — not official full FBS schedule |
| CFB Edge Board (`apps/web` markets-only) | Unchanged; no KEI invent | Markets-only |
| Live portal / recruiting / returning-production DB | **Not wired** | Gap |
| Calibrated unit grades (SP+ / PFF-class) | **Not wired** | Gap |

## Entry points

```bash
# Status / honesty contract (includes roster ladder + position group examples)
python scripts/cfb/run_hierarchical_season_sim.py --status-only

# Packaged demo: season paths + sample game
python scripts/cfb/run_hierarchical_season_sim.py --demo --n-sims 50 --sample-game UGA@ALA --week 1 --neutral
```

HTTP (model-service; additive):

- `GET  /cfb/season-engine/status`
- `POST /cfb/season-engine/project-game` (alias: `game-preview`)
- `POST /cfb/season-engine/simulate` (skeleton)

Tests: `services/model-service/tests/test_cfb_season_engine.py`  
Ops detail: `data/ops/cfb-position-projection-20260804.md` (also `cfb-roster-qb-20260804.md` for v0.2)

## What is solid vs approximate

**Solid**

- Layer boundaries and composition feed order
- Roster strength formula (snap/start + portal net + recruiting + experience)
- QB classification rules + class→offense multipliers
- Position group unit formula (talent / experience / portal_impact)
- `roster_strength` + `qb_situation_index` + unit grades as projection drivers
- project-game formula (strength → margin → spread/total/WP)
- Early-season uncertainty posture (inspectable diagnostics)
- API / CLI / ops honesty contract
- Additive isolation (does not modify NFL season engine or CFB Edge Board markets-only)

**Approximate**

- Packaged roster snap/start / portal / recruiting numerics
- Named QB talent and depth identities
- Position group talent composites and component fills
- Game win probabilities / spreads / totals
- In-path strength evolution

**Placeholder / deferred**

- Official full 2026 FBS schedule
- Live portal + returning production feeds
- Calibrated unit grades (SP+ / PFF-class)
- Special teams model (thin total nudge only)
- Player box production path
- CFP / conference standings
- Market-grade calibration / KEI fair lines on Edge Board

## Sample contrasts (v0.3)

Matchup family: power incumbent vs portal rebuild vs true freshman, same opponent (BALL), week 5 neutral — see ops note for full table and unit ablations.

| Home | qb_class | home_win_prob vs BALL |
| --- | --- | --- |
| UGA | incumbent | ≈ 0.96 |
| FSU | portal | ≈ 0.92 |
| COLO | true_freshman | ≈ 0.86 |

Unit ablations (roster/QB fixed): raise OL → offense + WP up; raise secondary → defense up; raise front seven → opponent scoring down / home WP up.

Near-coin-flip UGA@ALA in week 1 under early-season inflate remains expected — not a market claim. Layer snapshots include `roster_strength`, `qb_situation_index`, `position_groups.components`, and compose notes.

## Remaining gaps / next passes

1. Wire real 2026 FBS schedule (CFBD or packaged full slate)
2. Ingest portal + returning production + recruiting capital feeds (replace packaged numerics)
3. Calibrated / external unit grades (SP+ style) replacing approximate talent composites
4. Deepen player hooks → usage/production path (skill + QB)
5. Conference standings + CFP bracket skeleton on season_sim
6. Calibration pass against 2022–2025 FBS results
7. Optional Pro hub stub / Edge Board KEI only after calibrated fair lines exist

## Railway / deploy

Pushing model-service paths to `deploy-vercel` triggers `.github/workflows/deploy-railway.yml`.  
Live check after deploy: `GET /cfb/season-engine/status` on the Railway model-service URL — expect `engine_version: cfb-season-engine-v0.3-position-projection`.
