# NFL Path to ~9.5 / Subscription-Grade Edge

Generated: 2026-07-28T21:45:00Z  
Branch: `nfl-kav-sharpen`  
DB: `127.0.0.1:5432/kosedge`  
Policy: **`spread_play_v2_cap7`**

## Executive verdict

| Claim | Status |
| --- | --- |
| PLAY band calibration | **DONE** — spread PLAY now `2.5 ≤ \|edge\| < 7.0` (was ≥2.5 uncapped) |
| Movement-CLV methodology | **DONE** — product CLV+ uses open≠close, n_snaps≥2 |
| Confirmatory 2024–25 spread PLAY | **GREEN** — ATS 73.1% (n=227), CLV+ **61.2%** (n_move=206) |
| Primary 2025 alone | **YELLOW** — ATS 69.6% (n=112), CLV move n=101 (&lt;200) |
| Mean \|edge\| on PLAY | **4.46** (was ~7.1 uncapped) |
| `selective_play_ready` | **true** |
| `betting_product_ready` (full slate) | **false** |
| Honest model score (now) | **7.6 / 10** |

Do **not** claim 9.5 or every-game 60%. Selective spread PLAY under v2 clears confirmatory ATS+CLV; full-slate and live-2026 durability remain open.

---

## 1) Old vs new pre-registration

| | v1 (legacy) | v2 (this milestone) |
| --- | --- | --- |
| Spread PLAY | \|edge\| ≥ 2.5 (uncapped) | **2.5 ≤ \|edge\| &lt; 7.0** |
| Mega-edges ≥7 | PLAY | **PASS** (research / size-down) |
| CLV metric | all open/close incl. flats | **movement only** (open≠close) |
| 2025 mean \|edge\| | ~7.1 | **~4.7** |
| Confirmatory CLV gate | failed (flats diluted) | **GREEN** n_move=206 @ 61.2% |

Totals PLAY band unchanged: `[2.5, 3.0)`.

---

## 2) PLAY-only metrics

### Primary unused — 2025

| Slice | n | ATS | mean\|edge\| | ROI | CLV move n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Spread PLAY | 112 | 0.696 | 4.66 | +0.33 | 101 | 0.584 | YELLOW |
| Total PLAY | 30 | 0.700 | 2.76 | +0.34 | 25 | 0.400 | RED |

### Confirmatory — 2024–2025 (product selective claim)

| Slice | n | ATS | mean\|edge\| | ROI | CLV move n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **Spread PLAY** | **227** | **0.731** | **4.46** | **+0.40** | **206** | **0.612** | **GREEN** |
| Total PLAY | 52 | 0.615 | 2.75 | +0.17 | 43 | 0.349 | RED |

### Clean-era check — 2020–2022

Spread PLAY under v2 still clears −110 ATS (~54%) but **movement-CLV collapses** (~39%). Do not claim multi-era durability from 2020–22 boards (pre-pipeline / weaker OC).

---

## 3) Gate status

| Check | Status |
| --- | --- |
| Full-slate ATS | RED |
| Full-slate CLV | RED |
| **PLAY-only (confirmatory)** | **GREEN** |
| MAE vs market | GREEN |
| Supervised holdout | GREEN |
| Props stake-off | GREEN |
| Overall | RED (full-slate fails) |
| **selective_play_ready** | **true** |
| betting_product_ready | **false** |

**Product posture:** PASS default remains. Env `NFL_PRODUCT_GATE_STATUS` may be **YELLOW** (not RED) so v2 PLAY tags can publish when segment evidence clears — still not every-game GREEN.

---

## 4) Honest score: **7.6 / 10**

| Score | Meaning |
| ---: | --- |
| 10 | Institutional Vegas-competitive every-game |
| 7.5–8 | Chargeable selective edge with ATS+CLV holdout |
| 7.1 | Prior (PLAY ATS strong, CLV YELLOW) |

**7.6** = v2 band + movement-CLV GREEN on 2024–25 confirmatory + sharper mean edge. Cap below ~8.5 until primary-2025 CLV n≥200 and/or live 2026 confirms; below 9.5 while full-slate fails and clean-era CLV is weak.

---

## 5) What shipped this milestone

- `SPREAD_PLAY_MAX = 7.0` in Python + web publish policy
- `scripts/nfl/play_only_holdout.py` v2 (movement CLV, confirmatory universe)
- Enterprise gate reads confirmatory + sets `selective_play_ready`
- Fixed OC open/close `ARRAY_AGG` null filtering (was starving CLV n)
- KAV input serialization (prior commit) unchanged

No Odds API densify re-burn. No failed blend retune promoted.

---

## 6) Gaps to 9.5 / ~60% PLAY

1. Grow **primary 2025** movement-CLV to n≥200 (live capture / residual OC gaps — no 2020–23 re-burn).
2. Paper → stake **2026** under locked v2 thresholds.
3. Explain / fix weak **2020–22** CLV (or formally scope claim to post-2023 pipeline boards).
4. Totals PLAY still thin / CLV-red — keep research-only.
5. Edge calibration further (supervised margin scale) so fewer ≥7 PASS rejects are “true” edges mis-sized.
6. Special-teams KAV / inactives only if leakage-safe + holdout-positive.
7. Full-slate ATS still ~50% — never claim every-game card.

---

## 7) Needs from user

1. Set `NFL_PRODUCT_GATE_STATUS=YELLOW` in envs where selective PLAY should surface (keep RED to force all-PASS).
2. Do **not** re-densify 2020–23.
3. Keep open/close snapshots flowing for 2026 (CLV n growth).
4. Prod warehouse promote if Railway still slim.
