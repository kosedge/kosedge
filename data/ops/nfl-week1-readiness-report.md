# NFL Week-1 Readiness Report

**Generated:** 2026-07-29 (pre-Week-1 unification pass)  
**Branch:** `nfl-second-order-edge` → merge path `deploy-vercel`  
**Verdict:** **READY WITH CAVEATS**  
**Score:** **8.8 / 10** (was 8.7; +0.1 for production actuals pipeline + PRE/ML gate hardening + ops cadence)

---

## Executive verdict (founder)

Ship **selective spread PLAY** under YELLOW for REG season Week 1.  
Do **not** sell full-slate, totals PLAY, props stakes, or preseason PLAY.  
**100k season MC** + **QB starter lock** + **skill prior-anchor** landed.  
Player season board overall `publish_ready` is **true** (honest gates; floors not cut).  
Projections Hub: Projected | Actual — Actual live via `/nfl/ops/projection-actuals` (empty/— preseason; 2025 smoke OK).

---

## Posture by market

| Market | Posture | Notes |
| --- | --- | --- |
| **Sides (spread)** | **PLAY selective** | `spread_play_v2_cap7` [2.5, 7.0); confirmatory GREEN |
| **Moneyline** | **PLAY derived** | Only if spread PLAY + vig-aware EV ≥ 2%; PRE blocked |
| **Totals** | **PASS / sides-only** | Confirmatory CLV RED (~0.35); `TOTAL_PLAY_ENABLED=false` |
| **Props** | **Research only** | `PLAY_STAKE_ELIGIBLE=false` |
| **Preseason** | **INFO desk** | `NFL_PRESEASON_MODE=info` blocks season PLAY on PRE (API + Edge Board) |
| **Futures / win totals** | **Usable (100k)** | Bundle below; not a betting PLAY gate |
| **Player season totals** | **Publish GREEN** | Pass + skill gates true after QB lock + skill prior |

---

## Checklist status

| Item | Status |
| --- | --- |
| Paper book tracker | **Done** — latest artifact refreshed |
| ML EV gate | **Done** — PRE season_type wired |
| Totals band review | **Done** — sides-only |
| Aug 25 factor freeze | **Done** — H+D ON; E/B/A OFF + operator checklist |
| Preseason info desk | **Done** — fair-lines tags → Edge Board |
| Hard model pass | **Done** — no blend/PLAY recal |
| Projections Projected\|Actual | **Done** — DB writer + live API + file fallback |
| Weekly actuals pipeline | **Done** — production-ready (empty until REG scores) |
| Early-season W1–4 uncertainty | **Done** — D-style boost (no 50% blend) |
| 100k sims | **Done** — `nfl-preseason-sim-2026-20260729T160818Z` |
| QB starter volume lock | **Done** — dual rooms **0**; pass `publish_ready` **true** |
| Skill prior-anchor calibration | **Done** — skill + overall `publish_ready` **true** |
| Overall player `publish_ready` | **True (honest)** |
| Unit tests | Projection actuals + gates + ML + second-order green |

---

## 100k season sim

| | |
| --- | --- |
| Bundle | `data/ops/nfl-preseason-sim-2026-20260729T160818Z` |
| MC iterations | **100000** (team/futures unchanged by player regen) |
| Sanity | SB 1.0000 · division 7.9996 · playoff 13.9999 |
| Hub loads? | **Yes** |

---

## Weekly actuals (2026-07-29)

- Code: `data_platform_nfl/projection_actuals.py` + `scripts/nfl/write_projection_actuals.py`
- Live: `GET /nfl/ops/projection-actuals?season=2026`
- Write task: `POST /nfl/ops/write-projection-actuals?season=2026`
- Cadence: `data/ops/nfl-weekly-ops-cadence.md` (wired into `run-weekly-inseason-update.sh`)
- **2025 smoke:** 32 teams, 549 unique players; PHI 11–6; top passer ~4707 pass yards
- **2026:** empty scaffold (no REG scores yet) — UI shows —

---

## Locked model config

- Engine: KAV v3 + MC  
- Factors: H travel×weather ON, D error-regime ON (incl. W1–4 boost), E/B/A OFF  
- Product gate: YELLOW  
- Freeze date: **2026-08-25**

---

## Remaining → enterprise projections (honest ETA)

| Work | ETA |
| --- | --- |
| Live REG Week 1 scores → Actual column populates | **calendar** (pipeline ready) |
| Optional: rematerialize weekly baselines so props path matches season-total calibration | **2–3 eng days** |
| Optional: push QB lock into weekly baseline materialization | **1–2 eng days** |
| Confirmatory in-season paper after W1–4 | **calendar** |

---

## Needs from user

1. Confirm Vercel packs `data/ops` (tracing includes already set for `/pro/nfl/projections`).  
2. No PLAY widen / no E/B/A re-enable before Aug 25 protocol.  
3. After merge to `deploy-vercel`, verify Railway health + Vercel projections 200.

**Act on:** selective sides + ML EV; futures from 100k; player season totals board publish-ready (honest).  
**Do not claim:** 9.5 / full-slate ready.


---

## Prod verification (2026-07-29 evening)

| Check | Result |
| --- | --- |
| Railway `/health` | **200** ok |
| Railway fair-lines | **167** rows · ~**24** spread PLAY · `publish_tag_ml` present · `season_type=REG` |
| Railway `/nfl/ops/projection-actuals?season=2026` | **200** empty scaffold (preseason) |
| Vercel `/pro/nfl/projections` | **200** |
| PR | https://github.com/kosedge/kosedge/pull/24 |
| Deploy branch | `deploy-vercel` includes second-order merge |

Railway notes fixed during this pass: clear dashboard `rootDirectory` when using
`--path-as-root`; service domain target port **8080** (was 8000 → 502).
Worker/beat may still need a follow-up `railway up` sync (API is the board path).

