"""Tests — NFL Kickoff Injury → KEI cadence."""

from __future__ import annotations

from src.services.nfl_decision_engine import grade_side_points
from src.services.nfl_injury_kei_cadence import (
    aggregate_team_deltas,
    apply_kei_reprice_to_projection,
    describe_friday_1600_et,
    diff_sot_statuses,
    fixture_qb1_out_then_restore,
    load_cadence_config,
    must_force_kei_reprice,
    participation_from_status,
    recompute_side_tag,
    refresh_active_pr_rows,
    run_injury_kei_window,
    window_config,
)
from src.services.nfl_model_handicap import extract_model_markets_from_projection


def test_status_participation_map() -> None:
    assert participation_from_status("Out") == 0.0
    assert participation_from_status("doubtful") == 0.25
    assert participation_from_status("Questionable") == 0.5
    assert participation_from_status("limited") == 0.85
    assert participation_from_status("full") == 1.0
    assert participation_from_status("healthy") == 1.0


def test_windows_configurable() -> None:
    cfg = load_cadence_config(reload=True)
    assert "midweek" in cfg["windows"]
    assert "friday_final" in cfg["windows"]
    fri = window_config("friday_final")
    assert fri["hour_et"] == 16
    assert fri["scope"] == "full_slate"
    mid = window_config("midweek")
    assert mid["day_et"] == "thu"
    assert mid["scope"] == "affected"
    gd = window_config("gameday_inactives")
    assert gd["minutes_before_kickoff"] == 90
    assert gd.get("lock_pre_kick_kei") is True
    post = window_config("post_game")
    assert post["action"] == "no_kei_change"


def test_friday_operator_answer() -> None:
    text = describe_friday_1600_et()
    assert "SoT" in text
    assert "KEI" in text
    assert "Active PR" in text
    assert "Model" in text


def test_qb1_out_forces_reprice_and_moves_kei() -> None:
    before = [
        {
            "team": "KC",
            "player_id": "QB1",
            "position": "QB",
            "depth_order": 1,
            "injury_status": "healthy",
            "is_qb1": True,
        }
    ]
    after = [{**before[0], "injury_status": "out"}]
    changes = diff_sot_statuses(before, after)
    assert must_force_kei_reprice(changes)
    deltas = aggregate_team_deltas(changes)
    assert "KC" in deltas
    assert deltas["KC"].spread_pts >= 3.0
    assert deltas["KC"].alert is True
    assert deltas["KC"].confidence_delta < 0


def test_qb1_out_preserves_model_and_can_downgrade_tag() -> None:
    """Fixture: QB1 Out → KEI/tag move; Model snapshot unchanged."""
    projection = {
        "game_id": "BUF@KC",
        "markets": {
            "spread_home": -6.5,
            "total_mean": 47.5,
            "home_win_prob": 0.72,
            "away_win_prob": 0.28,
            "fair_home_ml": -260,
            "fair_away_ml": 210,
        },
        "model_markets": {
            "spread_home": -7.0,
            "total_mean": 48.0,
            "home_win_prob": 0.72,
            "away_win_prob": 0.28,
            "fair_home_ml": -260,
            "fair_away_ml": 210,
        },
    }
    market = -3.0
    week = 1
    before_tag = recompute_side_tag(
        kei_spread_home=-6.5, market_spread_home=market, week=week
    )
    # |−6.5 − (−3)| = 3.5 → STRONG PLAY under early bands (strong_min=3.25)
    assert before_tag["point_grade"] in {"PLAY", "STRONG PLAY"}
    assert grade_side_points(3.5, week) == "STRONG PLAY"

    deltas = aggregate_team_deltas(
        diff_sot_statuses(
            [
                {
                    "team": "KC",
                    "player_id": "QB1",
                    "position": "QB",
                    "depth_order": 1,
                    "injury_status": "healthy",
                    "is_qb1": True,
                }
            ],
            [
                {
                    "team": "KC",
                    "player_id": "QB1",
                    "position": "QB",
                    "depth_order": 1,
                    "injury_status": "out",
                    "is_qb1": True,
                }
            ],
        )
    )
    apply_kei_reprice_to_projection(
        projection,
        home_team="KC",
        away_team="BUF",
        team_deltas=deltas,
    )
    model = extract_model_markets_from_projection(projection)
    assert model is not None
    assert model["spread_home"] == -7.0
    assert model["total_mean"] == 48.0
    assert projection["line_role"] == "handicap"
    assert projection["markets"]["spread_home"] > -6.5  # home weaker

    after_tag = recompute_side_tag(
        kei_spread_home=float(projection["markets"]["spread_home"]),
        market_spread_home=market,
        week=week,
    )
    # Edge shrinks → tag can downgrade (STRONG → PLAY/LEAN/PASS)
    assert after_tag["edge_magnitude"] < before_tag["edge_magnitude"]
    rank = {"PASS": 0, "LEAN": 1, "PLAY": 2, "STRONG PLAY": 3, "EXCEPTIONAL": 4}
    assert rank[after_tag["action_label"]] <= rank[before_tag["action_label"]]


def test_qb1_restore_snaps_kei_back() -> None:
    payload = fixture_qb1_out_then_restore()
    out = payload["out"]
    restore = payload["restore"]
    assert out["noop"] is False
    assert restore["noop"] is False
    out_move = out["kei_moves"][0]
    restore_move = restore["kei_moves"][0]
    assert out_move["model_unchanged"] is True
    assert restore_move["model_unchanged"] is True
    # Out moves KEI toward zero; restore moves back toward prior KEI.
    assert out_move["kei_spread_after"] > out_move["kei_spread_before"]
    assert restore_move["kei_spread_after"] < restore_move["kei_spread_before"]
    # Restore should land near original KEI (-6.5)
    assert abs(restore_move["kei_spread_after"] - (-6.5)) < 0.2


def test_no_diff_heartbeat_noop() -> None:
    result = run_injury_kei_window(
        window="midweek",
        season=2026,
        week=1,
        previous_sot=[],
        current_sot=[],
        games=[],
        dry_run=True,
    )
    assert result.noop is True
    assert "HEARTBEAT" in result.ops_line or "no-diff" in result.reason


def test_post_game_no_kei() -> None:
    result = run_injury_kei_window(
        window="post_game",
        season=2026,
        week=1,
        previous_sot=[{"team": "KC", "player_id": "x", "injury_status": "out"}],
        current_sot=[{"team": "KC", "player_id": "x", "injury_status": "out"}],
        games=[],
        dry_run=True,
    )
    assert result.noop is True
    assert "tuesday_pr" in result.reason


def test_active_pr_refresh_freezes_model() -> None:
    rows = refresh_active_pr_rows(
        published_model_prs={"KC": 4.0, "BUF": 3.5},
        injury_adjusted_active={"KC": 1.0, "BUF": 3.5},
        ryan_adjs={"KC": 0.0},
    )
    assert rows["KC"]["model_pr"] == 4.0
    assert rows["KC"]["active_pr"] == 1.0
    assert rows["BUF"]["model_pr"] == 3.5


def test_gameday_locks_pre_kick_kei() -> None:
    game = {
        "game_id": "BUF@KC",
        "home_team": "KC",
        "away_team": "BUF",
        "model_spread_home": -7.0,
        "model_total_mean": 48.0,
        "kei_spread_home": -6.5,
        "kei_total_mean": 47.5,
        "market_spread_home": -3.0,
    }
    result = run_injury_kei_window(
        window="gameday_inactives",
        season=2026,
        week=1,
        previous_sot=[
            {
                "team": "KC",
                "player_id": "QB1",
                "position": "QB",
                "depth_order": 1,
                "injury_status": "questionable",
                "is_qb1": True,
            }
        ],
        current_sot=[
            {
                "team": "KC",
                "player_id": "QB1",
                "position": "QB",
                "depth_order": 1,
                "injury_status": "out",
                "is_qb1": True,
            }
        ],
        games=[game],
        dry_run=True,
    )
    assert result.locked_pre_kick is True
    assert "LOCK_PRE_KICK" in result.ops_line
