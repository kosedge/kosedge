# NFL Phase 3 — Historical Replay & Benchmark Gate (2026-08-09)

**Engine stamp:** `nfl-season-engine-v1.26-phase2-features-pathA-player-volume`  
**Protocol:** `nfl-historical-replay-v1-20260809`  
**Seasons scored:** 2019, 2020, 2021, 2022, 2023, 2024, 2025  
**Replicates / season:** `25` (seed base `20260809`)  
**PR target:** `deploy-vercel`

## Cutoff rules (no look-ahead)

| Season band | Depth cutoff | Strength prior |
|-------------|--------------|----------------|
| ≤2024 | nflverse `week=1` + `game_type=REG` | Y−1 play-weighted EPA (`nfl_dp_team_situational_weekly`, source=nflverse) |
| ≥2025 | latest nflverse `dt` on/before Labor Day Monday of season year | same Y−1 EPA |

**Forbidden inputs:** season-Y regular-season results, season-Y rolling features (week-1 rolling embeds Y games), end-of-year ranks, calibrating knobs on Y then scoring Y.

## Team wins scorecard (MAE / bias / Spearman ρ)

| Season | Model | Prior-year+reg | EPA power | Vegas | snapshot |
| --- | --- | --- | --- | --- | --- |
| 2019 | 2.284 / -0.000 / 0.533 | 2.383 / 0.000 / 0.391 | 2.420 / 0.204 / 0.532 | n/a | REG-3957c69a1ae2 |
| 2020 | 2.765 / -0.000 / 0.590 | 2.730 / -0.062 / 0.442 | 3.009 / 0.219 / 0.486 | n/a | REG-4bac4215d1ac |
| 2021 | 2.045 / -0.000 / 0.499 | 1.906 / -0.312 / 0.577 | 1.886 / -0.227 / 0.561 | n/a | REG-428af923e646 |
| 2022 | 2.502 / -0.000 / 0.311 | 2.594 / 0.031 / 0.166 | 2.997 / -0.119 / 0.267 | n/a | REG-5898cc7482d0 |
| 2023 | 1.917 / -0.000 / 0.454 | 2.065 / -0.031 / 0.413 | 2.350 / -0.099 / 0.409 | n/a | REG-c31a97fec281 |
| 2024 | 3.125 / 0.000 / 0.187 | 2.875 / 0.000 / 0.349 | 3.215 / 0.026 / 0.260 | n/a | REG-30b943729db3 |
| 2025 | 2.764 / -0.000 / 0.320 | 2.688 / 0.000 / 0.304 | 3.188 / -0.160 / 0.256 | n/a | 901-52999c5efafc |

## Pooled (equal team-weight via n)

| Metric | MAE / bias / ρ |
| --- | --- |
| model wins | 2.486 / -0.000 / 0.413 |
| prior-year+regression wins | 2.463 / -0.054 / 0.378 |
| epa_power wins | 2.723 / -0.022 / 0.396 |
| vegas wins | nan / nan / nan |
| model PF | 55.948 / -3.094 / 0.402 |
| model PA | 45.084 / -3.094 / 0.231 |
| model team pass yards | 373.507 / -90.630 / 0.486 |
| model team rush yards | 273.154 / -102.254 / 0.338 |
| model player pass yards | 847.873 / -58.148 / 0.698 |
| model player rush yards | 204.648 / 47.749 / 0.683 |
| model player rec yards | 230.946 / 155.415 / 0.573 |

## Where we add value vs where we do not

**Earned (pre-registered MAE wins or produced honest scorecards):**
- team_wins vs epa_power
- player_pass_yards scorecard produced (n=474)
- player_rush_yards scorecard produced (n=1053)
- player_rec_yards scorecard produced (n=1697)

**Not earned:**
- team_wins vs prior_year_regression (higher MAE)
- team_wins vs vegas (missing historical files)

| Gate | Status |
|------|--------|
| Phase 4 infrastructure unblocked | **YES** |
| Phase 4 model-value claim unblocked | **NO** |

Phase 4 infrastructure unblocked (repeatable no-look-ahead replay). Model-value claim stays blocked until team-wins MAE beats prior-year+regression.

## Watchlist rule

Fixed per era: top 5 prior-year volume at each of QB / RB / WR / TE (pass yards / rush+rec / rec yards). Not cherry-picked after errors.

## Data gaps

- Vegas preseason win totals: NOT AVAILABLE in-repo (no historical futures file). Baseline skipped.
- vegas_win_totals_missing

## Fantasy consensus

Skipped cleanly — no historical consensus ADP/projection archive in-repo for 2019–2025.

## Artifacts

- `data/ops/nfl-phase3-pathA-rerun-20260809/run_stamp.json`
- `data/ops/nfl-phase3-pathA-rerun-20260809/scorecards.json`
- `data/ops/nfl-phase3-pathA-rerun-20260809/pooled.json`
- `data/ops/nfl-phase3-pathA-rerun-20260809/verdict.json`
- Depth packs: `services/model-service/src/services/nfl_season_engine/data/historical/`

## How to re-run

```bash
DATABASE_URL=postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge \
  python scripts/nfl/run_historical_replay_benchmark.py \
    --seasons 2019-2025 --n-sims 40 --package-depth
```

## Explicit non-goals (this pass)

- No Phase 4 full calibration suite beyond reporting replay metrics
- No Decision Engine unlock from coherence alone
- No freezing 2026 baseline
- No team-specific sculpture to improve historical scores
