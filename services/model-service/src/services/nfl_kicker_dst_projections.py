"""Pure scoring/projection functions for season-long Kicker (K) and Team
Defense/Special Teams (DST) fantasy projections.

WHY THIS EXISTS
----------------
`nfl_player_projection_baselines` -- the source every other position's
season-long draft total is summed from (see
`nfl_fantasy_draft_rankings.py`'s module docstring) -- by design projects
zero offensive counting stats for every position outside QB/RB/WR/TE, so K
and DST have never had a season-long fantasy projection at all despite being
a required starting roster slot in essentially every real standard league
(ESPN/Yahoo/Sleeper defaults all include exactly 1 K and 1 DST). This module
is the real, data-driven fix for that gap.

SCORING CONVENTION
-------------------
Yahoo's default K/DST scoring (confirmed against Yahoo's own published
default settings, https://help.yahoo.com/kb/default-league-settings-fantasy-
football-sln6489.html -- identical to ESPN's default for every stat except a
minor difference in the 35+-points-allowed DST tier, where ESPN splits
35-45/46+ and Yahoo uses one flat 35+ tier):

  Kicker: FG 0-19/20-29/30-39 = 3 pts, FG 40-49 = 4 pts, FG 50+ = 5 pts,
  PAT made = 1 pt.

  DST: sack = 1 pt, interception = 2 pts, fumble recovery = 2 pts,
  defensive/special-teams TD = 6 pts, safety = 2 pts. Points-allowed is
  TIERED (not linear): 0 = 10 pts, 1-6 = 7, 7-13 = 4, 14-20 = 1, 21-27 = 0,
  28-34 = -1, 35+ = -4.

  Blocked-kick scoring (+2 pts in the Yahoo default) is deliberately NOT
  modeled here: real blocked kicks are extremely rare (league-wide well
  under 1 per team per season), so the maximum possible omitted value is on
  the order of ~2 fantasy points across an entire 17-game season --
  negligible next to a ~100-140 point season total and not worth the added
  real-data plumbing (nflverse's team-level blocked-kick counts are
  OFFENSE-side "our kick got blocked", requiring a self-join to the
  opponent's row to attribute the block to the blocking DEFENSE) for this
  scope.

DATA SOURCES (real, not invented)
-----------------------------------
  - `nfl_dp_kicker_weekly` / `nfl_dp_team_defense_weekly` (see
    `data_platform_nfl.kicking_defense_history`) -- real per-kicker FG
    attempts/makes by nflverse's own 6 distance buckets + PAT, and real
    per-team sacks/interceptions/fumble recoveries/defensive+special-teams
    TDs/safeties, normalized from nflreadpy's `load_player_stats()` /
    `load_team_stats()` (both already-ingested, no new external fetch).
  - `nfl_dp_schedules.home_score`/`away_score` for real points allowed
    (NOT `nfl_dp_team_game_stats.points_against`, which is silently NULL for
    every row in this database -- `load_team_stats()` has no points column
    at all, a real pre-existing gap discovered while building this feature;
    see docs/NFL_PROPS_FANTASY_FOUNDATION.md).
  - `nfl_dp_team_situational_weekly.red_zone_td_rate` -- this pipeline's own
    already-computed red-zone scoring efficiency, used to adjust each team's
    projected field-goal-attempt VOLUME (a team whose red zone trips stall
    into field goals more often than league average should generate MORE FG
    attempts for its kicker, holding overall scoring-volume history fixed).

METHODOLOGY
------------
Kicker: `field_goals_by_bucket_mean` = (team's own projected FG attempts,
split across nflverse's 6 real distance buckets using that team's own real
historical bucket-mix) x (that specific kicker's own real historical make
rate per bucket, shrunk toward the league-average bucket rate --
`shrink_rate_empirical_bayes` -- so a kicker with only a handful of career
50+ yard attempts isn't over-trusted on that small a sample). PAT attempts
scale with the team's own already-projected season offensive TD total (from
`nfl_player_projection_baselines`, the SAME real projection every other
position's season total is built from), not a separately-invented number.

DST: points-allowed fantasy points are NOT simply "tier(mean points
allowed)" -- the Yahoo tier scale is concave/nonlinear, so tiering the mean
systematically misprices a defense with real game-to-game variance (a
defense that allows exactly 21 every week scores worse in this tier system
than one that alternates between 7 and 35, even though both average 21).
`expected_points_allowed_fantasy_points` instead integrates the tier payoff
against a Normal approximation of the team's real per-game points-allowed
distribution (mean shrunk toward league average per `shrink_rate_...`, real
std from historical variance) -- the same "model the distribution, don't
just tier the point estimate" instinct this codebase applies everywhere else
via Monte Carlo (see `nfl_simulator.py`, box-score sim), done here
analytically via the Normal CDF since points-allowed tiering only needs
per-tier probability mass, not full replicate paths.

Sacks/interceptions/fumble recoveries/defensive TDs/safeties are scored
LINEARLY (no tiering), so a per-game rate x games-in-season is exact in
expectation -- no distributional modeling needed there. Each is shrunk
toward league average with its OWN prior-games strength, reflecting how
predictable that specific counting stat really is year to year: points
allowed and sacks are the most real-skill-driven and get the lightest
shrinkage; defensive/special-teams touchdowns are famously fluky
(low-frequency, largely opportunistic events) and get the heaviest --
this is also exactly why DST as a POSITION is a "wait until the last
round" position in real drafts (see `nfl_fantasy_draft_rankings.py`'s
`POSITION_TIER_BOUNDARIES`/`POSITION_REPLACEMENT_RANK` for where that shows
up in the draft-value math, not just here in the raw point projection).
"""

from __future__ import annotations

import math
from typing import Dict, Sequence, Tuple

FG_BUCKETS: Tuple[str, ...] = ("0_19", "20_29", "30_39", "40_49", "50_59", "60_plus")

FG_BUCKET_POINTS: Dict[str, float] = {
    "0_19": 3.0,
    "20_29": 3.0,
    "30_39": 3.0,
    "40_49": 4.0,
    "50_59": 5.0,
    "60_plus": 5.0,
}

PAT_POINTS = 1.0

# Pseudo-attempts of "league average" prior weight blended into every
# kicker's own real career bucket make-rate. 10 real attempts is roughly a
# season's worth of makes+misses in the busiest buckets (0-39) and several
# seasons' worth in the rarest (60+), so this shrinks the thin-sample buckets
# hard while barely moving a kicker's well-established short-range accuracy.
KICKER_ACCURACY_SHRINKAGE_PRIOR_ATTEMPTS = 10.0

# Pseudo-attempts of league-average prior blended into each team's own real
# historical FG-attempt distance-mix (bucket SHARE of total attempts, not
# accuracy) -- lighter than the kicker-accuracy prior since a full team
# (not one kicker) generates the sample, so even a few seasons of real games
# already carries a meaningful attempt count per bucket.
TEAM_FG_BUCKET_SHARE_SHRINKAGE_PRIOR_ATTEMPTS = 20.0

# Real 2026 NFL regular season length (17 games/team over an 18-week
# schedule with one bye), matching the games-per-season convention already
# used elsewhere in this codebase (e.g. `FALLBACK_EXPECTED_GAMES_GIVEN_APPEARANCE`
# in player_season_totals.py).
GAMES_PER_REGULAR_SEASON = 17.0

# Sensitivity of a team's projected FG-attempt volume to how far its real
# red-zone-TD rate sits from league average -- a team 10 points below league
# average red-zone TD rate (i.e. stalling into more field goals) gets its FG
# volume scaled up by 10% x this sensitivity. Deliberately the SAME
# coefficient (1.15) and clamp range ([0.75, 1.30]) already used by
# `opponent_pass_defense_factor` in data_platform_nfl/ingest.py for the
# analogous "how far is this real efficiency rate from league average"
# adjustment -- reused for architectural consistency rather than inventing a
# second, unvalidated sensitivity constant for the same kind of adjustment.
FG_VOLUME_REDZONE_SENSITIVITY = 1.15
FG_VOLUME_ADJUSTMENT_CLAMP = (0.75, 1.30)

# DST defensive-strength adjustment to a team's own historical points-
# allowed baseline, from real EPA-per-play-allowed vs. league average --
# same formula/coefficient/clamp as `opponent_pass_defense_factor` above,
# for the same "don't invent a second team-strength number" reason.
DST_DEFENSE_STRENGTH_SENSITIVITY = 1.15
DST_DEFENSE_STRENGTH_CLAMP = (0.75, 1.30)

# DST linear per-event scoring (Yahoo default).
DST_SACK_POINTS = 1.0
DST_INTERCEPTION_POINTS = 2.0
DST_FUMBLE_RECOVERY_POINTS = 2.0
DST_TOUCHDOWN_POINTS = 6.0
DST_SAFETY_POINTS = 2.0

# DST points-allowed-per-game tiers (Yahoo default): (min_pts, max_pts_or_None, fantasy_points).
DST_POINTS_ALLOWED_TIERS: Tuple[Tuple[int, "int | None", float], ...] = (
    (0, 0, 10.0),
    (1, 6, 7.0),
    (7, 13, 4.0),
    (14, 20, 1.0),
    (21, 27, 0.0),
    (28, 34, -1.0),
    (35, None, -4.0),
)

# Empirical-Bayes shrinkage prior strength (in real games) for each DST
# counting stat, reflecting how much real year-to-year skill signal that
# specific stat actually carries -- points allowed and sacks are the most
# real/repeatable, defensive+special-teams touchdowns are the least (a
# handful of fluky pick-sixes/scoop-and-scores), matching the well-known real
# fantasy convention that DST touchdowns are close to unpredictable.
DEFENSE_STAT_SHRINKAGE_PRIOR_GAMES: Dict[str, float] = {
    "points_allowed": 8.0,
    "sacks": 8.0,
    "interceptions": 12.0,
    "fumble_recoveries": 12.0,
    "defensive_tds": 32.0,
    "safeties": 48.0,
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def shrink_rate_empirical_bayes(*, sample_makes: float, sample_attempts: float, league_rate: float, prior_attempts: float) -> float:
    """Empirical-Bayes shrinkage of a real per-attempt rate toward a
    league-average rate: `(makes + prior_attempts * league_rate) /
    (attempts + prior_attempts)`. At `sample_attempts = 0` this returns
    exactly `league_rate` (a rookie/thin-sample kicker or team is
    projected at the league-average rate with no special-casing needed);
    as `sample_attempts` grows large relative to `prior_attempts`, it
    converges to the real observed rate."""
    if prior_attempts < 0:
        raise ValueError("prior_attempts must be >= 0")
    denominator = sample_attempts + prior_attempts
    if denominator <= 0:
        return league_rate
    return (sample_makes + prior_attempts * league_rate) / denominator


def project_team_fg_attempt_volume(
    *,
    team_fg_attempts_per_game_history: float,
    team_red_zone_td_rate: float,
    league_avg_red_zone_td_rate: float,
    games: float = GAMES_PER_REGULAR_SEASON,
) -> float:
    """Projects a team's season-total field-goal ATTEMPT volume (before any
    kicker-specific accuracy is applied) from that team's own real historical
    FG-attempts-per-game rate, adjusted by how much more/less often its real
    red-zone trips are currently converting to touchdowns than league
    average. A red-zone TD rate BELOW league average means more red-zone
    trips are stalling into field-goal attempts instead, so this scales FG
    volume UP in that case (and down for a red-zone-efficient team) -- see
    module docstring for why this reuses the existing
    `opponent_pass_defense_factor` formula shape/coefficients."""
    redzone_gap = league_avg_red_zone_td_rate - team_red_zone_td_rate
    adjustment = _clamp(1.0 + FG_VOLUME_REDZONE_SENSITIVITY * redzone_gap, *FG_VOLUME_ADJUSTMENT_CLAMP)
    return max(0.0, team_fg_attempts_per_game_history) * adjustment * games


def allocate_attempts_to_buckets(
    *, total_attempts: float, team_bucket_makes: Dict[str, float], team_bucket_attempts: Dict[str, float], league_bucket_shares: Dict[str, float]
) -> Dict[str, float]:
    """Splits `total_attempts` across `FG_BUCKETS` using this team's own
    real historical bucket-attempt SHARE (what fraction of this team's real
    FG attempts have fallen in each distance bucket), shrunk toward the
    league-average bucket-share distribution for teams with a thin
    historical attempt sample. `team_bucket_makes` is unused for the share
    computation (attempts, not makes, define a team's distance-mix) but
    accepted for signature symmetry with the kicker-accuracy shrinkage
    call site; kept explicit rather than silently ignored via **kwargs."""
    del team_bucket_makes
    team_total_attempts = sum(team_bucket_attempts.values())
    shares: Dict[str, float] = {}
    for bucket in FG_BUCKETS:
        league_share = league_bucket_shares.get(bucket, 1.0 / len(FG_BUCKETS))
        shrunk_share = shrink_rate_empirical_bayes(
            sample_makes=team_bucket_attempts.get(bucket, 0.0),
            sample_attempts=team_total_attempts,
            league_rate=league_share,
            prior_attempts=TEAM_FG_BUCKET_SHARE_SHRINKAGE_PRIOR_ATTEMPTS,
        )
        shares[bucket] = shrunk_share
    share_total = sum(shares.values())
    if share_total <= 0:
        return {bucket: total_attempts / len(FG_BUCKETS) for bucket in FG_BUCKETS}
    return {bucket: total_attempts * (share / share_total) for bucket, share in shares.items()}


def project_kicker_fg_makes_by_bucket(
    *,
    team_attempts_by_bucket: Dict[str, float],
    kicker_career_makes_by_bucket: Dict[str, float],
    kicker_career_attempts_by_bucket: Dict[str, float],
    league_make_rate_by_bucket: Dict[str, float],
) -> Dict[str, float]:
    """For each distance bucket, projects real expected FG MAKES as
    `team_attempts_by_bucket[bucket] * shrunk_kicker_make_rate[bucket]` --
    the real, data-driven `field_goals_by_bucket_mean` this feature is named
    for in the task spec."""
    makes: Dict[str, float] = {}
    for bucket in FG_BUCKETS:
        league_rate = league_make_rate_by_bucket.get(bucket, 0.0)
        shrunk_rate = shrink_rate_empirical_bayes(
            sample_makes=kicker_career_makes_by_bucket.get(bucket, 0.0),
            sample_attempts=kicker_career_attempts_by_bucket.get(bucket, 0.0),
            league_rate=league_rate,
            prior_attempts=KICKER_ACCURACY_SHRINKAGE_PRIOR_ATTEMPTS,
        )
        makes[bucket] = team_attempts_by_bucket.get(bucket, 0.0) * _clamp(shrunk_rate, 0.0, 1.0)
    return makes


def fantasy_points_from_field_goals(fg_makes_by_bucket: Dict[str, float]) -> float:
    return round(sum(fg_makes_by_bucket.get(bucket, 0.0) * FG_BUCKET_POINTS[bucket] for bucket in FG_BUCKETS), 4)


def project_pat_makes(*, team_offensive_tds_season: float, two_point_attempt_rate: float, league_pat_make_rate: float) -> float:
    """PAT attempts scale directly with the team's own already-projected
    season offensive touchdown total (from `nfl_player_projection_baselines`
    -- the SAME real projection every other position's season total is
    built from), minus the real observed share of touchdowns that go for a
    2-point conversion attempt instead of a kick. PAT accuracy is
    league-average for every kicker -- real make rates cluster extremely
    tightly (>92% league-wide) with negligible real kicker-to-kicker skill
    variance, unlike field-goal accuracy, so no per-kicker shrinkage is
    applied here."""
    pat_attempts = max(0.0, team_offensive_tds_season) * max(0.0, 1.0 - two_point_attempt_rate)
    return pat_attempts * _clamp(league_pat_make_rate, 0.0, 1.0)


def compute_kicker_season_fantasy_points(*, fg_makes_by_bucket: Dict[str, float], pat_makes: float) -> float:
    return round(fantasy_points_from_field_goals(fg_makes_by_bucket) + pat_makes * PAT_POINTS, 4)


def normal_cdf(x: float, *, mean: float, std: float) -> float:
    """Standard Normal CDF via `math.erf` (no scipy/numpy dependency, matching
    the plain-`math` style used throughout `nfl_simulator.py`/
    `nfl_player_projection_engine.py`). Degenerates to a step function at
    `std <= 0` (a "distribution" with zero variance is just the mean)."""
    if std <= 0:
        return 1.0 if x >= mean else 0.0
    return 0.5 * (1.0 + math.erf((x - mean) / (std * math.sqrt(2.0))))


def expected_points_allowed_fantasy_points_per_game(*, mean_points_allowed: float, std_points_allowed: float) -> float:
    """Expected DST fantasy points from the points-allowed tier scale for
    ONE game, given a Normal(`mean_points_allowed`, `std_points_allowed`)
    approximation of that team's real per-game points-allowed distribution.
    Integrates the (concave, tiered) payoff against the distribution instead
    of naively tiering the mean -- see module docstring for why that
    distinction matters here. Uses a continuity-corrected discrete Normal
    (tier boundaries evaluated at `n + 0.5`) since points allowed are real
    whole-number scores."""
    total = 0.0
    for lo, hi, points in DST_POINTS_ALLOWED_TIERS:
        lower_bound = normal_cdf(lo - 0.5, mean=mean_points_allowed, std=std_points_allowed)
        upper_bound = 1.0 if hi is None else normal_cdf(hi + 0.5, mean=mean_points_allowed, std=std_points_allowed)
        probability_mass = max(0.0, upper_bound - lower_bound)
        total += probability_mass * points
    return total


def shrink_defense_stat_per_game(*, stat_name: str, team_total: float, team_games: float, league_avg_per_game: float) -> float:
    """Shrinks a team's real historical per-game rate for `stat_name`
    (must be a key of `DEFENSE_STAT_SHRINKAGE_PRIOR_GAMES`) toward the
    league-average per-game rate, using that stat's own documented prior
    strength -- see module docstring / `DEFENSE_STAT_SHRINKAGE_PRIOR_GAMES`
    for why different DST counting stats get different shrinkage strength."""
    prior_games = DEFENSE_STAT_SHRINKAGE_PRIOR_GAMES[stat_name]
    return shrink_rate_empirical_bayes(
        sample_makes=team_total,
        sample_attempts=team_games,
        league_rate=league_avg_per_game,
        prior_attempts=prior_games,
    )


def project_team_points_allowed_mean(
    *, team_points_allowed_per_game_history: float, team_epa_per_play_defense_allowed: float, league_avg_epa_per_play_defense_allowed: float
) -> float:
    """Adjusts a team's shrunk historical points-allowed-per-game baseline
    by this pipeline's own already-computed defensive EPA-per-play-allowed
    signal relative to league average -- see module docstring for why this
    reuses `opponent_pass_defense_factor`'s exact formula shape/coefficients
    rather than inventing a second team-strength number from scratch."""
    epa_gap = team_epa_per_play_defense_allowed - league_avg_epa_per_play_defense_allowed
    adjustment = _clamp(1.0 + DST_DEFENSE_STRENGTH_SENSITIVITY * epa_gap, *DST_DEFENSE_STRENGTH_CLAMP)
    return max(0.0, team_points_allowed_per_game_history) * adjustment


def compute_dst_season_fantasy_points(
    *,
    points_allowed_mean_per_game: float,
    points_allowed_std_per_game: float,
    sacks_per_game: float,
    interceptions_per_game: float,
    fumble_recoveries_per_game: float,
    defensive_tds_per_game: float,
    safeties_per_game: float,
    games: float = GAMES_PER_REGULAR_SEASON,
) -> Dict[str, float]:
    """Full season DST fantasy point projection, returning every
    intermediate per-game-rate x points term alongside the total (same
    "persist the why, not just the final number" convention as
    `nfl_award_projections.py`'s `team_success_score`/`stat_composite`)."""
    points_allowed_component = expected_points_allowed_fantasy_points_per_game(
        mean_points_allowed=points_allowed_mean_per_game, std_points_allowed=points_allowed_std_per_game
    ) * games
    sacks_component = sacks_per_game * DST_SACK_POINTS * games
    interceptions_component = interceptions_per_game * DST_INTERCEPTION_POINTS * games
    fumble_recoveries_component = fumble_recoveries_per_game * DST_FUMBLE_RECOVERY_POINTS * games
    touchdowns_component = defensive_tds_per_game * DST_TOUCHDOWN_POINTS * games
    safeties_component = safeties_per_game * DST_SAFETY_POINTS * games
    total = (
        points_allowed_component
        + sacks_component
        + interceptions_component
        + fumble_recoveries_component
        + touchdowns_component
        + safeties_component
    )
    return {
        "points_allowed_component": round(points_allowed_component, 4),
        "sacks_component": round(sacks_component, 4),
        "interceptions_component": round(interceptions_component, 4),
        "fumble_recoveries_component": round(fumble_recoveries_component, 4),
        "touchdowns_component": round(touchdowns_component, 4),
        "safeties_component": round(safeties_component, 4),
        "total_points": round(total, 4),
    }


def mean(values: Sequence[float]) -> float:
    values = [v for v in values if v is not None]
    if not values:
        return 0.0
    return sum(values) / len(values)
