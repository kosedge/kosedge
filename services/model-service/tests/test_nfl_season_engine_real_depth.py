"""Real 2026 depth-chart cutover tests (v1.9.1)."""

from __future__ import annotations

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    build_packaged_real_universe,
    load_packaged_depth_chart,
    project_game_player_boxes,
    resolve_season_universe,
)
from src.services.nfl_season_engine.injury_paths import (
    InjuryPath,
    apply_injury_paths_for_week,
)
from src.services.nfl_season_engine.loaders import (
    ROSTER_SOURCE_DEMO,
    ROSTER_SOURCE_PACKAGED,
    ROSTER_SOURCE_WEEKLY,
    _rosters_from_depth_rows,
)


def test_engine_version_real_depth() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "real-depth" in DEFAULT_SEASON_ENGINE_VERSION
        or "smoke-polish" in DEFAULT_SEASON_ENGINE_VERSION
        or "survivor-planner" in DEFAULT_SEASON_ENGINE_VERSION
        or "calibration" in DEFAULT_SEASON_ENGINE_VERSION
        or "player-regression" in DEFAULT_SEASON_ENGINE_VERSION
        or "projected-sos" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_packaged_depth_covers_32_named_skill_teams() -> None:
    rows, meta = load_packaged_depth_chart(2026)
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED
    assert meta["roster_as_of"]
    assert len(rows) >= 32 * 4  # at least QB1/RB1/WR1/TE1 per team

    rosters, _hits, coverage = _rosters_from_depth_rows(
        rows, source=ROSTER_SOURCE_PACKAGED
    )
    assert coverage["depth_team_count"] == 32
    assert coverage["depth_named_skill_teams"] == 32
    assert coverage["depth_full_skill_starter_teams"] == 32

    # Sample fantasy-relevant RB1s / WR cores
    sf_rb1 = next(r for r in rosters["SF"] if r.position == "RB" and r.depth_order == 1)
    assert "McCaffrey" in sf_rb1.player_name
    buf_rb1 = next(r for r in rosters["BUF"] if r.position == "RB" and r.depth_order == 1)
    assert "Cook" in buf_rb1.player_name
    kc_wrs = [r.player_name for r in rosters["KC"] if r.position == "WR"]
    assert any("Rice" in n for n in kc_wrs)
    assert any("Worthy" in n for n in kc_wrs)


def test_packaged_real_universe_leaves_demo_depth() -> None:
    universe, meta = resolve_season_universe(season=2026, demo=False, session=None)
    assert meta["mode"] == "real"
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED
    assert meta["depth_source"] == ROSTER_SOURCE_PACKAGED
    assert meta["roster_source"] != ROSTER_SOURCE_DEMO
    assert int(meta["depth_named_skill_teams"]) >= 30

    packaged = build_packaged_real_universe(2026)
    assert packaged.notes["roster_source"] == ROSTER_SOURCE_PACKAGED
    assert packaged.notes["roster_as_of"] != "2025_offseason_approx"


def test_demo_true_still_uses_demo_depth() -> None:
    universe, meta = resolve_season_universe(season=2026, demo=True, session=None)
    assert meta["roster_source"] == ROSTER_SOURCE_DEMO
    assert meta["depth_source"] == ROSTER_SOURCE_DEMO


def test_weekly_rows_map_to_weekly_source_tag() -> None:
    """DB weekly rows feed the preferred source tag (no heavy tasks import)."""
    rows = [
        {
            "team": "SF",
            "player_name": "Christian McCaffrey",
            "position": "RB",
            "depth_order": 1,
            "role_confidence": 0.9,
        },
        {
            "team": "SF",
            "player_name": "Brock Purdy",
            "position": "QB",
            "depth_order": 1,
            "role_confidence": 0.9,
        },
        {
            "team": "SF",
            "player_name": "George Kittle",
            "position": "TE",
            "depth_order": 1,
            "role_confidence": 0.85,
        },
        {
            "team": "SF",
            "player_name": "Deebo Samuel",
            "position": "WR",
            "depth_order": 1,
            "role_confidence": 0.8,
        },
    ]
    rosters, _hits, coverage = _rosters_from_depth_rows(
        rows, source="depth_chart_weekly"
    )
    assert ROSTER_SOURCE_WEEKLY == "nfl_dp_depth_chart_weekly"
    assert coverage["depth_named_skill_teams"] >= 1
    assert any(
        r.player_name == "Christian McCaffrey"
        and str(r.source).startswith("depth_chart_weekly")
        for r in rosters["SF"]
    )


def test_synthetic_bye_matchup_notes() -> None:
    """Hypothetical bye-week matchups still return boxes but must be labeled."""
    universe = build_packaged_real_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="CAR",
        week=5,
        n_replicates=40,
        seed=3,
    )
    assert proj.notes.get("schedule_match") == "synthetic_matchup"
    assert "KC" in (proj.notes.get("bye_teams_in_query") or "")
    assert "CAR" in (proj.notes.get("bye_teams_in_query") or "")
    assert proj.notes.get("bye_warning")


def test_real_depth_game_boxes_roles_and_injury() -> None:
    universe = build_packaged_real_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="LA",
        away_team="SF",
        week=1,
        n_replicates=40,
        seed=11,
        include_diagnostics=True,
    )
    assert proj.notes.get("schedule_match") == "on_loaded_schedule"
    sf_players = [p for p in proj.players if p["team"] == "SF"]
    assert sf_players
    rb1 = next(p for p in sf_players if p.get("usage_role") == "RB1")
    assert "McCaffrey" in rb1["player_name"]
    depth = (proj.diagnostics or {}).get("depth_structure") or {}
    assert "SF" in depth or "LA" in depth

    # Injury reallocation still works on real names.
    adj_rosters, _strengths, adjustments = apply_injury_paths_for_week(
        universe.rosters,
        universe.strengths,
        [
            InjuryPath(
                team="SF",
                player_name="Christian McCaffrey",
                status="out",
                week_start=1,
                week_end=1,
            )
        ],
        week=1,
    )
    assert adjustments
    cmc = next(r for r in adj_rosters["SF"] if "McCaffrey" in r.player_name)
    assert cmc.snap_share < 0.15 or cmc.rush_share < 0.1
