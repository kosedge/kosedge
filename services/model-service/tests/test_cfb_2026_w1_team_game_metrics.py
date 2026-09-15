"""2026 W−1 raw unadjusted team-game metrics — research-only, no KE Ratings."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.current_season_2026 import (
    LIVE_STATUSES,
    assert_not_historical_write,
    classify_completion,
    research_dest_dir,
)
from src.services.cfb_warehouse.owned_metrics import (
    DEFINITIONS,
    OPPONENT_ADJUSTED,
    RESEARCH_ONLY,
    audit_epa_success,
    standard_success,
    team_game_raw_metrics,
)
from src.services.cfb_warehouse.pbp import PBP_SEASONS
from src.services.cfb_warehouse.paths import (
    HD_RAW_PBP,
    HD_RAW_PBP_CURRENT,
    REPO_RAW_PBP,
    REPO_RESEARCH_PBP_CURRENT,
    hd_pbp_current_target,
)
from src.services.cfb_warehouse.delayed_game_verify import (
    DELAYED_GAME_ID,
    OFFICIAL_AWAY_SCORE,
    OFFICIAL_HOME_SCORE,
)
from src.services.cfb_warehouse.team_game_w1_2026 import (
    PIPELINE_VERSION,
    PRODUCT_LABEL,
    SUCCESS_RATE_LABEL,
    build_eligibility_manifest,
    compose_team_game_table,
    default_as_of_week,
    filter_eligible_plays,
    run_research_pipeline,
    validate_outputs,
)


def _sched(
    gid: str,
    *,
    status: str,
    week: int,
    home_score=None,
    away_score=None,
    home: str = "Georgia Bulldogs",
    away: str = "Clemson Tigers",
) -> dict:
    view = classify_completion(
        status, home_score=home_score, away_score=away_score
    )
    return {
        "game_id": gid,
        "week": week,
        "season": 2026,
        "status_raw": status,
        "home": home,
        "away": away,
        "home_score": home_score,
        "away_score": away_score,
        **view,
    }


def _play(**kwargs):
    base = {
        "season": 2026,
        "week": 1,
        "game_id": "g-final",
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


def test_not_ke_ratings_and_unadjusted() -> None:
    assert RESEARCH_ONLY is True
    assert OPPONENT_ADJUSTED is False
    assert PRODUCT_LABEL == "raw unadjusted team-game metrics"
    assert "KE" not in PRODUCT_LABEL
    assert SUCCESS_RATE_LABEL == "EPA_success = EPA>0"
    assert "EPA>0" in DEFINITIONS["success_rate"]
    assert PIPELINE_VERSION.startswith("cfb-2026-w1-raw-team-game")


def test_refuses_historical_lake_write() -> None:
    try:
        assert_not_historical_write(HD_RAW_PBP / "play_by_play_2026.parquet")
    except RuntimeError as exc:
        assert "historical" in str(exc).lower()
    else:
        raise AssertionError("expected HD historical write to be refused")
    try:
        assert_not_historical_write(REPO_RAW_PBP / "play_by_play_2026.parquet")
    except RuntimeError as exc:
        assert "historical" in str(exc).lower()
    else:
        raise AssertionError("expected repo historical write to be refused")


def test_historical_2014_2025_lake_not_extended() -> None:
    assert PBP_SEASONS == tuple(range(2014, 2026))
    assert 2026 not in PBP_SEASONS
    dest = research_dest_dir("20260915")
    assert dest == REPO_RESEARCH_PBP_CURRENT / "as_of_20260915"
    assert dest.resolve() != HD_RAW_PBP.resolve()
    assert dest.resolve() != REPO_RAW_PBP.resolve()
    assert hd_pbp_current_target("2026-09-15") == HD_RAW_PBP_CURRENT / "as_of_20260915"
    assert "pbp_current" in str(hd_pbp_current_target("20260915"))


def test_live_aliases_include_halftime_and_end_period() -> None:
    assert "HALFTIME" in LIVE_STATUSES
    assert "END_PERIOD" in LIVE_STATUSES
    assert "STATUS_IN_PROGRESS" in LIVE_STATUSES
    live = classify_completion("HALFTIME", home_score=14, away_score=7)
    assert live["actually_completed"] is False
    endp = classify_completion("END_PERIOD", home_score=3, away_score=0)
    assert endp["actually_completed"] is False
    delayed_zero = classify_completion("DELAYED", home_score=0, away_score=0)
    assert delayed_zero["actually_completed"] is False
    delayed_mid = classify_completion("STATUS_DELAYED", home_score=21, away_score=0)
    assert delayed_mid["actually_completed"] is False
    assert delayed_mid["parked"] is True


def test_eligibility_excludes_live_and_week_ge_w() -> None:
    schedule = [
        _sched("g-final", status="STATUS_FINAL", week=1, home_score=42, away_score=26),
        _sched("g-scores-done", status="STATUS_UNKNOWN", week=1, home_score=17, away_score=14),
        _sched("g-live", status="STATUS_IN_PROGRESS", week=2, home_score=21, away_score=7),
        _sched("g-ht", status="HALFTIME", week=2, home_score=14, away_score=10),
        _sched("g-delay0", status="STATUS_DELAYED", week=2, home_score=0, away_score=0),
        _sched("g-delay-mid", status="STATUS_DELAYED", week=1, home_score=21, away_score=0),
        _sched("g-future", status="STATUS_FINAL", week=3, home_score=31, away_score=24),
        _sched("g-nopbp", status="STATUS_FINAL", week=1, home_score=10, away_score=7),
    ]
    pbp_ids = {
        "g-final",
        "g-scores-done",
        "g-live",
        "g-ht",
        "g-delay0",
        "g-delay-mid",
        "g-future",
        "orphan-pbp",
    }
    manifest = build_eligibility_manifest(
        schedule, pbp_ids, as_of_week=3, as_of="20260915"
    )
    by_id = {g["game_id"]: g for g in manifest["games"]}
    assert by_id["g-final"]["included"] is True
    assert by_id["g-scores-done"]["included"] is True
    assert by_id["g-live"]["included"] is False
    assert by_id["g-live"]["reason"] == "excluded_unfinished_live"
    assert by_id["g-ht"]["reason"] == "excluded_unfinished_live"
    assert by_id["g-delay0"]["included"] is False
    assert by_id["g-delay-mid"]["included"] is False
    assert by_id["g-delay-mid"]["reason"] == "excluded_unfinished_parked"
    assert by_id["g-future"]["reason"] == "excluded_week_ge_as_of"
    assert by_id["g-nopbp"]["reason"] == "excluded_completed_missing_pbp"
    assert by_id["orphan-pbp"]["reason"] == "excluded_pbp_unmatched_schedule"
    assert set(manifest["eligible_game_ids"]) == {"g-final", "g-scores-done"}
    assert manifest["eligible_count"] == 2
    assert manifest["opponent_adjusted"] is False
    assert default_as_of_week(schedule, pbp_ids) == 4  # max completed∩PBP week is 3


def test_eligibility_excludes_401868140_when_pbp_is_partial() -> None:
    """Official FINAL 49-7 plus a Q2 28-0 cut is fail-closed exclude."""
    partial = [
        {
            "game_id": DELAYED_GAME_ID,
            "id": n,
            "period": period,
            "end.homeScore": home,
            "end.awayScore": 0,
            "type.text": "Passing Touchdown",
            "drive.id": f"d{n}",
            "clock.displayValue": clock,
        }
        for n, (period, home, clock) in enumerate(
            ((1, 7, "6:27"), (1, 14, "4:25"), (2, 21, "12:24"), (2, 28, "10:27")),
            start=1,
        )
    ]
    final_row = _sched(
        DELAYED_GAME_ID,
        status="STATUS_FINAL",
        week=1,
        home_score=OFFICIAL_HOME_SCORE,
        away_score=OFFICIAL_AWAY_SCORE,
        home="Jacksonville State Gamecocks",
        away="Eastern Kentucky Colonels",
    )
    delayed_row = _sched(
        DELAYED_GAME_ID,
        status="STATUS_DELAYED",
        week=1,
        home_score=21,
        away_score=0,
        home="Jacksonville State Gamecocks",
        away="Eastern Kentucky Colonels",
    )
    for row in (final_row, delayed_row):
        manifest = build_eligibility_manifest(
            [row],
            {DELAYED_GAME_ID},
            as_of_week=3,
            as_of="20260915",
            plays=partial,
        )
        game = manifest["games"][0]
        assert game["included"] is False
        assert game["reason"] == "excluded_incomplete_pbp"
        assert manifest["eligible_count"] == 0
        audit = manifest.get("pbp_audit_401868140") or {}
        assert audit.get("complete_through_final") is False


def test_filter_plays_drops_live_and_current_week() -> None:
    plays = [
        _play(game_id="g-final", week=1, EPA=0.2),
        _play(game_id="g-live", week=2, EPA=9.0, id=2),
        _play(game_id="g-final", week=3, EPA=4.0, id=3),
    ]
    kept = filter_eligible_plays(plays, {"g-final"}, as_of_week=3)
    assert {p["game_id"] for p in kept} == {"g-final"}
    assert {p["week"] for p in kept} == {1}


def test_epa_success_label_is_gt_zero_not_standard_sr() -> None:
    plays = [
        _play(id=1, EPA=0.4, EPA_success=True, statYardage=6),
        _play(id=2, EPA=-0.3, EPA_success=False, statYardage=1),
    ]
    audit = audit_epa_success(plays)
    assert audit["verdict"] == "EPA_success_matches_EPA_gt_0"
    assert standard_success(_play(down=1, distance=10, statYardage=5)) is True
    rows = team_game_raw_metrics(plays)
    assert rows[0]["opponent_adjusted"] is False
    assert rows[0]["success_rate"] == 0.5


def test_team_game_table_has_off_def_and_opportunity() -> None:
    plays = [
        _play(
            id=1,
            pos_team="Georgia Bulldogs",
            def_pos_team="Clemson Tigers",
            EPA=0.2,
            EPA_success=True,
            **{"start.yardsToEndzone": 35, "type.text": "Passing Touchdown", "statYardage": 35},
        ),
        _play(
            id=2,
            pos_team="Clemson Tigers",
            def_pos_team="Georgia Bulldogs",
            EPA=-0.4,
            EPA_success=False,
            statYardage=1,
            **{"drive.id": "d2", "start.yardsToEndzone": 80},
        ),
    ]
    table = compose_team_game_table(plays)
    assert len(table) == 2
    uga = next(r for r in table if r["team"] == "Georgia Bulldogs")
    assert uga["opponent_adjusted"] is False
    assert uga["product_label"] == PRODUCT_LABEL
    assert uga["off_success_rate_label"] == SUCCESS_RATE_LABEL
    assert uga["off_success_rate"] == 1.0
    assert uga["def_success_rate"] == 0.0
    assert uga["scoring_opportunities"] == 1
    assert uga["points_per_opportunity"] == 6
    assert uga["pace_plays"] == 1


def test_pipeline_synthetic_slate_validates() -> None:
    schedule = [
        _sched("g-final", status="STATUS_FINAL", week=1, home_score=42, away_score=26),
        _sched("g-live", status="IN_PROGRESS", week=2, home_score=21, away_score=7),
        _sched("g-ht", status="STATUS_HALFTIME", week=2, home_score=10, away_score=10),
    ]
    plays = [
        _play(game_id="g-final", week=1, id=1, EPA=0.3, EPA_success=True),
        _play(
            game_id="g-final",
            week=1,
            id=2,
            pos_team="Clemson Tigers",
            def_pos_team="Georgia Bulldogs",
            EPA=-0.1,
            EPA_success=False,
            **{"drive.id": "d2"},
        ),
        _play(game_id="g-live", week=2, id=3, EPA=5.0, EPA_success=True),
        _play(game_id="g-ht", week=2, id=4, EPA=4.0, EPA_success=True),
    ]
    result = run_research_pipeline(
        as_of="20260915",
        as_of_week=3,
        dest_dir=Path("/tmp/cfb-w1-unit"),
        allow_fetch=False,
        plays=plays,
        schedule_rows=schedule,
        write_artifacts=False,
        commit_ops=False,
    )
    manifest = result["manifest"]
    table = result["table"]
    validation = result["validation"]
    assert manifest["eligible_count"] == 1
    assert manifest["eligible_game_ids"] == ["g-final"]
    assert {r["game_id"] for r in table} == {"g-final"}
    assert all(r["week"] < 3 for r in table)
    assert all(r["opponent_adjusted"] is False for r in table)
    assert validation["checks"]["zero_unfinished_rows"] is True
    assert validation["checks"]["included_count_equals_manifest_eligible"] is True
    assert validation["checks"]["leakage_week_lt_as_of"] is True
    assert validation["checks"]["opponent_adjusted_false_all_rows"] is True
    assert validation["checks"]["cfbd_unused"] is True
    assert validation["passed"] is True
    assert result["summary"]["not_ke_ratings"] is True
    assert result["summary"]["sp_plus_compose_changed"] is False
    assert result["summary"]["kei_or_edge_board"] is False


def test_validate_rejects_unfinished_and_leakage() -> None:
    manifest = {
        "eligible_game_ids": ["g1"],
        "eligible_count": 1,
        "historical_lake_write": False,
        "cfbd_used": False,
    }
    bad_unfinished = [
        {
            "game_id": "g-live",
            "week": 1,
            "opponent_adjusted": False,
            "product_label": PRODUCT_LABEL,
        }
    ]
    val = validate_outputs(
        bad_unfinished,
        manifest,
        as_of_week=3,
        field_stats={},
        pbp_sha256=None,
        schedule_sha256=None,
    )
    assert val["checks"]["zero_unfinished_rows"] is False
    assert val["passed"] is False

    leaked = [
        {
            "game_id": "g1",
            "week": 3,
            "opponent_adjusted": False,
            "product_label": PRODUCT_LABEL,
        }
    ]
    val2 = validate_outputs(
        leaked,
        manifest,
        as_of_week=3,
        field_stats={},
        pbp_sha256=None,
        schedule_sha256=None,
    )
    assert val2["checks"]["leakage_week_lt_as_of"] is False

    adj = [
        {
            "game_id": "g1",
            "week": 1,
            "opponent_adjusted": True,
            "product_label": PRODUCT_LABEL,
        }
    ]
    val3 = validate_outputs(
        adj,
        manifest,
        as_of_week=3,
        field_stats={},
        pbp_sha256=None,
        schedule_sha256=None,
    )
    assert val3["checks"]["opponent_adjusted_false_all_rows"] is False


def test_pipeline_module_has_no_cfbd_or_kei_wiring() -> None:
    src = Path(__file__).resolve().parents[1] / "src/services/cfb_warehouse/team_game_w1_2026.py"
    text = src.read_text(encoding="utf-8")
    assert "import cfbd" not in text
    assert "cfbd_get(" not in text
    assert "collegefootballdata.com" not in text
    assert "build_kei" not in text
    assert "kei_or_edge_board" in text
