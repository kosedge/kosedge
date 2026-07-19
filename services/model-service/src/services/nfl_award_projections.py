"""Pure scoring/ranking functions for MVP and Offensive Player of the Year
(OPOY) award projections.

METHODOLOGY (documented here, deliberately, rather than buried in numeric
constants -- this is a judgment call about how to weight real historical
voting patterns, not a formula fit against real vote data):

MVP voting historically rewards, roughly in this order of importance:
  1. Team success. Nearly every real NFL MVP plays for a team that made the
     playoffs, usually with a top-2 conference seed -- team win total (and,
     secondarily, projecting to actually WIN the division rather than just
     sneak into a wildcard spot) is the single strongest real correlate
     with MVP voting, ahead of any individual counting stat.
  2. Being a quarterback. Roughly 4 out of every 5 modern-era (post-1970)
     MVPs are QBs -- the position dominates a team's win/loss outcome more
     than any other and is simply the most "visible" position to voters.
     This is a real, well-documented historical bias in how the award is
     actually given out, not a claim that QBs matter more on the field than
     other positions -- we encode it directly and transparently as
     `MVP_POSITION_PRIOR_WEIGHT` rather than pretend the award is
     position-blind when the real voting record says otherwise.
  3. The player's own counting stats (yards + touchdowns) relative to
     positional peers. Real, and necessary (an MVP case needs a "good
     enough" statistical season), but historically weighted LESS than team
     success and position once a player already clears that bar -- which is
     exactly why an otherwise-qualified non-QB on a great team can still be
     out-scored by a QB on a similarly great team with a merely solid (not
     historically dominant) stat line.

OPOY has no "must be a QB" bias -- it goes to whichever OFFENSIVE player (any
position) had the most individually dominant statistical season. Team
success is still in the OPOY formula (a dominant statistical season racked
up in garbage time on a bad team is a real, historically weaker OPOY case
than the same numbers on a winning team) but weighted lower than for MVP,
and there is no QB prior at all -- an exceptional RB/WR/TE season is scored
on equal footing with a QB's.

None of these weights are fit against a real historical MVP-vote dataset --
that dataset doesn't exist for this exercise, and pretending otherwise would
overstate the rigor here. They are a transparent, documented judgment call
meant to track well-known voting patterns (team success first, QB bias
second, raw stats third for MVP; raw stat dominance first for OPOY), not a
regression-fit ground truth. Treat them as a defensible, inspectable
starting point -- every intermediate term (`team_success_score`,
`stat_composite`) is persisted alongside the final score specifically so the
"why" behind a ranking is never a black box.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

MVP_TEAM_WEIGHT = 0.45
MVP_STAT_WEIGHT = 0.35
MVP_POSITION_PRIOR_WEIGHT = 0.20
assert round(MVP_TEAM_WEIGHT + MVP_STAT_WEIGHT + MVP_POSITION_PRIOR_WEIGHT, 6) == 1.0

OPOY_TEAM_WEIGHT = 0.35
OPOY_STAT_WEIGHT = 0.65
assert round(OPOY_TEAM_WEIGHT + OPOY_STAT_WEIGHT, 6) == 1.0

QB_POSITION_PRIOR = 1.0
NON_QB_POSITION_PRIOR = 0.0

# Minimum projected season volume required to "qualify" as an award
# contender at all -- keeps committee-role backups with a handful of
# garbage-time snaps out of the leaderboard entirely, regardless of how a
# tiny-sample-size percentile happens to shake out (a backup who plays two
# mop-up drives and scores once would otherwise look like a "100th
# percentile" TD-rate outlier). Thresholds are set at roughly half of a
# realistic starter's season pace for that stat.
QB_MIN_PASS_YARDS = 1500.0
RB_MIN_SCRIMMAGE_YARDS = 400.0
WR_MIN_SCRIMMAGE_YARDS = 400.0
TE_MIN_SCRIMMAGE_YARDS = 300.0


def select_primary_starter_per_team_position(
    candidates: Sequence[Dict[str, Any]], *, volume_key: str
) -> List[Dict[str, Any]]:
    """Keeps only ONE candidate per (team, position) -- the one with the
    highest `volume_key` value -- and drops the rest.

    Real MVP/OPOY voting is never split across a team's depth chart: a
    team has exactly one "the" quarterback (or running back, etc.) in the
    conversation for an individual award in a given season, never several
    simultaneously. This is also a real, necessary guardrail against the
    current player-projection baseline occasionally projecting a backup
    (e.g. a clear #2/#3 quarterback) with volume close enough to the
    starter's to otherwise clear `meets_award_volume_threshold` and pollute
    the award pool -- keeping only each team's single highest-volume player
    per position structurally prevents a backup from ever out-competing
    their own team's starter for a nomination, regardless of how close the
    underlying projected volume happens to be.
    """
    best_by_team_position: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for candidate in candidates:
        key = (str(candidate.get("team") or ""), str(candidate.get("position") or "").upper())
        current_best = best_by_team_position.get(key)
        if current_best is None or float(candidate.get(volume_key) or 0.0) > float(current_best.get(volume_key) or 0.0):
            best_by_team_position[key] = candidate
    return list(best_by_team_position.values())


def min_max_normalize(value: float, values: Sequence[float]) -> float:
    """0-1 normalize `value` against the range spanned by `values`. Returns
    0.5 (exactly average) if every value in `values` is identical -- a
    degenerate (zero-width) range carries no ranking information, so this
    avoids a divide-by-zero while still returning a sane, neutral score."""
    if not values:
        return 0.5
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def compute_team_success_score(
    *, expected_wins: float, division_title_prob: float, peer_expected_wins: Sequence[float]
) -> float:
    """0-1 team-success component: mostly the team's projected win total
    (min-max normalized across ALL peer teams passed in -- callers should
    pass every team in the league, not just teams with a qualifying award
    candidate, so this normalization doesn't shift depending on which
    positions happen to have qualifying players in a given season), with a
    real but secondary boost for actually projecting to WIN the division
    (`division_title_prob` is already a probability in [0, 1], so it needs
    no further normalization)."""
    wins_component = min_max_normalize(expected_wins, peer_expected_wins)
    return round(0.7 * wins_component + 0.3 * max(0.0, min(1.0, division_title_prob)), 4)


def compute_stat_composite(
    *,
    total_yards: float,
    total_tds: float,
    peer_total_yards: Sequence[float],
    peer_total_tds: Sequence[float],
) -> float:
    """0-1 composite of a player's projected season yardage and touchdowns,
    each min-max normalized against SAME-POSITION qualifying peers only --
    so a QB's raw passing-yardage scale is never compared directly against a
    WR's receiving-yardage scale. Only each player's standing RELATIVE TO
    their own position group is compared; the resulting [0, 1] scores are
    then comparable ACROSS positions for OPOY, since both are now on a
    common "how dominant was this, for this position" scale."""
    yards_component = min_max_normalize(total_yards, peer_total_yards)
    tds_component = min_max_normalize(total_tds, peer_total_tds)
    return round(0.5 * yards_component + 0.5 * tds_component, 4)


def score_mvp_candidate(*, position: str, team_success_score: float, stat_composite: float) -> float:
    position_prior = QB_POSITION_PRIOR if str(position or "").upper() == "QB" else NON_QB_POSITION_PRIOR
    return round(
        MVP_TEAM_WEIGHT * team_success_score
        + MVP_STAT_WEIGHT * stat_composite
        + MVP_POSITION_PRIOR_WEIGHT * position_prior,
        4,
    )


def score_opoy_candidate(*, team_success_score: float, stat_composite: float) -> float:
    return round(OPOY_TEAM_WEIGHT * team_success_score + OPOY_STAT_WEIGHT * stat_composite, 4)


def meets_award_volume_threshold(
    *, position: str, pass_yards_total: float, rush_yards_total: float, receiving_yards_total: float
) -> bool:
    """Real-volume qualification gate -- see module-level threshold
    constants. Any position outside QB/RB/WR/TE (this model only projects
    offensive skill-position counting stats) never qualifies."""
    position = str(position or "").upper()
    if position == "QB":
        return pass_yards_total >= QB_MIN_PASS_YARDS
    scrimmage_yards = rush_yards_total + receiving_yards_total
    if position == "RB":
        return scrimmage_yards >= RB_MIN_SCRIMMAGE_YARDS
    if position == "WR":
        return scrimmage_yards >= WR_MIN_SCRIMMAGE_YARDS
    if position == "TE":
        return scrimmage_yards >= TE_MIN_SCRIMMAGE_YARDS
    return False


def rank_award_candidates(candidates: Sequence[Dict[str, Any]], *, score_key: str) -> List[Dict[str, Any]]:
    """Pure ranking pass: sorts a list of candidate dicts by `score_key`
    descending and adds a `rank_overall` field (1 = best). Ties are broken
    by `player_key` ascending for deterministic, reproducible output.
    Returns a NEW list of dicts; does not mutate the input."""
    ordered = sorted(
        candidates,
        key=lambda c: (-float(c.get(score_key) or 0.0), str(c.get("player_key") or "")),
    )
    output: List[Dict[str, Any]] = []
    for idx, candidate in enumerate(ordered, start=1):
        enriched = dict(candidate)
        enriched["rank_overall"] = idx
        output.append(enriched)
    return output
