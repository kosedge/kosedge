# OWNER ACCEPT — t4910u bounded diagnostic score 70

OWNER t4910u ACCEPT. Filing authorized. One score execution under frozen spec.

Expected Box sha8: **1102720e**. Recreated under `data/ops/` for this PR. Rehash this exec; if sha8 ≠ 1102720e the remount is documented in CALL_AUDIT (Box original was not mounted on this box).

## Accept

Bounded diagnostic scoring on 70 verified 2017 REG complete games.

NFL NO-GO · CERT=0.

Read-only on model math: no fit, tune, weight/feature/blend change, sample replacement, 2024–25 sealed access, market/CLV claims, publish, betting, merge, E1, CERT.

## Rest_days preflight

Tip 6ca03716 predates W8 rest_days ET fix (155d3ca0 / 90bf65ab). That fix only changed W8 offline eval callers, not framework/simulator. Hist Stage-1b packets already sealed rest_days via ET DOW (155d3ca0). **Bind sealed reconstructed rest_days_* from hist packets as IF inputs.** Do NOT re-derive rest via W8 eval caller at 6ca03716. Do NOT silently switch tip to 90bf65ab. If packet rest cannot be bound without a contract/code change: STOP, HOLD, propose corrected pin — do not invent.

## Pins

- IF tip / framework tree: **6ca03716** (full 6ca03716fe52930332d5ffba302c312a651980cc). market_blend=0.
- Source pins: simulator 52d9e909 · framework a0051cc4 · contract b41f4b43 · as-of cf514078 · PBP 84eacd96.
- Inputs: Stage-1b W2 tip 440314e4 (Alex PASS_RECON 91e2d7db) + W3–W6 tip f92aaea3 #671 (Alex PASS_RECON af30adba).
- EPA/success fields label RETRO_FIT / DEV_RESEARCH only (A1). Pass-rate/pressure/RZ independent.
- Sample: exactly 70 complete games (W2 14 + W3–W6 56). Exclude bye partials DET_NO MIA_ATL SF_WAS NYG_DEN.
- Failed/ineligible stay visible — no silent fill or substitute.
- Sim freeze: simulations=**4000**; seed_base + per-game seed formula frozen in PINS; tie: margin==0 counted away (same IF fair path).
- Binding seed formula: `seed = 201710 + (int(sha256(game_id.encode()).hexdigest()[:12], 16) % 1000003)`
- Benchmarks use pregame-only inputs.

## Metrics (rename + caveats)

- Forecast margin/spread/total/wp vs realized
- Straight-up outcome accuracy (NOT "ATS-vs-0") with ties reported separately — there is no historical betting line in this metric
- Calibration / Brier / log-loss: exploratory at N=70
- MAE/RMSE margin and total
- Compression/dispersion: forecast-margin SD vs realized-margin SD (do NOT expect equality); distinguish variation in forecast means from outcome noise; include predictive-distribution coverage if supported by sealed sim draws
- NO CLV / no 2017 odds
- Benchmarks: naive W-L · pick'em · constant-total prior 45.3 — labeled baselines ≠ edge proof

## Deliverables

DRAFT PR (do not merge) under `data/ops/nfl-hist-diag-score-70-t4910u/` with: SAMPLE_MANIFEST_70 · SCORE_RESULTS · METRICS_TABLE · COMPRESSION_HIST_DIAG · ASSUMPTIONS · CALL_AUDIT · PINS.json · SHA256SUMS · VERDICT_ENG.md · README.

Box-mirror friendly. Eng label CONDITIONAL_DIAG or SCORE_SEALED as honest. Rehash key pins on exec. 0 Odds credits.

## Done when

Packet sealed with tip sha; all 70 attempted; failures visible; rest_days bind documented; metrics match ACCEPT naming; no math change; PR link + tip sha8 returned to CoS.

Hypothesis you may discard: rest is already correct in packets so only consumption binding is required.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT
