# NFL Week-1 Readiness Report

**Generated:** 2026-07-29 (updated after 100k sim)  
**Branch:** `nfl-second-order-edge`  
**Verdict:** **READY WITH CAVEATS**  
**Score:** **8.0 / 10** (was 7.8; +0.2 for completed 100k team/futures MC)

---

## Executive verdict (founder)

Ship **selective spread PLAY** under YELLOW for REG season Week 1.  
Do **not** sell full-slate, totals PLAY, props stakes, or preseason PLAY.  
**100k season MC completed** — win totals / playoff / SB probs refreshed.  
Player season totals remain **research-grade** (`publish_ready=false` — dual QB rooms + skill leader floors).  
Projections Hub shows Projected | Actual (Actual = — until REG weeks).

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

---

## Checklist status

| Item | Status |
| --- | --- |
| Paper book tracker | **Done** — `data/ops/nfl-paper-book-latest.{json,md}` |
| ML EV gate | **Done** — Python + fair-lines wire + TS mirror + tests |
| Totals band review | **Done** — sides-only launch |
| Aug 25 factor freeze | **Done** — H+D ON; E/B/A OFF |
| Preseason info desk | **Done** — docs + publish-path block |
| Hard model pass | **Done** — no blend/PLAY recal |
| Projections Projected\|Actual | **Done** — UI + empty actuals scaffold |
| 100k sims | **Done** — `nfl-preseason-sim-2026-20260729T160818Z` (100000 iters) |
| Player `publish_ready` | **False (honest)** — see 100k section |
| Unit tests | **14 passed** (enterprise gates + ML policy); web vitest updated |

---

## 100k season sim — completed

| | |
| --- | --- |
| Bundle | `data/ops/nfl-preseason-sim-2026-20260729T160818Z` |
| Generated | `2026-07-29T16:12:46Z` |
| `season_monte_carlo_iterations` | **100000** |
| Games | 272 REG with model win-prob |
| Sanity | SB **1.0000** · division **7.9996** · playoff **13.9999** |
| Hub loads this bundle? | **Yes** — `nfl-preseason-artifacts.ts` sorts `nfl-preseason-sim-2026-*` reverse by name |
| Progress | `data/ops/nfl-100k-sim-progress.{json,md}` |
| Log | `data/ops/nfl-100k-sim-run.log` |

### `publish_ready: false` — why (do not fake green)

From `player_season_pass_quality.json` / quality checks:

1. **Pass:** `dual_full_volume_qb_rooms_count=7` (CIN, CLE, NO, ATL, SF, MIN, WAS) — two+ QBs with starter-scale yards on the same roster.
2. **Skill:** top rusher **1307.5** < 1400; top receiver **1234.9** < 1300; only **1** WR ≥1200 (gate wants 3).

Top passer Goff **4122.8** clears the ≥3800 floor; that alone is not enough for `publish_ready`.

**Safe action:** leave false. Fix path is depth-chart / role allocation + re-run player totals (not a threshold retune).

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

- UI: `/pro/nfl/projections` — Projected | Actual side-by-side.  
- Bundle: **100k** team/futures + player CSVs (research until publish_ready).  
- Actuals: `data/ops/nfl-projection-actuals-2026.json` empty scaffold until Week 1+.

---

## Remaining work → enterprise projections (honest ETA)

| Work | ETA | Notes |
| --- | --- | --- |
| Depth-chart / QB room volume fix → re-gen player totals | **2–5 eng days** | Clear 7 dual rooms; then re-check skill floors |
| Weekly actuals pipeline (DB → `nfl-projection-actuals-2026.json`) | **1–2 eng days** | After Week 1 kickoff; cron or ops script |
| Skill leader calibration (if still short after QB fix) | **1–3 eng days** | Only if holdout-backed; no vanity threshold cut |
| Deploy web (Vercel) with new bundle in repo | **<1 hour** after merge/push | Hub reads from `data/ops` at runtime on deploy FS — confirm prod includes `data/ops` or serve via API |
| Vercel `data/ops` availability | **Verify 0.5 day** | If prod image omits ops CSVs, wire artifact fetch or API |

**No densify. No PLAY widen. No E/B/A re-enable.**

---

## Needs from user

1. Approve depth-chart / starter locking workstream for player `publish_ready` (or accept research-grade player board through Week 1).  
2. Confirm whether Vercel deploy packs `data/ops/nfl-preseason-sim-*` (or needs blob/API).  
3. After Week 1: weekly actuals refresh owner.  
4. Do **not** ask to widen PLAY or re-enable E/B/A before Aug 25 freeze protocol.

---

## Why not full READY (10/10)

- Full-slate ATS still RED (product remains selective).  
- Totals not stake-eligible.  
- Player projections `publish_ready=false`.  
- Actuals pipeline not live until REG weeks.  
- Primary-2025 alone is YELLOW on CLV n; claim is confirmatory 2024–25 selective.

**Act on:** selective sides + ML EV under YELLOW; futures/win totals from 100k bundle; keep totals/props/preseason off the paid PLAY card; label player season totals research until publish_ready.
