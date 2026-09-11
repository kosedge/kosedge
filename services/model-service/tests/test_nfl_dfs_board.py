from __future__ import annotations

from src.services.nfl_dfs_board import DfsProjectionInput, assemble_dfs_board
from src.services.nfl_dfs_identity import DfsSalaryObservation, DfsSlateIdentity
from src.services.nfl_player_production import production_from_baseline_row


def _salary(**overrides) -> DfsSalaryObservation:
    data = dict(
        site="DK",
        season=2026,
        week=1,
        slate_id="151307",
        source_player_id="1",
        player_uid="uid-1",
        player_name="Josh Allen",
        team="BUF",
        opponent="HOU",
        position="QB",
        salary=7000,
        game_id="g1",
        game_label="BUF @ HOU",
        game_time=None,
        source="dk_csv",
        source_version="v1",
        captured_at="2026-09-10T12:00:00Z",
        is_current=True,
        identity_status="resolved",
    )
    data.update(overrides)
    return DfsSalaryObservation(**data)


def _proj(**overrides) -> DfsProjectionInput:
    row = {
        "pass_yards_mean": 260,
        "rush_yards_mean": 35,
        "receiving_yards_mean": 0,
        "receptions_mean": 0,
        "pass_tds_mean": 1.8,
        "rush_tds_mean": 0.4,
        "rec_tds_mean": 0,
        "pass_yards_std": 45,
        "rush_yards_std": 14,
        "receiving_yards_std": 4,
        "receptions_std": 1,
        "floor_outcome": {
            "pass_yards": 180,
            "rush_yards": 10,
            "receiving_yards": 0,
            "receptions": 0,
            "touchdowns": 0.8,
        },
        "ceiling_outcome": {
            "pass_yards": 340,
            "rush_yards": 70,
            "receiving_yards": 0,
            "receptions": 0,
            "touchdowns": 3.2,
        },
    }
    data = dict(
        player_uid="uid-1",
        player_name="Josh Allen",
        team="BUF",
        opponent="HOU",
        position="QB",
        game_id="g1",
        production=production_from_baseline_row(row),
        baseline_row=row,
    )
    data.update(overrides)
    return DfsProjectionInput(**data)


def test_board_values_only_certified_rows() -> None:
    board = assemble_dfs_board(
        requested=DfsSlateIdentity(season=2026, week=1, site="DK", slate_id="151307"),
        salaries=[
            _salary(),
            _salary(source_player_id="2", player_uid="uid-chase", player_name="Ja'Marr Chase", team="CIN", opponent="TB", position="WR", salary=7800),
        ],
        projections=[
            _proj(),
            _proj(
                player_uid="uid-chase",
                player_name="Ja'Marr Chase",
                team="CIN",
                opponent="TB",
                position="WR",
                production=production_from_baseline_row(
                    {
                        "pass_yards_mean": 0,
                        "rush_yards_mean": 4,
                        "receiving_yards_mean": 95,
                        "receptions_mean": 8,
                        "pass_tds_mean": 0,
                        "rush_tds_mean": 0,
                        "rec_tds_mean": 0.7,
                        "receiving_yards_std": 30,
                        "rush_yards_std": 5,
                        "pass_yards_std": 4,
                        "receptions_std": 2,
                        "floor_outcome": {"receiving_yards": 50, "receptions": 4, "rush_yards": 0, "pass_yards": 0, "touchdowns": 0.2},
                        "ceiling_outcome": {"receiving_yards": 150, "receptions": 12, "rush_yards": 12, "pass_yards": 0, "touchdowns": 1.5},
                    }
                ),
                baseline_row={
                    "receiving_yards_std": 30,
                    "rush_yards_std": 5,
                    "pass_yards_std": 4,
                    "receptions_std": 2,
                    "floor_outcome": {"receiving_yards": 50, "receptions": 4, "rush_yards": 0, "pass_yards": 0, "touchdowns": 0.2},
                    "ceiling_outcome": {"receiving_yards": 150, "receptions": 12, "rush_yards": 12, "pass_yards": 0, "touchdowns": 1.5},
                },
            ),
        ],
    )
    assert board.status == "ok"
    assert board.live is False
    assert len(board.rows) == 2
    assert all(row.value is not None for row in board.rows)
    assert board.summary["top_projection"] is not None
    assert board.as_public()["ownership"]["status"] == "unavailable"


def test_failed_joins_do_not_get_value() -> None:
    board = assemble_dfs_board(
        requested=DfsSlateIdentity(season=2026, week=1, site="DK", slate_id="151307"),
        salaries=[
            _salary(week=2),  # wrong week
            _salary(source_player_id="x", player_uid="uid-x", player_name="Wrong", team="KC", opponent="LAC"),
        ],
        projections=[_proj()],
    )
    assert board.rows == []
    assert all(item.reason != "ok" for item in board.rejected)
    assert board.diagnostics["season_average_substituted"] is False


def test_dk_rows_excluded_from_fd_board() -> None:
    board = assemble_dfs_board(
        requested=DfsSlateIdentity(season=2026, week=1, site="FD", slate_id="fd-main"),
        salaries=[_salary(site="DK", slate_id="fd-main")],
        projections=[_proj()],
    )
    assert board.rows == []
    assert any(item.reason == "site_mismatch" for item in board.rejected)


def test_duplicate_identity_omits_value() -> None:
    board = assemble_dfs_board(
        requested=DfsSlateIdentity(season=2026, week=1, site="DK", slate_id="151307"),
        salaries=[
            _salary(source_player_id="a", player_uid="uid-1"),
            _salary(source_player_id="b", player_uid="uid-1"),
        ],
        projections=[_proj()],
    )
    assert board.rows == []
    assert any(item.reason == "duplicate_player_identity" for item in board.rejected)


def test_missing_slate_does_not_invent_board() -> None:
    board = assemble_dfs_board(
        requested=DfsSlateIdentity(season=2026, week=1, site="DK", slate_id=""),
        salaries=[],
        projections=[],
        available_slates=[],
    )
    assert board.status == "no_slate"
    assert board.rows == []
    assert board.diagnostics["season_average_substituted"] is False
