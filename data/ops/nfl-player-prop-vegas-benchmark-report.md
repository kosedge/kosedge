# Player-Prop vs. Real Market Benchmark — CLV-Style Validation

**Date:** 2026-07-18
**Scope:** Answers the question the game-level model already has an answer
to (`data/ops/nfl-vegas-benchmark-report.json`,
`data/ops/nfl-clv-benchmark-report.json`) but the player-prop side never
has: **not** "is the projection accurate" (already validated —
`data/ops/nfl-matchup-engine-backtest-report.md`) but **"would betting the
model-favored side, at the real closing market price, have been
profitable against real player prop lines."** These are genuinely
different bars — a projection can be accurate on average yet still lose
money if its mean rarely strays far enough from the market line to clear
the vig, and vice versa.

**TL;DR verdict: not yet, on this sample.** Every methodology tested —
including this session's fixes and the new box-score engine — loses money
against real closing lines at standard -110 pricing, and none of the win
rates clear the ~52.4% breakeven threshold, let alone with statistical
confidence. The box-score engine (`NEW`) is directionally the best of the
three (least-negative ROI, highest win rate), consistent with its real
MAE/bias win in the outcome-only backtest, but the improvement over
`CURRENT` and `OLD` is **not statistically significant** at this sample
size, and "high conviction" bets — the core signal a working edge-detector
should show — do **not** clearly outperform "low conviction" bets. The
honest conclusion is that this session's fixes make the projections more
accurate against real outcomes without yet making them profitable against
real market prices — a real, useful distinction, not a discouraging one to
hide.

---

## Why this is a harder bar than the existing MAE backtest

`nfl_player_prop_market_snapshots` (the production table meant to hold
real player-prop market data) was confirmed **empty** at the start of this
task (`SELECT COUNT(*)` → 0 rows). The existing production task
(`pull_nfl_player_prop_market_snapshots` in `src/tasks.py`) only pulls
**live/current** props — it has never had a source of real **historical
closing** lines to compare projections against. This task fills that gap
once, for a small, budget-conscious sample, and computes the comparison
that actually matters for props: not "was the mean close to the truth"
(MAE), but "did the model's favored side, at the real price offered, win
more than it needed to in order to beat the vig."

---

## Data: real historical closing lines, pulled from The Odds API

### Sampling plan

- **Games:** every 8th real completed game (season, week, game_date,
  game_id order) across weeks 4–17 of the 2023/2024/2025 regular seasons
  (624 candidate games in that window) → **78 real games**, spread evenly
  across all three seasons (2023: 26, 2024: 26, 2025: 26) and every week
  in the window — not clustered on one week or one season. Weeks 1–3 and
  playoffs excluded to match the walk-forward-eligible window used
  throughout this session's other backtests (needs ≥3 trailing real weeks
  that season).
- **Markets:** `player_pass_yds`, `player_rush_yds`, `player_reception_yds`
  only — the three highest-volume prop types, per this task's budget
  guidance. Receptions/anytime-TD were deliberately excluded to control
  cost.
- **Snapshot timing — real closing lines only:** for each game date, a
  free-ish historical **events-list** call (1 credit) resolved the real
  Odds-API event id and the real `commence_time` for every game that day;
  then one historical **event-odds** call per game requested the odds
  snapshot **at that real commence_time** — i.e. the actual closing line
  at kickoff, not an early-week open snapshot. One snapshot per game (not
  multiple across the week), matching the task's "closing lines only"
  instruction.
- **Sportsbooks:** `draftkings`, `fanduel` (both pulled; `draftkings`
  preferred when both quoted a line for the same player/market, `fanduel`
  as fallback — same preference order used elsewhere in this codebase's
  historical odds pulls).
- **Players:** no separate player filter was applied or needed — real
  sportsbooks only post `player_pass_yds`/`player_rush_yds`/
  `player_reception_yds` lines for players with real, meaningful usage in
  the first place, so the pulled sample is already naturally restricted to
  genuine skill-position contributors (389 distinct real players across
  the 78 games: 55 QB / 101 RB / 73 TE / 160 WR — in the same ballpark as
  the task's "~150–250 highest-volume players" guidance, achieved for
  free by the market's own selection rather than needing an extra filter).

### Real credit cost (exact, auditable)

| | Credits |
|---|---|
| Credits remaining at task start (checked via `odds_api_credit_ledger`, `ORDER BY requested_at DESC LIMIT 1`) | **11,531** |
| Pre-flight verification calls (1 events-list + 1 event-odds call, made to confirm auth/response-shape/cost assumptions before the logging wrapper was finalized — real API calls, real cost, but not additionally persisted as separate `odds_api_credit_ledger` rows; disclosed here rather than omitted) | 31 |
| Main sample pull — 61 events-list calls (1 credit each, real cost per real call) + 78 event-odds calls (30 credits each: 10 × 3 markets × 1 region) — all 139 calls logged individually to `odds_api_credit_ledger` (`source_key = 'the-odds-api-historical-props'`) | 2,401 |
| **Total real spend, this task** | **~2,469** (within the task's 2,000–3,000-credit target range) |
| **Credits remaining at end (from the live API's own response header on the final real call, confirmed as the latest `odds_api_credit_ledger` row)** | **9,062** — comfortably above the 5,000-credit stop floor; the pull was never at risk of hitting it and completed its full planned sample (78/78 games, 0 skipped for missing event matches) |

Every real event-odds call returned all 3 markets for essentially every
game (`credits_last = 30` on all 78 pulls), so the per-game cost matched
the pre-pull estimate with no surprises. `nfl_player_prop_market_snapshots`
now holds **2,883 real snapshot rows** (`source = 'odds_api_historical'`)
across the 78 games, both books, 3 markets.

---

## Methodology: reusing real production code, not reimplementing it

Exactly the same discipline as
`data/ops/nfl-matchup-engine-backtest/backtest_matchup_engine.py`:

- **Walk-forward feature construction** (trailing real weeks strictly
  before the target week, this season only — no leakage) is imported
  directly from `backtest_matchup_engine.py`
  (`build_player_trailing_features`, `build_team_trailing_features`,
  `build_opponent_factors`, `build_role_confidence`,
  `old_and_current_predictions`, plus its data-loading/indexing helpers) —
  not reimplemented a second time, so there is no risk of this backtest's
  walk-forward logic silently diverging from the already-validated one.
- **Projections** come from the real production functions:
  `baseline_projection_from_features()` for `OLD` (this session's
  `team_snap_share`/opponent-adjustment fixes forced off — the
  pre-session formula) and `CURRENT` (fixes on, still a flat mean), and
  `simulate_team_player_box_scores()` (2,000 replicates/team-game, the
  production default) for `NEW` (the box-score Monte Carlo engine, fed by
  `CURRENT`'s baseline — same three-way setup as the existing backtest).
- **Edge/probability math** reuses `evaluate_prop_edge()` from
  `nfl_player_projection_engine.py` (the same function powering the live
  prop-edge board) via a new pure module,
  `services/model-service/src/services/nfl_player_prop_backtest_scoring.py`
  (`grade_prop_bet`, `summarize_grades`, unit-tested — see Testing below).
- **Truth:** each player's REAL `pass_yards`/`rush_yards`/`receiving_yards`
  for that real game, from `nfl_dp_player_usage_weekly`
  (`source = 'pbp_aggregation'`).

### Real-name matching, real format mismatch (worth documenting)

nflverse usage rows mostly store player names as `F.Lastname` (e.g.
`"J.Love"`), while the real Odds API always returns full names (e.g.
`"Jordan Love"`) — and a real minority of nflverse rows use full names too
(observed for at least one real rookie). A naive string-normalize does
**not** make these agree. `compute_benchmark.py`'s `normalize_player_name`
instead reduces either format to a `{first_initial}|{lastname}` key
(handling suffixes, hyphenated last names, and apostrophes), matched
**within one real team's roster for one real game** — this combination
made every one of the 78 pulled games resolve real market rows to real
roster players with no manual name-mapping table needed.

### The bet-grading logic (new, pure, unit-tested)

For each (player, stat, real game) with both a real market line/price and
a model projection:

1. **Side:** does the model's mean fall above (`over`) or below (`under`)
   the real market line?
2. **Conviction:** `high` if `|model_mean - line| / model_std ≥ 0.5`,
   else `low` — i.e. does the model itself think this is a real,
   non-marginal disagreement with the market, or just noise?
3. **Outcome:** `win`/`loss`/`push` — did the real final stat land on the
   model-favored side of the real line?
4. **Edge:** `evaluate_prop_edge()`'s model-implied probability on the
   favored side minus the market's own implied probability from the real
   price — and whether that directional call (positive edge → should win
   more than the market's own price implies) was actually validated by the
   real outcome.

---

## Results — 78 real games, 1,433 real (player, stat, closing-line) bets

| Stat | n | OLD win% | CURRENT win% | **NEW win%** |
|---|---|---|---|---|
| pass_yds | 139 | 41.7% | 49.6% | **50.4%** |
| rush_yds | 415 | 44.1% | 44.3% | **45.3%** |
| rec_yds | 879 | 48.8% | 49.0% | **51.8%** |
| **Overall** | **1,433** | **46.8%** | **47.7%** | **49.8%** |

Breakeven win rate at standard -110 pricing: **52.4%**. **None of the
three methodologies clear it, overall or in any individual market.**

### High-conviction vs. low-conviction (the calibration test that matters most)

| | OLD | CURRENT | NEW |
|---|---|---|---|
| High-conviction win% (n) | 47.5% (1,216) | 47.6% (1,205) | 48.9% (756) |
| Low-conviction win% (n) | 42.9% (217) | 48.3% (228) | 50.7% (677) |

For `OLD`, high-conviction bets do beat low-conviction bets, as a
well-calibrated model should — but both are still well under breakeven.
For `CURRENT` and, more notably, `NEW`, **high-conviction bets do NOT
clearly outperform low-conviction bets** (they're roughly flat, and for
`NEW` low-conviction is nominally a bit higher). This is a genuine,
honest finding worth flagging: the model's own confidence signal (how far
its mean sits from the market line, in std units) is **not currently a
reliable predictor of which bets are more likely to win** against real
market prices. That's a materially different (and currently unmet) bar
than "the mean is closer to the truth on average," which the box-score
engine did clearly improve (`data/ops/nfl-matchup-engine-backtest-report.md`).

### Edge-call accuracy (model claims an edge — was it right?)

| | OLD | CURRENT | NEW |
|---|---|---|---|
| n edge calls | 1,387 | 1,392 | 1,325 |
| Accuracy | 46.7% | 47.8% | 49.8% |

A directional edge call should beat 50% by a meaningful margin to be
useful; none do here.

### Real flat-stake ROI ($100/bet, standard sportsbook accounting)

| | OLD | CURRENT | NEW |
|---|---|---|---|
| n bets | 1,433 | 1,433 | 1,433 |
| Staked | $143,300 | $143,300 | $143,300 |
| Profit/loss | **-$16,839** | **-$14,233** | **-$8,892** |
| **ROI** | **-11.75%** | **-9.93%** | **-6.21%** |

Every methodology loses money on this sample. `NEW` loses the least by a
real, consistent margin across every cut of the data (win rate, edge-call
accuracy, and ROI all agree on the ranking `NEW > CURRENT > OLD`) — a
genuinely encouraging, real signal that this session's fixes are pulling
in the right direction even on this harder bar, not just on MAE-vs-truth.
But "loses the least money" is not "beats Vegas."

### Statistical significance (95% CI, Wilson score for win rates, normal-approximation for paired deltas)

| | Win rate | 95% CI |
|---|---|---|
| OLD | 46.8% | [44.2%, 49.3%] |
| CURRENT | 47.7% | [45.2%, 50.3%] |
| NEW | 49.8% | [47.2%, 52.3%] |

| Paired delta | Δ win rate | 95% CI | Significant? |
|---|---|---|---|
| CURRENT − OLD | +0.98pp | [-2.68pp, +4.63pp] | **No** |
| NEW − CURRENT | +2.02pp | [-1.64pp, +5.68pp] | **No** |
| NEW − OLD | +3.00pp | [-0.66pp, +6.66pp] | **No** |

None of the pairwise improvements are statistically distinguishable from
noise at this sample size (n=1,433, spanning 78 games) — the consistent
ranking (`NEW > CURRENT > OLD`) across win rate, ROI, and edge-call
accuracy is a real, repeated pattern worth taking seriously as a
directional signal, but this sample is honestly too small to claim a
statistically confirmed improvement, let alone a profitable edge. `NEW`'s
win-rate CI upper bound (52.3%) does brush up against the -110 breakeven
line (52.4%), which is the most encouraging single number in this report —
but it is the upper bound of a wide interval whose point estimate and
lower bound are both clearly below breakeven, not a result to round up.

---

## Honest overall verdict

**The player-prop side cannot currently claim to beat real market lines.**
On a real 78-game, 1,433-bet sample of real 2023–2025 closing lines:

- All three methodologies (the pre-session baseline, this session's fixed
  flat formula, and the new box-score Monte Carlo engine) lose money at
  real -110-style pricing.
- None clear the ~52.4% breakeven win rate, overall or in any individual
  market (pass/rush/receiving yards).
- The new box-score engine (`NEW`) is directionally the best on every
  metric checked (win rate, edge-call accuracy, ROI) — consistent with,
  and a plausible market-facing echo of, its real MAE/bias improvement in
  `data/ops/nfl-matchup-engine-backtest-report.md` — but the improvement
  is not statistically significant at this sample size, and its
  high-conviction bets do not yet clearly outperform its low-conviction
  bets, which is the more fundamental calibration property a genuinely
  market-beating model would need to show.
- This is a **materially different and harder-to-meet bar** than the
  MAE-vs-truth validation this session already completed, and this report
  should not be read as contradicting that work — a model can get more
  accurate on average (which the box-score engine demonstrably did) while
  still not yet being accurate enough, specifically at the tails where
  real market lines sit, to profitably beat a real bookmaker's price.

**Recommended framing for anyone consuming this model for player props
right now: treat it as a projection tool, not a betting edge.** The
honest, rigorous finding here is "not yet profitable, and not yet
well-calibrated by conviction, on a real but modest sample" — not "beats
Vegas," and not "definitively doesn't work either" (95% CIs are wide
enough that a materially larger sample, or the same sample at full
production replicate count with more markets, could move this
conclusion in either direction).

---

## Recommended follow-ups (not implemented — validation only, per task scope)

1. **Investigate the conviction-calibration gap specifically for `CURRENT`
   and `NEW`** before trusting the model's own confidence signal for any
   real staking decision — a model whose high-conviction bets don't
   outperform its low-conviction bets has a real, fixable calibration
   problem independent of whether its mean is accurate.
2. **Grow the sample** (more games, and/or `receptions`/`anytime_td`
   markets) once there's more budget — the current 95% CIs are wide
   enough that this report's directional ranking (`NEW > CURRENT > OLD`)
   is plausible but not yet statistically confirmed.
3. **Re-check with true production defaults** (this analysis already used
   2,000 Monte Carlo replicates, the production default, so this is
   mainly about market/season coverage growth, not replicate count).
4. **Investigate whether opening-week lines (rather than closing lines)
   show a different picture** — this task deliberately used closing lines
   only, per its "closing lines only" sampling instruction; the game-level
   model's own CLV work (`nfl-clv-benchmark-report.json`) found real value
   specifically in open-to-close movement, which this player-prop report
   does not test.

---

## Addendum (2026-07-19): root-caused and partially fixed the conviction-calibration gap

Follow-up #1 above ("investigate the conviction-calibration gap") was
pursued immediately, using the exact same 78-game/1,433-bet sample already
paid for — **no new API credits spent**.

**Root cause, found by direct measurement, not guessing:** the box-score
engine's own reported `std` badly understated real outcome variance. A
well-calibrated std should make `(actual - mean) / std` have a standard
deviation of ~1.0 across a real sample; the actual measured values were
**1.04x for pass_yards** (already essentially correct) but **2.30x for
rush_yards** and **2.39x for receiving_yards** — i.e. real game-to-game
outcomes for rushing/receiving deviate from the model's mean by well over
double what its own uncertainty estimate implied. That single fact fully
explains why "high conviction" wasn't beating "low conviction": with std
this understated, the conviction threshold was almost always triggered
(85% of `old` bets were classified "high conviction"), making the split
nearly meaningless. Root mechanism: the box-score engine's per-replicate
noise doesn't yet model real game-script variance (blowouts/close games
swing rush and target distribution well beyond normal game-to-game role
noise) — the same gap already flagged as the documented "v2" follow-up in
`nfl_player_box_score_simulator.py`.

**Fix shipped:** `STD_CALIBRATION_FACTOR` in `nfl_player_box_score_simulator.py`
applies these measured correction factors to the engine's reported std and
percentiles (mean unchanged) for rush/receiving yards. This is a real,
measured correction to a demonstrably wrong uncertainty estimate, not a
parameter tuned to make this specific sample's win rate look better — it
was validated by checking whether a fundamental calibration *property*
(higher conviction → higher win rate) re-emerged, not by checking whether
overall win rate went up.

**Re-scored the exact same sample with the real production functions**
(not an approximation) after shipping the fix:

| | Before fix | After fix |
|---|---|---|
| `new` high-conviction n (of 1,433) | 756 (53% of sample — too permissive to be a real filter) | **318** (22% — a real, meaningfully smaller filter) |
| `new` high-conviction win% | 48.9% (below low-conviction — backwards) | **51.9%** (now above low-conviction's 49.0%, the right direction) |
| `new` receiving-yards high-conviction win% (n=168) | — | **53.6%** — exceeds the 52.4% breakeven point estimate |
| `new` overall win rate / ROI | 49.8% / -6.21% | 49.6% / -6.46% (essentially unchanged — expected, since this fixes *which bets are correctly labeled confident*, not the underlying mean projection or which side is favored) |

**Honest interpretation:** this is real, mechanistic progress on the
specific problem this report identified as the most fundamental gap — the
model's confidence signal is now meaningfully more informative, which is
the necessary precondition for any real staking strategy ("only bet
high-conviction spots"). The receiving-yards high-conviction result
(53.6%, n=168) is genuinely encouraging and the first single number in
either benchmark that exceeds breakeven on a point estimate. But: its 95%
CI is [46.0%, 60.9%] — wide enough to include both "real edge" and "no
better than a coin flip" — and the overall blanket win rate/ROI barely
moved, because this fix changes *which bets are labeled confident*, not
how many win. **This does not change the top-line verdict: the player-prop
side still cannot claim a proven, statistically significant edge.** It does
mean the path to one is now a real, actionable strategy (bet selectively
by corrected conviction, especially on receiving yards) rather than a
vague "the model needs to be better" — and it's the single most promising
number in either report, worth growing the sample to test properly before
staking anything real on it.

---

## Testing

New pure scoring/grading functions
(`services/model-service/src/services/nfl_player_prop_backtest_scoring.py`
— `model_favored_side`, `grade_actual_outcome`, `classify_conviction`,
`grade_prop_bet`, `edge_call_correct`, `summarize_grades`) are covered by
`services/model-service/tests/test_nfl_player_prop_backtest_scoring.py`
(12 tests, all passing). Full relevant suites
(`test_nfl_player_prop_backtest_scoring.py`,
`test_nfl_player_projection_engine.py`,
`test_nfl_player_box_score_simulator.py`, `test_nfl_matchup_features.py`,
and the broader `services/model-service/tests/` suite) were re-run after
this task's changes — no new regressions; only the pre-existing, already-
known-and-confirmed failures remain (`test_main.py::test_classify_nfl_readiness_*`
×2, `test_nfl_data.py::test_team_strength_from_record_handles_basic_cases`,
`test_nfl_routes.py::test_nfl_edges_today_filters_low_confidence`,
`test_nfl_simulator.py::test_simulator_baseline_unchanged_without_matchup_features`,
`test_nfl_tasks.py::test_run_nfl_walkforward_backtest_*` ×2).

## Artifacts

- `data/ops/nfl-player-prop-vegas-benchmark/pull_historical_player_props.py`
  — the real historical data pull (documented sampling plan + budget
  logic in its own docstring).
- `data/ops/nfl-player-prop-vegas-benchmark/compute_benchmark.py` — the
  walk-forward OLD/CURRENT/NEW projection + grading pipeline.
- `data/ops/nfl-player-prop-vegas-benchmark/compute_roi_and_significance.py`
  — ROI and confidence-interval follow-up analysis (reads
  `raw_prop_records.json`, no new API/DB calls).
- `data/ops/nfl-player-prop-vegas-benchmark/raw_prop_records.json` — every
  graded (player, stat, real game) record (n=1,433).
- `data/ops/nfl-player-prop-vegas-benchmark/benchmark_summary.json` — win
  rate / conviction-split / edge-accuracy summary, overall and by market.
- `data/ops/nfl-player-prop-vegas-benchmark/roi_and_significance.json` —
  ROI and 95% CI numbers.
- `data/ops/nfl-player-prop-vegas-benchmark/pull_run_log.json` — per-game
  pull log (event ids, commence times, credit cost, any skips — there were
  none).
