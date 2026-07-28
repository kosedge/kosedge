# NFL Path to ~9.5 / Subscription-Grade Edge

Generated: 2026-07-28T22:00:00Z  
Branch: `nfl-kav-sharpen`  
Policy: **`spread_play_v2_cap7`**  
Active supervised fit: **schema v3** (v4 ST candidate rolled back)

## Executive verdict

| Claim | Status |
| --- | --- |
| Selective PLAY (2024–25 confirmatory) | **GREEN** — ATS 73.1% n=227, CLV+ 61.2% n_move=206 |
| `selective_play_ready` | **true** |
| `betting_product_ready` | **false** (full-slate RED) |
| Primary 2025 CLV n≥200 | **BLOCKED** — only 112 PLAY spreads under v2 band (math ceiling) |
| Special-teams KAV → supervised v4 | **Built + tested — NOT promoted** (holdout regresses) |
| Honest score (now) | **7.6 / 10** |

---

## 1) PLAY / CLV status (unchanged product claim)

| Universe | n | ATS | mean\|edge\| | CLV move n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2024–25 confirmatory | 227 | 0.731 | 4.46 | **206** | **0.612** | **GREEN** |
| 2025 primary | 112 | 0.696 | 4.66 | 101 | 0.584 | YELLOW |

**Hard blocker for primary-2025 CLV n≥200:** under `2.5≤|edge|<7`, 2025 yields only ~112 PLAY spreads. Owned OC already has ≥2 snaps on all 285 settled games; densify cannot create more PLAY tags. Expanding the band would undo calibration. Product claim correctly uses **2024–25 confirmatory**.

---

## 2) Special-teams KAV experiment (this iteration)

| Step | Result |
| --- | --- |
| PBP ST EPA (FG/XP/punt/kickoff) | 7124 team-game rows |
| Weekly ST KAV + week−1 matchup lag | 1409/1693 games 2020–25 (week1 = 0 by design) |
| Supervised schema v4 (+3 ST features) | Chronological holdout n=570 |
| vs v3 | Brier **+0.0011**, margin MAE **+0.046**, total MAE **−0.035** |
| Promote? | **NO** — rolled active fit back to v3 |

Artifacts: `nfl-st-kav-build.json`, `nfl-kav-supervised-retrain-v4.json`, `nfl-kav-supervised-v3-vs-v4.json`.

---

## 3) Gate status

| Check | Status |
| --- | --- |
| PLAY-only confirmatory | GREEN |
| Supervised holdout (active v3) | GREEN |
| MAE vs market | GREEN |
| Full-slate ATS/CLV | RED |
| selective_play_ready | **true** |
| betting_product_ready | **false** |

PASS default remains. Prefer `NFL_PRODUCT_GATE_STATUS=YELLOW` to surface v2 PLAY tags.

---

## 4) Honest score: **7.6 / 10**

No score bump from ST (failed holdout). Selective CLV GREEN already priced in at 7.6.

---

## 5) Gaps to 9.5

1. Live **2026** paper→stake under locked v2 thresholds (only path to grow “unused” CLV without widening band).
2. ST / inactives: need a formulation that **improves** chronological holdout before re-sim.
3. Edge magnitude: further shrink model↔market gap without killing PLAY ATS.
4. Totals PLAY still research-only.
5. Full-slate ATS ~50% — never claim every-game card.
6. 2020–22 CLV weak — scope claim to post-2023 pipeline boards.

---

## 6) Needs from user

1. `NFL_PRODUCT_GATE_STATUS=YELLOW` where selective PLAY should publish.
2. Do **not** re-densify 2020–23 (won’t fix primary-2025 PLAY n ceiling).
3. Keep 2026 open/close snapshots flowing.
4. Optional: approve limited **2024–25 residual** Odds pulls only if any single-snap dates appear later — not needed now (0 missing).
