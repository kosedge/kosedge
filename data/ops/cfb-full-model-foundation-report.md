# Full CFB Model: Foundation → Season Sim (v0.4)

**Branch:** `feat/cfb-season-sim` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.4-season-sim`  
**Date:** 2026-08-04  
**Status:** Hierarchical foundation standing through season simulation. Layers 1–4 intact; season_sim upgraded from skeleton to densified full-season paths with win distributions, week samples, and optional conference standings. Early-season uncertainty is week-indexed and inspectable. Calibration intentionally thin. Additive vs NFL engine and CFB markets-only Edge Board.

## Goal

Stand up an NFL-caliber *structure* for CFB 2026 that we can run the season through and evaluate next summer — without pretending historical team ratings alone are enough.

Design constraints (2026 reality):

- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity
- QB situation disproportionately important
- Position groups must be real drivers (not unused cosmetics)
- Early-season uncertainty very high

**v0.2 focus:** roster construction + QB situation as primary drivers.  
**v0.3 focus:** position groups + stronger team projection.  
**v0.4 focus:** season simulation + early-season uncertainty + project-game drivers. See `data/ops/cfb-season-sim-20260804.md`.

## Architecture (layers + feed order)

```
roster_construction ──┐  roster_strength
qb_situation ─────────┼──► team_projection ──► project-game / season_sim
position_groups ──────┘  qb_situation_index + unit grades
                                  │
                                  └─► player_hooks (thin attach)
priors / early_season_uncertainty ──► widens W1–W4 margins + softens separation
schedule.densify_schedule ──► usable season paths (labeled approximate)
```

| Layer | Module | Responsibility | Solid vs approximate |
| --- | --- | --- | --- |
| 1 Roster construction | `roster_construction.py` | Snap/start-weighted returning production, portal net, recruiting, experience → **roster_strength** | **Formula solid.** Packaged numerics **approximate**. Live feeds **gap**. |
| 2 QB situation | `qb_situation.py` | Incumbent / portal / open competition / true freshman + OL/weapons → **qb_situation_index** | **Classification + class multipliers solid.** Named talent **approximate**. |
| 3 Position groups | `position_groups.py` | OL, skill, front seven, secondary (+ thin ST); components talent/experience/portal_impact | **Formula solid.** Packaged talent **approximate**. Soft fills **placeholder**. |
| 4 Team projection | `team_projection.py` | Compose → O/D indices; unit-aware game projection + drivers/uncertainty | Weights inspectable; roster + QB + units drive. Win probs **approximate**. |
| Season sim | `season_sim.py` | Path-coherent season wins dist, week sample, ranking, optional conf standings | Structure solid; densified schedule + evolution **approximate**. |
| Schedule | `schedule.py` | Seed sample + densify toward ~12 games/team | Artifact real; paths **approximate / not official**. |
| Player hooks | `player_hooks.py` | Thin QB/skill identity attach | Wiring solid; identities thin. |
| Priors | `priors.py` / `calibration.py` | League env + early-season uncertainty (CFB-wider than NFL) | Explicitly approximate. |

Package root: `services/model-service/src/services/cfb_season_engine/`

## Data sources

| Source | Role | Fidelity |
| --- | --- | --- |
| `data/cfb_fbs_team_priors_2026.json` | Packaged FBS team priors; roster/QB/unit grades + unit components | Approximate / placeholder curated-estimated |
| `data/cfb_sample_schedule_2026.json` | Seed slate for densify | Approximate seed — not official |
| Densified schedule (runtime) | Usable season paths (~12 gpt) | Approximate synthetic — `packaged_sample_densified` |
| `data/cfb_fbs_conferences_2026.json` | Affiliation map for pairing + standings | Approximate |
| CFB Edge Board (`apps/web` markets-only) | Unchanged; no KEI invent | Markets-only |
| Live portal / recruiting / returning-production DB | **Not wired** | Gap |
| Official full 2026 FBS schedule | **Not in-repo** | Gap |

## Entry points

```bash
# Status / honesty contract
python scripts/cfb/run_hierarchical_season_sim.py --status-only

# Packaged demo: season paths + sample game
python scripts/cfb/run_hierarchical_season_sim.py --demo --n-sims 25 --sample-game UGA@ALA --week 1 --neutral
```

HTTP (model-service; additive):

- `GET  /cfb/season-engine/status`
- `POST /cfb/season-engine/project-game` (alias: `game-preview`)
- `POST /cfb/season-engine/simulate` (season paths; default n_sims=15)

Tests: `services/model-service/tests/test_cfb_season_engine.py`  
Ops detail: `data/ops/cfb-season-sim-20260804.md` (also `cfb-position-projection-20260804.md`, `cfb-roster-qb-20260804.md`)

## What is solid vs approximate

**Solid**

- Layer boundaries and composition feed order
- Roster strength formula (snap/start + portal net + recruiting + experience)
- QB classification rules + class→offense multipliers
- Position group unit formula (talent / experience / portal_impact)
- `roster_strength` + `qb_situation_index` + unit grades as projection drivers
- project-game formula (strength → margin → spread/total/WP) + drivers/uncertainty blocks
- Early-season uncertainty posture (week-indexed narrowing, inspectable)
- Season-sim path coherence (wins distribution, week sample, ranking structure)
- API / CLI / ops honesty contract
- Additive isolation (does not modify NFL season engine or CFB Edge Board markets-only)

**Approximate**

- Packaged roster snap/start / portal / recruiting numerics
- Named QB talent and depth identities
- Position group talent composites and component fills
- Densified schedule paths (not official FBS slate)
- Conference affiliations / standings
- Game win probabilities / spreads / totals
- In-path strength evolution
- Season win totals / ranking-ish order (SOS-sensitive under densify)

**Placeholder / deferred**

- Official full 2026 FBS schedule feed
- Live portal + returning production feeds
- Calibrated unit grades (SP+ / PFF-class)
- Special teams model (thin total nudge only)
- Player box production path
- CFP bracket
- Market-grade calibration / KEI fair lines on Edge Board

## Sample contrasts

**Layers (unchanged from v0.3):** UGA incumbent > FSU portal > COLO true_freshman vs BALL; unit ablations move offense/defense/WP.

**Early uncertainty:** TEX@OSU (or ALA@UGA) week 1 `margin_sd` materially wider than week 5; `uncertainty` block exposes narrowing schedule.

**Season sim:** densified paths return wins for essentially all packaged FBS teams; top board is approximate/SOS-sensitive — see ops note.

## Remaining gaps / next passes

1. Wire real 2026 FBS schedule (CFBD or packaged full slate)
2. Ingest portal + returning production + recruiting capital feeds (replace packaged numerics)
3. Calibrated / external unit grades (SP+ style) replacing approximate talent composites
4. Deepen player hooks → usage/production path (skill + QB)
5. CFP bracket skeleton on season_sim
6. Calibration pass against 2022–2025 FBS results
7. Optional Pro hub stub / Edge Board KEI only after calibrated fair lines exist

## Railway / deploy

Pushing model-service paths to `deploy-vercel` triggers `.github/workflows/deploy-railway.yml`.  
Live check after deploy:

- `GET /cfb/season-engine/status` → `engine_version: cfb-season-engine-v0.4-season-sim`
- `POST /cfb/season-engine/project-game` with drivers + uncertainty
- `POST /cfb/season-engine/simulate` with season_paths / win distributions
