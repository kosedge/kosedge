# NFL Team-Level Game Simulator — Calibration Audit Report

**Date:** 2026-07-19
**Scope:** `services/model-service/src/services/nfl_simulator.py` (score /
win-probability / total Monte Carlo engine) and its upstream team-strength
input pipeline (`nfl_handicapping_framework.py`'s EPA-to-points conversion,
and `tasks.py`'s `_load_team_strength_priors` / team-strength-selection
logic that feeds it) — the code that actually produces this platform's
"beat Vegas" product (spreads, totals, win probabilities). Explicitly
**not** in scope: the player-level projection engine
(`nfl_player_projection_engine.py`) audited earlier today, or the
matchup-engine backtest work in `data/ops/nfl-matchup-engine-backtest*`.

## TL;DR verdict

**Found and fixed one real, confirmed, significant miscalibration** — not
in `nfl_simulator.py`'s own math (which checks out), but one level up, in
the team-strength *signal selection* logic that decides what actually feeds
`nfl_simulator.py` once a season is under way. The live production pipeline
was silently preferring a crude ESPN win-loss-record-derived team-strength
index over the real, EPA-based rolling-feature prior for the **entire
season past week 1** — even though only the EPA-based signal was ever
validated against real historical games. A real backtest against 855 real
2023-2025 games confirms the record-based signal that was actually live is
**worse than the market itself** (spread MAE 10.73 vs. the market's 9.79),
while the EPA-based signal it was silently overriding **beats the market**
(9.50 MAE) — exactly the kind of signal that was already validated in
`scripts/nfl/historical_market_backtest.py` but never actually wired into
the live path once a team has played a game. Fixed by flipping the
fallback priority. Everything else checked below — the EPA-to-index
conversion formula itself, the base priors (home-field, total, stdev), the
market-blend weights, the totals-calibration layer, and the full-season
win-total distribution shape — came back well-calibrated against real data
and required no changes.

---

## What was checked, and how

### 1. Full read of `nfl_simulator.py` and its team-strength inputs

Read `nfl_simulator.py` (643 lines) end-to-end along with
`nfl_handicapping_framework.py` (the separate "EPA-to-points conversion"
module the task asked to look for — `compute_nfl_projection_decomposition`
is exactly that: it converts `offense_index`/`defense_index` team-strength
ratios into margin/total point contributions). Traced every numeric
coefficient back to either (a) a real backtest artifact already on disk
(`data/ops/nfl-market-blend-backtest-2026-07-17.json`,
`scripts/nfl/historical_market_backtest.py`), or (b) a plausible-looking but
unvalidated constant, then checked category (b) against real data.

### 2. Traced where `offense_index`/`defense_index` actually come from in production

Two candidate sources exist:

- **`nfl_data.team_strength_from_record()`** — converts an ESPN win-loss
  record string (e.g. `"11-6"`) into an index via
  `offense = 0.90 + 0.22*win_pct`, `defense = 0.92 + 0.20*win_pct`. This is
  populated into `nfl_game_context` by `tasks.pull_nfl_context_snapshot`
  and is a real signal, but a crude one — it conflates a team's offensive
  and defensive strength into the same single win-percentage number, and it
  has never been backtested against real outcomes anywhere in this
  codebase.
- **`tasks._load_team_strength_priors()`** — converts real, in-season
  rolling EPA/pressure features (`nfl_dp_team_rolling_features_weekly`)
  into the same index shape via `offense_index = 1.0 + (off_epa*0.75) +
  (pressure_delta*0.18)`, `defense_index = 1.0 + (-def_epa_allowed*0.90) +
  (pressure_delta*0.14)`. **This is the exact formula
  `scripts/nfl/historical_market_backtest.py` used** to validate the model
  against 2013-2025 real closing lines (spread MAE 9.62 vs. the market's
  9.92 — the model beat the market on this signal).

The live task that drives the scheduled daily production pipeline
(`tasks.run_nfl_market_simulations`) previously resolved which one to use
like this:

```python
offense_home = (
    (home_prior.offense_index) or base_offense_home  # EPA prior, if record-based is degenerate
) if abs(base_offense_home - 1.0) < 1e-6 else base_offense_home  # record-based, otherwise
```

i.e. it used the record-based signal **whenever a team had a
non-degenerate win-loss record** (any team that's played a single game),
falling back to the EPA-based prior only for a genuine 0-0 cold start. In
practice this meant the EPA-based signal — the only one ever validated end
to end — was live for roughly the first week of a season only, and silently
replaced by the unvalidated win-loss heuristic for the other ~17 weeks.

### 3. Real backtest: does the record-based signal that's actually live hold up?

Built `data/ops/nfl-team-simulator-calibration-audit/backtest_record_vs_epa_signal.py`,
which replays 855 real games (2023-2025, from `nfl_dp_schedules`, all with
real closing lines) through the **actual production `simulate_nfl_game()`**
function twice per game — once with each team's real cumulative win-loss
record **entering that game** (computed with no leakage, walk-forward, from
that season's real prior results only — exactly mirroring what
`team_strength_from_record` would have seen live), and once with the real
EPA-based rolling-feature prior for that same game/week. Real results:

| Signal | Spread MAE | Spread corr. w/ actual | Total MAE | Total corr. w/ actual |
|---|---|---|---|---|
| **RECORD-based (what was actually live)** | **10.73** | **0.27–0.35** | **10.67** | **0.03–0.07** |
| EPA-based (validated signal) | 9.50 | 0.65–0.67 | 10.03 | 0.43–0.45 |
| Market (closing line) | 9.79 | 0.47–0.49 | 10.12 | 0.31–0.33 |

The record-based signal that was actually driving live production is
**worse than blind market consensus** on spread accuracy (10.73 vs. 9.79)
and has roughly **half the correlation** with real outcomes that the
EPA-based signal has. This is a real, significant, confirmed degradation —
the model was leaving real accuracy on the table for the entire season past
week 1, hidden behind an aggregate CLV metric (see below) that never
isolated this specific signal-selection choice.

**Why the positive CLV backtest didn't catch this:** `data/ops/nfl-clv-benchmark-report.json`
measures whether the model's recommended side beats the *closing* line
relative to the *opening* line — a real, valid metric, but a different
question from "how close is the model's predicted margin/total to the real
final score," which is what actually matters for the underlying signal
quality this audit is checking. A model can still show a positive,
if modest (47-60% positive rate), CLV edge while using a genuinely inferior
team-strength signal underneath — especially once the 30%-weighted market
blend (`NFL_MARKET_BLEND_SPREAD_WEIGHT`/`_TOTAL_WEIGHT`) is layered on top,
which pulls the model's raw picks partway back toward the market regardless
of which raw signal produced them. This is exactly the "don't presume
team-level is fine just because the aggregate CLV signal is positive"
scenario the task asked to check for.

### 4. Full-season Monte Carlo win-total distribution shape (2024, 2025)

Built `data/ops/nfl-team-simulator-calibration-audit/backtest_season_win_totals.py`:
replayed every real game in the 2024 and 2025 seasons through
`simulate_nfl_game()` (both signals), then Monte-Carlo'd 2,000 full-season
replicates by sampling each game's winner from the model's `home_win_prob`.

- **Distribution shape:** both signals produce a real, smooth, roughly
  bell-shaped win-total distribution centered near 8-9 wins (min 0-1, p10=6,
  p50=8-9, p90=11, max 16-17) — **not** clustered or bimodal. This part of
  the simulator checks out fine for both signals; the shape test alone does
  not distinguish signal quality (per-game win probabilities pool close to
  .500 leaguewide regardless of which signal produced them, so both
  naturally regress toward a bell curve).
- **Per-team accuracy (the real differentiator):** mean-absolute-error of
  each team's simulated-mean season win total vs. their real actual win
  total: **2024: record-based 2.65 wins/team vs. EPA-based 2.44** (EPA
  ~8% more accurate); **2025: record-based 2.39 vs. EPA-based 2.20** (EPA
  ~8% more accurate). Consistent with the head-to-head spread/total finding
  above — the EPA-based signal is measurably, consistently better at
  reproducing real outcomes.

### 5. Real league averages vs. the model's base priors

Checked `get_nfl_handicapping_config()`'s base priors against real 2023-2025
league scoring (from `nfl_dp_schedules`, `home_score`/`away_score`):

| Prior | Model value | Real 2023-2025 | Verdict |
|---|---|---|---|
| `base_total_points` | 43.5 | 43.8 (2023) / 46.0 (2024) / 46.0 (2025), ~45.3 avg | Slightly low (~1.8 pts) but well within the framework's own `[30, 66]` clamp and the separately-fit `totals_calibration` linear layer (real slope/intercept refit against actual historical totals once `sample_size >= 80`) is specifically designed to correct exactly this kind of residual bias. Not a "3-6x" bug — a fine-tuning-level gap, not forcing a change. |
| `home_field_points` | 1.35 | avg real home margin 2.92 (2023) → 2.28 (2024) → 2.03 (2025), shrinking (matches the well-known real-world trend of NFL home-field advantage shrinking in recent seasons) | Plausible; real home-field-advantage-controlling-for-team-strength estimates in the 1-2 point range are standard in the literature, and this prior sits inside that range even against the most recent (smallest) season. |
| `base_score_stdev` | 9.2 (clamped `[7.6, 12.2]`) | real single-team-game score stdev 9.83-10.35 (home), 9.39-9.98 (away) | Close, on the low side by ~0.5-1.0 points, but the `totals_adjustments.stdev_points` injury-driven upward adjustment (up to +2.0) and the clamp ceiling (12.2) already allow it to reach the real range on a per-game basis. Not a confirmed bug. |
| `NFL_MARKET_BLEND_SPREAD_WEIGHT` / `_TOTAL_WEIGHT` | 0.30 / 0.30 | Already real-data-validated: `scripts/nfl/historical_market_backtest.py` swept weights 0.0-1.0 against 3,562 real 2013-2025 games and 0.30 won both sweeps (see `data/ops/nfl-market-blend-backtest-2026-07-17.json`) | Already validated, no re-check needed. |

None of these base priors showed the "3-6x off" magnitude of bug found in
today's player-engine audit — they're all within a defensible range of real
data, unlike the team-strength-selection bug above.

---

## The fix

**File:** `services/model-service/src/tasks.py` (the live
`run_nfl_market_simulations` production task, and its supporting
`_load_team_strength_priors` neighbor).

Extracted the selection logic into a new, directly unit-tested pure
function, `_resolve_team_strength_indices()`, and flipped its priority:
**prefer the real EPA-based rolling-feature prior whenever it exists**,
falling back to the record-based ESPN win-loss estimate only for a genuine
cold start (no rolling-feature rows at all for that team/season — the one
case `_load_team_strength_priors` cannot itself backfill, since it already
falls back to the *prior* season's final rolling features when the current
season has no rows yet).

```python
def _resolve_team_strength_indices(
    *, base_offense_home, base_offense_away, base_defense_home, base_defense_away,
    home_prior, away_prior,
) -> tuple[float, float, float, float]:
    epa_offense_home = _to_float(home_prior.get("offense_index"))
    epa_offense_away = _to_float(away_prior.get("offense_index"))
    epa_defense_home = _to_float(home_prior.get("defense_index"))
    epa_defense_away = _to_float(away_prior.get("defense_index"))
    return (
        epa_offense_home if epa_offense_home is not None else base_offense_home,
        epa_offense_away if epa_offense_away is not None else base_offense_away,
        epa_defense_home if epa_defense_home is not None else base_defense_home,
        epa_defense_away if epa_defense_away is not None else base_defense_away,
    )
```

A full in-code comment documenting the real bug/root cause/methodology (in
the style of today's player-engine fixes) is attached to this function in
`tasks.py`. Two new regression tests
(`test_resolve_team_strength_indices_prefers_real_epa_prior_over_record`,
`test_resolve_team_strength_indices_falls_back_to_record_on_genuine_cold_start`)
lock in both branches in `services/model-service/tests/test_nfl_tasks.py`.

**`nfl_simulator.py` itself required zero changes** — its own math (the
Monte Carlo score sampling, market-blend, totals-calibration, moneyline
conversion) is correct; the bug was entirely in what got fed into it.

### Known, lower-priority follow-up not fixed in this pass

`routes/nfl.py`'s `POST /simulations/{game_id}` endpoint (a manual,
admin-triggered single-game re-simulate route, **not** the scheduled
production driver) reads `offense_index_home`/etc. directly from
`nfl_game_context` with no EPA-prior fallback at all, so it has the same
underlying issue whenever it's invoked after week 1. Left as-is in this
pass because (a) it's not the code path driving the live product or the
CLV benchmark, and (b) fixing it cleanly would require either duplicating
`_load_team_strength_priors`'s SQL in `routes/nfl.py` or introducing a new
`routes -> tasks` import that the codebase currently avoids (task dispatch
from routes is done via celery task-name strings, not direct imports).
Flagging honestly rather than forcing an architecturally awkward fix.

---

## Regression testing

- `services/model-service`: full suite passes with **zero new
  regressions**. The 7 previously-known pre-existing failures remain
  exactly as documented (`test_classify_nfl_readiness_*` x2,
  `test_team_strength_from_record_handles_basic_cases`,
  `test_nfl_edges_today_filters_low_confidence`,
  `test_simulator_baseline_unchanged_without_matchup_features`,
  `test_run_nfl_walkforward_backtest_*` x2) — confirmed via a direct rerun
  of `tests/test_nfl_tasks.py` and `tests/test_nfl_simulator.py`, plus a
  full-suite run.
  - Environmental note, unrelated to this change: in this sandboxed
    environment, the 4 tests in `test_nfl_supervised_retrain.py` that call
    `fit_nfl_supervised_models()` (a real scikit-learn
    `HistGradientBoosting` fit) run extremely slowly (10+ minutes each,
    with the process spending most of its wall-clock time idle rather than
    burning CPU) — confirmed this is pre-existing and has nothing to do
    with this change by running one of them in complete isolation (same
    slowness) and by noting `nfl_supervised_retrain.py` was never touched.
    Not one of the 7 documented pre-existing *failures* (they do pass, just
    slowly), so not a regression, but worth flagging for whoever next runs
    the full suite in this environment.
- `services/data-platform-nfl`: **44/44 passed**, matching the documented
  baseline exactly.

---

## Files touched

- `services/model-service/src/tasks.py` — new `_resolve_team_strength_indices()`
  helper (with full root-cause documentation), call site in
  `run_nfl_market_simulations` updated to use it.
- `services/model-service/tests/test_nfl_tasks.py` — 2 new regression tests.
- `data/ops/nfl-team-simulator-calibration-audit/` — this audit's real
  backtest scripts (`backtest_record_vs_epa_signal.py`,
  `backtest_season_win_totals.py`) and raw output
  (`record_vs_epa_backtest_records.json`), kept for re-checkability.
- `data/ops/nfl-team-simulator-calibration-audit-report.md` — this report.
