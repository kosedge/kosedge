# NFL Path to ~9.5 / Subscription-Grade Edge

Generated: 2026-07-28T23:20:00Z  
Branch: `nfl-kav-sharpen`  
Policy: **`spread_play_v2_cap7`** (unchanged — not re-promoted)  
Active supervised fit: **schema v3** (ST v4 rejected; QB continuity probe rejected)

## Executive verdict / next milestone

| Claim | Status |
| --- | --- |
| Selective PLAY (2024–25 confirmatory, v2 band) | **GREEN** — ATS ~72.4% n=232, CLV+ ~59.8% n_move=214 |
| `selective_play_ready` | **true** |
| `betting_product_ready` | **false** (full-slate RED) |
| Primary 2025 CLV n≥200 | **BLOCKED** — ~112 PLAY spreads under v2 (math ceiling) |
| Walk-forward tighter bands | **Registered research-only** — better CLV+, fail n_clv≥200 |
| ST KAV / QB continuity | **Built + tested — NOT promoted** |
| Honest score (now) | **7.7 / 10** (provisional +0.1 for narrow E/H/D wiring; holdout ablation pending — see `nfl-narrow-second-order-report.md`) |

**Product env note:** set `NFL_PRODUCT_GATE_STATUS=YELLOW` to surface selective PLAY (RED forces all PASS). This is the main user-env gate for publishing tags; model work below still ships regardless.

---

## 1) Walk-forward edge-band study (this iteration)

Protocol: select on **2023 only** → confirm once on **2024–25** (no peeking).  
Artifact: `data/ops/nfl-walkforward-play-band-study.{json,md}`  
Code: `scripts/nfl/walkforward_play_band_study.py`  
Constants: `RESEARCH_SPREAD_PLAY_BANDS` in `nfl_side_total_publish_policy.py`

| Band | Role | Confirm n | ATS | CLV n | CLV+ | Gate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| **[2.5,7)** | **product v2** | 232 | 0.724 | **214** | 0.598 | **GREEN** |
| [4.0,8) | research | 172 | 0.756 | 155 | **0.645** | YELLOW |
| [4.0,7) | research | 132 | 0.758 | 120 | 0.633 | YELLOW |
| [5.0,8) | research (2023 CLV+ leader) | 127 | 0.787 | 112 | 0.625 | YELLOW |
| [3.5,7) | research | 158 | 0.759 | 145 | 0.614 | YELLOW |

**Decision:** keep product `spread_play_v2_cap7`. No capped band beats v2 on confirmatory GREEN volume. Uncapped bands excluded from research registration (mega-edge calibration risk).

---

## 2) Feature probes (leakage-safe; promote only if holdout improves)

| Experiment | Result | Promote? |
| --- | --- | --- |
| ST KAV → schema v4 | prior: Brier/margin regress | **NO** (quarantined) |
| QB continuity (week-lagged primary passer) | Brier +0.0003, margin MAE +0.015 | **NO** |
| Injury / rest / dome / turf | already in v3 FEATURE_KEYS | — |
| Weather / travel | live sim inputs present; not added to supervised (no holdout win yet) | deferred |
| Line-move as model feature | not added (timing discipline; CLV grading only) | deferred |

QB probe artifact: `data/ops/nfl-qb-continuity-holdout-probe.json`  
Coverage: 1075/3562 rows with both-team QB flags (~2022–25 attempts data).

---

## 3) Sim / quality

| Item | Result |
| --- | --- |
| Projection inputs KAV audit | 2025 boards were missing KAV keys → **backfilled 240** rows from matchup pack (markets unchanged) |
| 2025 KAV still missing | ~34% (week-1 / null matchup KAV) |
| 2026 KAV in matchup | **0** until real weekly features exist — not invented |
| Paper track universe bug | Was grading 2025 playoffs on `season_year=2026` rows → **fixed** (`sch.season=2026` required) |
| Clean 2026 paper | 241 season games, 11 unsettled spread PLAY, **0 settled** |

Artifacts: `nfl-projection-input-completeness.json`, `nfl-kav-projection-inputs-backfill.json`, `nfl-paper-track-2026.{json,md}`

---

## 4) Gate status (unchanged product claim)

| Check | Status |
| --- | --- |
| PLAY-only confirmatory (v2) | GREEN |
| Supervised holdout (active v3) | GREEN |
| MAE vs market | GREEN |
| Full-slate ATS/CLV | RED |
| selective_play_ready | **true** |
| betting_product_ready | **false** |

PASS default remains. Prefer `NFL_PRODUCT_GATE_STATUS=YELLOW` to surface v2 PLAY tags.

---

## 5) Honest score: **7.7 / 10**

Provisional +0.1 after narrow second-order ship (info velocity, travel×weather, thin coach, light error-regime). **Not** holdout-confirmed. ST/QB remain rejected; product band unchanged; primary-2025 CLV n≥200 still math-blocked. Details: `nfl-narrow-second-order-report.md`.

---

## 6) Gaps to 9.5 / next unblocked work

1. Live **2026** paper→stake under locked v2 (and optionally shadow research bands) as scores land.
2. Supervised features that **beat** chronological holdout (travel deltas, weather when outdoor, inactives with week−1 lag).
3. Edge magnitude shrink without killing PLAY ATS/CLV.
4. Totals PLAY still research-only.
5. Do **not** re-promote ST KAV; do **not** densify 2020–23 Odds API.

---

## 7) Needs from user

1. `NFL_PRODUCT_GATE_STATUS=YELLOW` where selective PLAY should publish.
2. Keep 2026 open/close snapshots flowing.
3. No Odds API densify of 2020–23.
