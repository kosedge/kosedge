"""Scoped NFL kicker / FG / XP layer — scoring bridge + game boxes."""

from __future__ import annotations

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_demo_universe,
    project_game_player_boxes,
)
from src.services.nfl_season_engine.calibration import ENGINE_VERSION as CAL_VERSION
from src.services.nfl_season_engine.kicker_layer import (
    LEAGUE_FG_ATTEMPTS_PER_TEAM_GAME,
    LEAGUE_TEAMS,
    GAMES_PER_TEAM_SEASON,
    league_fg_volume_sanity,
    project_game_kicking,
    script_fg_attempt_multiplier,
    team_kicker_profile,
)
from src.services.nfl_season_engine.scoring_bridge import production_to_offensive_points


def test_engine_version_includes_kicker_layer() -> None:
    assert CAL_VERSION == DEFAULT_SEASON_ENGINE_VERSION
    assert "kicker-layer" in CAL_VERSION
    assert CAL_VERSION.startswith("nfl-season-engine-v1.27")


def test_scoring_with_fg_exceeds_td_only_path() -> None:
    td_only = production_to_offensive_points(
        pass_yards=3800,
        rush_yards=1800,
        pass_tds=24,
        rush_tds=12,
        ints=10,
        include_fg_stub=False,
        team="KC",
    )
    with_kick = production_to_offensive_points(
        pass_yards=3800,
        rush_yards=1800,
        pass_tds=24,
        rush_tds=12,
        ints=10,
        include_fg_stub=True,
        team="KC",
    )
    assert with_kick["offensive_points"] > td_only["offensive_points"]
    assert with_kick["points_from_fg"] > 0
    assert with_kick["points_from_xp"] > 0
    assert with_kick["fg_att"] > 0
    assert with_kick["fg_made"] > 0


def test_zero_fg_league_fails_sanity() -> None:
    zero = league_fg_volume_sanity([0.0] * LEAGUE_TEAMS)
    assert zero["ok"] is False
    assert zero["zero_fg_fail"] is True

    healthy = league_fg_volume_sanity(
        [LEAGUE_FG_ATTEMPTS_PER_TEAM_GAME * GAMES_PER_TEAM_SEASON] * LEAGUE_TEAMS
    )
    assert healthy["ok"] is True
    assert healthy["zero_fg_fail"] is False


def test_script_lead_increases_fg_attempts() -> None:
    lead = script_fg_attempt_multiplier(script_detail="large_lead", time_bucket="late")
    deficit = script_fg_attempt_multiplier(
        script_detail="large_deficit", time_bucket="late"
    )
    assert lead > deficit


def test_dome_improves_long_make_vs_adverse_outdoor() -> None:
    dome = project_game_kicking(
        team="DET",
        offensive_tds=2.5,
        outdoor_adverse=False,
    )
    outdoor = project_game_kicking(
        team="BUF",
        offensive_tds=2.5,
        outdoor_adverse=True,
    )
    assert dome["fg_made_by_band"]["long"] > outdoor["fg_made_by_band"]["long"]


def test_game_boxes_include_kicking_lines() -> None:
    universe = build_demo_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=40,
        seed=11,
        use_cache=False,
    )
    assert "kicker-layer" in proj.engine_version
    assert proj.kicking
    assert proj.kicking["home"]["fg_att"] > 0
    assert proj.kicking["away"]["fg_att"] > 0
    assert proj.kicking["home"]["fg_made"] > 0
    assert proj.kicking["home"]["xp_att"] > 0
    assert proj.kicking["home"]["xp_made"] > 0
    assert proj.kicking["team_points"]["home"]["points_from_fg"] > 0
    assert proj.kicking["team_points"]["home"]["points_from_kicking"] > 0
    home_td = float(proj.kicking["team_points"]["home"]["points_from_skill_tds"])
    home_kick = float(proj.kicking["team_points"]["home"]["points_from_kicking"])
    assert (
        proj.kicking["team_points"]["home"]["points_skill_tds_plus_kicking"]
        > home_td
    )
    assert home_kick > 0
    assert proj.notes.get("fg_display") == "mean_fg_xp_low_depth_estimate"
    assert proj.notes.get("depth_label") == "low-depth estimate"


def test_defaults_and_fg_display_share_research_depth_gate() -> None:
    """Game Boxes default ≥2k; FG honesty notes use the same precision gate."""
    from src.services.nfl_season_engine.sim_depth import (
        default_n_game_box,
        default_n_survivor_paths,
        depth_meta,
        is_honest_precision,
    )

    assert default_n_game_box() >= 2000
    assert default_n_survivor_paths() >= 2000
    meta = depth_meta(default_n_game_box(), surface="game_boxes")
    assert meta["honest_precision"] is True
    assert meta["depth_label"] == "research depth"
    assert is_honest_precision(2000)
    assert (
        "mean_fg_xp_research_depth"
        if is_honest_precision(2000)
        else "mean_fg_xp_low_depth_estimate"
    ) == "mean_fg_xp_research_depth"
    assert (
        "mean_fg_xp_research_depth"
        if is_honest_precision(50)
        else "mean_fg_xp_low_depth_estimate"
    ) == "mean_fg_xp_low_depth_estimate"


def test_anonymous_kicker_when_no_depth_k() -> None:
    profile = team_kicker_profile("KC", roles=[])
    assert profile.kicker_name == ""
    assert profile.source == "league_prior"
