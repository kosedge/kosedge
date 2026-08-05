# Full CFB Model: Foundation → UI Exposure (v0.6.1)

**Branch:** `feat/cfb-projection-calibration` → `deploy-vercel`  
**Engine version:** `cfb-season-engine-v0.6.1-calibration`  
**Date:** 2026-08-04  
**Status:** Hierarchical foundation through season simulation, HFA + coaching continuity, Pro UI, **v0.6 ESPN 2026 real-roster overlay**, plus **v0.6.1 measured projection calibration**. Still approximate (not market-grade KEI). Additive vs NFL engine and CFB markets-only Edge Board.

## Goal

Stand up an NFL-caliber *structure* for CFB 2026 that we can run the season through and evaluate next summer — without pretending historical team ratings alone are enough.

Design constraints (2026 reality):

- Extreme roster turnover (portal + NIL + draft + freshmen)
- Weak YoY team identity
- QB situation disproportionately important
- Position groups must be real drivers (not unused cosmetics)
- Early-season uncertainty very high
- Home-field advantage is variable (not a flat 3-pt blanket)
- Coaching staff changes matter most early (HC/DC > OC)

**v0.2 focus:** roster construction + QB situation as primary drivers.  
**v0.3 focus:** position groups + stronger team projection.  
**v0.4 focus:** season simulation + early-season uncertainty + project-game drivers.  
**v0.5 focus:** variable HFA + coaching continuity. See `data/ops/cfb-hfa-coaching-20260804.md`.  
**v0.5.1 focus:** first UI surface + measured projection tightening. See `data/ops/cfb-ui-exposure-20260804.md`.
**v0.6 focus:** ESPN 2026 real-roster / depth / portal-history overlay. See `data/ops/cfb-real-roster-20260804.md`.  
**v0.6.1 focus:** measured projection calibration (team indices, spreads/totals sanity, win-dist width). See `data/ops/cfb-projection-calibration-20260804.md`.

## Architecture (layers + feed order)

```
roster_construction ──┐  roster_strength
qb_situation ─────────┼──► team_projection ──► project-game / season_sim
position_groups ──────┤  qb_situation_index + unit grades
coaching_continuity ──┘  week-decayed HC/OC/DC penalties + index mults
home_field ──────────────► game-time variable HFA (baseline ~2 pts)
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
| 4 Team projection | `team_projection.py` | Compose → O/D indices; unit-aware game projection + drivers/uncertainty | Weights inspectable; roster + QB + units + coaching drive. Win probs **approximate**. |
| Home field | `home_field.py` | Variable HFA buckets (elite→poor), night note, major-env flags | **Bucket structure solid.** Team env_scores **approximate**. |
| Coaching continuity | `coaching_continuity.py` | New HC/OC/DC flags, week decay, uncertainty boost | **Decay + relative penalties solid.** Staff flags **approximate**. |
| Season sim | `season_sim.py` | Path-coherent season wins dist, week sample, ranking, optional conf standings | Structure solid; densified schedule + evolution **approximate**. |
| Schedule | `schedule.py` | Seed sample + densify toward ~12 games/team | Artifact real; paths **approximate / not official**. |
| Player hooks | `player_hooks.py` | Thin QB/skill identity attach | Wiring solid; identities thin. |
| Priors | `priors.py` / `calibration.py` | League env + early-season uncertainty + v0.6.1 calibration knobs | Explicitly approximate (sanity-calibrated, not CLV). |

Package root: `services/model-service/src/services/cfb_season_engine/`

## Data sources

| Source | Role | Fidelity |
| --- | --- | --- |
| `data/cfb_fbs_team_priors_2026.json` | Packaged FBS team priors; roster/QB/unit + **home_field** + **coaching** | Roster/QB/units overlaid from ESPN snapshot; HFA/coaching curated approximate |
| `data/cfb_real_roster_snapshot_2026.json` | ESPN 2026 roster / depth / portal-history snapshot | Real identities; derived numerics approximate |
| `data/cfb_sample_schedule_2026.json` | Seed slate for densify (+ optional `night_game`) | Approximate seed — not official |
| Densified schedule (runtime) | Usable season paths (~12 gpt) | Approximate synthetic — `packaged_sample_densified` |
| `data/cfb_fbs_conferences_2026.json` | Affiliation map for pairing + standings | Approximate |
| CFB Edge Board (`apps/web` markets-only) | Unchanged; no KEI invent | Markets-only |
| Live portal / recruiting / returning-production DB | Optional; packaged ESPN snapshot ships in-image | Snapshot solid; DB optional |
| Live home splits / coaching-change feeds | **Not wired** | Gap |
| Official full 2026 FBS schedule | **Not in-repo** | Gap |

## Entry points

```bash
# Status / honesty contract
python scripts/cfb/run_hierarchical_season_sim.py --status-only

# Packaged demo: season paths + sample game
python scripts/cfb/run_hierarchical_season_sim.py --demo --n-sims 25 --sample-game UGA@ALA --week 1 --neutral
```

HTTP (model-service; additive):

- `GET  /cfb/season-engine/status` (includes `team_codes` + `power_style_ladder`)
- `POST /cfb/season-engine/project-game` (alias: `game-preview`; supports `night_game`)
- `POST /cfb/season-engine/simulate` (season paths; default n_sims=15)

Web (Vercel BFF; secrets server-side):

- `/pro/cfb/model` · `/pro/cfb/project-game`
- `/api/cfb/season-engine/{status,project-game,simulate}`

Tests: `services/model-service/tests/test_cfb_season_engine.py`, `test_cfb_real_roster.py`  
Ops detail: `data/ops/cfb-projection-calibration-20260804.md` (also `cfb-real-roster-20260804.md`, `cfb-ui-exposure-20260804.md`, `cfb-hfa-coaching-20260804.md`, `cfb-season-sim-20260804.md`)

## What is solid vs approximate

**Solid**

- Layer boundaries and composition feed order
- Roster strength formula (snap/start + portal net + recruiting + experience)
- QB classification rules + class→offense multipliers
- Position group unit formula (talent / experience / portal_impact)
- `roster_strength` + `qb_situation_index` + unit grades as projection drivers
- Variable HFA bucket structure (baseline ~2 pts; elite→poor)
- Coaching continuity flags + week-decay schedule (HC/DC > OC early)
- project-game formula (strength → margin → spread/total/WP) + drivers/uncertainty blocks
- Early-season uncertainty posture (week-indexed narrowing, inspectable)
- Season-sim path coherence (wins distribution, week sample, ranking structure)
- API / CLI / ops honesty contract
- Additive isolation (does not modify NFL season engine or CFB Edge Board markets-only)

**Approximate**

- Packaged roster snap/start / portal / recruiting numerics
- Named QB talent and depth identities
- Position group talent composites and component fills
- HFA env_scores / venue labels (not live home ATS splits)
- Coaching staff change flags for 2026 (curated proxies)
- Densified schedule paths (not official FBS slate)
- Conference affiliations / standings
- Game win probabilities / spreads / totals (v0.6.1 sanity-calibrated; not CLV)
- In-path strength evolution
- Season win totals / ranking-ish order (SOS-sensitive under densify; G5 paths still soft)

**Placeholder / deferred**

- Official full 2026 FBS schedule feed
- Live portal + returning production feeds
- Live home scoring-margin / ATS feed
- Live coaching-change feed
- Full night-game / weather model
- Calibrated unit grades (SP+ / PFF-class)
- Special teams model (thin total nudge only)
- Player box production path
- CFP bracket
- Market-grade calibration / KEI fair lines on Edge Board

## Sample contrasts

**Layers (v0.3):** UGA incumbent > FSU portal > COLO true_freshman vs BALL; unit ablations move offense/defense/WP.

**Early uncertainty (v0.4):** TEX@OSU (or ALA@UGA) week 1 `margin_sd` materially wider than week 5; `uncertainty` block exposes narrowing schedule.

**Variable HFA (v0.5):** LSU elite home (~3.4) vs BALL poor (~0.7) — ~2.7 pt gap; night_game adds +0.3 note.

**Coaching (v0.5):** PSU new HC+OC+DC — W1 own-scoring adj much more negative than W5/W8; UGA returning staff gets tiny continuity bonus.

**Season sim:** densified paths return wins for essentially all packaged FBS teams; HFA + coaching flow through `realize_game_scores`.

## Remaining gaps / next passes

1. Wire real 2026 FBS schedule (CFBD or packaged full slate)
2. ~~Ingest portal + returning production + recruiting capital feeds~~ **v0.6 done (ESPN snapshot; CFBD optional)** — deepen measured SNAP%/full portal-out next
3. Live home-split feed to replace venue proxies
4. Live coaching-change feed to replace curated flags
5. Calibrated / external unit grades (SP+ style) replacing approximate talent composites
6. Deepen player hooks → usage/production path (skill + QB)
7. CFP bracket skeleton on season_sim
8. ~~Projection sanity calibration (decompress indices, bettable mismatch spreads)~~ **v0.6.1 done** — deepen with 2022–2025 graded backtest next
9. Edge Board KEI only after calibrated fair lines exist (keep markets-only until then)
10. Richer Pro desks (season-path explorer, conference standings UI) beyond project-game

## Railway / deploy

Pushing model-service paths to `deploy-vercel` triggers `.github/workflows/deploy-railway.yml`.  
Live check after deploy:

- `GET /cfb/season-engine/status` → `engine_version: cfb-season-engine-v0.6.1-calibration`
- `POST /cfb/season-engine/project-game` with `drivers.matchup.hfa` + coaching adj + ratio clamp diag
- `POST /cfb/season-engine/simulate` with `diagnostics.variable_hfa` / `coaching_continuity`
- Web: `https://www.kosedge.com/pro/cfb/model` + `/pro/cfb/project-game` (shows calibration version)
