"""Minimum viable scoring bridge: production → points → W/L honesty.

Phase-1 contract: yards/TDs are not a parallel fantasy universe. This module
documents an explicit, inspectable conversion from team season (or game)
production into offensive points.

v1.27: FG/XP via scoped ``kicker_layer`` (coarse bands + XP) replaces the
proportional 22% stub. Full ST / return markets remain out of scope.

v1.19: published season-total PF/PA/W/L close-the-loop lives in
``data_platform_nfl.defensive_production_stack`` (offense → PF → schedule
PA → Pythagorean wins = 272). Game-level path W/L still comes from
realized scores in ``game_script`` / ``season_sim`` (zero-sum).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from src.services.nfl_season_engine.kicker_layer import (
    GAMES_PER_TEAM_SEASON,
    kicking_points_for_season_production,
    kicker_layer_documentation,
    team_kicker_profile,
)

# Points attribution (offensive skill production).
POINTS_PER_PASS_YARD = 0.04  # ~25 yards / point → 1 point per 25 pass yards
POINTS_PER_RUSH_YARD = 0.10
POINTS_PER_REC_YARD = 0.10
POINTS_PER_PASS_TD = 6.0
POINTS_PER_RUSH_TD = 6.0
POINTS_PER_REC_TD = 6.0
POINTS_PER_INT = -2.0
# Legacy stub share retained for docs / A-B only; production path uses kicker_layer.
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
    team: str = "",
    games: float = GAMES_PER_TEAM_SEASON,
    outdoor_adverse: bool = False,
    use_legacy_fg_stub: bool = False,
) -> Dict[str, float]:
    """Convert box / season production into an offensive points estimate.

    When ``include_fg_stub`` is True (default), FG/XP come from the scoped
    kicker layer unless ``use_legacy_fg_stub`` forces the old proportional fill.
    """
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

    points_from_fg = 0.0
    points_from_xp = 0.0
    fg_extras = 0.0
    fg_att = 0.0
    fg_made = 0.0
    xp_att = 0.0
    xp_made = 0.0

    if include_fg_stub:
        if use_legacy_fg_stub:
            fg_extras = skill * (
                FG_EXTRAS_POINT_SHARE / max(1e-6, 1.0 - FG_EXTRAS_POINT_SHARE)
            )
            points_from_fg = fg_extras
        else:
            # Team offensive TDs for XP: pass + rush (rec_tds double-count pass).
            offensive_tds = float(pass_tds) + float(rush_tds)
            if offensive_tds <= 0 and float(rec_tds) > 0:
                offensive_tds = float(rec_tds)
            profile = team_kicker_profile(team or "LEAGUE")
            kick = kicking_points_for_season_production(
                team=team or "LEAGUE",
                offensive_tds=offensive_tds,
                games=games,
                profile=profile,
                outdoor_adverse=outdoor_adverse,
            )
            points_from_fg = float(kick["points_from_fg"])
            points_from_xp = float(kick["points_from_xp"])
            fg_extras = points_from_fg + points_from_xp
            fg_att = float(kick["fg_att"])
            fg_made = float(kick["fg_made"])
            xp_att = float(kick["xp_att"])
            xp_made = float(kick["xp_made"])

    total = skill + fg_extras
    return {
        "points_from_yards": round(from_yards, 3),
        "points_from_tds": round(from_tds, 3),
        "points_from_turnovers": round(from_turnovers, 3),
        "points_from_fg": round(points_from_fg, 3),
        "points_from_xp": round(points_from_xp, 3),
        # Backward-compatible alias (now real FG+XP, not proportional magic).
        "points_from_fg_extras_stub": round(fg_extras, 3),
        "fg_att": round(fg_att, 3),
        "fg_made": round(fg_made, 3),
        "xp_att": round(xp_att, 3),
        "xp_made": round(xp_made, 3),
        "offensive_points": round(total, 3),
    }


def team_season_points_from_player_totals(
    player_totals: Mapping[str, Mapping[str, Any]],
    team: str,
    *,
    games: float = GAMES_PER_TEAM_SEASON,
    outdoor_adverse: bool = False,
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
    # Rec TDs are already in pass TDs at team level — omit from TD point sum.
    return production_to_offensive_points(
        pass_yards=pass_y,
        rush_yards=rush_y,
        rec_yards=0.0,
        pass_tds=pass_td,
        rush_tds=rush_td,
        rec_tds=0.0,
        ints=ints,
        include_fg_stub=True,
        team=team,
        games=games,
        outdoor_adverse=outdoor_adverse,
    )


def wins_zero_sum_ok(mean_wins_sum: float, *, expected: float = 272.0, tol: float = 0.05) -> bool:
    return abs(float(mean_wins_sum) - float(expected)) <= float(tol)


def scoring_bridge_documentation() -> Dict[str, Any]:
    kick_docs = kicker_layer_documentation()
    return {
        "version": "scoring_bridge_v2_kicker_layer",
        "status": "approximate_kicker_layer",
        "points_per_pass_yard": POINTS_PER_PASS_YARD,
        "points_per_rush_yard": POINTS_PER_RUSH_YARD,
        "points_per_td": POINTS_PER_PASS_TD,
        "fg_extras_point_share_legacy": FG_EXTRAS_POINT_SHARE,
        "kicker_layer": kick_docs,
        "notes": (
            "Game W/L from realized Layer-2 scores (zero-sum). "
            "This bridge reconciles season production → offensive points for "
            "diagnostics; FG/XP come from the scoped approximate kicker layer "
            "(coarse bands + XP), not a full ST market."
        ),
    }
