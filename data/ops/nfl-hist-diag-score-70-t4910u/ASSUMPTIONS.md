# ASSUMPTIONS — t4910u bounded diagnostic score (70)

Sealed **before** first `SCORE_RESULTS` write. Do not change formulas after that write.

OWNER t4910u ACCEPT · CoS EXEC_FREEZE · NFL NO-GO · CERT=0 · 0 Odds credits.

Eng label is diagnostic only. This file is not CERT, E1, merge, publish, or a betting claim.

## What this run is

One frozen Independent Fair consume of **exactly 70** verified 2017 REG complete games:

- W2 complete 14 from Stage-1b tip `440314e4` (Alex PASS_RECON sha8 `91e2d7db`)
- W3–W6 complete 56 from Stage-1b tip `f92aaea3` (Alex PASS_RECON sha8 `af30adba`, PR #671)

Excluded (visible, not filled, not substituted):

- W2 ineligible: `2017_02_CHI_TB`, `2017_02_MIA_LAC` (already out of W2 sealed sample)
- W6 bye partials: `2017_06_DET_NO`, `2017_06_MIA_ATL`, `2017_06_SF_WAS`, `2017_06_NYG_DEN`

Failed / ineligible stay visible. No silent fill.

## Read-only on model math

No fit, tune, weight, feature, or blend change. No sample replacement. No 2024–25 sealed access. No market / CLV claims. No publish. No betting. No merge. No E1. No CERT.

IF tip / framework tree: **`6ca03716fe52930332d5ffba302c312a651980cc`**.

Source pins (rehashed this exec):

| pin | sha8 | object |
|---|---|---|
| simulator | **52d9e909** | `nfl_simulator.py` @ 6ca03716 |
| framework | **a0051cc4** | `nfl_handicapping_framework.py` @ 6ca03716 |
| contract | **b41f4b43** | `ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md` |
| as-of | **cf514078** | pregame as-of identity |
| PBP | **84eacd96** | cited only; not re-opened for this score |
| market_blend | **0** | IF fair path; `market_spread_home=None`, `market_total=None` |

`deploy-vercel` HEAD `nfl_simulator.py` is a **different** object (not 52d9e909). This run loads simulator + framework from the 6ca03716 worktree only.

## rest_days bind — BIND_PACKET_ONLY

**CoS-ruled PASS if this bind is obeyed.**

Tip `6ca03716` predates the W8 rest_days ET fix (`155d3ca0` / `90bf65ab`). That fix changed W8 offline eval callers only, not framework/simulator.

Hist Stage-1b packets already sealed `rest_days_home` / `rest_days_away` via **ET DOW** (Thu=4, Mon=6, else=7) from target kickoff local America/New_York weekday. Same value both sides. Not team-specific days-since-last-game.

This score:

1. Reads sealed reconstructed `rest_days_*` from the hist packet `RECON_MATRIX.csv` rows.
2. Passes those values as `NflGameInputs.rest_days_home` / `rest_days_away`.
3. Does **not** call `nfl_data.rest_days_from_schedule`.
4. Does **not** call W8 `verify_rest_days` / UTC DOW heuristic at 6ca03716.
5. Does **not** silently switch the IF tip to `90bf65ab`.
6. Does **not** use `games.csv` hardcoded 7.0 rest columns.

UTC-DOW contrast may be recorded on the manifest for audit. It is **not** an IF input.

If packet rest could not be bound without a contract/code change, this run would STOP (HOLD). It could be bound: `NflGameInputs` already accepts `rest_days_*`. Consumption binding only. Hypothesis accepted: rest is already correct in packets.

## Sim freeze

```
seed_base = 201710
seed(game_id) = 201710 + (int(sha256(game_id.encode()).hexdigest()[:12], 16) % 1000003)
simulations = 4000
tie: realized or sim margin == 0 counted AWAY (same IF fair path:
     home_wins = count(margin > 0); away_prob = 1 - home_prob)
market_blend = 0
```

`seed_base=201710` is season-month `2017-10` as an integer. Documented here on first write. Do not change after first `SCORE_RESULTS` write.

IF invoke:

```
simulate_nfl_game_independent_fair(
    inputs,
    simulations=4000,
    seed=seed(game_id),
    market_spread_home=None,
    market_total=None,
)
```

Default totals linear calibration dict is not supplied → slope 1 / intercept 0 / source `defaults` (no-op). Not a tune.

## Forecast fields (ACCEPT naming)

From the labeled Independent Fair payload / markets (unblended draws):

| name | source | note |
|---|---|---|
| forecast_margin | `independent_fair.margin_mu` | home − away |
| forecast_spread | `−forecast_margin` | home spread |
| forecast_total | `independent_fair.total_mu` | |
| forecast_wp_home | `markets.home_win_prob` | IF path; sim ties → away |
| forecast_wp_away | `1 - forecast_wp_home` | |

Realized (scores only; **no 2017 odds used in metrics**):

| name | formula |
|---|---|
| realized_margin | `home_score − away_score` |
| realized_spread | `−realized_margin` |
| realized_total | `home_score + away_score` |
| realized_su | HOME if margin>0; AWAY if margin<0; TIE if margin==0 |

Score source: `historical_oos_games.csv` sha256 **1ee90fac** — 2017 REG `home_score` / `away_score` only. Market columns on that file are **not consumed**.

Team join: `(season, week, home_team, away_team)` using packet `home_team` / `away_team` (LAR, WSH, OAK, JAX). No alias invention.

## Straight-up outcome accuracy (NOT "ATS-vs-0")

There is **no historical betting line** in this metric.

- IF SU pick = HOME if `forecast_wp_home > 0.5` else AWAY (wp==0.5 → AWAY; same IF tie path).
- Ties (realized margin==0) reported **separately**. They are not IF-correct and not IF-wrong in the decided SU rate.
- Decided SU accuracy = correct decided picks / decided games (ties excluded from the denominator).
- n_ties is reported.

This is not ATS vs a market number. Do not rename it ATS.

## Calibration / Brier / log-loss (exploratory at N=70)

Outcome encoding for probabilistic scores: `y_home = 1` if realized_margin>0 else `0` (ties treated as not-home, matching IF away-tie convention). Clip `p` to `[1e-6, 1-1e-6]`.

- Brier = mean `(p − y)^2`
- Log-loss = mean `−[y log p + (1−y) log(1−p)]`
- Reliability buckets are exploratory only. N=70 is not a certification sample.

## MAE / RMSE

- Margin: `forecast_margin` vs `realized_margin`
- Total: `forecast_total` vs `realized_total`

## Compression / dispersion

Do **not** expect forecast-margin SD == realized-margin SD.

- `sd_forecast_means` = sample SD of the 70 `forecast_margin` values (variation in forecast means).
- `sd_realized_margin` = sample SD of the 70 `realized_margin` values (outcome noise + signal).
- `sd_if_sigma` = mean of per-game `independent_fair.sigma` (IF score-error prior, not a claim of equality).

Predictive-distribution coverage (supported): replay the sealed IF draw loop using the returned `diagnostics.mean_home_points`, `mean_away_points`, and `independent_fair.sigma` with the **same** `random.Random(seed)` and `max(0, gauss)` clip. That loop is the only RNG consumer inside `simulate_nfl_game` at 6ca03716. Coverage:

- margin in sim p10–p90
- total in sim p10–p90
- nominal 80% interval; N=70 exploratory

## Benchmarks (labeled baselines ≠ edge proof)

Frozen here before first score write. Pregame-only inputs. Not edge. Not CLV. Not a market beat.

### Naive W-L

Uses sealed packet `record_asof_home` / `record_asof_away` (`W-L` or `W-L-T` strings). No 2017 market. No post-kickoff record.

```
parse record → W, L, T≥0
games = W + L + T
winpct = W / games          # packet rows for the 70 always have games≥1
wp_home_naive = 0.5 + 0.5 * (winpct_home - winpct_away)   # already in [0,1]
naive_su_pick = HOME if wp_home_naive > 0.5 else AWAY     # equality → AWAY
```

Ties in a record string count in the denominator only. Packet W2–W6 as-of strings on the 70 are `W-L` (no T observed at seal time); the T clause is defined so the formula does not later change if one appears.

### Pick'em

```
wp_home_pickem = 0.5
forecast_margin_pickem = 0.0
pickem_su_pick = HOME        # classic no-information home pick
```

Pick'em is not ATS-vs-0. It is a no-information SU / margin=0 baseline.

### Constant-total prior 45.3

```
forecast_total_const = 45.3
```

Used only as a total MAE/RMSE baseline. Framework prior name `NFL_FRAMEWORK_PRIOR_TOTAL_POINTS` default 45.3. Not a tune.

## EPA / success label

Packet EPA and success fields are **RETRO_FIT / DEV_RESEARCH only (A1)**. Pass-rate, pressure, and RZ are independent of that label. This score consumes sealed reconstructed values as IF inputs and does not re-fit them.

## What is not in this packet

CLV · 2017 odds as a metric · stake tags · PLAY / LEAN · FREE_PUBLIC · E1 · CERT · 2024–25 holdout values · Railway / Odds API · W8 eval rest re-derive · tip switch to 90bf65ab.

NFL NO-GO · CERT=0
