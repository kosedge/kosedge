from __future__ import annotations

from src.services.nba_player_prop_projection import (
    aggregate_stub_rows,
    project_player_markets,
)
from src.services.nba_prop_edge_policy import (
    evaluate_nba_prop_edge,
    ou_balance_report,
)
from src.services.nba_publish_policy import board_publish_posture


def test_project_player_markets_produces_four_markets():
    rows = project_player_markets(
        player_id="1",
        player_name="Jayson Tatum",
        team_key="BOS",
        minutes=36.0,
        usage_proxy=22.0,
        pts_per_min=0.75,
        reb_per_min=0.22,
        ast_per_min=0.14,
        threes_per_min=0.08,
        sample_games=8,
        team_pace=102.0,
        team_ortg=118.0,
    )
    assert {r.market_key for r in rows} == {"pts", "reb", "ast", "threes"}
    pts = next(r for r in rows if r.market_key == "pts")
    assert pts.model_mean > 20
    assert pts.model_std > 0


def test_aggregate_stub_rows_rates():
    agg = aggregate_stub_rows(
        [
            {
                "player_id": "1",
                "player_name": "A",
                "team_key": "BOS",
                "minutes": 30,
                "pts": 24,
                "reb": 6,
                "ast": 4,
                "fg3m": 3,
                "usage_proxy": 20,
            },
            {
                "player_id": "1",
                "player_name": "A",
                "team_key": "BOS",
                "minutes": 34,
                "pts": 28,
                "reb": 8,
                "ast": 5,
                "fg3m": 2,
                "usage_proxy": 22,
            },
        ]
    )
    assert agg["sample_games"] == 2
    assert abs(agg["pts_per_min"] - (52 / 64)) < 1e-6


def test_role_collapse_refuses_under_play():
    edge = evaluate_nba_prop_edge(
        market_key="pts",
        model_mean=8.0,
        model_std=4.0,
        line=24.5,
        over_price=-110,
        under_price=-110,
        sample_games=10,
    )
    assert edge["tag"] == "PASS"
    assert edge["reason"] == "model_role_collapse"
    assert edge["stake_eligible"] is False


def test_ou_balance_and_publish_posture():
    bal = ou_balance_report(
        [
            {"diagnostics": {"tag": "PLAY", "tag_side": "OVER"}},
            {"diagnostics": {"tag": "PLAY", "tag_side": "UNDER"}},
            {"diagnostics": {"tag": "PASS"}},
        ]
    )
    assert bal["play_n"] == 2
    assert bal["balanced"] is True
    posture = board_publish_posture(n_with_close_lines=79, ats=0.506)
    assert posture["props"] == "research_only"
