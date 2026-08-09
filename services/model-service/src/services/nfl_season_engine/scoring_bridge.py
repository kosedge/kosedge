"""Minimum viable scoring bridge: production → points → W/L honesty.

Phase-1 contract: yards/TDs are not a parallel fantasy universe. This module
documents an explicit, inspectable conversion from team season (or game)
production into offensive points. Full FG/special-teams markets remain
approximate stubs.

Game-level W/L already comes from realized scores in ``game_script`` /
``season_sim`` (zero-sum: one winner per game). This bridge is for
diagnostics and season-total reconciliation — it does **not** replace
path scores.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

# Points attribution (offensive skill production).
POINTS_PER_PASS_YARD = 0.04  # ~25 yards / point → 1 point per 25 pass yards
POINTS_PER_RUSH_YARD = 0.10
POINTS_PER_REC_YARD = 0.10
POINTS_PER_PASS_TD = 6.0
POINTS_PER_RUSH_TD = 6.0
POINTS_PER_REC_TD = 6.0
POINTS_PER_INT = -2.0
# FG / extras stub: share of team points not from offensive TDs/yards.
FG_EXTRAS_POINT_SHARE = 0.22
# Typical offensive points when using yard+TD bridge before FG fill.
TARGET_OFFENSIVE_PPG = 21.8


def production_to_offensive_points(
    *,
    pass_yards: float = 0.0,
    rush_yards: float = 0.0,
    rec_yards: float = 0.0,
    pass_tds: float = 0.0,
    rush_tds: float = 0.0,
    rec_tds: float = 0.0,
    ints: float = 0.0,
    include_fg_stub: bool = True,
) -> Dict[str, float]:
    """Convert box / season production into an offensive points estimate."""
    from_yards = (
        float(pass_yards) * POINTS_PER_PASS_YARD
        + float(rush_yards) * POINTS_PER_RUSH_YARD
        # rec yards overlap pass yards for team offense — count rush + pass only
        # at team level. When called for skill players, callers should pass
        # team aggregates with rec_yards=0 for team scoring.
        + float(rec_yards) * POINTS_PER_REC_YARD
    )
    from_tds = (
        float(pass_tds) * POINTS_PER_PASS_TD
        + float(rush_tds) * POINTS_PER_RUSH_TD
        + float(rec_tds) * POINTS_PER_REC_TD
    )
    from_turnovers = float(ints) * POINTS_PER_INT
    skill = max(0.0, from_yards + from_tds + from_turnovers)
    fg_extras = 0.0
    if include_fg_stub:
        # Fill toward a league-ish PPG band without inventing a full FG model.
        fg_extras = skill * (FG_EXTRAS_POINT_SHARE / max(1e-6, 1.0 - FG_EXTRAS_POINT_SHARE))
    total = skill + fg_extras
    return {
        "points_from_yards": round(from_yards, 3),
        "points_from_tds": round(from_tds, 3),
        "points_from_turnovers": round(from_turnovers, 3),
        "points_from_fg_extras_stub": round(fg_extras, 3),
        "offensive_points": round(total, 3),
    }


def team_season_points_from_player_totals(
    player_totals: Mapping[str, Mapping[str, Any]],
    team: str,
) -> Dict[str, float]:
    """Aggregate named player production for one team → points bridge."""
    pass_y = rush_y = pass_td = rush_td = rec_td = ints = 0.0
    for row in player_totals.values():
        if str(row.get("team") or "") != team:
            continue
        pass_y += float(row.get("pass_yards") or 0.0)
        rush_y += float(row.get("rush_yards") or 0.0)
        pass_td += float(row.get("pass_tds") or 0.0)
        rush_td += float(row.get("rush_tds") or 0.0)
        rec_td += float(row.get("rec_tds") or 0.0)
        ints += float(row.get("ints") or 0.0)
    # Team scoring: pass yards already embed aerial offense; do not double-count rec yards.
    return production_to_offensive_points(
        pass_yards=pass_y,
        rush_yards=rush_y,
        rec_yards=0.0,
        pass_tds=pass_td,
        rush_tds=rush_td,
        rec_tds=rec_td,
        ints=ints,
        include_fg_stub=True,
    )


def wins_zero_sum_ok(mean_wins_sum: float, *, expected: float = 272.0, tol: float = 0.05) -> bool:
    return abs(float(mean_wins_sum) - float(expected)) <= float(tol)


def scoring_bridge_documentation() -> Dict[str, Any]:
    return {
        "version": "scoring_bridge_v1",
        "status": "approximate_fg_stub",
        "points_per_pass_yard": POINTS_PER_PASS_YARD,
        "points_per_rush_yard": POINTS_PER_RUSH_YARD,
        "points_per_td": POINTS_PER_PASS_TD,
        "fg_extras_point_share": FG_EXTRAS_POINT_SHARE,
        "notes": (
            "Game W/L from realized Layer-2 scores (zero-sum). "
            "This bridge reconciles season production → offensive points for "
            "diagnostics; FG/XP/special teams are a proportional stub, not a "
            "calibrated kicking market."
        ),
    }
