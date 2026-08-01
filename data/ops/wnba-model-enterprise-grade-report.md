# WNBA Model — Enterprise Grade Report

**Canary:** `wnba-poss-sim-20260801-phase3`  
**Model:** `wnba-v1-poss-sim` / props `wnba-player-props-v1`  
**Publish posture:** research_only (mainlines + props)

## Grade summary

| Area | Grade | Notes |
|------|-------|-------|
| Simulator fidelity | A- | Harmonic-mean pace, 40-min scaling, WNBA ORtg/DRtg priors |
| Sport isolation | A | Separate tables/keys; no NBA prior import; abbr sport-scoped |
| Close-line join | A- | ET ±1 + full name/abbr aliases (ports NBA BOCE lesson) |
| Odds densify discipline | A | Credit-capped; skip if owned; ≥1.5M floor |
| Props policy | A | Role-collapse Under refuse; stake_eligible=False |
| Desk honesty | A | Empty slate returns status, never invents prices |
| Ops cadence | B+ | Beat: morning ingest/context/sim + 3am daily cycle |

## Sport-specific differences baked in

1. **40-minute games** — pace = possessions per 40; OT ~5 possessions/side.
2. **Harmonic-mean pace** — expected game pace = `2ab/(a+b)` (not arithmetic).
3. **League priors** — pace 81, ORtg/DRtg 103, home court 2.25, 3PT rate ~0.34.
4. **Season year** — tip year / May-start rule (`wnba_season_year_from_date`).
5. **13-team map** — ATL/CHI/CON/DAL/GSV/IND/LAS/LA/MIN/NY/PHX/SEA/WSH + aliases LVA→LAS, NYL→NY, WAS→WSH.
6. **Abbr collisions** — all hierarchy joins use `leagues.code='wnba'`.
7. **Props** — 40-min minutes cap; higher usage soft-scale; role-collapse Under refuse.

## Inventory truth

Use `GET /wnba/ops/inventory` (or `/api/jobs/wnba-inventory`) on the model-service DB — not explore summaries against empty Postgres.

## Ship notes (2026-08-01)

| Item | Value |
|------|-------|
| Feature tip | `cursor/wnba-model-phases-0-3-9ea3` |
| Production branch | `deploy-vercel` |
| Canary | `wnba-poss-sim-20260801-phase3` |
| Model service | `https://model-service-production-e253.up.railway.app` |
| Pro fair-lines | `https://www.kosedge.com/pro/wnba/fair-lines` |
| Pro props | `https://www.kosedge.com/pro/wnba/props` |

Health canary intentionally skips DDL under lock pressure (bootstrap/densify). Demo sim is DB-free and validates harmonic-mean + 40-min priors. Ingest seasons include **2026** (in-season tip year).

## Live URLs

- Health: `/wnba/health`
- Fair lines: `/wnba/fair-lines` → Pro `/pro/wnba/fair-lines`
- Props board: `/wnba/props/board` → Pro `/pro/wnba/props`
- Inventory: `/wnba/ops/inventory`
- Demo: `POST /wnba/simulations/demo`

## Non-goals / preserved

- Do not break NBA / NFL / MLB stacks.
- No college props.
- No stake-eligible PLAY tags until holdout clears.
