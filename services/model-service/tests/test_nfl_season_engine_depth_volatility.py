"""Tests for depth-chart structure, committee splits, and role volatility (v1.5)."""

from __future__ import annotations

import random

from src.services.nfl_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    InjuryPath,
    build_demo_universe,
    project_game_player_boxes,
    simulate_full_season,
)
from src.services.nfl_season_engine.depth_chart import (
    COMMITTEE_RUSH_SPLITS,
    FEATURE_RUSH_SPLITS,
    apply_depth_chart_base_shares,
    apply_weekly_role_volatility,
    classify_team_depth,
    herfindahl_rush,
    top1_rush_share,
    wr_hierarchy_gap,
)
from src.services.nfl_season_engine.injury_paths import apply_injury_paths_for_week
from src.services.nfl_season_engine.season_sim import simulate_one_season_path
from src.services.nfl_season_engine.types import PlayerRole, TeamStrengthState
from src.services.nfl_season_engine.usage_roles import annotate_usage_roles


def _rb(team: str, name: str, depth: int, rush: float, tgt: float = 0.06) -> PlayerRole:
    return PlayerRole(
        player_key=f"{team}-RB{depth}-{name}",
        player_name=name,
        team=team,
        position="RB",
        depth_order=depth,
        snap_share=0.5,
        rush_share=rush,
        target_share=tgt,
        route_share=tgt * 2.0,
        source="test",
    )


def _wr(team: str, name: str, depth: int, tgt: float) -> PlayerRole:
    return PlayerRole(
        player_key=f"{team}-WR{depth}-{name}",
        player_name=name,
        team=team,
        position="WR",
        depth_order=depth,
        snap_share=0.7,
        target_share=tgt,
        route_share=tgt * 4.0,
        source="test",
    )


def test_engine_version_depth_volatility() -> None:
    # Depth-chart volatility remains a capability; version tag moved to v1.6.
    assert DEFAULT_SEASON_ENGINE_VERSION.startswith("nfl-season-engine-v1.")
    assert (
        "depth-volatility" in DEFAULT_SEASON_ENGINE_VERSION
        or "game-script" in DEFAULT_SEASON_ENGINE_VERSION
        or "red-zone" in DEFAULT_SEASON_ENGINE_VERSION
    )


def test_feature_vs_committee_carry_concentration() -> None:
    feature_roles = [
        _rb("AAA", "Feature1", 1, 0.55),
        _rb("AAA", "Feature2", 2, 0.22),
    ]
    committee_roles = [
        _rb("BBB", "Comm1", 1, 0.40),
        _rb("BBB", "Comm2", 2, 0.34),
        _rb("BBB", "Comm3", 3, 0.20),
    ]
    feat_adj, feat_struct = apply_depth_chart_base_shares(
        feature_roles, force_table_splits=True
    )
    comm_adj, comm_struct = apply_depth_chart_base_shares(
        committee_roles, force_table_splits=True
    )
    assert feat_struct.rb_structure == "feature"
    assert comm_struct.rb_structure == "committee"

    feat_hhi = herfindahl_rush(feat_adj)
    comm_hhi = herfindahl_rush(comm_adj)
    assert feat_hhi > comm_hhi
    assert top1_rush_share(feat_adj) > top1_rush_share(comm_adj)
    # Documented splits applied.
    assert abs(top1_rush_share(feat_adj) - FEATURE_RUSH_SPLITS[2][0]) < 1e-6
    assert abs(top1_rush_share(comm_adj) - COMMITTEE_RUSH_SPLITS[3][0]) < 1e-6


def test_murky_wr_hierarchy_smaller_gap_than_clear() -> None:
    clear = [
        _wr("CCC", "Alpha", 1, 0.24),
        _wr("CCC", "Beta", 2, 0.16),
        _wr("CCC", "Gamma", 3, 0.08),
    ]
    murky = [
        _wr("DDD", "A", 1, 0.18),
        _wr("DDD", "B", 2, 0.17),
        _wr("DDD", "C", 3, 0.14),
    ]
    clear_adj, clear_s = apply_depth_chart_base_shares(clear, force_table_splits=True)
    murky_adj, murky_s = apply_depth_chart_base_shares(murky, force_table_splits=True)
    assert clear_s.wr_hierarchy == "clear"
    assert murky_s.wr_hierarchy == "murky"
    assert wr_hierarchy_gap(murky_adj) < wr_hierarchy_gap(clear_adj)


def test_volatility_shifts_roles_with_seed_stability() -> None:
    universe = build_demo_universe(2026)
    base = {
        "DET": list(universe.rosters["DET"]),
        "SF": list(universe.rosters["SF"]),
    }
    structs = {t: classify_team_depth(t, r) for t, r in base.items()}

    a1, t1 = apply_weekly_role_volatility(base, week=3, rng=random.Random(99), structures=structs)
    a2, t2 = apply_weekly_role_volatility(base, week=3, rng=random.Random(99), structures=structs)
    assert len(t1) == len(t2)
    for r1, r2 in zip(a1["DET"], a2["DET"]):
        assert r1.rush_share == r2.rush_share
        assert r1.target_share == r2.target_share

    b1, _ = apply_weekly_role_volatility(base, week=3, rng=random.Random(7), structures=structs)
    c1, _ = apply_weekly_role_volatility(base, week=5, rng=random.Random(99), structures=structs)
    det_a = [r.rush_share for r in a1["DET"] if r.position == "RB"]
    det_b = [r.rush_share for r in b1["DET"] if r.position == "RB"]
    det_c = [r.rush_share for r in c1["DET"] if r.position == "RB"]
    # Different seed or week changes the path shares.
    assert det_a != det_b or det_a != det_c


def test_injury_committee_realloc_zeros_injured_and_uneven() -> None:
    committee = annotate_usage_roles(
        [
            _rb("EEE", "C1", 1, 0.38, 0.08),
            _rb("EEE", "C2", 2, 0.30, 0.06),
            _rb("EEE", "C3", 3, 0.18, 0.04),
            _wr("EEE", "W1", 1, 0.20),
        ]
    )
    committee, struct = apply_depth_chart_base_shares(committee, force_table_splits=True)
    assert struct.rb_structure == "committee"
    injured = next(r for r in committee if r.player_name == "C1")
    path = InjuryPath(
        player_key=injured.player_key,
        team="EEE",
        status="out",
        week_start=1,
        week_end=1,
    )
    adj, _, adjustments = apply_injury_paths_for_week(
        {"EEE": committee},
        {"EEE": TeamStrengthState(team="EEE")},
        [path],
        week=1,
    )
    out_role = next(r for r in adj["EEE"] if r.player_key == injured.player_key)
    assert out_role.rush_share == 0.0
    remain = sorted(
        [r for r in adj["EEE"] if r.position == "RB" and r.player_key != injured.player_key],
        key=lambda r: -r.rush_share,
    )
    assert len(remain) >= 2
    # Uneven: top remaining > second (not equal split of freed volume).
    assert remain[0].rush_share > remain[1].rush_share
    assert adjustments
    assert "committee" in adjustments[0].realloc_notes.lower() or "uneven" in (
        adjustments[0].realloc_notes.lower()
    )


def test_injury_feature_rb1_promotes_rb2() -> None:
    feature = annotate_usage_roles(
        [
            _rb("FFF", "Ace", 1, 0.55, 0.10),
            _rb("FFF", "Backup", 2, 0.22, 0.04),
            _wr("FFF", "X", 1, 0.20),
        ]
    )
    feature, struct = apply_depth_chart_base_shares(feature, force_table_splits=True)
    assert struct.rb_structure == "feature"
    ace = next(r for r in feature if r.player_name == "Ace")
    backup = next(r for r in feature if r.player_name == "Backup")
    assert ace.usage_role == "RB1"
    assert backup.usage_role == "RB2"
    path = InjuryPath(
        player_key=ace.player_key, team="FFF", status="out", week_start=2, week_end=2
    )
    adj, _, _ = apply_injury_paths_for_week(
        {"FFF": feature},
        {"FFF": TeamStrengthState(team="FFF")},
        [path],
        week=2,
    )
    ace_adj = next(r for r in adj["FFF"] if r.player_key == ace.player_key)
    backup_adj = next(r for r in adj["FFF"] if r.player_key == backup.player_key)
    assert ace_adj.rush_share == 0.0
    assert backup_adj.rush_share > backup.rush_share
    assert backup_adj.usage_role == "RB1"


def test_thin_chart_no_crash() -> None:
    thin = [_rb("GGG", "Only", 1, 0.50)]
    adj, struct = apply_depth_chart_base_shares(thin, force_table_splits=True)
    assert struct.rb_structure == "thin"
    assert len(adj) == 1
    path = InjuryPath(
        player_key=adj[0].player_key, team="GGG", status="out", week_start=1, week_end=1
    )
    out, _, _ = apply_injury_paths_for_week(
        {"GGG": adj},
        {"GGG": TeamStrengthState(team="GGG")},
        [path],
        week=1,
    )
    assert next(r for r in out["GGG"]).rush_share == 0.0


def test_cook_rice_realism_bounds_hold() -> None:
    universe = build_demo_universe(2026)
    proj = project_game_player_boxes(
        universe,
        home_team="KC",
        away_team="BUF",
        week=1,
        n_replicates=200,
        seed=2026,
        include_diagnostics=True,
    )
    assert (
        "depth-volatility" in proj.engine_version
        or "game-script" in proj.engine_version
        or "red-zone" in proj.engine_version
    )
    cook = next(p for p in proj.players if "Cook" in p["player_name"])
    rice = next(p for p in proj.players if "Rice" in p["player_name"])
    assert cook["point_estimate"]["rush_yards"] < 95.0
    assert rice["distributions"]["receptions"]["mean"] < 8.0
    assert "depth_structure" in proj.diagnostics
    assert "BUF" in proj.diagnostics["depth_structure"]
    assert "role_transitions" in proj.diagnostics


def test_season_path_volatility_diagnostics() -> None:
    universe = build_demo_universe(2026)
    result = simulate_full_season(
        universe, n_sims=2, seed=42, include_diagnostics=True
    )
    assert (
        "depth-volatility" in result.engine_version
        or "game-script" in result.engine_version
        or "red-zone" in result.engine_version
    )
    assert "depth_structure" in result.diagnostics
    assert "role_transitions_sample" in result.diagnostics

    # Seed stability on a short custom schedule (2 weeks) instead of full 272.
    from src.services.nfl_season_engine.types import EngineUniverse, ScheduledGame
    from src.services.nfl_season_engine.team_strength import initialize_strengths

    mini = EngineUniverse(
        season=2026,
        schedule=[
            ScheduledGame(2026, 1, "g1", "DET", "SF"),
            ScheduledGame(2026, 2, "g2", "SF", "DET"),
        ],
        strengths=initialize_strengths(
            {
                "DET": {"offense_index": 1.1, "defense_index": 1.0, "source": "t"},
                "SF": {"offense_index": 1.05, "defense_index": 1.1, "source": "t"},
            }
        ),
        rosters={
            "DET": list(universe.rosters["DET"]),
            "SF": list(universe.rosters["SF"]),
        },
    )
    path_a = simulate_one_season_path(
        mini, rng=random.Random(11), collect_role_transitions=True
    )
    path_b = simulate_one_season_path(
        mini, rng=random.Random(11), collect_role_transitions=True
    )
    assert path_a["wins"] == path_b["wins"]
    assert path_a["role_transitions"] == path_b["role_transitions"]


def test_demo_det_committee_sf_murky() -> None:
    universe = build_demo_universe(2026)
    det = classify_team_depth("DET", universe.rosters["DET"])
    sf = classify_team_depth("SF", universe.rosters["SF"])
    phi = classify_team_depth("PHI", universe.rosters["PHI"])
    assert det.rb_structure == "committee"
    assert sf.wr_hierarchy == "murky"
    assert phi.rb_structure == "feature"
    assert phi.wr_hierarchy == "clear"
