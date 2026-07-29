# NFL Week-1 Readiness Report

**Generated:** 2026-07-29  
**Branch:** `nfl-second-order-edge`  
**Verdict:** **READY WITH CAVEATS**  
**Score:** **7.8 / 10**

---

## Executive verdict (founder)

Ship **selective spread PLAY** under YELLOW for REG season Week 1.  
Do **not** sell full-slate, totals PLAY, props stakes, or preseason PLAY.  
Projections Hub shows Projected | Actual (Actual = — until REG data).  
100k futures sims are wired but not re-run this session — use existing ~50k bundle until overnight 100k completes.

---

## Posture by market

| Market | Posture | Notes |
| --- | --- | --- |
| **Sides (spread)** | **PLAY selective** | `spread_play_v2_cap7` [2.5, 7.0); confirmatory GREEN |
| **Moneyline** | **PLAY derived** | Only if spread PLAY + vig-aware EV ≥ 2% |
| **Totals** | **PASS / sides-only** | Confirmatory CLV RED (~0.35); `TOTAL_PLAY_ENABLED=false` |
| **Props** | **Research only** | `PLAY_STAKE_ELIGIBLE=false` |
| **Preseason** | **INFO desk** | `NFL_PRESEASON_MODE=info` blocks season PLAY on PRE |

---

## Checklist status

| Item | Status |
| --- | --- |
| Paper book tracker | **Done** — `data/ops/nfl-paper-book-latest.{json,md}` (2025: 100 spread PLAY, ATS 70%, CLV+ 56%, 79 ML PLAY) |
| ML EV gate | **Done** — Python + fair-lines wire + TS mirror + tests |
| Totals band review | **Done** — sides-only launch (`nfl-totals-band-review.md`) |
| Aug 25 factor freeze | **Done** — docs + `nfl-factor-freeze-aug25.md` (H+D ON; E/B/A OFF) |
| Preseason info desk | **Done** — docs + publish-path block |
| Hard model pass | **Done** — no blend/PLAY recal (`nfl-hard-model-pass.md`) |
| Projections Projected\|Actual | **Done** — hub page + `nfl-projection-actuals.ts` + empty 2026 scaffold |
| 100k sims path | **Wired** — `NFL_SEASON_SIMS=100000`; full run **not** completed this session |
| Unit tests | **14 passed** (enterprise gates + ML policy); web vitest updated |

---

## Locked model config

- Engine: KAV v3 + MC  
- Factors: H travel×weather ON, D error-regime ON, E/B/A OFF  
- Product gate: YELLOW  
- Freeze date: **2026-08-25**

---

## Preseason status

Separate desk only (`docs/NFL_PRESEASON_INFO_DESK.md`). Tags: INFO / WATCH / PASS.  
Never mix exhibition ATS into season PLAY gates.

---

## Projections status

- UI: `/pro/nfl/projections` — every key metric shows **Projected** and **Actual**.  
- Actual source: `data/ops/nfl-projection-actuals-2026.json` (empty scaffold until Week 1+).  
- Team wins + player yards / receptions / TDs covered.

---

## 100k / futures status

| | |
| --- | --- |
| Command | `NFL_SEASON_SIMS=100000 .venv/bin/python scripts/nfl/simulate_2026_season.py` |
| Blocker | Multi-hour wall-clock; not faked this session |
| Interim | Existing `nfl-preseason-sim-2026-*` bundles (~50k era) remain usable |

See `data/ops/nfl-100k-sims-path.md`.

---

## Needs from user

1. **Optional overnight:** run 100k season sims (command above) on machine with DB.  
2. **Visual Crossing key** (optional polish for H weather path) — Open-Meteo still works.  
3. After Week 1 starts: weekly overwrite of `nfl-projection-actuals-2026.json`.  
4. Do **not** ask to widen PLAY or re-enable E/B/A before Aug 25 freeze protocol.

---

## Why not full READY (10/10)

- Full-slate ATS still RED (product remains selective).  
- Totals not stake-eligible.  
- Fresh 100k futures run pending.  
- Primary-2025 alone is YELLOW on CLV n; claim is confirmatory 2024–25 selective.

**Act on:** market selective sides + ML EV under YELLOW; keep totals/props/preseason off the paid PLAY card.
