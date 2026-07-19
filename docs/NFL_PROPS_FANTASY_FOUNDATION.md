# NFL Props + Fantasy Foundation

This document defines the enterprise-safe player projection, props, and fantasy layer built on top of the existing NFL game-level simulator and data platform.

## Architecture

- Data platform computes weekly projection features in `nfl_player_projection_features_weekly` using normalized PBP + usage/situational aggregates.
- Identity graph resolves every player row to canonical `player_uid` before downstream joins:
  - `nfl_player_identities` (canonical node)
  - `nfl_player_source_id_map` (source + external id map with confidence, trust flags, first/last seen)
  - `nfl_player_aliases` (name variants + normalized alias + context window)
  - `nfl_player_mapping_events` (resolver version, rule, confidence, status, full audit payload)
  - `nfl_player_mapping_review_queue` (unresolved/conflict/manual-guardrail queue)
  - `nfl_player_mapping_quality_snapshots` (weekly SLA metrics + readiness state)
- Model-service materializes player baseline projections in `nfl_player_projection_baselines` with deterministic bounded math and uncertainty blocks.
- Market ingestion stores player prop snapshots in `nfl_player_prop_market_snapshots`.
- Props model computes projection-vs-market edges into `nfl_player_prop_model_edges`.
- Fantasy transformer writes profile-specific outcomes/ranks/tiers into `nfl_fantasy_weekly_projections`.
- Layer-level ops/readiness audits are persisted in `nfl_projection_audit_runs`.

## Pipeline Tasks

- `src.tasks.pull_nfl_player_prop_market_snapshots(season, week)`
- `src.tasks.materialize_nfl_player_baseline_projections(season, week, model_version)`
- `src.tasks.materialize_nfl_player_box_score_sims(season, week, model_version, replicates)`
- `src.tasks.materialize_nfl_player_season_box_score_sims(season, model_version)`
- `src.tasks.materialize_nfl_player_props_edges(season, week, model_version)`
- `src.tasks.materialize_nfl_fantasy_projections(season, week, model_version)`
- `src.tasks.run_nfl_player_projection_cycle(season, week, model_version, pull_market_snapshots=true)`
- `src.tasks.run_nfl_identity_refresh(season, week, model_version)`
- `src.tasks.apply_nfl_identity_manual_resolutions(limit=200, reviewer="system-weekly-identity-sync")`
- `src.tasks.run_nfl_identity_quality_snapshot(season=None, week=None, source_system=None)`

## API Surfaces

- `GET /nfl/projections/players`
- `GET /nfl/props/board`
- `GET /nfl/fantasy/rankings`
- `GET /nfl/fantasy/draft-rankings`
- `GET /nfl/awards/projections`
- `GET /nfl/ops/projections-readiness`
- `POST /nfl/ops/materialize-player-baselines`
- `POST /nfl/ops/materialize-player-props`
- `POST /nfl/ops/materialize-fantasy`
- `POST /nfl/ops/materialize-fantasy-draft-rankings`
- `POST /nfl/ops/materialize-award-projections`
- `POST /nfl/ops/run-player-cycle`
- `GET /nfl/identity/queue`
- `POST /nfl/identity/queue/{queue_id}/action`
- `POST /nfl/identity/refresh`
- `POST /nfl/identity/manual-reconciliations`
- `POST /nfl/identity/quality-snapshot`
- `GET /nfl/identity/quality/latest`

## Operating Model

### Weekly cadence

1. Run `run_nfl_identity_refresh` for target season/week (this also runs baseline/props/fantasy materialization).
2. Run `apply_nfl_identity_manual_resolutions` for queued guardrail remaps and approved queued mappings.
3. Run `run_nfl_identity_quality_snapshot` and read `GET /nfl/identity/quality/latest`.
4. Run `GET /nfl/ops/projections-readiness` for layer readiness and `GET /health/nfl-production-readiness` for model gate.
5. Publish props/fantasy only when identity + projection gates are in approved states.

### Manual review workflow

1. Query `GET /nfl/identity/queue?queue_status=pending`.
2. For each unresolved/conflict item, approve/reject via `POST /nfl/identity/queue/{queue_id}/action`.
3. Approved actions must include canonical `player_uid` to create a trusted source-id mapping.
4. Re-run `POST /nfl/identity/quality-snapshot` after material queue changes.

### SLA thresholds (publish/no-publish)

- **Identity coverage rate:** target `>= 0.94`; warning below `0.94`; no-publish below `0.90`.
- **High-confidence auto-map rate:** target `>= 0.75`.
- **Unresolved rate:** no-publish above `0.06`.
- **Conflict rate:** no-publish above `0.02`.
- **Source freshness:** warning above 12h since last source-id update.
- **Guardrail policy:** no silent remap of trusted links (`confidence >= 0.95`) without explicit mapping event + queue record.

## Rookie handling + uncertainty

`nfl_player_projection_features_weekly` is derived directly from
`nfl_dp_player_usage_weekly` -- a player with zero usage rows is invisible
to every prop/fantasy projection downstream, with no separate "rookie mode."
Rookies (and any rostered player with no prior-season usage) are seeded
with a real historical draft-tier baseline by the data platform's preseason
bootstrap (see `docs/NFL_DATA_PLATFORM.md#preseason-bootstrap`) so they flow
through this same pipeline unmodified rather than being silently absent.

That baseline carries a real signal (`feature_payload->>'usage_source'` on
`nfl_player_projection_features_weekly`, either `rookie_baseline_v1` or
`preseason_hydrate_v1`/`pbp_aggregation`) into
`services/model-service/src/services/nfl_player_projection_engine.py`'s
`PlayerFeatureInputs.experience_confidence` field. A rookie projected to the
same *mean* as a veteran genuinely carries more outcome uncertainty -- there
is no track record backing the number -- so `experience_confidence` widens
the projection's `_std` fields (never the mean) via `variance_widening`,
visible in each baseline's `uncertainty` block. This directly affects prop
edge sizing (`evaluate_prop_edge`) and floor/ceiling outcome ranges.

## Season-total artifacts (player_regular_season_totals.csv / player_playoff_totals.csv)

The live web app reads two flat CSV artifacts directly off disk (see
`apps/web/lib/nfl-preseason-artifacts.ts`), bundled alongside the team-level
season Monte Carlo output in each `data/ops/nfl-preseason-sim-<season>-<ts>/`
directory: `player_regular_season_totals.csv` and `player_playoff_totals.csv`.
These are generated by `services/data-platform-nfl/src/data_platform_nfl/player_season_totals.py`
and wired into `scripts/nfl/simulate_2026_season.py`, which calls
`generate_and_write_player_season_totals()` fresh into the new bundle's
`out_dir` on every run.

**This used to silently go stale.** Before this fix, `simulate_2026_season.py`
`shutil.copy`'d these two files forward unchanged from whichever prior bundle
happened to have them, with no generator at all -- so they could freeze
indefinitely at an old methodology (`games_projected` was a hardcoded `18`
for every regular-season player and `4` for every playoff player, and
`anytime_td_prob` was left as an unaggregated single-week probability). Do
not reintroduce a copy-forward step here; if this file ever needs to change
again, change the generator, not the bundling script.

**Regular season methodology** (`generate_player_regular_season_totals`):
for every player, sum each real week's `*_mean` projection from
`nfl_player_projection_baselines` (season, week, ..., WHERE `game_id` is
non-empty -- bye weeks leave `game_id` blank on the weekly baseline row, so
this naturally excludes them without any special-casing) into that column's
season total. `games_projected` is a real `COUNT` of those weeks, never a
constant. `anytime_td_prob` is aggregated as `1 - PRODUCT(1 - p_w)` across
real weeks -- the probability of scoring in **at least one** game this
season -- rather than summed (summing per-game probabilities is invalid
above ~2 games since it isn't bounded by 1, and would double up on
information already captured by `rush_tds_total + rec_tds_total`).

**Playoff methodology** (`generate_player_playoff_totals`): there is no real
playoff schedule to project against, so each player's regular-season
per-game average rate is multiplied by their team's real **expected number
of playoff games**, sourced from `scripts/nfl/simulate_2026_season.py`'s
50,000-replicate bracket Monte Carlo (each replicate resolves an exact
`games_played` count per team -- 0 through 4 -- averaged across all
replicates into `expected_playoff_games_by_team`, passed into the
generator). This is a real per-team expectation, not a hardcoded
games-per-team constant. If ever called without that simulator context, the
module falls back to `FALLBACK_EXPECTED_GAMES_GIVEN_APPEARANCE` (`26/14`
games per playoff appearance, derived from the current 14-team bracket's 13
total games / 26 team-game appearances) times the team's `playoff_prob` --
see the docstring in `player_season_totals.py` for the full derivation.

Re-run `python3 scripts/nfl/simulate_2026_season.py` any time the weekly
projection pipeline changes materially -- it always regenerates both CSVs
from current `nfl_player_projection_baselines` data, so there is no separate
"remember to refresh the player files" step.

## Per-game player box-score Monte Carlo engine

Every projection layer above this point (`nfl_player_projection_baselines`,
season totals, fantasy rankings) is built from
`baseline_projection_from_features()` -- a single **deterministic
mean+std per player per week**, with no opponent-specific play-volume
sampling and no correlation between players on the same team. That's
enough for a marginal "what's this player's expected line" number, but not
enough for a real simulated **box score**: it can't answer "if this team
throws the ball a lot in this game, does the QB's attempts AND every one
of his receivers' targets move up together" the way a real game actually
plays out.

`services/model-service/src/services/nfl_player_box_score_simulator.py`
adds that layer. For one real scheduled game, one team's players are
simulated together across N replicates:

1. **Team-level volume anchor** (`TeamVolumeContext`, from
   `compute_team_volume_context()`): each replicate draws one shared
   `total_plays` and `pass_rate` from a Normal distribution centered on
   that team's own **trailing real** `nfl_dp_team_situational_weekly`
   performance (walk-forward safe -- only weeks strictly before the target
   week, falling back to the full prior season when there's no trailing
   data yet). **Design choice, and why:** `nfl_simulator.simulate_nfl_game()`
   (the validated, Vegas-backtested team-level score simulator) only
   models the home/away **score** distribution -- it has no play-count or
   pass-rate concept at all, so there's no real "team pass volume" signal
   to derive from its replicate outputs without inventing an unvalidated
   score-to-plays mapping bolted onto code this project has explicitly
   said not to rewrite. This is "option B" from the original task spec, not
   a hook into `simulate_nfl_game`'s replicate loop -- see the v2 follow-up
   note in the module docstring for what a future full hookup would need
   (an additive, non-breaking change exposing `simulate_nfl_game`'s raw
   per-replicate score/margin arrays).
2. **Player allocation within the replicate** (`simulate_team_player_box_scores()`):
   each player's `baseline_projection_from_features()` output (already
   opponent-adjusted -- see `opponent_pass_defense_factor`/`opponent_rush_defense_factor`
   above) supplies both their mean share of the team's pass/rush pool and
   their mean per-unit efficiency (yards/attempt, catch rate, etc). Shares
   are allocated via a two-layer random draw: a single **shared-concentration
   Dirichlet** across every player in the pool (this is what makes the
   requested team-level coherence work -- every player's allocation for
   that replicate comes from the SAME draw, so a big-volume replicate lifts
   the whole group together) plus an independent, **role-confidence-scaled**
   Gamma multiplier per player (a bell-cow back's share is tighter
   game-to-game than a committee back's, without touching either player's
   mean share). See `_normalize_shares_to_pool()`'s docstring for why
   shares are rescaled to (nearly) exhaust the team's real volume pool
   instead of using each player's raw baseline share unmodified -- this
   also turned out to fix a real accuracy bug, not just enable the
   coherence property (see the backtest report below).
3. **Persistence**: `src.tasks.materialize_nfl_player_box_score_sims(season, week, model_version, replicates)`
   writes one row per player per real game to `nfl_player_game_box_score_sims`
   (`infra/db/032_nfl_player_game_box_score_sims.sql`) -- a `{mean, std,
   p10, p25, p50, p75, p90}` block per stat (`pass_yards_dist`,
   `rush_yards_dist`, `receiving_yards_dist`, `receptions_dist`,
   `total_tds_dist`, `fantasy_points_ppr_dist`, etc.), plus a handful of
   flattened `*_mean` columns for simple indexed queries. This is exactly
   the shape needed to answer "will this WR go over 75 receiving yards
   against this specific defense this week."
4. **Season aggregation**: `src.tasks.materialize_nfl_player_season_box_score_sims(season, model_version)`
   sums real per-game rows into `nfl_player_season_box_score_sims` via
   `aggregate_game_sims_to_season()` -- linearity of expectation for the
   mean (same principle `player_season_totals.py` already uses), extended
   to also carry a real season-level **std** (`sqrt(sum(week_variance))`,
   assuming independence across weeks) since the per-game sim actually
   produces one, unlike a flat per-week point mean.

### Weekly update cadence (keeping projections from freezing at the preseason prior)

`nfl_dp_player_usage_weekly` seeds ALL 18 weeks of a future season with the
SAME flat per-game synthetic value at preseason bootstrap time
(`preseason_hydration.py`) -- a played week gets overwritten with real
`pbp_aggregation` data automatically, but **remaining future weeks stayed
frozen at the original preseason/rookie-baseline snapshot indefinitely**
with no mechanism to incorporate real in-season signal. That's now closed
by `refresh_future_player_usage_from_rolling_real_weeks(season, through_week)`
in `preseason_hydration.py`: once real weeks exist
(`source = 'pbp_aggregation'`, week <= `through_week`), it blends each
player's real in-season per-game rate into every remaining future week
still tagged with a synthetic source (`compute_rolling_blend_weight()`
ramps linearly from 0 at 0 real games to full weight at 4 real games --
`ROLLING_SHRINKAGE_FULL_WEIGHT_GAMES` -- so an early-season role change
doesn't overreact to a 1-game sample, but by week 5 the real signal fully
dominates). Never touches an actual played week; only rewrites still-synthetic
future rows (tagged `rolling_hydrate_v1`). Run this every week right after
that week's real usage lands, before re-materializing
`nfl_player_projection_features_weekly` for the remaining weeks: `python3 -m data_platform_nfl.cli --refresh-rolling-player-usage --through-week <W> --seasons <season>`.

### Backtest verdict

Walk-forward backtested against real 2023-2025 box scores in
`data/ops/nfl-matchup-engine-backtest-report.md` (n=11,453 player-games for
the flat-baseline comparison, n=2,337 for the box-score engine comparison).
**Headline result: the box-score engine fixes a real, previously-undetected
systematic under-projection bias on every receiving-game stat** (receiving
yards MAE improves ~13%, bias magnitude drops ~55%; targets and receptions
improve ~7% and ~18% respectively) -- traced to the flat formula's
per-player target-share terms not summing back to a team's real pass-attempt
total. Passing yards improves modestly (~2%); rushing yards is a small,
honestly-flagged regression (~1% worse for RB, the dominant rushing
position) at the backtest's reduced replicate count (250 vs. the production
default of 2,000) -- see the report's Recommended Follow-Ups for the
suggested next check.

### Running it

```bash
# One real scheduled week, after nfl_player_projection_features_weekly is materialized for it:
python3 -c "from src.tasks import materialize_nfl_player_box_score_sims as m; print(m(season=2026, week=5))"

# Season-to-date aggregation (safe to re-run any time after weekly sims exist):
python3 -c "from src.tasks import materialize_nfl_player_season_box_score_sims as m; print(m(season=2026))"
```

## Season-long fantasy draft rankings

`nfl_fantasy_weekly_projections` / `GET /nfl/fantasy/rankings` only ever
answer "who should I start THIS week" -- keyed by `(season, week, ...)`,
there is no season-aggregate concept at all, so it cannot answer a draft-day
question. `nfl_fantasy_season_draft_rankings` / `GET /nfl/fantasy/draft-rankings`
is the season-long counterpart, materialized by
`src.tasks.materialize_nfl_fantasy_season_draft_rankings(season, model_version)`.

**Season totals**: for every `(team, player_id)` with real QB/RB/WR/TE
weekly rows in `nfl_player_projection_baselines`, SQL
`SUM(...)` adds up each real week's `*_mean` projection into a season total
-- the same per-week-mean-summation math as
`data_platform_nfl.player_season_totals.aggregate_weekly_projection_rows`
(not literally shared code, since model-service has no package dependency
on data-platform-nfl -- these are separate services that only share the
Postgres schema). Grouping is keyed by the real `(team, player_id)` pair,
never by display name -- real 2026 roster data has at least one case (two
different players both named "B.Robinson" on the same team) where grouping
by name alone would have silently merged two distinct players' stats.
Season totals are then fed through the already-canonical
`fantasy_points_from_projection()` once per scoring profile (`standard`,
`half_ppr`, `ppr`).

**Rookie flag**: `is_rookie` / `rookie_year` / `draft_number` come from a
`LEFT JOIN` to `nfl_dp_rosters` on `(season, team, player_id)` -- `is_rookie`
is true exactly when `rookie_year = season`. Rookies are surfaced, not
hidden, since draft-day analysts specifically want to see rookie risk/upside
called out rather than blended anonymously into the board.

**Position rank vs. overall rank -- these answer different questions.**
`rank_position` is the traditional "Nth-best AT THIS POSITION by raw
points" ranking. `rank_overall`, by contrast, is ordered by **Value Over
Replacement (VOR)**, not raw points -- see
`services/model-service/src/services/nfl_fantasy_draft_rankings.py`'s
module docstring for the full rationale, summarized here: standard/half-PPR
scoring gives nearly every real starting QB a high, tightly-clustered point
total (a QB's fantasy floor from passing volume alone is high), while
RB/WR/TE point totals fan out far more widely between an elite starter and
a replacement-level waiver option. Sorting the whole board by raw points
therefore stacks the top of the board with QBs, which is backwards from how
real single-QB drafts actually play out (an elite RB/WR goes round 1; even
a top-5 QB often waits until round 3-6, since a 12-team league only ever
needs ~12 competent QBs and there's rarely a shortage of them). VOR instead
asks "how much better is this player than the free replacement at the same
position", using position-specific replacement ranks for a standard 12-team
single-QB roster (`POSITION_REPLACEMENT_RANK`: QB/TE = 12, RB/WR = 30,
reflecting one dedicated starting slot per team for QB/TE vs. two slots
plus the bulk of the FLEX slot for RB/WR). Both `replacement_points` and
`value_over_replacement` are persisted alongside `total_points` so the
"why" behind the overall ranking is inspectable.

**Draft tiers** (`tier`) are assigned from a fixed, documented
position-rank ladder (`POSITION_TIER_BOUNDARIES` -- e.g. QB: elite/QB1/QB2/
streamer/bench; RB & WR: elite/RB1-WR1/RB2-WR2/flex/bench; TE: elite/TE1/
streamer/bench), not a statistical gap-detection algorithm -- gap detection
is fragile against a single point-total blip between two adjacent ranks,
while a fixed rank-based convention is transparent and reproducible run to
run.

**A known, deliberate defensive gap this data currently has**: at the time
this was built, some teams' backup/depth-chart QBs were projected with
passing volume close enough to their own team's starter that a naive
approach could rank a clear backup above their own starter within the QB
position group. This is not something this ranking layer tries to silently
paper over at the position-rank level for fantasy (backups still show up,
correctly, deep in `rank_position`/`tier` once real per-player point totals
differ at all) -- but it is exactly why the season-long **award**
projections below apply an explicit "one candidate per team per position"
guardrail (see `select_primary_starter_per_team_position`), since an award
leaderboard has much less tolerance for a backup slipping in than a full
908-player draft board does.

### Kicker (K) and Team Defense/Special Teams (DST) projections

QB/RB/WR/TE season totals above come straight from
`nfl_player_projection_baselines`, which by design projects zero offensive
counting stats for every other position -- so K and DST had NO season-long
fantasy projection at all until this section's methodology, despite being a
required starting roster slot in essentially every real standard league
(ESPN/Yahoo/Sleeper defaults all include exactly 1 K and 1 DST). Built by
`services/model-service/src/services/nfl_kicker_dst_projections.py`
(pure scoring/shrinkage functions) plus the `_fetch_kicker_season_players` /
`_fetch_dst_season_players` orchestration in `tasks.py`.

**Scoring convention**: Yahoo's default K/DST scoring (confirmed against
Yahoo's own published default league settings -- identical to ESPN's
default for every stat except a minor difference in the top points-allowed
DST tier). Kicker: FG 0-39yd = 3 pts, FG 40-49yd = 4 pts, FG 50+yd = 5 pts,
PAT made = 1 pt. DST: sack = 1 pt, interception = 2 pts, fumble recovery =
2 pts, defensive/special-teams TD = 6 pts, safety = 2 pts, points allowed
tiered 0=10 / 1-6=7 / 7-13=4 / 14-20=1 / 21-27=0 / 28-34=-1 / 35+=-4. Blocked
kicks (+2 in the Yahoo default) are a deliberate, documented omission --
real blocked kicks are rare enough (well under 1/team/season) that the
omitted value is negligible next to a ~100-140 point season total, and
attributing a block to the correct DEFENSE requires a self-join nflverse
doesn't provide directly.

**Real data sources, not invented**: this required normalizing two NEW
tables from data ALREADY sitting in Postgres (no new external fetch) --
`nfl_dp_kicker_weekly` (real per-kicker FG attempts/makes by nflverse's own
6 real distance buckets + PAT, from `nfl_dp_player_game_stats.metrics` where
`position = 'K'`) and `nfl_dp_team_defense_weekly` (real per-team sacks/
interceptions/fumble recoveries/defensive+special-teams TDs/safeties, from
`nfl_dp_raw_objects.payload` where `object_type = 'team_game_stats'`). Both
were always present in the raw ingested payloads, just never normalized
into typed columns before this feature -- see
`data_platform_nfl.kicking_defense_history` (`--materialize-kicking-
defense-history` CLI flag; safe to re-run any time, call after every
`ingest_nflverse_snapshot`).

**A real pre-existing data gap discovered while building this**:
`nfl_dp_team_game_stats.points_for`/`points_against` are silently `NULL`
for every row in this database -- `nflreadpy.load_team_stats()` has no
points column at all, so the ingest code's `row.get("points_allowed")`
always returned `None`. `nfl_dp_team_defense_weekly.points_allowed` is
instead correctly sourced from the real final score on
`nfl_dp_schedules.home_score`/`away_score`. This pre-existing gap in the
general ingest pipeline was left as-is (out of scope here, and touching the
shared `ingest_nflverse_snapshot` loop carried unnecessary risk) but is
flagged here so it isn't silently rediscovered later.

**Kicker methodology**: `field_goals_by_bucket_mean` = (team's projected
season FG-attempt volume, split across nflverse's 6 real distance buckets
using that team's own real historical bucket-mix) x (that specific kicker's
own real career make rate per bucket, shrunk toward the league-average
bucket rate via empirical-Bayes shrinkage -- `shrink_rate_empirical_bayes`,
10-real-attempt prior strength -- so a kicker with only a handful of career
50+ yard attempts isn't over-trusted on that small a sample; a rookie with
zero history is projected at exactly the league-average rate, no special-
casing needed). Team FG-attempt volume is each team's own real historical
attempts-per-game, adjusted by how far its CURRENT real red-zone-TD rate
(from `nfl_dp_team_situational_latest`, this pipeline's own already-
computed red-zone efficiency signal) sits from league average -- a team
converting red-zone trips to touchdowns LESS often than league average gets
MORE projected FG attempts (stalled drives become field goals), using the
same formula shape/coefficients as `opponent_pass_defense_factor` in
`data_platform_nfl/ingest.py` rather than inventing a second, unvalidated
sensitivity constant. PAT attempts scale off the team's own already-
projected season offensive TD total from `nfl_player_projection_baselines`
(`SUM(pass_tds_mean + rush_tds_mean)` -- deliberately NOT `+ rec_tds_mean`
too, since every real passing TD is thrown by a QB AND caught by a
receiver, and adding all three double-counts the passing share; this was
caught during this feature's own plausibility check, when Nick Folk's
PAT volume implied an unrealistic ~61 offensive TDs for Atlanta instead of
the real, plausible ~48). PAT accuracy uses the real league-average make
rate (>92% league-wide, negligible real kicker-to-kicker skill variance,
unlike FG accuracy) rather than per-kicker shrinkage. One kicker per team is
selected (`_select_primary_kickers_per_team`) by real recent-season FG
attempt volume when a team rosters two K's.

**DST methodology**: sacks/interceptions/fumble recoveries/defensive+
special-teams touchdowns/safeties are each the team's own real historical
per-game rate, shrunk toward league average with a stat-specific prior
strength reflecting how much real year-to-year skill signal that stat
actually carries (`DEFENSE_STAT_SHRINKAGE_PRIOR_GAMES`: points allowed and
sacks shrink the LEAST -- 8-game prior, the most real/repeatable skill;
defensive+special-teams touchdowns shrink the MOST -- 32-game prior,
reflecting the well-known real fantasy fact that DST touchdowns are close
to unpredictable fluky events). Points-allowed additionally gets a real
defensive-strength adjustment from `epa_per_play_defense_allowed`
(`nfl_dp_team_situational_latest`) relative to league average -- again the
same formula/coefficients as `opponent_pass_defense_factor`, reused rather
than invented. Season fantasy points from points-allowed are NOT simply
"tier(mean points allowed)": the Yahoo tier scale is concave/nonlinear, so
tiering the season average systematically misprices a defense with real
game-to-game variance. `expected_points_allowed_fantasy_points_per_game`
instead integrates the tier payoff against a Normal approximation of the
team's real per-game points-allowed distribution (continuity-corrected
Normal CDF via `math.erf`, the same plain-`math` idiom this codebase
already uses in `nfl_simulator.py`/`nfl_player_projection_engine.py`'s own
`_normal_cdf` -- no new scipy/numpy dependency), using a shared league-wide
std (a team-specific variance estimate from ~70 historical games is itself
noisy; real game-to-game points-allowed variance is driven mostly by
opponent/game-script variance, which is fairly consistent across teams).
Every other DST counting stat is linear (no tiering), so a shrunk per-game
rate x real scheduled games is exact in expectation.

**Why K/DST don't wrongly show up as premium picks**: real fantasy drafters
treat K/DST as "wait until the last round or two" -- the position as a
whole has low year-over-year predictability and low variance between the
best and 20th-best option. `nfl_fantasy_draft_rankings.py`'s
`POSITION_REPLACEMENT_RANK` gives K/DST a replacement rank of 12 (the same
"exactly one dedicated leaguewide starting slot per team, never flex-
eligible" logic already used for QB/TE), and -- critically -- this does NOT
need an artificial downward fudge factor on top: because real kicker/DST
season point totals are genuinely tightly clustered (~60-135 points
league-wide, vs. RB/WR spanning 300+ down to near 0), `total_points[rank 1]
- total_points[rank 12]` for K/DST comes out naturally small relative to
RB/WR's spread -- the exact same VOR mechanism the module docstring already
describes for why a high, tightly-clustered QB distribution doesn't
dominate the overall board. K/DST also get their OWN short tier ladder
(`elite`/`K1`-or-`DST1`/`streamer`/`bench`) rather than falling back to the
generic default, so "who's the best AVAILABLE kicker/defense right now" is
still answerable even though the position overall drafts late.

**2026 sanity check** (materialized against real 2026 preseason-hydrated
data): top-5 projected K ranged ~158-170 half-PPR points, top-5 projected
DST ranged ~126-136 -- both within a real, plausible full-season range for
a good K/DST in standard-family scoring, and neither cracks the top ~48
overall picks on the combined board (`rank_overall`), correctly reflecting
the real "wait" convention.

## MVP / Offensive Player of the Year award projections

`nfl_award_projections` / `GET /nfl/awards/projections`, materialized by
`src.tasks.materialize_nfl_award_projections(season, model_version, top_n)`,
projects the top MVP and Offensive Player of the Year (OPOY) contenders from
real projected season stats + real projected team win totals. The full
scoring methodology lives in
`services/model-service/src/services/nfl_award_projections.py`'s module
docstring -- summarized here:

**Team success matters most for MVP.** Nearly every real NFL MVP plays for
a team that made the playoffs, usually with a top-2 conference seed --
`team_success_score` (0.7 &times; min-max-normalized projected win total
across the whole league + 0.3 &times; the team's projected division-title
probability, both sourced from the season Monte Carlo's
`team_regular_season_outcomes.csv`) is weighted `MVP_TEAM_WEIGHT = 0.45`,
the single largest MVP term.

**Being a quarterback is a real, documented historical bias.** Roughly 4 out
of every 5 modern-era MVPs are QBs. This is encoded directly and
transparently as `MVP_POSITION_PRIOR_WEIGHT = 0.20` (full credit for QB,
zero for every other position) rather than hidden -- an exceptional non-QB
season on a great team can still out-score a middling QB season, but a
merely-good QB season on a similarly great team wins the tiebreak, matching
real voting patterns.

**The player's own stats matter, but weighted below team + position for
MVP** (`MVP_STAT_WEIGHT = 0.35`). `stat_composite` blends a player's
projected season yardage and touchdowns (passing + rushing for QBs, rushing
+ receiving for everyone else), each independently min-max normalized
against SAME-POSITION qualifying peers only -- so a QB's raw passing-yardage
scale is never compared directly to a WR's receiving-yardage scale, only
each player's standing relative to their own position group is compared,
which is what makes the resulting `[0, 1]` scores comparable ACROSS
positions for OPOY.

**OPOY has no QB bias at all** -- `OPOY_STAT_WEIGHT = 0.65` /
`OPOY_TEAM_WEIGHT = 0.35`, and any offensive position can win purely on
stat dominance (with team success as a real but secondary tiebreaker,
since a dominant statistical season racked up on a last-place team is a
historically weaker OPOY case than the same numbers on a winning team).

**None of these weights are fit against a real historical MVP-vote
dataset** -- that dataset doesn't exist for this exercise. They are a
transparent, documented judgment call meant to track well-known real voting
patterns, not a regression-fit ground truth -- which is exactly why
`team_success_score` and `stat_composite` (not just the final
`award_score`) are persisted on every row, so the "why" behind a ranking is
inspectable rather than a black box.

**Qualification gates** (`meets_award_volume_threshold`): a player needs
real starter-level projected volume to even be considered (QB: 1,500+
projected pass yards; RB/WR: 400+ projected scrimmage yards; TE: 300+) --
this keeps committee/backup pieces with a handful of garbage-time snaps out
of the pool regardless of how a tiny-sample-size percentile happens to
shake out.

**"One candidate per team per position" guardrail**
(`select_primary_starter_per_team_position`): real MVP/OPOY voting is never
split across a team's depth chart -- a team has exactly one "the"
quarterback (or running back, etc.) in the award conversation in a given
season, never several simultaneously. This is also a necessary defensive
guardrail: the current player-projection baselines occasionally project a
clear backup quarterback with passing volume close enough to the starter's
to otherwise clear `meets_award_volume_threshold` on its own (a real
observed case during validation: a third-string QB projected within ~10% of
his own team's starter's season passing yardage). Keeping only each team's
single highest-volume player per position structurally prevents a backup
from ever out-competing their own team's starter for a nomination,
regardless of how close the underlying projected volume happens to be --
this is the concrete fix for the general failure mode "a backup QB on a bad
team surfaces as an MVP frontrunner", which would indicate a formula bug,
not a valid model output.

**Team win-total source**: there is no DB table for the season Monte
Carlo's team-level output yet (that persistence is owned by the separate
season-simulator workstream) -- `_load_latest_team_season_outcomes` reads
the same `team_regular_season_outcomes.csv` bundle the web app reads (see
`apps/web/lib/nfl-preseason-artifacts.ts`), picking the most recent
`data/ops/nfl-preseason-sim-<season>-<timestamp>/` directory. If no bundle
is found, award materialization is skipped entirely (returns
`status: "skipped"`) rather than fabricating placeholder win totals.

## Data Source Matrix

| Source | Free/Paid | Fields Used | Ingestion Cadence | Reliability / Risk Notes | Implementation Status |
| --- | --- | --- | --- | --- | --- |
| nflverse / nflreadpy | Free (open data, dataset terms apply) | PBP (`load_pbp`), schedules, rosters, injuries, weekly stats | Daily + weekly rebuilds | Broad coverage and reproducible dictionaries; must respect upstream data-owner terms | Integrated now |
| The Odds API (NFL event odds, player props markets) | Free tier + paid quotas | Player prop lines/prices (`player_pass_yds`, `player_rush_yds`, `player_reception_yds`, `player_receptions`, `player_anytime_td`) | Hourly near slate + pre-kickoff refresh | Practical for V1 but quota cost/coverage variance by sportsbook/region | Integrated now |
| ESPN public scoreboard endpoints (unofficial) | Free | Schedule/status fallback and context snapshots | Daily + hourly | Unofficial and undocumented; no SLA, endpoint change risk | Integrated now (fallback context source) |
| SportsDataIO (FantasyData) NFL feeds | Paid | Official depth charts, richer injury status, projections/fantasy metadata, prop/archive feeds | Near real-time + scheduled | Better depth-role confidence and injury freshness than free stack; commercial contract required for full live feeds | Not integrated (recommended paid upgrade) |
| Sportradar Odds Comparison Player Props | Paid (enterprise) | Multi-book player props, mappings, structured change-log feeds | Minute-level polling / change-log driven | Enterprise-grade normalization and bookmaker mapping; contract onboarding required | Not integrated (recommended for production props scale) |
| Stats Perform / Opta | Paid (enterprise) | Advanced player/team context, tracking-derived features, premium betting/fantasy context | Real-time + batched historical | Highest quality for advanced role/usage and proprietary context; expensive and sales-led | Not integrated (recommended for advanced model quality) |

## Paid Gap Analysis (What Is Still Needed)

- Depth chart quality: free rosters/injuries do not consistently provide definitive role ordering near kickoff.
- Injury latency/precision: free feeds are strong but still weaker than official/enterprise injury status updates.
- Props market continuity: free quota and sportsbook coverage can miss low-liquidity or alternate lines.
- Player/entity mapping: robust cross-provider IDs are needed for long-term enterprise reconciliation and audit.

## Recommended Paid Adoption Order

1. SportsDataIO for depth-chart + injury + fantasy operational hardening.
2. Sportradar player props for market coverage normalization and change-log driven updates.
3. Stats Perform/Opta only when premium tracking-driven features are required for model edge expansion.
