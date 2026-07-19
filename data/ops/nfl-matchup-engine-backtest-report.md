# Matchup-Aware Box-Score Engine — Walk-Forward Backtest Report

**Date:** 2026-07-18
**Scope:** Validates the new per-game player box-score Monte Carlo engine
(`services/model-service/src/services/nfl_player_box_score_simulator.py`)
against real historical outcomes, and separately re-validates this
session's earlier flat-baseline fixes (`team_snap_share`, opponent-adjusted
efficiency factors) in a genuine walk-forward setting (they were previously
validated via unit tests and a preseason cold-start anecdote, not yet
against real in-season historical data).

Walk-forward and read-only, same discipline as
`data/ops/nfl-preseason-methodology-backtest-report.md`: every input for
target week **W** is built from **trailing real weeks (< W) only**, this
season — no leakage. Analysis code:

- `data/ops/nfl-matchup-engine-backtest/backtest_matchup_engine.py`
- Raw per-record outputs: `full_sample_records.json` (n=11,453),
  `box_score_records.json` (n=2,337), same folder.

The script imports the REAL production functions directly
(`baseline_projection_from_features`, `simulate_team_player_box_scores`,
`compute_team_volume_context`) — it is not a re-implementation of the logic
being tested.

---

## TL;DR verdict

**Ship the box-score engine.** It fixes a real, previously-undetected
systematic under-projection bias in receiving production (the dominant prop
category) — receiving yards MAE improves **~13%** and bias magnitude drops
**~55%**; targets and receptions improve **~7%** and **~18%** respectively,
with receptions bias dropping **~84%**. Passing yards improves modestly
(~2%). **Rushing yards is a wash to a small regression** (~1% worse MAE for
the dominant rushing position, RB) — flagged honestly below, not hidden.

This session's earlier flat-baseline fixes (`team_snap_share`,
opponent-adjusted factors) show only a **small net effect in this
walk-forward, in-season setting** (as opposed to the large effect they had
in the preseason cold-start scenario originally motivating them) — expected
and explained below, not a red flag.

---

## Methodology

### Three methodologies compared

| Name | What it is |
|---|---|
| **OLD** | `baseline_projection_from_features()` called with `team_snap_share=0.0` (falls back to the old touch-share `snap_proxy` signal) and both opponent factors forced to `1.0` (neutral) — i.e., exactly the pre-this-session production formula. Both fallbacks are backward-compatible by design and unit-tested (`test_qb_volume_falls_back_to_snap_proxy_when_team_snap_share_missing`). |
| **CURRENT** | The same function with this session's real `team_snap_share` and real opponent-adjusted factors wired through — still a **flat, single-mean** projection, no per-game sampling. This is what's live in production today, before this task's work. |
| **NEW** | CURRENT's baseline feeds `simulate_team_player_box_scores()` — the new engine. Reported mean is the **across-replicate mean** of the simulated box score (see design note below for why this can differ from CURRENT's mean, not just add variance). |

All three consume the **identical walk-forward feature inputs** (see
below) so any MAE/bias difference is attributable only to the
formula/engine, not to different data.

### Walk-forward feature construction (no leakage)

For each target week **W** in `{2023, 2024, 2025} × weeks 4–17`:

- **Player role features** (`snap_proxy`, `team_snap_share`, `target_proxy`,
  `route_proxy`, `rush_share`, `red_zone_share`, `qb_dropback_factor`,
  `qb_pressure_factor`, `role_confidence`) — computed from that player's
  real `nfl_dp_player_usage_weekly` rows for weeks **strictly before W**
  this season only (ratio-of-trailing-sums, same formula shape as
  `materialize_player_projection_features()`'s SQL, just averaged over
  trailing weeks instead of reading week W's own actual result).
- **Team context** (`team_pace_factor`, `team_pass_rate_factor`, and for
  NEW, the full `TeamVolumeContext`) — from trailing real
  `nfl_dp_team_situational_weekly` rows (`source = 'nflverse'`, weeks < W).
- **Opponent-adjusted factors** — from the real scheduled opponent's
  (`nfl_dp_schedules`) trailing defensive EPA/pressure stats vs. a
  trailing league average, same formula as production.
- **Truth** — that player's REAL week-W `pass_yards` / `rush_yards` /
  `receiving_yards` / `targets` / `receptions` from
  `nfl_dp_player_usage_weekly` (`source = 'pbp_aggregation'`).

**Eligibility:** a real skill-position player (QB/RB/WR/TE) with
`involvement_plays > 0` in week W (truth exists) and at least 1 trailing
real week this season (features exist). `availability_confidence` is held
flat at 0.90 and `experience_confidence` at veteran level for all three
methodologies (injury/rookie-widening effects only touch std, not the
means being compared here, and are held identical across all three
methodologies either way, so they cannot bias the comparison).

### Two-tier sample (for tractable Monte Carlo runtime)

- **Full sample** (OLD vs. CURRENT, no Monte Carlo needed — both are
  deterministic): **all weeks 4–17, all 3 seasons, n = 11,453 player-games.**
- **Box-score subset** (OLD vs. CURRENT vs. NEW — NEW requires running the
  Monte Carlo, 250 replicates/team-game for backtest speed vs. the
  production default of 2,000): **weeks 6, 10, 14 only, all 3 seasons,
  n = 2,337 player-games.** Chosen to span early/mid/late season while
  keeping runtime reasonable; OLD/CURRENT numbers on this subset are
  reported alongside NEW for a fair apples-to-apples comparison (they
  differ slightly from the full-sample numbers just because it's a
  different, smaller slate of weeks, not a different formula).

---

## Results: OLD vs. CURRENT (this session's earlier fixes), full sample, n=11,453

| Stat | OLD MAE | OLD bias | CURRENT MAE | CURRENT bias | Verdict |
|---|---|---|---|---|---|
| pass_yards | 8.930 | −0.736 | 9.070 | **+1.691** | Slightly worse MAE (+1.6%); bias flips sign and grows |
| rush_yards | 8.191 | −1.624 | 8.172 | −1.632 | Essentially unchanged |
| receiving_yards | 18.945 | −16.140 | 18.856 | −15.950 | Marginal improvement (~0.5% MAE) |
| targets | 1.834 | −1.391 | 1.834 | −1.391 | **Identical** — `targets_mean` doesn't use either fixed input |
| receptions | 1.493 | −1.219 | 1.493 | −1.219 | **Identical** — same reason |

**Why the effect is small here, unlike the preseason anecdote:** the
`team_snap_share` fix mattered most in the **cold-start preseason case**,
where a real starting QB's touch-share (`snap_proxy`) has no in-season
track record to lean on and the formula weighted it at 70%. In a
**walk-forward, in-season** setting, a real starter's trailing `snap_proxy`
(touch share among teammates) is already a stable, correlated proxy for
"is this the guy" once you're conditioning on weeks he actually played —
so the two signals mostly agree, and swapping one for the other doesn't
move the mean much on average. The opponent-adjustment fix only feeds into
the `receiving_yards`/`rush_yards`/`pass_yards` *efficiency* terms (never
`targets_mean`/`carries_mean`), which is exactly what the identical
targets/receptions rows above confirm. Genuinely useful finding: **the
biggest real-world value of both fixes is at the cold-start/preseason
boundary, not on in-season week-to-week walk-forward accuracy** — worth
knowing, not a reason to reconsider either fix (they were never claimed to
help in-season accuracy; they closed a QB-crushing bug and added
previously-nonexistent opponent awareness).

One small negative to flag honestly: `pass_yards` MAE ticks up slightly
under CURRENT (bias flips from a small under-projection to a larger
over-projection). This is a real, small, worth-watching effect, not
something to block on — see Recommended Follow-Up.

---

## Results: OLD vs. CURRENT vs. NEW (box-score engine), subset, n=2,337

| Stat | OLD MAE | CURRENT MAE | **NEW MAE** | OLD bias | CURRENT bias | **NEW bias** | NEW vs. OLD MAE Δ |
|---|---|---|---|---|---|---|---|
| pass_yards | 8.847 | 9.064 | **8.675** | −0.325 | +2.069 | **−1.871** | **−1.9%** |
| rush_yards | 8.215 | 8.202 | **8.295** | −1.630 | −1.656 | **−0.548** | **+1.0%** (regression) |
| receiving_yards | 18.661 | 18.551 | **16.196** | −15.755 | −15.574 | **−7.021** | **−13.2%** |
| targets | 1.850 | 1.850 | **1.714** | −1.406 | −1.406 | **+0.457** | **−7.4%** |
| receptions | 1.450 | 1.450 | **1.185** | −1.175 | −1.175 | **−0.184** | **−18.3%** |

**The headline finding:** both OLD and CURRENT carry a large, systematic
**under-projection bias on every receiving-game stat** (receiving_yards
bias ≈ −16 yards, i.e. real players are catching for ~16 more yards/game
on average than the flat formula projects; targets/receptions similarly
under-shoot). This is a genuine, previously-undetected bug in the flat
formula, unrelated to the opponent-adjustment/team_snap_share fixes: each
player's `targets_mean`/`carries_mean` is computed from a **standalone,
independently-calibrated per-player formula** (a function of that player's
own `target_proxy`, confidence terms, etc.), and when you sum every
pass-catcher's `targets_mean` on a real team, it lands **well under** that
team's real total pass attempts — the per-player confidence/role dampening
terms don't independently sum back to the team total by construction, so a
meaningful chunk of a team's real receiving volume was quietly
"evaporating" rather than landing on any modeled player.

The box-score engine's Dirichlet allocation step **renormalizes** each
group's shares to (nearly) exhaust the team's real trailing play-volume
pool (see `_normalize_shares_to_pool()`'s docstring in
`nfl_player_box_score_simulator.py`) — this was originally designed purely
to enable the requested team-level coherence property, but this backtest
shows it **also fixes a real accuracy bug as a side effect**: receiving
yards MAE improves 13.2%, bias magnitude drops more than half, and
targets/receptions both improve meaningfully. This is exactly the kind of
result the project's backtesting discipline exists to surface — a fix that
looks like "just adding realistic variance" turns out to also correct a
real mean-level bias.

**The honest downside:** `rush_yards` is a **small regression** (+1.0%
MAE pooled; see position breakdown below — RB, the dominant rushing
position, is ~2% worse). Rushing volume doesn't suffer from the same
"evaporating share" problem receiving does (there are fewer competing
runners per team, so `carries_mean` already sums closer to a team's real
rush attempts even in the flat formula) — so the same renormalization that
fixes receiving has less to fix for rushing, and the added per-replicate
sampling noise (250 replicates, below the production default of 2,000) is
enough to net out slightly negative on this metric. `pass_yards` is a
small net win (−1.9% MAE) — QB attempts already have a share near 1.0 with
little to renormalize, so this mostly reflects the Monte Carlo mean
tracking the (already slightly-improved) CURRENT baseline closely, with a
small edge.

### By position (subset, n=2,337)

| Position (n) | Stat | OLD MAE | CURRENT MAE | **NEW MAE** |
|---|---|---|---|---|
| QB (281) | pass_yards | 73.548 | 75.357 | **72.119** |
| QB (281) | rush_yards | 13.765 | 13.739 | **13.482** |
| RB (626) | rush_yards | 22.581 | 22.547 | **23.004** |
| RB (626) | receiving_yards | 12.064 | 12.019 | **11.407** |
| RB (626) | receptions | 1.393 | 1.393 | **1.199** |
| TE (501) | receiving_yards | 18.802 | 18.721 | **16.533** |
| TE (501) | targets | 1.736 | 1.736 | **1.936** (regression) |
| TE (501) | receptions | 1.547 | 1.547 | **1.286** |
| WR (929) | receiving_yards | 28.572 | 28.370 | **24.037** |
| WR (929) | targets | 2.638 | 2.638 | **2.195** |
| WR (929) | receptions | 1.860 | 1.860 | **1.467** |

WR carries the largest absolute win (receiving_yards MAE −4.5 yards/game,
−15.8% relative) since WRs are both the largest position group and the
group whose flat-formula target shares summed furthest under 1.0. TE
`targets` is a second honest regression to flag (+11.5% worse) even though
TE `receiving_yards`/`receptions` both clearly improve — plausible
explanation: TE target shares are typically small and volatile relative to
WRs/RBs, so TE's per-player Dirichlet allocation noise (role_confidence-driven)
is proportionally larger relative to its own mean, adding more relative MAE
noise on the target *count* even while the resulting yards/receptions (which
also benefit from the volume-pool fix) improve. RB `rush_yards` is the other
flagged regression (discussed above).

---

## Recommended follow-ups (not implemented — validation only, per task scope)

1. **Ship the box-score engine as-is.** The receiving-game win is large,
   consistent across all three receiving-relevant stats (yards/targets/receptions),
   and traces to a real, explainable, previously-undetected bug fix — not
   a one-metric fluke.
2. **RB rush_yards regression: confirmed real, first fix attempt disproven,
   root cause narrowed.** Re-checked at full production replicate count
   (2,000): unchanged (~2% regression persists, not Monte Carlo noise from
   this report's original 250-replicate test). Tried a pool-specific
   tighter Dirichlet concentration for rush allocation (34 -> 52) on the
   hypothesis that added share-variance was the cause — re-tested at 800
   replicates, RB rush_yards MAE was unchanged (22.99 either way),
   disproving that hypothesis. Reverted rather than ship an unjustified
   parameter. Follow-up diagnostic: queried real `rush_share`/`target_proxy`
   SQL feature columns directly (the raw usage-ratio inputs, not
   `baseline_projection_from_features()`'s output) across 2025 weeks 4-17 —
   both already sum to ~0.96 per team, essentially identically for rush and
   pass. So the "evaporating share" effect this engine's renormalization
   fixes is NOT a rush-vs-receiving asymmetry in the raw usage data; it's
   introduced downstream inside `baseline_projection_from_features()`'s own
   confidence-scaling/clamping logic, likely to differing degrees by
   position group in a way not yet isolated. Real next step for whoever
   picks this up: diagnose confidence_scale's effect on the SUM of
   `carries_mean` across a real roster vs. the sum of `targets_mean`,
   holding real usage shares fixed, to find where the two diverge — a
   targeted fix belongs in the baseline formula itself, not in the
   box-score engine's allocation layer, given this finding.
3. **Investigate the CURRENT pass_yards bias flip** (small negative vs.
   small positive, found in the OLD-vs-CURRENT full-sample comparison).
   Not blocking, but worth a look at whether `team_snap_share`'s weighting
   (55% of `qb_volume_signal`) is slightly too aggressive walk-forward,
   independent of this task's box-score work.
4. **Re-run the box-score subset comparison at full production replicate
   count (2,000)** once there's budget for the ~8x longer runtime, to
   confirm the headline numbers hold (expected: means converge tighter,
   MAE should if anything improve slightly for NEW as Monte Carlo noise
   shrinks).

---

## ADDENDUM (2026-07-19): re-run after the `targets_mean` foundational fix — the box-score engine's receiving-yards edge was a symptom of the same bug this backtest already flagged

**What changed:** commit `5c098d36` fixed `baseline_projection_from_features()`'s
`targets_mean` for both WR/TE and RB. It previously multiplied `target_proxy`
(a real target *share*) by a small arbitrary fixed coefficient (11.5 for
WR/TE, 7.0 for RB) instead of the player's real team pass-attempts estimate
— this is the exact mechanism identified above in "Recommended Follow-Up #2"
(RB rush regression root-cause note) and in the main body's "evaporating
share" finding: per-player `targets_mean` values summed to well under a
team's real pass attempts. That fix is now live in production and this
backtest script re-run (same walk-forward methodology, same code path,
`baseline_projection_from_features` imported directly — **OLD now also
carries this fix**, since it lives unconditionally inside the shared
formula, not behind either of OLD's two fallback flags).

**This directly answers the question this backtest was designed to ask:**
did the box-score engine's earlier receiving-yards win come from a genuine
Monte-Carlo/coherence advantage, or was it partly just correcting the same
per-player-share-undercount bug via its Dirichlet pool renormalization? Real
re-run numbers, below — **it was overwhelmingly the latter.**

### (a) The flat baseline's own receiving-yards MAE improved substantially, on its own, from this fix alone

Full sample (OLD vs. CURRENT, weeks 4–17, n=11,453 — both flat, no Monte
Carlo, before vs. after the fix):

| Stat | OLD MAE (before fix) | OLD MAE (after fix) | Δ | OLD bias (before) | OLD bias (after) |
|---|---|---|---|---|---|
| receiving_yards | 18.945 | **16.055** | **−15.3%** | −16.140 | **−8.531** (−47.1% magnitude) |
| targets | 1.834 | 1.654 | −9.8%* | −1.391 | +0.250 |
| receptions | 1.493 | 1.235 | −17.3%* | −1.219 | −0.317 |
| pass_yards | 8.930 | 8.930 | unchanged | −0.736 | −0.736 |
| rush_yards | 8.191 | 8.191 | unchanged | −1.624 | −1.624 |

*targets/receptions MAE moves here are the direct, mechanical result of the
formula fix itself (real targets are now realistically ~2x higher per
pass-catcher) — pass_yards/rush_yards are unaffected because the fix only
touches WR/TE/RB `targets_mean`, not QB `attempts_mean` or `carries_mean`.
CURRENT shows the same pattern (receiving_yards MAE 18.856 → 16.082,
**−14.7%**; bias −15.950 → −8.174, **−48.8% magnitude**) — confirms this is
the shared-formula fix, not specific to either OLD or CURRENT's fallback
flags.

**Yes — a substantial chunk of "realistic receiving production" was
recovered by the flat baseline fix alone**, exactly as this report's
"evaporating share" finding predicted it should be, once someone fixed the
per-player formula rather than papering over it with pool renormalization.

### (b) The box-score engine's relative edge over the now-fixed baseline collapsed to a wash (and flipped to a small regression on targets/receptions)

Box-score subset (OLD vs. CURRENT vs. NEW, weeks 6/10/14, n=2,337 — real
Monte Carlo re-run):

| Stat | NEW vs. OLD, before fix | NEW vs. OLD, after fix | What changed |
|---|---|---|---|
| receiving_yards | **−13.2%** (18.661→16.196) | **−0.08%** (16.070→16.057) | Edge is now a statistical wash |
| targets | **−7.4%** (1.850→1.714) | **+4.7% regression** (1.656→1.733) | Flipped from win to loss |
| receptions | **−18.3%** (1.450→1.185) | **+1.5% regression** (1.206→1.224) | Flipped from win to loss |
| pass_yards | −1.9% (8.847→8.675) | −2.0% (8.847→8.668) | Unchanged (QB path untouched by fix) |
| rush_yards | +1.0% regression (8.215→8.295) | +0.9% regression (8.215→8.286) | Unchanged (RB rushing path untouched by fix) |

Position-level receiving_yards confirms the same collapse everywhere it
mattered before:

| Position | NEW vs OLD, before fix | NEW vs OLD, after fix |
|---|---|---|
| WR (n=929) | −15.8% (28.572→24.037) | **−0.1%** (23.918→23.893) |
| TE (n=501) | −12.1% (18.802→16.533) | **−0.7%** (16.553→16.439) |
| RB (n=626) receiving | −5.4% (12.064→11.407) | **+0.7% regression** (11.100→11.177) |

**Verdict, updated:** the box-score engine's headline receiving-yards win
(−13.2% MAE, the centerpiece of the original TL;DR) is **not** an
independent Monte-Carlo/coherence benefit — it was almost entirely the
Dirichlet pool renormalization silently correcting the same per-player
target-share-undercount bug that's now fixed properly at the source. With
the source fixed, the box-score engine's receiving-yards accuracy is now
statistically indistinguishable from the (much simpler, much cheaper) flat
baseline, and it's now a small net *negative* on targets/receptions (the
count stats), on top of the pre-existing small rush_yards regression that
was never resolved.

**This does not mean the box-score engine has no value** — it still exists
to answer a different question (coherent per-replicate team-level box
scores, e.g. for correlated same-game parlay/DFS use cases, and per-stat
variance/percentile bands, not just a point mean) — but **its
accuracy-improvement justification is gone**. The original TL;DR's "ship
the box-score engine" recommendation was based on a real measurement that,
in hindsight, was measuring two effects at once (the intended
renormalization behavior + an unintended bug-masking side effect); now that
they're disentangled, the engine should be evaluated purely on
distributional/coherence value, not on point-accuracy, for any future
prioritization decision.

**Root-cause consistency check:** this is also the correct resolution to
this report's own "Recommended follow-up #2" (RB rush_yards regression
investigation) — that note concluded the "evaporating share" asymmetry
"is introduced downstream inside `baseline_projection_from_features()`'s
own confidence-scaling/clamping logic" and recommended fixing it "in the
baseline formula itself, not in the box-score engine's allocation layer."
That is exactly what commit `5c098d36` did, and the RB rush_yards
regression itself (a genuinely separate, rushing-specific issue, since the
fix does not touch `carries_mean`) is essentially unchanged, as expected:
22.581→23.004 (+1.9%) before vs. 22.581→22.975 (+1.7%) after — confirming
it really is independent of the receiving-share bug this fix addressed.

Raw re-run outputs: `full_sample_records.json` (n=11,453),
`box_score_records.json` (n=2,337) in the same folder — overwritten by this
addendum's re-run (previous pre-fix raw records are superseded; the summary
numbers from the original run are preserved verbatim in the tables above).
