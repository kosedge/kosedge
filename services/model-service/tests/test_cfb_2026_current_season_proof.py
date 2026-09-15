"""2026 current-season SDV proof — no CFBD, no historical-lake writes."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

try:
    import pandas as pd  # noqa: F401
except ImportError:  # pragma: no cover — CI image has no pandas
    pd = None  # type: ignore[assignment]

from src.services.cfb_warehouse.current_season_2026 import (
    COMPLETED_STATUSES,
    FORBIDDEN_HOST_FRAGMENTS,
    METRIC_FIELD_REQUIREMENTS,
    PBP_FILENAME,
    SCHEDULE_FILENAME,
    SEASON,
    assert_not_historical_write,
    classify_completion,
    classify_status,
    field_support_matrix,
    path_convention,
    reconcile_coverage,
    research_dest_dir,
)
from src.services.cfb_warehouse.pbp import PBP_CORE_COLUMNS, PBP_SEASONS
from src.services.cfb_warehouse.paths import (
    HD_RAW_PBP,
    HD_RAW_PBP_CURRENT,
    REPO_RAW_PBP,
    REPO_ROOT,
    hd_pbp_current_target,
)


def test_season_and_sdv_filenames() -> None:
    assert SEASON == 2026
    assert PBP_FILENAME == "play_by_play_2026.parquet"
    assert SCHEDULE_FILENAME == "cfb_schedule_2026.parquet"


def test_historical_pbp_seasons_not_extended() -> None:
    """Do not rewrite 2014–2025 ingest range as if 2026 replaced it."""
    assert PBP_SEASONS == tuple(range(2014, 2026))
    assert 2026 not in PBP_SEASONS


def test_repo_root_is_monorepo_not_service_data_tree() -> None:
    if (REPO_ROOT / "apps" / "web").is_dir():
        assert (REPO_ROOT / "data" / "cfb").is_dir()
        assert REPO_ROOT.name != "model-service"


def test_path_convention_versions_current_away_from_historical() -> None:
    conv = path_convention("20260915")
    assert conv["historical_canonical_hd"] == str(HD_RAW_PBP)
    assert conv["current_season_hd_target"] == str(
        HD_RAW_PBP_CURRENT / "as_of_20260915"
    )
    assert conv["versioning"] == "raw/cfb/pbp_current/as_of_YYYYMMDD/"
    assert "pbp_current" in conv["vm_research_path"]
    assert "/raw/cfb/pbp/" not in conv["vm_research_path"].replace("pbp_current", "")
    dest = research_dest_dir("20260915")
    assert dest == Path(conv["vm_research_path"])
    assert dest.resolve() != HD_RAW_PBP.resolve()
    assert dest.resolve() != REPO_RAW_PBP.resolve()


def test_hd_target_helper() -> None:
    assert hd_pbp_current_target("2026-09-15") == HD_RAW_PBP_CURRENT / "as_of_20260915"


def test_refuse_historical_lake_write() -> None:
    try:
        assert_not_historical_write(HD_RAW_PBP / "play_by_play_2026.parquet")
    except RuntimeError as exc:
        assert "historical" in str(exc).lower()
    else:
        raise AssertionError("expected historical write to be refused")
    try:
        assert_not_historical_write(REPO_RAW_PBP / "play_by_play_2026.parquet")
    except RuntimeError as exc:
        assert "historical" in str(exc).lower()
    else:
        raise AssertionError("expected repo historical fallback write to be refused")


def test_cfbd_hosts_are_parked() -> None:
    assert "collegefootballdata.com" in FORBIDDEN_HOST_FRAGMENTS


def test_classify_status_final_and_scheduled() -> None:
    assert classify_status("STATUS_FINAL") == "completed"
    assert classify_status("Final") == "completed"
    assert classify_status("STATUS_SCHEDULED") == "not_completed"
    assert classify_status("STATUS_IN_PROGRESS") == "not_completed"
    assert classify_status("", completed_flag=True) == "completed"
    assert classify_status("", home_score=31, away_score=24) == "completed_inferred_from_scores"
    assert classify_status("WEIRD_TOKEN") == "unknown_status"
    assert "STATUS_FINAL" in COMPLETED_STATUSES


def test_classify_completion_does_not_treat_live_scores_as_done() -> None:
    live = classify_completion("STATUS_IN_PROGRESS", home_score=35, away_score=0)
    assert live["status_final"] is False
    assert live["actually_completed"] is False
    assert live["w1_eligibility"] == "excluded_unfinished_live"
    delayed_zero = classify_completion("STATUS_DELAYED", home_score=0, away_score=0)
    assert delayed_zero["actually_completed"] is False
    delayed_score = classify_completion("STATUS_DELAYED", home_score=21, away_score=0)
    assert delayed_score["actually_completed"] is True
    final = classify_completion("STATUS_FINAL", home_score=42, away_score=26)
    assert final["status_final"] is True
    assert final["actually_completed"] is True
    assert final["w1_eligibility"] == "eligible_completed"


def test_reconcile_coverage_reports_gaps() -> None:
    schedule = [
        {
            "game_id": "1",
            "status_class": "completed",
            "status_final": True,
            "actually_completed": True,
            "snapshot_bucket": "status_final",
            "week": 1,
        },
        {
            "game_id": "2",
            "status_class": "completed",
            "status_final": True,
            "actually_completed": True,
            "snapshot_bucket": "status_final",
            "week": 1,
        },
        {
            "game_id": "3",
            "status_class": "not_completed",
            "status_final": False,
            "actually_completed": False,
            "snapshot_bucket": "in_progress",
            "week": 2,
        },
        {
            "game_id": "4",
            "status_class": "not_completed",
            "status_final": False,
            "actually_completed": False,
            "snapshot_bucket": "in_progress",
            "week": 2,
        },
    ]
    cov = reconcile_coverage(schedule, ["1", "4", "9"])
    assert cov["completed_on_schedule"] == 2
    assert cov["completed_in_pbp"] == 1
    assert cov["completed_missing_pbp"] == 1
    assert cov["completed_missing_pbp_ids"] == ["2"]
    assert cov["status_final_in_pbp"] == 1
    assert cov["actually_completed_in_pbp"] == 1
    assert cov["actually_completed_missing_pbp"] == 1
    assert cov["pbp_reconcile"]["in_progress"] == 1
    assert cov["pbp_reconcile"]["unmatched"] == 1
    assert cov["w1_eligible_completed_in_pbp"] == 1
    assert cov["w1_excluded_unfinished_or_unmatched"] == 2
    assert cov["pbp_not_on_schedule"] == 1
    assert cov["pbp_not_completed_on_schedule"] == 1
    assert cov["schedule_without_pbp"] == 2
    assert cov["coverage_rate_completed"] == 0.5
    assert cov["by_week"]["1"]["completed_missing_pbp"] == 1
    assert any("STATUS_FINAL-in-snapshot" in g for g in cov["honest_gaps"])
    assert "not proof of every actually completed game" in cov["disclaimer"]


@pytest.mark.skipif(pd is None, reason="pandas not installed in this environment")
def test_field_support_matrix_core_and_metrics() -> None:
    import pandas as pd

    n = 5
    data = {c: [1] * n for c in PBP_CORE_COLUMNS}
    data["EPA"] = [0.1, 0.2, None, 0.0, -0.1]
    data["statYardage"] = [4, 15, 2, 0, 8]
    df = pd.DataFrame(data)
    matrix = field_support_matrix(df)
    assert matrix["core31_absent"] == []
    assert matrix["metrics"]["EPA"]["class"] == "SUPPORTED"
    assert matrix["metrics"]["explosiveness"]["class"] == "SUPPORTED"
    assert matrix["metrics"]["scoring_opportunity"]["class"] == "SUPPORTED"
    assert matrix["ppa_present"] is False
    assert "EPA" in METRIC_FIELD_REQUIREMENTS
    assert "start.yardsToEndzone" in METRIC_FIELD_REQUIREMENTS


@pytest.mark.skipif(pd is None, reason="pandas not installed in this environment")
def test_field_support_marks_absent_epa() -> None:
    import pandas as pd

    df = pd.DataFrame({"game_id": [1, 2], "down": [1, 2]})
    matrix = field_support_matrix(df)
    assert matrix["metrics"]["EPA"]["class"] == "UNSUPPORTED"
    assert "EPA" in matrix["core31_absent"]


def test_current_season_module_has_no_cfbd_calls() -> None:
    src = Path(__file__).resolve().parents[1] / "src/services/cfb_warehouse/current_season_2026.py"
    text = src.read_text(encoding="utf-8")
    assert "import cfbd" not in text
    assert "cfbd_get(" not in text
    assert "collegefootballdata.com" in text  # parked denylist only
    assert "api.collegefootballdata" in text
