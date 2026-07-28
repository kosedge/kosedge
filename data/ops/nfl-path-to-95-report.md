# NFL Path to ~9.5 / Subscription-Grade Edge

Generated: 2026-07-28T21:50:00Z  
Branch: `nfl-kav-sharpen`  
Policy: **`spread_play_v2_cap7`** (`2.5 ≤ |edge| < 7.0`)

## Executive verdict

| Claim | Status |
| --- | --- |
| Confirmatory 2024–25 spread PLAY | **GREEN** — ATS 73.1% (n=227), CLV+ 61.2% (n_move=206) |
| Primary-2025 CLV n≥200 | **HARD CEILING** — consensus move n=100 / PLAY n=112 |
| Totals PLAY GREEN band | **NONE** — keep RED / research-only |
| Product era scope | **2024+ confirmatory** (2023+ pipeline supportive; 2020–22 CLV fails) |
| 2026 paper track | **SCAFFOLDED** — 23 spread PLAY tags; 12 early settled (thin) |
| `selective_play_ready` | **true** |
| `betting_product_ready` | **false** (full-slate RED) |
| Honest score (now) | **7.7 / 10** |

---

## 1) Primary-2025 CLV ceiling (no credit re-burn)

| Metric | Value |
| --- | ---: |
| 2025 settled schedule | 285 |
| Owned OC ≥2 snaps | 285 (after orphan rematch: +24 snaps) |
| Slate-wide open≠close | ~249 |
| v2 PLAY n | **112** |
| Consensus movement-CLV n | **100** |
| Consensus CLV+ | **59.0%** |
| Multi-book movement-CLV n | 163 (CLV+ 60.1%) — **secondary only** |

**Hard ceiling:** Inside the locked v2 PLAY band, primary-2025 consensus movement-CLV **cannot** reach n≥200 (only 112 PLAY games). Expanding the band would undo calibration; Odds densify re-burn is forbidden. Multi-book inflates n by double-counting games — not used for `selective_play_ready`.

Artifact: `nfl-play-durability-totals-scan.json`, rematch: `nfl-oc-orphan-rematch.json`.

---

## 2) Totals PLAY

Scanned bands on 2024–25 / 2023–25: **no GREEN** (ATS+CLV n≥200 @ ≥55%).

| Band | 2024–25 n | ATS | CLV n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| shipped `[2.5, 3.0)` | 50 | 0.62 | 37 | 0.24 | RED |
| `[2.0, 3.0)` | 103 | 0.61 | 83 | 0.35 | ATS-only |
| `[3.0, 4.0)` | 76 | 0.72 | 65 | 0.39 | ATS-only |

**Verdict:** Keep totals PLAY research-only; do not flip stake.

---

## 3) Era durability (spread v2)

| Era | n | ATS | CLV move n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| 2020–2022 | 403 | 0.556 | 238 | 0.458 | ATS-only (CLV fail) |
| 2023 | 120 | 0.700 | 101 | 0.545 | ATS-only |
| **2024–2025** | **232** | **0.724** | **214** | **0.603** | **GREEN** |
| 2023–2025 | 352 | 0.716 | 315 | 0.584 | GREEN |

**Product scope:** Selective spread PLAY claim = **2024+ confirmatory regime** (+ live 2026). Do **not** market multi-era durability from 2020–22 CLV.

---

## 4) 2026 paper track

Script: `scripts/nfl/paper_track_2026.py` → `nfl-paper-track-2026.{json,md}`

| Item | Count |
| --- | ---: |
| Games 2026 | 314 |
| With proj + line | 151 |
| Spread PLAY paper tags | 23 |
| Unsettled spread PLAY | 11 |
| Settled spread PLAY (early/Jan window) | 12 |
| Settled ATS (thin) | 0.667 (n=12) |
| Settled CLV+ (thin) | 0.222 (n_move=9) |

Re-run weekly as the season progresses. Thin settled sample is **not** a promotion signal.

---

## 5) Gate status

| Check | Status |
| --- | --- |
| Full-slate ATS / CLV | RED |
| PLAY-only confirmatory | **GREEN** |
| Primary-2025 CLV n≥200 | Impossible under v2 without re-burn / band expand |
| Totals PLAY | RED |
| MAE / supervised / props | GREEN / GREEN / GREEN |
| **selective_play_ready** | **true** |
| **betting_product_ready** | **false** |

PASS default remains. `NFL_PRODUCT_GATE_STATUS=YELLOW` allows selective PLAY tags; leave RED for all-PASS.

---

## 6) Honest score: **7.7 / 10**

| Was | Now | Why |
| ---: | ---: | --- |
| 7.6 | **7.7** | Ceiling documented + orphan rematch + era scope + 2026 paper scaffold + totals honesty |

Still far from 9.5: no primary-2025 CLV n≥200, no totals GREEN, live-2026 unproven, full-slate fails.

---

## 7) Gaps to 9.5

1. Accumulate **live 2026** PLAY ATS/CLV under locked v2 (paper → stake).  
2. Accept primary-2025 CLV ceiling — grow sample only via **new season** OC.  
3. Totals need a separate model track (current bands CLV-failed).  
4. Optional leakage-safe lifts (ST KAV / inactives) only if holdout-positive.  
5. Never claim every-game card while full-slate ATS ~50%.

---

## 8) Needs from user

1. `NFL_PRODUCT_GATE_STATUS=YELLOW` where selective PLAY should publish.  
2. No 2020–23 densify re-burn.  
3. Keep capturing open/close through 2026 (only path to larger primary-season CLV n).  
4. Prod warehouse promote if Railway still slim.
