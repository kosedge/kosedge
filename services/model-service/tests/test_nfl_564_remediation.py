"""NFL #564 remediation — outcomes, EPA authority, overlays off, integrity."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from src.services.nfl_epa_authority import (
    NFL_2026_W1_OUTCOMES,
    NFL_2026_W2_SLATE,
    NflWlPersistRefused,
    build_multi_matchup_integrity_report,
    merge_readiness_with_outcomes_coverage,
    overlays_must_stay_off,
    rematerialize_week_epa_overlays_off,
    resolve_adhoc_simulation_strength,
    resolve_current_nfl_board_week_from_rows,
    week1_outcomes_coverage_fixture,
)
from src.services.nfl_regression_diagnose import LOCKED_SCORING, locked_scoring_snapshot

ROUTES_NFL = Path(__file__).resolve().parents[1] / "src" / "routes" / "nfl.py"
PUBLIC_FLAG = (
    Path(__file__).resolve().parents[3]
    / "apps"
    / "web"
    / "lib"
    / "cfb-edge-board-public.ts"
)


def test_week1_outcomes_fixture_covers_completed_slate() -> None:
    cov = week1_outcomes_coverage_fixture()
    assert cov["before_ingest_sample_size"] == 0
    assert cov["after_ingest_sample_size"] == 16
    assert cov["sample_size"] == 16
    assert cov["last_game_date"] == "2026-09-14"
    assert len(NFL_2026_W1_OUTCOMES) == 16
    keys = {row["key"] for row in NFL_2026_W1_OUTCOMES}
    assert {"ATL@PIT", "CHI@CAR", "SF@LAR", "DEN@KC"} <= keys


def test_readiness_sample_size_folds_outcomes_when_snapshot_empty() -> None:
    before = merge_readiness_with_outcomes_coverage(
        snapshot_sample_size=0,
        snapshot_last_game_date=None,
        snapshot_calendar_days=0,
        outcomes_sample_size=0,
        outcomes_last_game_date=None,
        outcomes_calendar_days=0,
    )
    after = merge_readiness_with_outcomes_coverage(
        snapshot_sample_size=0,
        snapshot_last_game_date=None,
        snapshot_calendar_days=0,
        outcomes_sample_size=16,
        outcomes_last_game_date=date(2026, 9, 14),
        outcomes_calendar_days=5,
    )
    assert before["sample_size"] == 0
    assert before["coverage_source"] == "quality_snapshot"
    assert after["sample_size"] == 16
    assert after["coverage_source"] == "nfl_market_outcomes"
    assert after["last_game_date"] == date(2026, 9, 14)


def test_current_week_advances_past_completed_week1() -> None:
    rows = []
    for game in NFL_2026_W1_OUTCOMES:
        rows.append(
            {
                "week": 1,
                "game_date": game["game_date"],
                "home_score": game["home_score"],
                "away_score": game["away_score"],
                "has_outcome": True,
            }
        )
    for game in NFL_2026_W2_SLATE:
        rows.append(
            {
                "week": 2,
                "game_date": game["game_date"],
                "home_score": None,
                "away_score": None,
                "has_outcome": False,
            }
        )
    stuck = resolve_current_nfl_board_week_from_rows(
        [
            {
                "week": 1,
                "game_date": "2026-09-14",
                "home_score": None,
                "away_score": None,
                "has_outcome": False,
            },
            {
                "week": 2,
                "game_date": "2026-09-17",
                "home_score": None,
                "away_score": None,
                "has_outcome": False,
            },
        ],
        today=date(2026, 9, 15),
    )
    advanced = resolve_current_nfl_board_week_from_rows(rows, today=date(2026, 9, 15))
    assert stuck == 1
    assert advanced == 2


def test_adhoc_uses_packaged_epa_not_win_loss() -> None:
    resolved = resolve_adhoc_simulation_strength(
        home_abbr="ATL",
        away_abbr="CAR",
        context_offense_home=0.90,
        context_defense_home=0.92,
        context_offense_away=0.90,
        context_defense_away=0.92,
        home_record_summary="0-1",
        away_record_summary="0-1",
    )
    assert resolved.source == "packaged_epa_prior"
    assert resolved.overlays_off is True
    assert abs(resolved.offense_index_home - 0.90) > 0.02
    assert abs(resolved.offense_index_away - 0.90) > 0.02


def test_adhoc_refuses_when_packaged_epa_missing() -> None:
    try:
        resolve_adhoc_simulation_strength(
            home_abbr="ZZZ",
            away_abbr="YYY",
            context_offense_home=1.12,
            context_defense_home=1.12,
            context_offense_away=0.90,
            context_defense_away=0.92,
            home_record_summary="1-0",
            away_record_summary="0-1",
            priors={},
        )
    except NflWlPersistRefused as exc:
        assert exc.reason == "packaged_epa_unavailable"
    else:
        raise AssertionError("expected NflWlPersistRefused")


def test_adhoc_route_source_is_epa_or_refuse() -> None:
    src = ROUTES_NFL.read_text(encoding="utf-8")
    start = src.index("def run_nfl_simulation")
    end = src.index("\ndef _nfl_web_launch_bundle_candidates", start)
    fn = src[start:end]
    assert "resolve_adhoc_simulation_strength" in fn
    assert "nfl_wl_persist_refused" in fn
    assert "production_promote" in fn


def test_overlays_stay_off_after_week1_when_forced() -> None:
    assert overlays_must_stay_off(completed_reg_season=0, force_overlays_off=False) is True
    assert overlays_must_stay_off(completed_reg_season=16, force_overlays_off=False) is False
    assert overlays_must_stay_off(completed_reg_season=16, force_overlays_off=True) is True


def test_w2_remat_artifact_overlays_off_and_checksum() -> None:
    remat = rematerialize_week_epa_overlays_off()
    assert remat["production_promote"] is False
    assert remat["overlays_off"] is True
    assert remat["game_count"] == 16
    assert remat["checksum_sha256"]
    assert len(remat["checksum_sha256"]) == 64
    for game in remat["games"]:
        assert game["strength_source"] == "packaged_epa_prior"
        assert game["overlays"]["personnel_efficiency"] is False
        assert game["overlays"]["injuries_depth"] is False
        assert game["overlays"]["personnel_margin_points"] == 0.0
        assert game["overlays"]["injuries_margin_points"] == 0.0
    scoring = locked_scoring_snapshot()
    assert scoring["base_total_points"] == LOCKED_SCORING["base_total_points"]
    assert scoring["home_field_points"] == LOCKED_SCORING["home_field_points"]


def test_multi_matchup_integrity_report_passes_without_overlay_leak() -> None:
    remat = rematerialize_week_epa_overlays_off()
    report = build_multi_matchup_integrity_report(remat=remat)
    assert report["passed"] is True
    assert report["double_count_check"] == "pass"
    assert report["recommendation"] == "HOLD_PUBLIC"
    assert report["production_promote"] is False
    assert len(report["matchups"]) >= 4
    assert "ATL@PIT" in report["material_wl_vs_epa_keys"]
    assert "CHI@CAR" in report["material_wl_vs_epa_keys"]
    assert not report["overlay_leaks"]


def test_public_board_flag_stays_false() -> None:
    text = PUBLIC_FLAG.read_text(encoding="utf-8")
    assert "NFL_EDGE_BOARD_PUBLIC_ENABLED = false" in text
