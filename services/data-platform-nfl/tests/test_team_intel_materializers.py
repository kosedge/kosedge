from __future__ import annotations

from data_platform_nfl.team_intel import build_standings_rows, infer_depth_chart_rows


def test_build_standings_rows_tracks_weekly_cumulative_record() -> None:
    rows = build_standings_rows(
        [
            {
                "season": 2026,
                "week": 1,
                "home_team": "BUF",
                "away_team": "MIA",
                "home_score": 24,
                "away_score": 17,
            },
            {
                "season": 2026,
                "week": 2,
                "home_team": "MIA",
                "away_team": "BUF",
                "home_score": 20,
                "away_score": 20,
            },
        ]
    )
    by_key = {(r["team"], r["week"]): r for r in rows}
    assert by_key[("BUF", 1)]["wins"] == 1
    assert by_key[("BUF", 1)]["losses"] == 0
    assert by_key[("BUF", 2)]["ties"] == 1
    assert by_key[("BUF", 2)]["points_for"] == 44
    assert by_key[("MIA", 2)]["losses"] == 1
    assert by_key[("MIA", 2)]["ties"] == 1


def test_infer_depth_chart_rows_orders_by_role_and_penalizes_injuries() -> None:
    rows = infer_depth_chart_rows(
        season=2026,
        week=5,
        roster_rows=[
            {"team": "BUF", "player_id": "qb1", "player_name": "Starter QB", "position": "QB"},
            {"team": "BUF", "player_id": "qb2", "player_name": "Backup QB", "position": "QB"},
            {"team": "BUF", "player_id": "wr1", "player_name": "Alpha WR", "position": "WR"},
            {"team": "BUF", "player_id": "wr2", "player_name": "Limited WR", "position": "WR"},
        ],
        usage_rows=[
            {
                "team": "BUF",
                "player_id": "qb1",
                "involvement": 100,
                "targets": 0,
                "rush_attempts": 8,
                "pass_attempts": 108,
                "active_weeks": 3,
                "latest_week": 5,
            },
            {
                "team": "BUF",
                "player_id": "qb2",
                "involvement": 4,
                "targets": 0,
                "rush_attempts": 1,
                "pass_attempts": 4,
                "active_weeks": 1,
                "latest_week": 5,
            },
            {
                "team": "BUF",
                "player_id": "wr1",
                "involvement": 42,
                "targets": 28,
                "rush_attempts": 2,
                "pass_attempts": 0,
                "active_weeks": 3,
                "latest_week": 5,
            },
            {
                "team": "BUF",
                "player_id": "wr2",
                "involvement": 39,
                "targets": 25,
                "rush_attempts": 1,
                "pass_attempts": 0,
                "active_weeks": 3,
                "latest_week": 5,
            },
        ],
        injury_rows=[
            {
                "team": "BUF",
                "player_id": "wr2",
                "player_name": "Limited WR",
                "report_status": "questionable",
                "practice_status": "DNP",
            }
        ],
    )
    qb_rows = [r for r in rows if r["position"] == "QB"]
    wr_rows = [r for r in rows if r["position"] == "WR"]

    assert qb_rows[0]["depth_order"] == 1
    assert qb_rows[0]["player_id"] == "qb1"
    assert qb_rows[0]["depth_slot"] == "starter"
    assert qb_rows[1]["player_id"] == "qb2"
    assert qb_rows[1]["depth_slot"] == "backup"

    assert wr_rows[0]["player_id"] == "wr1"
    assert wr_rows[1]["player_id"] == "wr2"
    assert wr_rows[0]["role_confidence"] > wr_rows[1]["role_confidence"]
