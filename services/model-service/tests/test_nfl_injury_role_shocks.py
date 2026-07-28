from __future__ import annotations

from src.services.nfl_injury_role_shocks import (
    availability_from_injury_statuses,
    redistribute_team_usage_for_injuries,
)


def test_out_status_is_hard_unavailable() -> None:
    assert availability_from_injury_statuses("Out", "Full") < 0.20
    assert availability_from_injury_statuses("Questionable", "Did Not Participate") < 0.35


def test_injury_redistributes_rb_rush_share_to_healthy_back() -> None:
    out = redistribute_team_usage_for_injuries(
        [
            {
                "player_id": "rb1",
                "position": "RB",
                "availability": 0.10,
                "rush_share": 0.70,
                "target_proxy": 0.05,
                "qb_starter_share": 0.0,
            },
            {
                "player_id": "rb2",
                "position": "RB",
                "availability": 0.95,
                "rush_share": 0.25,
                "target_proxy": 0.08,
                "qb_starter_share": 0.0,
            },
            {
                "player_id": "rb3",
                "position": "RB",
                "availability": 0.95,
                "rush_share": 0.05,
                "target_proxy": 0.02,
                "qb_starter_share": 0.0,
            },
        ]
    )
    assert out["rb1"]["rush_share"] < 0.10
    assert out["rb2"]["rush_share"] > 0.50
    assert abs(sum(v["rush_share"] for v in out.values()) - 1.0) < 1e-6
    assert out["rb1"]["injury_shock"] > 0.5


def test_healthy_room_unchanged() -> None:
    rows = [
        {
            "player_id": "a",
            "position": "WR",
            "availability": 0.95,
            "rush_share": 0.0,
            "target_proxy": 0.28,
            "qb_starter_share": 0.0,
        },
        {
            "player_id": "b",
            "position": "WR",
            "availability": 0.92,
            "rush_share": 0.0,
            "target_proxy": 0.18,
            "qb_starter_share": 0.0,
        },
    ]
    out = redistribute_team_usage_for_injuries(rows)
    assert abs(out["a"]["target_proxy"] - 0.28) < 1e-9
    assert out["a"]["injury_shock"] == 0.0
