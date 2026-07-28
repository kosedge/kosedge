# Preseason Projection Methodology — Walk-Forward Backtest Report

**Date:** 2026-07-18
**Scope:** Validates the two fixes made to the NFL preseason data-hydration pipeline this session:

1. `rookie_baselines.py` — real historical draft-tier baselines replacing "rookie = silently absent."
2. `preseason_hydration.py::hydrate_preseason_team_situational()` — full prior-season team average replacing "flat carry-forward of the last game of the prior season."

Both backtests are **walk-forward** (each target season's baseline is built only from data strictly before that season — no leakage) and **read-only** (throwaway scripts in `data/ops/nfl-preseason-methodology-backtest/`, no production tables/code touched). Analysis code:

- `data/ops/nfl-preseason-methodology-backtest/backtest_a_rookie_baseline.py`
- `data/ops/nfl-preseason-methodology-backtest/backtest_b_team_epa_prior.py`
- Raw per-record outputs: `backtest_a_records.json`, `backtest_b_records.json` in the same folder.

---

## TL;DR verdicts

| Backtest | Verdict |
|---|---|
| **A — Rookie usage baseline** | **Ship it.** Landslide win over the status-quo (implicit zero) baseline — MAE cut ~60-75% depending on metric/position. One real, fixable bias found: **rookie RB touches are over-projected by ~13% overall, and the over-projection is getting worse in the two most recent classes (2023: +31%, 2024: +30%)** — likely a real-world trend (committee/timeshare backfields) that an unweighted 2013–present average can't track. See recommendation below. |
| **B — Team EPA prior (stats-only half)** | **Ship it.** Full prior-season average beats last-game-of-prior-season snapshot by **47% lower MAE for offensive EPA/play and 62% lower MAE for defensive EPA/play allowed**, consistently across all 3 backtested seasons, with near-zero bias (average) vs. a real +0.077 systematic bias (last-week snapshot makes defenses look worse than they are — teams resting starters/tanking late). Market-futures blend not backtested (see scope note). |

---

## Backtest A: Rookie usage draft-tier baseline

### Methodology

For each target season **Y ∈ {2019, 2020, 2021, 2022, 2023, 2024}**:

1. **Build the baseline with no leakage.** Recomputed `compute_rookie_usage_baselines()`'s exact bucketing/averaging logic (same SQL, same `DRAFT_TIERS`, same `min_sample_players = 3` cutoff, same cross-position-same-tier fallback from `get_rookie_baseline()`), but scoped to `rookie_year <= Y-1` — i.e. for the 2022 target season, the baseline only ever sees real rookie seasons 2013–2021. In every one of the 6 backtested seasons, every (position, tier) combination actually needed by that season's real rookies had a baseline available (0 fell through to the "no baseline / all-zero" path).
2. **Evaluation set.** Every real player in `nfl_dp_rosters` with `rookie_year = season = Y`, `position IN (QB, RB, WR, TE, FB, HB)` (FB/HB had zero qualifying rookies in 2019–2024 and don't appear below), and a **known `draft_number`** (per task spec — undrafted/UDFA rookies excluded from the primary eval set; see supplementary note), who recorded real usage (`nfl_dp_player_usage_weekly`, `source = 'pbp_aggregation'`, `games_played > 0` weeks) that season. n = 383 rookie-seasons pooled across the 6 years.
3. **Prediction vs. actual.** Baseline's per-game prediction for that player's `(position, draft_tier)` vs. the player's real season average per game (sum of real weekly stats over `games_played > 0` weeks, divided by games played).
4. **Metrics.** MAE and bias (mean signed error = mean(predicted − actual)) for:
   - `involvement_plays` (the table's broadest usage counter — for skill-position players this is essentially targets + rush attempts + (for QBs) dropbacks)
   - `touches` = `targets + rush_attempts` (task-specified combined metric; **note:** for QBs this materially undercounts real workload since it excludes dropbacks/pass attempts — `involvement_plays` is the more meaningful QB metric and is reported alongside it)
5. **Counterfactual.** The real status quo before this fix: rookies had **no row at all**, which is equivalent to every downstream consumer implicitly projecting **0** usage. Scored the same evaluation set against a flat 0 prediction.

### Results — pooled across 2019–2024, n=383 rookie-seasons

**Overall:**

| Metric | New baseline MAE | New baseline bias | Zero-baseline (status quo) MAE | Zero-baseline bias | MAE improvement |
|---|---|---|---|---|---|
| `involvement_plays` | 3.11 | +0.29 | 7.91 | −7.91 | **60.7%** |
| `touches` (targets+rush) | 1.99 | +0.21 | 4.77 | −4.77 | **58.4%** |

The zero-baseline bias is trivially −(actual average) by construction — it's the "how big is the blind spot" number. New-baseline bias near 0 means no gross over/under-shoot at the pooled level, but see the breakdown below for real structure hiding inside that average.

**By position:**

| Position | n | Baseline MAE (touches) | Baseline bias (touches) | Zero MAE (touches) | Mean actual touches/gm | Mean predicted touches/gm | Relative bias |
|---|---|---|---|---|---|---|---|
| QB | 48 | 1.40 | −0.30 | 2.93 | 2.93 | 2.63 | **−10.2%** |
| RB | 105 | 3.72 | +1.04 | 8.07 | 8.07 | 9.11 | **+12.9%** |
| TE | 69 | 1.15 | −0.21 | 2.80 | 2.80 | 2.59 | **−7.6%** |
| WR | 161 | 1.39 | +0.01 | 4.01 | 4.01 | 4.01 | +0.2% |

(QB `touches` under-represents real QB workload since it excludes dropbacks; QB `involvement_plays` MAE is 9.73 with a small −0.44 bias against a much larger real mean of ~28/game — proportionally the QB baseline is actually well-centered, it's just a noisier absolute number because starting-QB rookies range from "immediate starter" to "clipboard holder.")

**By draft tier (touches):**

| Tier | n | Baseline MAE | Baseline bias | Zero MAE |
|---|---|---|---|---|
| R1_top10 | 25 | 1.63 | −0.70 | 5.87 |
| R1_11_32 | 34 | 1.71 | −0.71 | 7.31 |
| R2_R3 | 110 | 2.37 | +0.64 | 5.64 |
| R4_R5 | 120 | 2.03 | +0.37 | 4.23 |
| R6_R7 | 94 | 1.68 | +0.09 | 3.22 |

**By season (touches):**

| Season | n | Baseline MAE | Baseline bias | Zero MAE |
|---|---|---|---|---|
| 2019 | 54 | 2.05 | +0.14 | 5.06 |
| 2020 | 63 | 1.87 | +0.30 | 5.12 |
| 2021 | 63 | 2.12 | −0.14 | 4.77 |
| 2022 | 70 | 2.21 | +0.19 | 4.76 |
| 2023 | 67 | 1.57 | +0.34 | 4.49 |
| 2024 | 66 | 2.09 | +0.42 | 4.48 |

Every single one of the 6 backtested seasons individually beats the zero-baseline by roughly 2-3x on MAE — this is not an artifact of one lucky year.

### The one real, fixable finding: rookie RB over-projection, worsening over time

Pooled, rookie RB touches are over-projected by **+12.9%** on average (predicted 9.11/gm vs. actual 8.07/gm) — the largest positional bias of the four skill positions (WR is essentially unbiased at +0.2%; QB and TE are modestly *under*-projected). Breaking that down by season shows it isn't stable — it's trending worse:

| Season | n (RB) | Actual touches/gm | Predicted touches/gm | Relative bias |
|---|---|---|---|---|
| 2019 | 17 | 8.49 | 9.35 | +10.1% |
| 2020 | 16 | 9.39 | 11.14 | +18.7% |
| 2021 | 17 | 8.70 | 7.62 | **−12.4%** |
| 2022 | 22 | 7.82 | 8.46 | +8.1% |
| 2023 | 15 | 7.85 | 10.29 | **+31.0%** |
| 2024 | 18 | 6.38 | 8.31 | **+30.2%** |

The two most recent classes (2023, 2024) show a much larger over-projection (+31%, +30%) than the four seasons before them (average ~+6%, and even briefly *negative* in 2021). This pattern is consistent with a real, well-documented league trend: rookie/early-career RB workload has been shrinking industry-wide as more teams adopt committee/timeshare backfields, and this baseline is an **unweighted average of every rookie class back to 2013** — it can't track that drift, so as real recent-year usage keeps falling, the historical mean increasingly overshoots it.

This is a real bias worth fixing, but it is *not* a reason to hold the ship — it is a second-order refinement on top of a first-order fix that is unambiguously a massive improvement over the zero-baseline status quo (MAE 3.72 vs 8.07, i.e. still ~54% better than zero even with the over-projection included).

### Supplementary check (not part of primary spec): including UDFA rookies

The task scoped the primary eval to rookies with a known `draft_number` (drafted only). For completeness, re-running with all 540 skill-position rookie-seasons (383 drafted + 157 UDFA) gives touches MAE 1.98 (baseline) vs. 4.36 (zero) — a consistent ~55% improvement, and the 157 UDFA-only rookies individually show baseline MAE 1.96 vs. zero MAE 3.36. The zero-baseline counterfactual claim holds just as strongly for UDFA as for drafted rookies.

---

## Backtest B: Preseason team EPA prior (stats-only half)

### Methodology

For each target season **Y ∈ {2023, 2024, 2025}** (chosen because `nfl_dp_team_situational_weekly` has complete real (`source = 'nflverse'`) weekly data, including playoff weeks, for 2018–2025):

1. **New methodology ("prior-season average"):** replicate the exact core query in `hydrate_preseason_team_situational()` — `AVG(epa_per_play_offense)` / `AVG(epa_per_play_defense_allowed)` per team, grouped over every weekly row in season `Y-1` (this naturally includes playoff weeks for teams that made the playoffs, exactly as production does — each week is one row, un-weighted by whether it was a real game).
2. **Naive alternative it replaced ("last-week snapshot"):** for each team, the single row for their **last played week of season `Y-1`** (`MAX(week)` where `games_played > 0` — for playoff teams this is their final playoff game, e.g. the Super Bowl for that season's two finalists; for non-playoff teams it's typically week 18).
3. **Truth:** the actual full target-season (`Y`) average of the same two columns, same aggregation.
4. **Metric:** MAE and bias of each method's `Y-1`-derived prediction vs. truth, across all 32 teams × 3 seasons (n=96 team-seasons).

**Explicit scope limitation (per task):** this backtest validates only the stats-only half of the fix. The market-futures blend (`market_signals.py`, 50/50 blend with Super Bowl-odds percentile) is **not** backtested here — historical Super Bowl futures odds for 2022/2023/2024 (the seasons whose *following* season we're predicting) aren't readily available in this DB/session, and the task explicitly scoped this out. The numbers below are for the underlying stats-only average, which is the core of the fix and the part directly comparable to the noisy single-snapshot it replaced.

### Results — pooled across 2023, 2024, 2025 (n=96 team-seasons)

| Metric | Full prior-season avg MAE | Full prior-season avg bias | Last-week-snapshot MAE | Last-week-snapshot bias | MAE improvement |
|---|---|---|---|---|---|
| `epa_per_play_offense` | 0.0843 | −0.0024 | 0.1588 | −0.0335 | **46.9%** |
| `epa_per_play_defense_allowed` | 0.0725 | −0.0029 | 0.1896 | +0.0770 | **61.8%** |

The prior-season average is essentially unbiased (bias ≈ 0 for both columns — it neither systematically over- nor under-shoots league-wide). The last-week snapshot carries a real, consistent **+0.077 bias on defense allowed** — i.e., it systematically makes defenses look *worse* than their true full-season quality — plausibly because "last week of the season" disproportionately includes garbage-time/backups-playing/tanking scenarios for eliminated teams, and small-sample randomness for playoff teams' single elimination games.

### Per-season breakdown

| Season | Offense avg MAE | Offense last-week MAE | Defense avg MAE | Defense last-week MAE |
|---|---|---|---|---|
| 2023 | 0.0853 | 0.1498 | 0.0635 | 0.1876 |
| 2024 | 0.0853 | 0.1717 | 0.0866 | 0.2076 |
| 2025 | 0.0823 | 0.1548 | 0.0674 | 0.1735 |

The improvement is consistent — not a one-season fluke. Every one of the 3 seasons independently shows the full-season average beating the single-game snapshot by roughly 2x on MAE for both offense and defense.

### Verdict

**Ship it.** The core "average beats a single-game snapshot" claim is unambiguous, large (47-62% MAE reduction), and stable across all 3 backtested seasons. This is the expected statistical result (averaging ~17-22 noisy weekly samples reduces variance relative to any one of them) and the backtest confirms it holds in practice on real EPA data, not just in theory. No fixable bias was found in the stats-only half — bias is already ≈0.

---

## Recommended follow-up (not implemented — validation only, per task scope)

1. **Fix the RB over-projection drift (Backtest A).** Consider either (a) a recency-weighted average (e.g. exponential decay or a rolling N-season window, say last 6-8 rookie classes) instead of the unweighted 2013–present average for the RB bucket specifically, or (b) at minimum, monitor this every offseason when `compute_rookie_usage_baselines()` is re-run — if the 2025 rookie RB class also comes in ~25-30% below the current baseline's prediction, that's strong confirmation this is a real trend, not two-season noise, and justifies prioritizing the fix. Given only 2 of 6 backtested seasons show the larger gap, I'd treat this as "watch and confirm with one more season" rather than "fix immediately," but it's worth flagging now since it's cheap to check.
2. **No action needed for Backtest B** — the stats-only average is unbiased and clearly superior; nothing to fix. (The market-futures blend is a separate, already-designed enhancement layered on top and wasn't in scope for this backtest.)
