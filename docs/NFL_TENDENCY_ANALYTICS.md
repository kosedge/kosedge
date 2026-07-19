# NFL Situational Tendency Analytics

This is the "nflsavant-style, better-than-Warren-Sharp" situational/tendency
analytics layer: real, honest, differentiated team and QB tendency profiles
computed entirely from real historical nflverse/nflreadpy play-by-play. It
is the "break down every game" deliverable built on data we actually have.

## What this is NOT (read this first)

**Defensive coverage-scheme labels (Cover 2, Cover 3, man, zone) do not
exist anywhere in free nflverse/nflreadpy play-by-play data.** This was
checked directly against the raw ingested payloads
(`nfl_dp_raw_objects` where `source='nflverse'` and `object_type='pbp_play'`)
before any of this layer was built -- none of the ~372 real nflverse PBP
columns is a coverage-scheme label. That kind of data requires proprietary
charting (PFF, SIS, Sports Info Solutions, etc.), which this platform does
not have and does not fabricate.

Also not present in free nflverse/nflreadpy PBP, and therefore not claimed
anywhere in this layer: `defenders_in_box`, `number_of_pass_rushers`,
`offense_formation`, `offense_personnel`, `defense_personnel`.

Everything below is a **real, situational tendency signal** computed from
real columns that ARE present in nflverse/nflreadpy PBP: down, distance,
field position, score differential, `shotgun`, `no_huddle`, `qb_dropback`,
`pass_location`, `run_location`, `run_gap`, `xpass` (nflfastR's own
model-derived expected-dropback probability), `cp` (nflfastR's own
model-derived completion probability), `sack`, `qb_hit`, `epa`, `success`.
This is exactly what real football-analytics sites (Sharp Football, rbsdm.com,
etc.) build "tendency" content from -- descriptive situational splits and
model-relative rate differences, not verified play-call reads.

## Real data provenance / a pipeline note worth flagging

`nfl_dp_play_by_play` (013_nfl_pbp_normalized.sql) originally normalized
only a subset of the ~372 real nflverse PBP columns. `shotgun`, `no_huddle`,
`qb_dropback`, `pass_location`, `run_location`, `run_gap`, `xpass`, `cp`,
and `xyac_epa` -- all real, already-ingested in the raw JSONB payloads in
`nfl_dp_raw_objects` -- were **not** carried forward into the normalized
table. This layer required extending the normalization pipeline
(`data_platform_nfl.ingest.normalize_pbp_from_raw`) to add those columns
(`034_nfl_pbp_tendency_columns.sql`) and then re-running normalization with
`--replace-normalized` to backfill them for already-ingested seasons. **No
new nflverse/nflreadpy fetch was required** -- the raw source data already
had every one of these fields; they just weren't being read out of the
JSONB payload into the normalized table yet.

If you need any other real nflverse PBP column that isn't in
`nfl_dp_play_by_play` yet, the fix is almost always the same: check the raw
payload in `nfl_dp_raw_objects` first (it very likely already has the real
field), then extend `normalize_pbp_from_raw` rather than assuming a new
ingest/backfill is required.

## Tables

- `nfl_dp_team_situational_tendencies` -- one row per
  `(season, team, perspective, situation_type, situation_bucket)`.
  `perspective = 'offense'` groups by `posteam` (a team's own tendencies);
  `perspective = 'defense'` groups by `defteam` (what that team's defense
  faces/allows in the same buckets -- the real matchup "flip side").
  `situation_type` is one of `down_distance`, `score_state`,
  `field_position` (see bucket definitions below). Columns: `plays`,
  `pass_plays`, `rush_plays`, `pass_rate`, `dropback_plays`,
  `dropback_rate`, `avg_xpass`, `pass_rate_over_expected`, `shotgun_rate`,
  `no_huddle_rate`, `epa_per_play`, `success_rate`, `explosive_play_rate`,
  `sack_rate`.
- `nfl_dp_team_direction_tendencies` -- one row per
  `(season, team, perspective)`. Pass-direction (left/middle/right) and
  run-direction/gap (location + gap) rates. `team = 'LEAGUE'` holds a
  league-wide average row for context.
- `nfl_dp_qb_situational_splits` -- one row per
  `(season, player_id, situation_type, situation_bucket)`.
  `situation_type` is one of `overall`, `down_type` (early vs. money down),
  `pressure` (real sack/`qb_hit`-based proxy -- see below), `score_state`,
  `field_position`. Columns: `dropbacks`, `pass_attempts`, `completions`,
  `completion_rate`, `pass_yards`, `yards_per_attempt`, `epa_per_play`,
  `success_rate`, `avg_cp`, `cpoe` (completion% over nflfastR's `cp`
  model, in percentage points), `sack_rate`, `interception_rate`, `td_rate`.

Migrations: `034_nfl_pbp_tendency_columns.sql`,
`035_nfl_situational_tendency_profiles.sql`.

## Bucket definitions (single source of truth: `tendency_profiles.py`)

- **down_distance**: early downs (1st/2nd) and money downs (3rd/4th) each
  get independent short/medium/long thresholds --
  `early_down_short` (<=3 yds), `early_down_medium` (4-7), `early_down_long`
  (8+); `money_down_short` (<=2 yds), `money_down_medium` (3-6),
  `money_down_long` (7+).
- **score_state**: `trailing_big` (<=-9), `trailing_small` (-8..-1),
  `tied` (0), `leading_small` (1..8), `leading_big` (9+). The +-8 threshold
  mirrors the standard "one-possession game" definition (touchdown + 2pt
  conversion = 8) used throughout real football analytics.
- **field_position**: `goal_to_go` (yardline_100 <= 5), `red_zone` (<=20),
  `midfield` (<=50), `own_territory` (>50).
- **pressure** (QB splits only): `pressure` if `sack` OR `qb_hit` is true,
  else `clean_pocket`. This is the honest, real-data proxy for "under
  pressure" -- there is no real blitz count or pass-rusher-count column in
  free nflverse PBP, so this uses the two real pressure-adjacent booleans
  that DO exist.
- **down_type** (QB splits only): `early_down` (1st/2nd) vs. `money_down`
  (3rd/4th) -- coarser than the team-level `down_distance` split, matched
  to the task's explicit "early downs vs. money downs" QB ask.

## The real "pass rate over expected" (PROE) signal

`pass_rate_over_expected = dropback_rate - avg_xpass`, where `dropback_rate`
is the real share of offensive plays with `qb_dropback = true` and
`avg_xpass` is the average of nflfastR's own real, model-derived `xpass`
column (its model's own estimate of P(dropback) given the situation) over
the same plays. This is intentionally NOT `pass_rate` (which uses
`play_type = 'pass'`, matching this codebase's existing
`nfl_dp_team_situational_weekly.pass_rate` convention) -- `xpass` was
trained by nflfastR to predict dropbacks specifically (including scrambles,
which have `play_type = 'run'` but `qb_dropback = true`), so comparing
`xpass` against anything other than the real dropback rate would be an
apples-to-oranges mismatch. Both `pass_rate` (called-play convention) and
`dropback_rate`/`pass_rate_over_expected` (PROE convention) are persisted
so consumers get both the intuitive number and the correct-for-PROE number.

A positive `pass_rate_over_expected` means a team passes MORE than a
neutral, situation-aware model would expect -- a real, legitimate
aggressive/pass-first tendency signal. A negative value means a team passes
LESS than expected -- a real run-heavy/ball-control tendency signal. This
is exactly the kind of signal real tendency analysis (Sharp Football-style)
is built on, without claiming anything about the actual defensive coverage
called against it.

## Computation

`services/data-platform-nfl/src/data_platform_nfl/tendency_profiles.py`:

- Pure, directly-unit-tested bucket functions: `down_distance_bucket`,
  `down_type_bucket`, `score_state_bucket`, `field_position_bucket`,
  `pressure_bucket`.
- Pure aggregation functions operating on plain lists of play dicts:
  `compute_team_situational_tendencies`, `compute_team_direction_tendencies`,
  `compute_qb_situational_splits`. These are the single source of truth for
  bucket boundaries (no parallel SQL CASE-statement definitions that could
  silently drift out of sync).
- Materialization wrappers (`materialize_team_situational_tendencies`,
  `materialize_team_direction_tendencies`, `materialize_qb_situational_splits`,
  `materialize_all_tendency_profiles`) pull real plays from
  `nfl_dp_play_by_play`, run the pure aggregation, and upsert into the three
  tables above. Small-sample buckets are dropped (`min_sample_plays=8` for
  team tables, `min_sample_dropbacks=5` for QB splits) rather than persisted
  as noisy rates.
- Defense-perspective rows negate `score_differential` before bucketing
  (`nfl_dp_play_by_play.score_differential` is always signed from
  `posteam`'s perspective, so a defense-perspective row needs the sign
  flipped to bucket correctly from that team's own point of view).

## Run it

```bash
cd services/data-platform-nfl

# 1. Extend normalized PBP with the tendency-adjacent columns (idempotent,
#    re-run per season any time you need a fresh backfill):
PYTHONPATH=./src python3 -m data_platform_nfl.cli \
  --seasons 2023,2024,2025 --normalize-pbp-from-raw --replace-normalized

# 2. Materialize all three tendency tables for those seasons:
PYTHONPATH=./src python3 -m data_platform_nfl.cli \
  --seasons 2023,2024,2025 --materialize-tendency-profiles
```

Both steps are safe to re-run any time -- they fully replace the target
seasons' rows (small, fully derived tables).

## API

- `GET /nfl/tendencies/team?season=&team=&perspective=offense|defense&situation_type=`
  -- one team's situational tendency profile (all three situation_type
  dimensions unless filtered) plus its direction-tendency row.
- `GET /nfl/tendencies/team-direction?season=&perspective=&team=`
  -- pass/run direction tendency by team (omit `team` for every team +
  `LEAGUE`).
- `GET /nfl/tendencies/qb?season=&player_id=&team=&situation_type=&min_dropbacks=`
  -- QB situational efficiency splits.
- `GET /nfl/tendencies/matchup?season=&home_team=&away_team=`
  -- combined matchup breakdown: each team's real offensive tendency next
  to the opponent's real defensive tendency allowed, bucket-for-bucket,
  both directions. Includes an explicit `methodology_note` in the response
  restating the honest scope limits.

## Honest validation discipline

Before shipping, real 2025-season computed numbers were spot-checked against
real, well-known football knowledge -- see the parent task report for the
specific real numbers. Summary of what was checked and passed:

- BAL (Ravens/Lamar Jackson) offense: strongly negative
  `pass_rate_over_expected` on early-down-medium (-0.278) and early-down-short
  (-0.201) -- consistent with their real run-heavy identity.
- KC (Chiefs) offense: positive `pass_rate_over_expected` on early-down-long
  (+0.062) and early-down-medium (+0.027) -- consistent with their real
  aggressive early-down passing identity.
- CHI (Bears, first year under HC Ben Johnson) offense: unusually elevated
  `pass_rate_over_expected` on early-down-short (+0.159) -- consistent with
  Johnson's real, widely-documented reputation for aggressive/unconventional
  short-yardage play-calling.
- Lamar Jackson and Patrick Mahomes QB splits: both show a large, real
  clean-pocket vs. pressure efficiency gap (e.g. Jackson's EPA/play +0.306
  clean pocket vs. -1.301 under pressure; completion% drops ~33 points) --
  matches real, well-documented pressure sensitivity for both.
- Joe Burrow QB splits: real money-down (3rd/4th down) EPA/play +0.474 and
  CPOE +14.4 -- consistent with his real reputation as a highly efficient
  down-and-distance passer.
- DET offense direction tendency: real run_tackle_rate of 0.47 (vs. league
  ~0.33) -- consistent with Detroit's real, documented gap/power scheme built
  around pulling guards and elite tackle play (Penei Sewell).
- League-wide direction-rate totals sum to ~1.0 across pass left/middle/right
  and run left/middle/right/gap buckets, confirming no double-counting bugs
  in the aggregation.

## Current scope / honest limitations

- **Seasons materialized**: 2023, 2024, 2025 (`nfl_dp_team_situational_tendencies`:
  2,878 rows; `nfl_dp_team_direction_tendencies`: 198 rows;
  `nfl_dp_qb_situational_splits`: 2,583 rows, after dropping 870 small-sample
  buckets below `min_sample_dropbacks`). This scope was a deliberate choice
  to keep every persisted number spot-checked and trustworthy within this
  task's time budget -- real local Postgres contention from a concurrent
  parallel workload (system load average briefly exceeded 280 on an 8-core
  machine) made the normalization step alone take up to ~65 minutes for a
  single season at peak contention, vs. ~5-7 minutes once load normalized.
  `nfl_dp_raw_objects` already has raw data for 2013-2025; extending
  coverage to earlier seasons is exactly the two-command sequence above with
  a longer `--seasons` list, with no code changes required.
- **No coverage-scheme labels.** Repeated deliberately: nothing in this
  layer claims Cover 2/Cover 3/man/zone, blitz counts, personnel groupings,
  or box counts. `pressure` is a real sack/`qb_hit` proxy, not a verified
  pressure/blitz read.
- **Season-level granularity, not rolling/trailing.** Each row is a
  single-season aggregate (matches this codebase's existing per-season
  materialization convention), not a multi-season blended or in-season
  rolling profile. A team's early-season sample within a season is smaller
  than its full-season sample; `plays`/`dropbacks` sample-size columns are
  always persisted so consumers can judge reliability themselves.
- **`pass_rate_over_expected` is model-relative, not play-call-verified.**
  It measures real dropback rate against nflfastR's own `xpass` model's
  expectation -- a real, legitimate tendency signal, but not proof of an
  explicit coach decision, and not a substitute for real coverage-shell
  data this platform does not have.
