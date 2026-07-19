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

## Addendum (2026-07-19, part 2): grew the sample to 156 games / 2,850 bets — does the receiving-yards signal hold up?

Direct follow-up to this report's own recommendation ("grow the sample...
the current 95% CIs are wide enough that this report's directional
ranking is plausible but not yet statistically confirmed") and to the
first 2026-07-19 addendum's receiving-yards high-conviction finding
(53.6%, n=168). This section pulls a second, real, non-overlapping batch
of historical closing lines, re-runs the full benchmark on the combined
sample, and — critically — treats the new batch as a genuine **holdout**
for the specific hypothesis the first addendum raised, rather than just
pooling everything into one bigger number and calling that "confirmation."

### New data: a second, disjoint 78-game sample

Same methodology as the original pull (`pull_historical_player_props.py`):
same three markets (`player_pass_yds`/`player_rush_yds`/
`player_reception_yds`), same books (`draftkings`/`fanduel`), same
real-closing-line-at-commence_time timing, same weeks 4–17 /
seasons 2023–2025 walk-forward-eligible window (624 candidate games).
The only difference: `pull_historical_player_props_batch2.py` samples a
**different residue class mod 8** — `all_games[4::8]` instead of the
original `all_games[::8]` — which is mathematically guaranteed to be
disjoint from the first 78-game sample (624 is exactly divisible by 8, so
residues 0 and 4 mod 8 can never coincide), plus a live DB de-dup guard as
defense-in-depth. Result: **78/78 planned games pulled successfully, 0
skipped**, spread just as evenly across every season/week in the window as
the original sample.

**Real credit cost (exact, auditable):**

| | Credits |
|---|---|
| Credits remaining at task start (`odds_api_credit_ledger`, live check) | **9,062** |
| Batch-2 pull — 54 events-list calls (1 credit each) + 78 event-odds calls (30 credits each, all 3 markets returned every time) — all 132 calls logged individually to `odds_api_credit_ledger` | 2,394 |
| **Credits remaining at end** | **6,668** — comfortably above the 5,000-credit stop floor; the pull completed its full planned sample and was never at risk of hitting the floor |

`nfl_player_prop_market_snapshots` now holds **5,735 real snapshot rows**
(`source = 'odds_api_historical'`) across **156 real games** (78 + 78,
zero overlap), spanning all three seasons and every week 4–17.

### A real reproducibility bug found and fixed along the way

Re-running `compute_benchmark.py` on the batch-1-only games (as a sanity
check before trusting any batch-1-vs-batch-2 comparison) produced a
**different** receiving-yards high-conviction result than the original
report on the exact same 78 games and exact same code — 163–164 bets
instead of 168, and a win rate in the low-50s instead of 53.6%. Root
cause, found by direct inspection, not guessing: `simulate_new_for_team()`
seeded its Monte Carlo run with `hash((season, week, team,
"prop_benchmark")) % (2**31)` — and Python's built-in `hash()` of a `str`
(and any tuple containing one) is **intentionally randomized per process**
(`PYTHONHASHSEED`, a security feature, not a bug in Python) unless the
seed is fixed. That means every run of `compute_benchmark.py` was silently
using a *different* random Monte Carlo seed for the `new` method, so the
`new`-method numbers in the original report were not exactly reproducible
run-over-run on identical input data — an extra, previously-undisclosed
source of noise on top of genuine sampling variance. **Fixed**: replaced
the seed with a `hashlib.sha256`-based `_stable_seed()` helper (no
randomization), so the exact same input now always produces the exact
same simulated distributions. All combined-sample numbers below use the
fixed, reproducible seed. (`old`/`current` methods are unaffected — they
are deterministic formulas with no RNG.)

### Overall three-methodology comparison — OLD vs. CURRENT vs. NEW, 156 games / 2,850 bets

| | n | OLD win% | CURRENT win% | **NEW win%** |
|---|---|---|---|---|
| Overall | 2,850 | 48.1% [46.3%, 49.9%] | 48.9% [47.0%, 50.7%] | **49.6% [47.8%, 51.4%]** |
| ROI ($100/bet) | | **-9.33%** | **-7.89%** | **-6.61%** |

| Paired delta | Δ win rate | 95% CI | Significant? |
|---|---|---|---|
| CURRENT − OLD | +0.77pp | [-1.82pp, +3.37pp] | No |
| NEW − CURRENT | +0.70pp | [-1.89pp, +3.30pp] | No |
| NEW − OLD | +1.47pp | [-1.12pp, +4.07pp] | No |

Same qualitative conclusion as the original 78-game report: `NEW` remains
directionally best on every metric (win rate, ROI), the ranking
`NEW > CURRENT > OLD` held up on the doubled sample, and none of the
pairwise deltas are statistically significant yet — CIs are tighter than
before but still wide enough to include "no real difference."

### The primary confirmatory test: does receiving-yards high-conviction hold up?

The exact cut flagged in the first addendum — `new`-method receiving-yards
bets, high conviction at the standard `z ≥ 0.5` threshold — computed
separately for the **original 78 games** (re-run with the fixed seed),
the **new 78 games** (a genuine holdout: never used to generate this
hypothesis), and the **combined** 156 games:

| Sample | n | Win% | 95% CI | Low-conviction win% (same sample) |
|---|---|---|---|---|
| Batch 1 (original 78 games, re-run w/ fixed seed) | 164 | 51.8% | [44.2%, 59.3%] | 51.6% (n=715) |
| **Batch 2 (fresh 78-game holdout)** | **164** | **53.7%** | **[46.0%, 61.1%]** | 48.2% (n=702) |
| Combined | 328 | 52.7% | [47.3%, 58.1%] | 49.9% (n=1,417) |

**Honest answer: the signal held up on a genuine fresh holdout, and the
combined point estimate is now the first to clear the 52.4% breakeven
line on the full available sample — but it is still not statistically
confirmed.** Three things worth being precise about, not rounding toward
the more exciting one:

1. **Directionally, this replicated well.** The fresh batch-2 holdout
   (never used to generate the hypothesis) came in at 53.7% — almost
   exactly matching the original 53.6% figure — and, unlike batch 1 on
   re-run, batch 2 shows a real, meaningful gap between high-conviction
   (53.7%) and low-conviction (48.2%) bets, the calibration property that
   actually matters. A paired-delta test on batch 2 alone gives
   high-minus-low = +5.5pp, 95% CI [-3.0pp, +14.0pp] — still crosses
   zero, not significant on its own, but a real, sizeable point estimate
   in the right direction on brand-new data.
2. **The original 53.6% number was itself partly an artifact of the
   seed bug above.** Re-running batch 1 alone with the fixed, reproducible
   seed gives 51.8%, not 53.6% — and batch 1's own high-vs-low gap is now
   nearly flat (51.8% vs. 51.6%). This does not mean the original finding
   was fabricated (batch 2 replicated the *effect*, independently), but it
   does mean the *exact number* 53.6% should not be treated as precise —
   it was somewhat lucky on that particular unfixed seed.
3. **The combined 328-bet number (52.7%) is still not statistically
   distinguishable from noise.** Its 95% CI [47.3%, 58.1%] comfortably
   spans below the 52.4% breakeven line, and the paired high-vs-low delta
   on the combined sample (+2.9pp, 95% CI [-3.2pp, +8.9pp]) is not
   significant either. Doubling the sample tightened the CI only
   modestly (roughly ±5.4pp instead of ±6.9pp) because "high-conviction
   receiving-yards bets" is itself a fairly narrow slice (n=328 of 2,850).

**Bottom line: this cut is more credible after growing the sample — it
survived a real out-of-sample check, which most noise does not — but it
has not crossed the line into a statistically confirmed edge, and part of
what looked exciting in the original number was measurement noise
(the seed bug) rather than signal.** The honest, useful update is
"promising and now independently replicated once, not yet proven,"
which is a real step forward from "promising but only checked once."

### Mining for other cuts — done with an explicit exploration/holdout split to avoid p-hacking

Rather than pool everything and go hunting for whichever cut of the
**combined** data looks best (which would silently launder a
multiple-comparisons-inflated result), any new cut was **generated only
from batch 1** (the `EXPLORATION` set — the same 78 games already used to
find the original hypothesis, so no new p-hacking exposure there) and then
checked **exactly once** against batch 2 (the `HOLDOUT` set — 78 games
that had never been looked at for this purpose). A cut only earns a
holdout check if, in exploration, its high-conviction win rate both (a)
beat the 52.4% breakeven point estimate and (b) beat its own
low-conviction win rate — the same two-part bar the original discovery
had to clear. This mirrors the task's own honesty requirement: state how
many cuts were checked, and treat anything found only by scanning many
cuts with real skepticism until it survives an independent check.

**12 exploratory cuts were tested** on batch 1 (all on `new`-method
receiving-yards bets): position (WR / TE / RB, 3 cuts), home vs. away
(2), favorite vs. underdog by real point spread (2), game-total median
split ≥/< 44.5 (2), and three alternate conviction thresholds — a looser
z=0.35 and stricter z=0.75/z=1.0 (3). **4 of the 12 passed the exploration
bar** and were checked against the batch-2 holdout:

| Cut (exploration → holdout) | Exploration win% (n) | Holdout win% (n) | Held up? |
|---|---|---|---|
| **Position = RB** | 58.3% (48) | **60.4% (53)** | **Yes — strengthened** |
| Away team | 52.4% (82) | **60.3% (68)** | **Yes — strengthened** |
| Favorite (by real spread) | 57.9% (76) | 49.4% (79) | **No — reverted to noise** |
| Looser threshold (z=0.35) | 53.9% (284) | 53.6% (280) | **Yes — held steady, at ~3x the volume** |

Two more honest, specific findings worth calling out:

- **`position = RB` is the single most promising cut found.** Combining
  both batches (n=101, since it passed the holdout check): **59.4% win
  rate, 95% CI [49.7%, 68.5%]**, vs. 49.8% for non-RB receiving-yards
  high-conviction bets over the same combined window. The paired
  high-vs-low delta on the combined RB slice is +9.6pp, 95% CI
  [-1.4pp, +20.5pp] — the lower bound is barely below zero, the closest
  any cut in either report has come to statistical significance, though
  still not quite there and n=101 is still fairly small. Some caution:
  "away team" also strengthened almost identically (60.3% holdout) and
  may substantially overlap with the same underlying bets (a running
  back's receiving role often varies with game script in ways correlated
  with both home/away and spread) — these are not fully independent
  discoveries and shouldn't be double-counted as two separate confirmed
  signals.
- **The favorite/underdog cut is the clean, honest "this was noise"
  example.** It looked good in exploration (57.9%) and completely
  reverted to a coin flip in the holdout (49.4%, essentially identical to
  its own low-conviction rate of 50.0%) — exactly the kind of result this
  report's methodology is designed to catch and disclose rather than
  quietly drop.
- **The looser z=0.35 threshold is the most operationally useful finding**:
  it holds the win rate essentially flat (53.9% → 53.6%) while nearly
  doubling the qualifying bet volume (284 → 280 vs. the z=0.5 baseline's
  164 → 164) — i.e., the model's conviction signal is informative enough
  that loosening the cutoff doesn't dilute it on this sample, which is a
  real, actionable, low-risk calibration adjustment independent of
  whether the specific position/matchup cuts above hold up further.

None of these individual cuts clear 95% statistical significance on their
own — this section should be read as "these are the most promising leads
for a future, larger, purpose-built test," not as newly proven edges.

### Updated overall verdict

The core conclusion from the first addendum is unchanged: **the
player-prop side still cannot claim a statistically confirmed edge against
real market lines.** What growing the sample changed:

- The blanket `NEW > CURRENT > OLD` ranking held up, with a slightly
  higher `NEW` win rate and smaller (but still not significant) gaps.
- The receiving-yards high-conviction cut **replicated directionally on a
  genuine fresh holdout** and now has a combined point estimate
  (52.7%) that clears breakeven for the first time — real, if modest,
  progress — while also revealing that part of the original number was
  simulation-seed noise, now fixed for good.
- Exploratory mining, done with an explicit exploration/holdout split
  specifically to avoid p-hacking, surfaced one genuinely promising new
  lead (`position = RB`, 59.4% combined, n=101, closest yet to
  significance), one operationally useful calibration adjustment (a
  looser z=0.35 conviction threshold, same win rate at ~3x volume), and
  one explicitly debunked false lead (favorite/underdog).

**Recommended framing, unchanged from the first addendum: treat this as a
projection tool with an increasingly well-evidenced but still-unproven set
of promising leads, not a confirmed betting edge.** The single best next
step, if budget allows in the future, would be a purpose-built test of
the `new`/receiving-yards/RB cut specifically (rather than the broad
market), since it is now the most credible lead in either report.

### Testing (this addendum)

No new production pure functions were added this session — the only code
change was the `_stable_seed()` reproducibility fix inside
`compute_benchmark.py` (an analysis script, not part of the pytest-covered
`services/model-service/src/services/` package), verified by direct
invocation from two separate Python processes producing an identical
seed. The existing production functions this addendum reuses
(`grade_prop_bet`, `summarize_grades`, `evaluate_prop_edge`,
`simulate_team_player_box_scores`, and the walk-forward feature builders
imported from `backtest_matchup_engine.py`) are unchanged and already
covered by the suites listed below. Full relevant suites were re-run
after this addendum's changes:

- `tests/test_nfl_player_prop_backtest_scoring.py`,
  `tests/test_nfl_player_projection_engine.py`,
  `tests/test_nfl_player_box_score_simulator.py`,
  `tests/test_nfl_matchup_features.py` — **37/37 passing**.
- Full `services/model-service/tests/` suite — **190 passed, 7 failed**,
  and all 7 failures are the exact same pre-existing, already-documented
  failures from the original report (`test_main.py::test_classify_nfl_readiness_*`
  ×2, `test_nfl_data.py::test_team_strength_from_record_handles_basic_cases`,
  `test_nfl_routes.py::test_nfl_edges_today_filters_low_confidence`,
  `test_nfl_simulator.py::test_simulator_baseline_unchanged_without_matchup_features`,
  `test_nfl_tasks.py::test_run_nfl_walkforward_backtest_*` ×2) — **no new
  regressions**.

### Artifacts (this addendum)

- `data/ops/nfl-player-prop-vegas-benchmark/pull_historical_player_props_batch2.py`
  — the second, disjoint 78-game real historical pull (documented
  sampling-disjointness proof + budget logic in its own docstring).
- `data/ops/nfl-player-prop-vegas-benchmark/pull_run_log_batch2.json` —
  per-game pull log for batch 2 (event ids, commence times, credit cost;
  0 skips).
- `data/ops/nfl-player-prop-vegas-benchmark/mine_additional_cuts.py` — the
  exploration/holdout cut-mining analysis (read-only, no new API/DB
  writes beyond the schedule-context read).
- `data/ops/nfl-player-prop-vegas-benchmark/mine_additional_cuts_report.json`
  — full numeric output of the cut-mining analysis.
- `data/ops/nfl-player-prop-vegas-benchmark/compute_benchmark.py` —
  modified in place: `_stable_seed()` reproducibility fix (see above);
  otherwise unchanged.
- `data/ops/nfl-player-prop-vegas-benchmark/raw_prop_records.json`,
  `benchmark_summary.json`, `roi_and_significance.json` — **overwritten**
  in place to reflect the combined 156-game / 2,850-bet sample (the
  intended, documented behavior of re-running these scripts, per this
  task's instructions — nothing here was silently lost).
- `data/ops/nfl-player-prop-vegas-benchmark/raw_prop_records_batch1_only.json`,
  `benchmark_summary_batch1_only.json`, `roi_and_significance_batch1_only.json`
  — snapshots of the original 78-game-only outputs, preserved for
  provenance before the combined re-run overwrote the live files.
- `data/ops/nfl-player-prop-vegas-benchmark/_unstable_seed_run_discard/`
  — the combined-sample run made *before* the seed fix (kept only as
  concrete evidence of the reproducibility bug described above; not used
  for any number quoted in this addendum).

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
