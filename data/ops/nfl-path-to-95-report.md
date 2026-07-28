# NFL Path to ~9.5 / Subscription-Grade Edge

Generated: 2026-07-28T21:00:00Z  
Branch: `nfl-kav-sharpen`  
DB: `127.0.0.1:5432/kosedge`

## Executive verdict

| Claim | Status |
| --- | --- |
| Phase A commit/push | **DONE** (tree was already clean @ `096a973e`) |
| PLAY-only unused holdout evaluator | **DONE** (`scripts/nfl/play_only_holdout.py`) |
| Pre-registered thresholds | spread PLAY ≥2.5; total PLAY ∈ [2.5, 3.0) |
| 2025 spread PLAY ATS | **0.762** (n=206) — clears −110 / stretch band |
| 2025 spread PLAY CLV+ | **0.533** (n_clv=105) — **fails** product n≥200 @ 55% |
| GREEN shrink segment | **none** |
| Betting-product / selective PLAY GREEN | **NO — YELLOW/RED** |
| Honest model score (now) | **7.1 / 10** |

Do **not** claim 9.5 or ~60% subscription win rate. ATS on the PLAY slice looks strong; CLV does not clear the pre-registered product floor.

---

## 1) PLAY-only holdout (primary)

Pre-registered policy matches `nfl_side_total_publish_policy`.

| Slice (2025) | n | ATS | ROI (−110u) | CLV n | CLV+ | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Combined PLAY | 312→232* | 0.759 | +0.45 | 119 | 0.496 | YELLOW |
| Spread PLAY | 206 | **0.762** | +0.46 | 105 | 0.533 | YELLOW |
| Total PLAY | 26 | 0.731 | +0.40 | 14 | 0.214 | RED |

\*After `external_id` dedupe + pre-kickoff projection selection.

**Shrink ladder (pre-declared):** no GREEN segments. Best remaining: `spread_edge_5.0_plus` (YELLOW). Totals stay research-only (n&lt;60).

**Honesty notes**

1. Edge-side PLAY ATS ≫ model-as-line ATS (~0.52 on full 2025 slate). Large |edge| vs close means “bet model side at market” can cover often while the model line itself is poorly calibrated.
2. CLV+ ~53% with n=105 blocks subscription GREEN (need ≥55% with n≥200).
3. Threshold selection originally used 2023–25 bucket study — 2025 overlap disclosed; walk-forward by season is in `nfl-play-only-holdout.json`.
4. KAV fields were applied at sim-time via matchup pack / supervised features, but were **missing from serialized projection `inputs`** — fixed in `nfl_simulator.py` for future boards (auditability). No Odds API re-burn.

Artifacts: `data/ops/nfl-play-only-holdout.{json,md}`

---

## 2) Model improvement (this milestone)

| Item | Result |
| --- | --- |
| PLAY-only holdout script | Shipped; DB-first; owned OC CLV |
| Enterprise gate `play_only_holdout` | Wired into evaluator + docs |
| KAV audit serialization | Fixed (home/away kav_* + kav_as_of_week in projection inputs) |
| Supervised v3 / densify 2020–23 | Unchanged — do not re-burn |
| Blend retune | Not promoted (prior failed/conservative stance kept) |
| Props | Stake-off unchanged |

Further feature work (special teams KAV unit, inactives, weather/travel CLV features) remains queued — not promoted without PLAY CLV GREEN.

---

## 3) Gate status

| Check | Status |
| --- | --- |
| Full-slate ATS | RED (~0.50) |
| Full-slate CLV | RED/YELLOW |
| PLAY-only holdout | **YELLOW** (ATS ok, CLV short) |
| MAE vs market | GREEN |
| Supervised holdout | GREEN |
| Props stake-off | GREEN |
| Overall / betting-product ready | **RED / false** |
| Selective PLAY ready | **false** |

---

## 4) Honest score: **7.1 / 10**

| Score | Meaning |
| ---: | --- |
| 10 | Institutional Vegas-competitive every-game |
| 7 | Chargeable **selective** edge with holdout evidence |
| 5.5 | Prior baseline |

**7.1** = prior 6.8 + PLAY-only holdout infrastructure + ATS evidence on selective slice + gate honesty. Cap below ~7.5 until CLV n/rate clears on pre-registered PLAY universe (live 2026 preferred).

---

## 5) Gaps to 9.5 / ~60% PLAY

1. Grow owned OPEN→CLOSE CLV on PLAY tags to n≥200 with +rate ≥55% (live season + densified history; no re-burn of completed densify).
2. Calibrate edge magnitude (reduce false PLAY volume; mean |edge| ~7 is too wide vs market).
3. Confirm 2026 live PLAY ATS/CLV under locked thresholds (paper → stake).
4. Ensure KAV appears in new projection audits post-fix; spot-check week≥2 boards.
5. Special-teams / inactives / QB continuity only if leakage-safe and holdout-positive.
6. Props remain research-only until dedicated holdout.
7. Prod warehouse promote if Railway still on slim DB.

---

## 6) Needs from user

1. Keep `NFL_PRODUCT_GATE_STATUS` conservative (RED/YELLOW) — PASS default.
2. Do **not** re-densify 2020–23 OC.
3. Optional: `gh auth` already OK — PR #15 is the vehicle; review PLAY holdout artifacts there.
4. For live CLV growth: continue capturing open/close into `odds_snapshots` through 2026 season.
