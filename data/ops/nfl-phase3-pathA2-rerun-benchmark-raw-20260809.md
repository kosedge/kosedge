# NFL Phase 3 — Historical Replay & Benchmark Gate (2026-08-09)

**Engine stamp:** `nfl-season-engine-v1.26-phase3-pathA2-usage-prior`  
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
| 2019 | 2.366 / -0.000 / 0.426 | 2.383 / 0.000 / 0.391 | 2.420 / 0.204 / 0.532 | n/a | REG-3957c69a1ae2 |
| 2020 | 2.815 / 0.000 / 0.553 | 2.730 / -0.062 / 0.442 | 3.009 / 0.219 / 0.486 | n/a | REG-4bac4215d1ac |
| 2021 | 2.040 / -0.000 / 0.525 | 1.906 / -0.312 / 0.577 | 1.886 / -0.227 / 0.561 | n/a | REG-428af923e646 |
| 2022 | 2.488 / -0.000 / 0.216 | 2.594 / 0.031 / 0.166 | 2.997 / -0.119 / 0.267 | n/a | REG-5898cc7482d0 |
| 2023 | 1.775 / -0.000 / 0.557 | 2.065 / -0.031 / 0.413 | 2.350 / -0.099 / 0.409 | n/a | REG-c31a97fec281 |
| 2024 | 3.195 / -0.000 / 0.239 | 2.875 / 0.000 / 0.349 | 3.215 / 0.026 / 0.260 | n/a | REG-30b943729db3 |
| 2025 | 2.925 / 0.000 / 0.109 | 2.688 / 0.000 / 0.304 | 3.188 / -0.160 / 0.256 | n/a | 901-52999c5efafc |

## Pooled (equal team-weight via n)

| Metric | MAE / bias / ρ |
| --- | --- |
| model wins | 2.515 / -0.000 / 0.375 |
| prior-year+regression wins | 2.463 / -0.054 / 0.378 |
| epa_power wins | 2.723 / -0.022 / 0.396 |
| vegas wins | nan / nan / nan |
| model PF | 54.720 / -3.232 / 0.435 |
| model PA | 45.637 / -3.232 / 0.213 |
| model team pass yards | 373.704 / -92.277 / 0.468 |
| model team rush yards | 272.166 / -102.236 / 0.351 |
| model player pass yards | 781.812 / 31.858 / 0.659 |
| model player rush yards | 199.842 / 57.597 / 0.692 |
| model player rec yards | 238.870 / 154.830 / 0.503 |

## Where we add value vs where we do not

**Earned (pre-registered MAE wins or produced honest scorecards):**
- team_wins vs epa_power
- player_pass_yards scorecard produced (n=472)
- player_rush_yards scorecard produced (n=1051)
- player_rec_yards scorecard produced (n=1699)

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

- `data/ops/nfl-phase3-pathA2-rerun-20260809/run_stamp.json`
- `data/ops/nfl-phase3-pathA2-rerun-20260809/scorecards.json`
- `data/ops/nfl-phase3-pathA2-rerun-20260809/pooled.json`
- `data/ops/nfl-phase3-pathA2-rerun-20260809/verdict.json`
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
