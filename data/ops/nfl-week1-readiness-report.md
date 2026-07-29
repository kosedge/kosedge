# NFL Week-1 Readiness Report

**Generated:** 2026-07-29 (updated after QB starter lock)  
**Branch:** `nfl-second-order-edge`  
**Verdict:** **READY WITH CAVEATS**  
**Score:** **8.3 / 10** (was 8.0; +0.3 for clearing dual QB rooms / pass publish gate)

---

## Executive verdict (founder)

Ship **selective spread PLAY** under YELLOW for REG season Week 1.  
Do **not** sell full-slate, totals PLAY, props stakes, or preseason PLAY.  
**100k season MC** + **QB starter volume lock** landed — win totals / SB usable;  
pass-season board clears dual-room gate.  
Player board overall `publish_ready` still **false** on **skill leader floors only** (honest).  
Projections Hub: Projected | Actual (Actual = — until REG).

---

## Posture by market

| Market | Posture | Notes |
| --- | --- | --- |
| **Sides (spread)** | **PLAY selective** | `spread_play_v2_cap7` [2.5, 7.0); confirmatory GREEN |
| **Moneyline** | **PLAY derived** | Only if spread PLAY + vig-aware EV ≥ 2% |
| **Totals** | **PASS / sides-only** | Confirmatory CLV RED (~0.35); `TOTAL_PLAY_ENABLED=false` |
| **Props** | **Research only** | `PLAY_STAKE_ELIGIBLE=false` |
| **Preseason** | **INFO desk** | `NFL_PRESEASON_MODE=info` blocks season PLAY on PRE |
| **Futures / win totals** | **Usable (100k)** | Bundle below; not a betting PLAY gate |
| **Player season totals** | **Pass gate GREEN / skill RED** | See QB lock section |

---

## Checklist status

| Item | Status |
| --- | --- |
| Paper book tracker | **Done** |
| ML EV gate | **Done** |
| Totals band review | **Done** — sides-only |
| Aug 25 factor freeze | **Done** — H+D ON; E/B/A OFF |
| Preseason info desk | **Done** |
| Hard model pass | **Done** — no blend/PLAY recal |
| Projections Projected\|Actual | **Done** + weekly actuals writer scaffold |
| 100k sims | **Done** — `nfl-preseason-sim-2026-20260729T160818Z` |
| QB starter volume lock | **Done** — dual rooms **0**; pass `publish_ready` **true** |
| Overall player `publish_ready` | **False (honest)** — skill floors only |
| Unit tests | Player season totals **8 passed** (incl. QB lock); enterprise/ML prior suite green |

---

## 100k season sim

| | |
| --- | --- |
| Bundle | `data/ops/nfl-preseason-sim-2026-20260729T160818Z` |
| MC iterations | **100000** (team/futures unchanged by player regen) |
| Sanity | SB 1.0000 · division 7.9996 · playoff 13.9999 |
| Hub loads? | **Yes** |

---

## QB starter lock (2026-07-29)

Report: `data/ops/nfl-qb-starter-lock-report.md`  
Code: `data_platform_nfl/player_season_totals.py`  
Regen (no 100k re-run): `scripts/nfl/regen_player_season_totals.py`

| Gate | Before | After |
| --- | ---: | ---: |
| Dual full-volume QB rooms | 7 | **0** |
| Pass `publish_ready` | false | **true** |
| Skill `publish_ready_skill` | false | **false** |
| Overall `publish_ready` | false | **false** |

Skill still fails: top rush **1307.5** &lt; 1400; top rec **1234.9** &lt; 1300; WR≥1200 count **1** (need 3).  
**Do not cut thresholds.**

---

## Locked model config

- Engine: KAV v3 + MC  
- Factors: H travel×weather ON, D error-regime ON, E/B/A OFF  
- Product gate: YELLOW  
- Freeze date: **2026-08-25**

---

## Remaining → enterprise projections (honest ETA)

| Work | ETA |
| --- | --- |
| RB/WR share calibration so skill leaders clear floors | **2–4 eng days** |
| Weekly actuals populate (`write_projection_actuals.py --from-db`) after Week 1 | **1–2 eng days** |
| Optional: push QB lock into weekly baseline materialization (not just season totals) | **1–2 eng days** |
| Deploy web with updated bundle | **&lt;1 hour** after merge |

---

## Needs from user

1. Approve RB/WR volume calibration workstream (or accept skill research-grade through early season).  
2. Confirm Vercel packs `data/ops` (tracing includes already set for `/pro/nfl/projections`).  
3. No PLAY widen / no E/B/A re-enable before Aug 25 protocol.

**Act on:** selective sides + ML EV; futures from 100k; player pass board usable post-lock; skill totals still research.
