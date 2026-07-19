"""Pure ranking/tiering functions for SEASON-LONG fantasy draft rankings.

`nfl_fantasy_weekly_projections` (see nfl_player_projection_engine.py's
`fantasy_points_from_projection` and tasks.py's
`materialize_nfl_fantasy_projections`) answers "who should I start THIS
week" -- it has no season-aggregate concept. Draft-day fantasy analysis
needs the opposite question answered: "who should I draft for the WHOLE
season". This module owns only the pure, side-effect-free ranking and
tiering logic for that -- the season-total counting stats themselves are
summed by the caller (`materialize_nfl_fantasy_season_draft_rankings` in
tasks.py) directly from `nfl_player_projection_baselines` via SQL `SUM(...)`
across every real week (same per-week-mean-summation math used by
`data_platform_nfl.player_season_totals.aggregate_weekly_projection_rows`,
not literally shared code since model-service has no dependency on the
data-platform-nfl package -- these are separate services that only share
the Postgres schema), and fantasy points are computed from those season
totals via the already-canonical `fantasy_points_from_projection()`.

WHY OVERALL RANK USES VALUE OVER REPLACEMENT (VOR), NOT RAW POINTS
--------------------------------------------------------------------
Sorting the whole board by raw season fantasy points is a well-known
beginner mistake for single-QB leagues: standard/half-PPR scoring (~1 pt per
25 pass yards + 4 pts/passing TD) gives basically every real starting QB a
high, tightly-clustered point total, while RB/WR/TE point totals fan out
much more widely between an elite RB1 and a replacement-level waiver option.
A raw-points sort therefore stacks the ENTIRE top of the board with QBs
(even mediocre ones), which is exactly backwards from how real single-QB
drafts play out -- there, an elite RB/WR goes in round 1 and even a top-5 QB
often waits until round 3-6, because a 12-team single-QB league only ever
needs 12-ish competent QBs and there's rarely a shortage of them, whereas
elite RB/WR production is scarce and irreplaceable.

Value Over Replacement fixes this by asking "how much better is this player
than the player I could otherwise get for free off the waiver wire at the
same position", which is the actual question a draft decision answers.
`POSITION_REPLACEMENT_RANK` sets, for each position, WHICH positional rank
counts as "replacement level" in a standard 12-team single-QB roster
(1 QB, 2 RB, 2 WR, 1 TE, 1 RB/WR/TE flex):
  - QB and TE get exactly one dedicated leaguewide starting slot per team
    (12 total) -- flex is almost never filled by a QB, and rarely by a TE.
  - RB and WR each get two dedicated slots per team (24 total) PLUS the
    large majority of the FLEX slot in practice, approximated here as 30
    (24 dedicated + roughly half the 12 flex slots each, since RB/WR
    dominate flex usage over TE in real leagues).
This is a standard, widely-used approximation (sometimes called "the
RB30/WR30 rule") for 12-team single-QB PPR/half-PPR formats -- not a
precise optimization, but a real, transparent convention, not an arbitrary
one.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

# Draft-tier bucket boundaries per position, expressed as the maximum
# *position rank* (1-indexed, inclusive) that still belongs to each tier
# label. These mirror the loose, real conventions fantasy analysts publish
# on draft boards (an "elite" tier of the top few players at a position,
# then a "starter-quality" (RB1/WR1/QB1) tier, then a "solid backup /
# streaming" tier, then bench/waiver-wire filler) -- simplified to a fixed
# rank-based cut rather than a statistical gap-detection algorithm, since
# gap detection is fragile against a single point-total blip between two
# adjacent ranks while a fixed convention is transparent and reproducible.
# Positions not listed fall back to DEFAULT_TIER_BOUNDARIES.
POSITION_TIER_BOUNDARIES: Dict[str, List[Tuple[int, str]]] = {
    "QB": [(3, "elite"), (8, "QB1"), (16, "QB2"), (24, "streamer"), (10_000, "bench")],
    "RB": [(3, "elite"), (12, "RB1"), (24, "RB2"), (36, "flex"), (10_000, "bench")],
    "WR": [(3, "elite"), (12, "WR1"), (24, "WR2"), (36, "flex"), (10_000, "bench")],
    "TE": [(3, "elite"), (8, "TE1"), (16, "streamer"), (10_000, "bench")],
    # K/DST get their OWN, shorter tier ladder rather than falling back to
    # DEFAULT_TIER_BOUNDARIES -- real drafters still want to know "who's the
    # best available kicker/defense right now" even though the position as a
    # WHOLE is famously "wait until the last round or two" (see
    # POSITION_REPLACEMENT_RANK below for where that real dynamic actually
    # gets enforced -- tiers alone don't fix a naive same-scale VOR).
    "K": [(3, "elite"), (12, "K1"), (24, "streamer"), (10_000, "bench")],
    "DST": [(3, "elite"), (12, "DST1"), (24, "streamer"), (10_000, "bench")],
}
DEFAULT_TIER_BOUNDARIES: List[Tuple[int, str]] = [(12, "starter"), (10_000, "bench")]

# See module docstring's "WHY OVERALL RANK USES VALUE OVER REPLACEMENT"
# section for the derivation of these numbers. K/DST keep replacement rank
# 12 (informational only -- see DST_KICKER_APPENDED_TO_BOARD_END below for
# why their OVERALL rank is no longer driven by this VOR math at all).
POSITION_REPLACEMENT_RANK: Dict[str, int] = {"QB": 12, "TE": 12, "RB": 30, "WR": 30, "K": 12, "DST": 12}

# Real bug found by checking the VOR math end-to-end against real-world ADP
# behavior, not just trusting the theoretical formula: at ANY replacement
# rank tested (1 through 24), realistic 2026 K/DST point projections still
# landed the top kicker/DST somewhere in overall picks ~60-90 -- nowhere
# close to where every real standard-league ADP dataset (Yahoo/ESPN/
# Sleeper/FantasyPros) actually drafts them (the LAST one or two rounds,
# typically pick 150+ of a 180-192-pick, 12-team, 15-16-round draft).
# Root cause: raising K/DST's replacement rank to reflect their real
# in-season streamability (bye-week/matchup streaming keeps a decent K/DST
# available off waivers most weeks, unlike RB/WR) doesn't actually help --
# a real, honest check of the skill-position pool shows 828 of 908 real
# non-K/DST players ALREADY sit at VOR <= 0 (deep bench/waiver-tier skill
# players), so no replacement-rank choice for K/DST cleanly separates them
# from that same deep bench on a single shared VOR scale; K/DST would
# always land somewhere inside that 828-player pile rather than below all
# of it, no matter how their own replacement rank is tuned. This is a real,
# well-documented limitation of naive position-agnostic VOR (not specific
# to this codebase) -- which is exactly why every real fantasy site solves
# it the same way this constant now does: K/DST get moved to the bottom of
# the overall board as a fixed positional convention, not left to compete
# on the same VOR scale as skill positions. `rank_season_fantasy_players`
# uses this to sort K/DST strictly after every other position in the
# overall order, while still preserving real, meaningful position-level
# rank/tier/VOR for "who's the best AVAILABLE kicker/DST right now" within
# that bottom tier.
POSITIONS_APPENDED_TO_BOARD_END: Tuple[str, ...] = ("K", "DST")
DEFAULT_REPLACEMENT_RANK = 24


def assign_draft_tier(position: str, position_rank: int) -> str:
    """Given a player's rank WITHIN their own position (1 = best at that
    position), return the draft-tier label for that position. Falls back to
    DEFAULT_TIER_BOUNDARIES for any position (K/DST/etc.) without a bespoke
    tier ladder defined above."""
    boundaries = POSITION_TIER_BOUNDARIES.get(str(position or "").upper(), DEFAULT_TIER_BOUNDARIES)
    for max_rank, label in boundaries:
        if position_rank <= max_rank:
            return label
    return boundaries[-1][1]


def compute_replacement_level_points(points_sorted_desc: Sequence[float], position: str) -> float:
    """`points_sorted_desc` must already be sorted descending for this
    position's full player pool. Returns the points total of the player
    sitting at that position's replacement rank (see
    `POSITION_REPLACEMENT_RANK`) -- or the worst available player's points
    if the pool is shallower than the replacement rank (there IS no
    cheaper replacement available in that case, so the last player in the
    pool defines the floor)."""
    if not points_sorted_desc:
        return 0.0
    rank = POSITION_REPLACEMENT_RANK.get(str(position or "").upper(), DEFAULT_REPLACEMENT_RANK)
    idx = min(rank, len(points_sorted_desc)) - 1
    return points_sorted_desc[idx]


def compute_value_over_replacement(total_points: float, replacement_points: float) -> float:
    return round(total_points - replacement_points, 4)


def rank_season_fantasy_players(players: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pure ranking pass over a list of player dicts (each must include
    `player_key`, `position`, and `total_points`; every other key is passed
    through unchanged). Returns a NEW list of dicts (does not mutate the
    input) with `rank_position`, `tier`, `replacement_points`,
    `value_over_replacement`, and `rank_overall` added to each.

    `rank_position` is the traditional "Nth-best at this position by raw
    points" ranking. `rank_overall` is instead ordered by
    `value_over_replacement` (see module docstring) -- the realistic
    draft-value ordering across positions.

    Ties are broken by `player_key` ascending so output order is
    deterministic given the same input -- this matters because ranks are
    persisted, and a non-deterministic tie-break would make re-running the
    materializer produce spurious rank churn for players with identical
    projected point totals.
    """
    players_by_position: Dict[str, List[Dict[str, Any]]] = {}
    for player in players:
        position = str(player.get("position") or "UNK").upper()
        players_by_position.setdefault(position, []).append(dict(player))

    for position, group in players_by_position.items():
        group.sort(key=lambda p: (-float(p.get("total_points") or 0.0), str(p.get("player_key") or "")))
        points_sorted_desc = [float(p.get("total_points") or 0.0) for p in group]
        replacement_points = compute_replacement_level_points(points_sorted_desc, position)
        for position_rank, player in enumerate(group, start=1):
            player["rank_position"] = position_rank
            player["tier"] = assign_draft_tier(position, position_rank)
            player["replacement_points"] = round(replacement_points, 4)
            player["value_over_replacement"] = compute_value_over_replacement(
                float(player.get("total_points") or 0.0), replacement_points
            )

    all_players = [player for group in players_by_position.values() for player in group]
    # See POSITIONS_APPENDED_TO_BOARD_END's docstring: K/DST are sorted
    # after every other position regardless of their own VOR (a real,
    # documented positional convention every real ADP dataset follows, not
    # a VOR tuning problem), then by VOR within that bottom tier so "best
    # available K/DST right now" is still meaningful.
    board_end_positions = {p.upper() for p in POSITIONS_APPENDED_TO_BOARD_END}
    overall_ordered = sorted(
        all_players,
        key=lambda p: (
            str(p.get("position") or "").upper() in board_end_positions,
            -float(p.get("value_over_replacement") or 0.0),
            str(p.get("player_key") or ""),
        ),
    )
    for overall_idx, player in enumerate(overall_ordered, start=1):
        player["rank_overall"] = overall_idx
    return overall_ordered
