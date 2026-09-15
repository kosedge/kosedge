"""Research-only owned PBP metrics — no opponent-adj, no KEI."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.owned_metrics import (
    OPPONENT_ADJUSTED,
    RESEARCH_ONLY,
    audit_epa_success,
    down_bucket,
    drive_metrics,
    filter_plays_w_minus_1,
    is_explosive,
    league_rollups,
    opportunity_summary,
    play_points,
    rolling_form,
    standard_success,
    team_game_raw_metrics,
)
from src.services.cfb_warehouse.owned_pbp import (
    INVENTORY_HIST_GAMES,
    INVENTORY_HIST_PLAYS,
    INVENTORY_EXPECTED,
    hist_totals,
    reconcile_to_inventory,
)
from src.services.cfb_warehouse.paths import REPO_ROOT
from src.services.cfb_warehouse.season_2026_w1 import features_for_week


def _play(**kwargs):
    base = {
        "season": 2024,
        "week": 1,
        "game_id": "g1",
        "id": 1,
        "drive.id": "d1",
        "pos_team": "Georgia Bulldogs",
        "def_pos_team": "Clemson Tigers",
        "down": 1,
        "distance": 10,
        "start.yardsToEndzone": 75,
        "statYardage": 5,
        "type.text": "Rush",
        "EPA": 0.2,
        "EPA_success": True,
        "scrimmage_play": True,
        "pass": False,
        "rush": True,
        "rz_play": False,
        "pos_score_diff": 0,
    }
    base.update(kwargs)
    return base


def test_research_flags_forbid_adj() -> None:
    assert RESEARCH_ONLY is True
    assert OPPONENT_ADJUSTED is False


def test_repo_root_prefers_monorepo_not_service_data_tree() -> None:
    """Do not resolve warehouse fallback to services/model-service/data."""
    if (REPO_ROOT / "apps" / "web").is_dir():
        assert (REPO_ROOT / "data" / "cfb").is_dir()
        assert REPO_ROOT.name != "model-service"


def test_inventory_hist_totals() -> None:
    assert hist_totals() == {"plays": INVENTORY_HIST_PLAYS, "games": INVENTORY_HIST_GAMES}
    assert sum(INVENTORY_EXPECTED[y]["plays"] for y in (2021, 2022, 2023, 2024)) == 612597


def test_reconcile_match_and_drift() -> None:
    match = reconcile_to_inventory(
        {
            "season": 2024,
            "raw_bytes": 55106146,
            "raw": {"plays": 162950, "games": 946, "columns": 477},
        }
    )
    assert match["exact_match"] is True
    drift = reconcile_to_inventory(
        {
            "season": 2024,
            "raw_bytes": 1,
            "raw": {"plays": 1, "games": 1, "columns": 1},
        }
    )
    assert drift["exact_match"] is False
    assert drift["status"] == "drift_or_different_copy"


def test_epa_success_audit_matches_gt_zero() -> None:
    plays = [
        _play(id=1, EPA=0.4, EPA_success=True, statYardage=6),
        _play(id=2, EPA=-0.3, EPA_success=False, statYardage=1, down=1, distance=10),
        _play(id=3, EPA=1.2, EPA_success=True, statYardage=20, **{"pass": True, "rush": False}),
    ]
    audit = audit_epa_success(plays)
    assert audit["verdict"] == "EPA_success_matches_EPA_gt_0"
    assert audit["agree_EPA_gt_0"] == 1.0


def test_standard_success_and_explosive() -> None:
    assert standard_success(_play(down=1, distance=10, statYardage=5)) is True
    assert standard_success(_play(down=1, distance=10, statYardage=4)) is False
    assert standard_success(_play(down=3, distance=4, statYardage=4)) is True
    assert is_explosive(_play(EPA=0.2, statYardage=16)) is True
    assert is_explosive(_play(EPA=1.1, statYardage=2)) is True
    assert is_explosive(_play(EPA=0.2, statYardage=4)) is False


def test_down_buckets() -> None:
    assert down_bucket(_play(down=1, distance=10))["early"] is True
    assert down_bucket(_play(down=1, distance=10))["standard"] is True
    assert down_bucket(_play(down=2, distance=8))["passing"] is True
    assert down_bucket(_play(down=2, distance=4))["standard"] is True
    assert down_bucket(_play(down=3, distance=1))["passing"] is True


def test_success_rate_and_pace_denominators() -> None:
    plays = [
        _play(id=1, EPA=0.2, EPA_success=True, statYardage=5),
        _play(id=2, EPA=-0.4, EPA_success=False, statYardage=1),
        _play(id=3, game_id="g2", week=2, EPA=0.1, EPA_success=True, statYardage=8),
    ]
    rows = team_game_raw_metrics(plays)
    g1 = next(r for r in rows if r["game_id"] == "g1")
    assert g1["n_plays"] == 2
    assert g1["success_rate"] == 0.5
    assert g1["opponent_adjusted"] is False
    roll = league_rollups(rows)
    assert roll["team_games"] == 2
    assert roll["opponent_adjusted"] is False


def test_scoring_opportunity_and_ppo() -> None:
    plays = [
        _play(id=1, **{"drive.id": "d1", "start.yardsToEndzone": 75, "type.text": "Rush"}),
        _play(
            id=2,
            **{
                "drive.id": "d1",
                "start.yardsToEndzone": 35,
                "type.text": "Passing Touchdown",
                "statYardage": 35,
            },
        ),
        _play(
            id=3,
            **{"drive.id": "d2", "start.yardsToEndzone": 80, "type.text": "Punt", "scrimmage_play": False},
        ),
    ]
    drives = drive_metrics(plays)
    by_id = {d["drive_id"]: d for d in drives}
    assert by_id["d1"]["scoring_opportunity"] is True
    assert by_id["d1"]["points"] == 6
    assert by_id["d2"]["scoring_opportunity"] is False
    assert play_points(_play(**{"type.text": "Field Goal Good"})) == 3
    summ = opportunity_summary(drives)
    assert summ["scoring_opportunities"] == 1
    assert summ["points_per_opportunity"] == 6
    assert summ["finish_rate"] == 1.0


def test_w_minus_1_excludes_current_and_future() -> None:
    plays = [
        _play(week=1, EPA=0.2),
        _play(week=2, game_id="g2", EPA=9.0, EPA_success=True),
        _play(week=3, game_id="g3", EPA=-9.0),
    ]
    kept = filter_plays_w_minus_1(plays, season=2024, as_of_week=2)
    assert {p["week"] for p in kept} == {1}
    form = rolling_form(plays, season=2024, as_of_week=2)
    assert form and form[0]["feature_week"] == 1
    assert form[0]["as_of_week"] == 2


def test_2026_scaffold_empty_is_honest() -> None:
    out = features_for_week([], as_of_week=3)
    assert out["status"] == "no_2026_plays_before_cutoff"
    assert out["plays_used"] == 0
    assert out["leakage_ok"] is True
    assert out["opponent_adjusted"] is False
    plays = [
        {
            "season": 2026,
            "week": 1,
            "game_id": "26-1",
            "id": 1,
            "drive.id": "x",
            "pos_team": "Georgia Bulldogs",
            "def_pos_team": "Clemson Tigers",
            "EPA": 0.1,
            "EPA_success": True,
            "scrimmage_play": True,
            "down": 1,
            "distance": 10,
            "statYardage": 5,
            "start.yardsToEndzone": 70,
            "type.text": "Rush",
            "pass": False,
            "rush": True,
        },
        {
            "season": 2026,
            "week": 3,
            "game_id": "26-3",
            "id": 2,
            "drive.id": "y",
            "pos_team": "Georgia Bulldogs",
            "def_pos_team": "Clemson Tigers",
            "EPA": 5.0,
            "EPA_success": True,
            "scrimmage_play": True,
            "down": 1,
            "distance": 10,
            "statYardage": 40,
            "start.yardsToEndzone": 40,
            "type.text": "Rushing Touchdown",
            "pass": False,
            "rush": True,
        },
    ]
    week3 = features_for_week(plays, as_of_week=3)
    assert week3["plays_used"] == 1
    assert week3["max_week_included"] == 1
    assert week3["leakage_ok"] is True
