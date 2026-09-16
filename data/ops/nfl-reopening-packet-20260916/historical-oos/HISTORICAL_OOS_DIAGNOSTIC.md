# HISTORICAL OOS DIAGNOSTIC — frozen packaged-EPA (overlays OFF)

**As of:** 2026-09-16T16:18:52-04:00 (ET)  
**Live git_sha:** `153b6a884a8e` (confirmed `GET /health` on `https://model-service-production-e253.up.railway.app`)  
**Public:** **HOLD**; Coming soon **ON**; board **NO-GO**  
**Verdict:** **`MODEL_SIGNAL_WEAK`** — research diagnosis only; **not** a CLEAR to reopen.

Diagnosis only. No tuning, refit, coefficient change, feature invention, threshold tune, market-fit, prod writes, remat-to-prod, or `unlock_overlays`. Candidate predictions/equation unchanged.

## Candidate identity

| Field | Value |
|---|---|
| SHA lineage | `153b6a884a8e8a66336fcfc3fa9907742ae978c3` |
| Priors | packaged EPA (`prior_source=packaged_epa_prior`) |
| Overlays | **OFF** (personnel/injury OFF) |
| Scoring lock | `nfl-handicap-core-v3.1` base **45.3** / HFA **1.05** / caps unchanged |
| Exact outcome-backed chapter | 2026 W1 n=16 (folded from `PREDICTIVE_EVAL_HISTORICAL_OOS_W1`) |
| Multi-season chapters | 2024 & 2025 season-start priors reconstructed from prior-season `nfl_dp_team_situational_weekly` (nflverse) → same locked `decompose_matchup` |

W1 identity recon vs filed artifact: **PASS** (ATL@PIT decompose −0.7631 / 44.6523 matched in smoke).

## Chronological OOS design (PIT)

**Not** one mixed 2013–2026 blob for the candidate.

| Test season | Packaged train (pregame-only) | Trailing | n packaged |
|---|---|---|---:|
| 2024 | 2023 situational season averages → strength indices | week-aligned rolling 5g | 285 |
| 2025 | 2024 situational season averages | week-aligned rolling 5g | 285 |
| 2026 | packaged file `as_of=2026-08-08` | rolling where window>0 | 16 (W1 completed only) |

- Expanding **by season** for packaged book; within-season W-L updated **after** each game for the record comparator.
- Trailing join matches in-repo `record_vs_epa` PIT: features at `(season, week, team)`.
- Schedules/scores/lines: Railway `nfl_dp_schedules` read-only (**no Odds API burn**).
- Sign: `spread_home` negative = home favored; error = model − actual; `actual_spread_home = away − home`.

### DATA_INSUFFICIENT gaps (honest)

- Packaged priors **cannot** be built for test seasons ≤2023 (no prior-season situational in warehouse).
- Trailing EPA unavailable pre-2023 (no rolling features).
- July-31 matchup-sim freeze: reproducible for **2026 W1 stamps only**; multi-season **UNREPRODUCIBLE**.
- Closing-line grade for 2026 W1 still unavailable (no Odds burn).

## Comparators (same games, frozen equation)

1. **Packaged-EPA candidate** (season-start book; overlays OFF)  
2. **July-31 freeze** — W1 2026 only (live stamps)  
3. **Trailing EPA** — rolling 5g → same decompose  
4. **Naive:** home pick'em (spread 0), HFA-only (−1.05), locked mean total 45.3, previous-year mean home margin  
5. **Historical market** — nflverse `spread_line`/`total_line` on schedules (converted to home-spread convention); W1 also has warehouse opens from filed eval  

Record W-L book included as integrity comparator only (not the candidate).

## Key metrics

### Exact candidate — 2026 W1 (n=16)

| | Spread | Total |
|---|---:|---:|
| MAE | 12.6044 | 13.2488 |
| Favorite SU | 8/16 (50%) | — |

Enterprise secondary bars (9.5 / 10.5) **miss**. Protocol floor N=200 **miss**.

### Reconstructed packaged OOS — pooled 2024–2026

| Predictor | n spread | Spread MAE | Spread RMSE | Spread bias | n total | Total MAE |
|---|---:|---:|---:|---:|---:|---:|
| **Packaged EPA** | 586 | **10.9463** | 14.148 | 1.0525 | 586 | **10.4901** |
| Market (nflverse) | 586 | 9.7474 | 12.5299 | 0.5785 | 586 | 10.1459 |
| Pick'em + mean total | 586 | 11.2184 | 14.4424 | 2.116 | 586 | 10.6369 |
| HFA-only | 586 | 11.1307 | 14.3263 | 1.066 | — | — |
| Prev-year mean margin | 586 | 11.0953 | 14.2939 | -0.4683 | — | — |
| Trailing EPA (pooled 2023–26; different n) | 871 | 9.5523 | 12.4339 | 1.2213 | 871 | 10.0435 |

Bootstrap 95% CI (packaged spread MAE 2024–26): **[10.2164, 11.6643]**

### ΔMAE vs baselines (candidate − baseline; **negative = better**)

| Contrast | Spread ΔMAE | 95% CI | CI excludes 0? |
|---|---:|---|---|
| Packaged − market | 1.1988 | [0.8167, 1.5672] | True |
| Packaged − pick'em | -0.2721 | [-0.4619, -0.0756] | True |
| Packaged − trailing (same games) | 1.5086 | [1.2482, 1.7605] | True |
| Packaged − July-31 (W1 only) | 0.4131 | [-0.6392, 1.4044] | False |

By-season tables: `historical_oos_by_season.csv`. Game-level: `historical_oos_games.csv`.

## Slices (packaged 2024–2026)

See `historical_oos_slices.json`. Skipped with reason: QB continuity; detailed pace/explosiveness (avoid feature invention). Divisional / early-late / fav-dog / spread-magnitude / total-environment / EPA-disagreement / roof filed where data allows.

## Failure mode

**Primary: `MIXED`** with weights `CALIBRATION 0.30 / INFORMATION 0.20 / ARCHITECTURE 0.40 / SAMPLE_NOISE 0.10`.

Evidence (summary):

- Packaged 2024-2026 spread MAE=10.9463 vs market MAE=9.7474; ΔMAE vs market=1.1988 CI=[0.8167, 1.5672] (positive Δ => worse than market).
- Totals: packaged MAE=10.4901 with locked base 45.3 / caps; W1 CHI@CAR residual 96 vs ~45.5 is compressed-model total failure (ARCHITECTURE on totals).
- Packaged vs trailing ΔMAE spread=1.5086 CI=[1.2482, 1.7605] (CI excludes 0) — season-start packaged book is **strictly worse** than trailing 5g on same equation (ARCHITECTURE).
- Vs pick'em ΔMAE=-0.2721 CI=[-0.4619, -0.0756] — tests whether any directional information exists.
- Exact frozen candidate identity (SHA 153b6a884a8e, packaged 2026 priors, overlays OFF) outcome-backed n=16 W1 MAE spread=12.6044; SU fav agreement 50% — SAMPLE_NOISE dominates single-season early chapter.
- Early-season OOD dampening + near-pick'em compression visible in W1 opens (model sits near pick'em vs larger opens) → CALIBRATION/shrinkage behavior.

## Incremental value (packaged vs trailing)

Identical games 2024-2026 with both packaged and trailing predictions; ΔMAE = packaged - trailing (neg=packaged better); bootstrap CI.

- Spread ΔMAE: **1.5086** CI [1.2482, 1.7605]
- Total ΔMAE: **0.5198** CI [0.3547, 0.6757]

**Honest conclusion: NULL / NEGATIVE.** Packaged is **worse** than trailing on spread (ΔMAE=1.5086, CI [1.2482, 1.7605], CI excludes 0). Season-start packaged EPA does **not** add OOS margin information beyond trailing 5g EPA; trailing dominates on the overlapping set.

## Analogs (W2 pregame commentary only — no new live board numbers)

| Matchup | Packaged fair (research remat) | Historical failure-mode resemblance |
|---|---|---|
| **CAR@ATL** | -2.9043 / 44.5339 | Resembles W1 CHI@CAR / compressed near-pick'em book vs a market that may disagree on side; historical failure mode = INFORMATION+CALIBRATION when EPA book is flat while market has a clear lean. Also integrity lesson from ATL@PIT: do not trust W-L over-move. |
| **MIA@SF** | -3.9635 / 47.6704 | Resembles W1 games where packaged EPA stayed conservative vs a larger market number (dog-side systematic lean in W1 opens); failure mode CALIBRATION/shrinkage if SF market favorite is large. |
| **DET@BUF** | -1.5802 / 46.0993 | Resembles moderate-edge early-season matchups (both 1-0 entering W2 in diagnose fixture); historical mode SAMPLE_NOISE + early-season OOD — trailing window still thin. |
| **MIN@CHI** | -1.8479 / 42.703 | Resembles W1 GB@MIN / CHI@CAR family: NFC North volatility and totals blowout risk; ARCHITECTURE on totals if game goes script-off. |
| **NO@BAL** | -1.5888 / 43.5239 | Resembles W1 BAL@IND mismatch-style: if packaged book is flatter than market, INFORMATION gap vs market; watch dog/favorite disagreement slice. |

## Verdict

# `MODEL_SIGNAL_WEAK`

**Reasons:**  
- Packaged beats pick'em on spread with CI excluding 0
- Does not clearly beat market
- Exact live-SHA candidate outcome-backed n=16 (W1) MAE=12.6044; multi-season uses reconstructed season-start priors under same locked equation

**Recommended direction (research only):** Research only — do NOT CLEAR reopen. Expand chronological OOS with PIT season-start priors through more seasons if situational densifies pre-2023; investigate calibration/shrinkage vs market opens; treat totals as architecture rethink (not coefficient nudge on 96-point outlier); quantify packaged vs trailing incremental on larger trailing-available set; keep overlays OFF / Coming soon ON.

**Explicit non-actions:** no board flip; Coming soon stays ON; overlays stay OFF; no CLEAR; no coefficient/scoring change; CFB separate; no Odds burn; no prod remat.

## Supporting artifacts

- `HISTORICAL_OOS_DIAGNOSTIC.json` — machine metrics  
- `historical_oos_games.csv` / `historical_oos_by_season.csv`  
- `historical_oos_slices.json` / `historical_oos_baselines.json`  
- Folded: `PREDICTIVE_EVAL_HISTORICAL_OOS_W1.*` (PARTIAL n=16)  
