"""D-1 / v1 P-3 drop-one fixtures — any injury path (C-7).

No live apply. Overlays stay off. No 2024/2025 fit or holdout join.
"""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import pytest

from src.services.nfl_handicapping_framework import compute_nfl_projection_decomposition
from src.services.nfl_injury_nowcast import (
    _aggregate_team_nowcast,
    _merge_roster_continuity_into_nowcast,
    compute_team_week_injury_severity,
    fetch_nfl_injury_nowcast,
)
from src.services.nfl_injury_null_contract import (
    FLAG_INJURY_PARTIAL_OFF,
    FLAG_MISSING_KOSEDGE_INJURY_NOWCAST,
    FLAG_RAW_INJURIES_2026_REFUSED,
    FIT_PROTOCOL_ID,
    GAME_LINE_INJURY_GUARDS,
    GAME_LINE_NOWCAST_KEYS,
    IDENTITY_RULE_SEASON_FALLBACK,
    IDENTITY_RULE_TEAM_MATCH,
    IDENTITY_RULE_UNRESOLVED,
    INJURY_FIELD_SHORT_NAME,
    INJURY_PATH_FIELDS,
    MISSING_DISCLOSURE,
    FitRowFailure,
    apply_injury_residual_once,
    bound_hash,
    build_injury_accounting_ledger,
    config_hash,
    count_identity_resolutions,
    empty_nowcast_payload,
    evaluate_fit_as_of,
    impact_triple,
    parse_fit_kickoff_utc,
    refuse_raw_injury_source,
    resolve_fit_player_identity,
    resolve_nfl_totals_env,
    resolve_unscaled_indices,
    write_sealed_injury_export,
)
from pathlib import Path

from src.services.nfl_season_engine.qb_premium import fetch_inactive_qb_ids
from src.services.nfl_simulator import NflGameInputs, _build_totals_adjustments, simulate_nfl_game

TASKS_SRC = (Path(__file__).resolve().parents[1] / "src" / "tasks.py").read_text()


COMPLETE_RESIDUAL = {
    "off_home": 0.4,
    "def_home": 0.2,
    "ol_home": 0.1,
    "off_away": 0.3,
    "def_away": 0.15,
    "ol_away": 0.05,
}

COMPLETE_FRAMEWORK = dict(
    offense_index_home=1.0,
    offense_index_away=1.0,
    defense_index_home=1.0,
    defense_index_away=1.0,
    rest_days_home=7.0,
    rest_days_away=7.0,
    matchup_adjustments={},
    totals_adjustments={},
    injury_nowcast_impact_home=0.18,
    injury_nowcast_impact_away=0.25,
    injury_nowcast_freshness_home_hours=20.0,
    injury_nowcast_freshness_away_hours=18.0,
    injury_nowcast_confidence_home=0.74,
    injury_nowcast_confidence_away=0.71,
    injury_nowcast_offense_multiplier_home=0.98,
    injury_nowcast_offense_multiplier_away=0.95,
    injury_nowcast_defense_multiplier_home=1.01,
    injury_nowcast_defense_multiplier_away=1.06,
)

COMPLETE_SIM_INJURY = dict(
    injury_nowcast_confidence_home=0.8,
    injury_nowcast_confidence_away=0.7,
    injury_nowcast_impact_home=0.3,
    injury_nowcast_impact_away=0.2,
    injury_nowcast_offense_multiplier_home=0.96,
    injury_nowcast_offense_multiplier_away=0.97,
    injury_nowcast_defense_multiplier_home=1.03,
    injury_nowcast_defense_multiplier_away=1.02,
)


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _EmptyInjurySession:
    def execute(self, sql, params=None):
        query = str(sql)
        if "nfl_dp_injuries" in query or "nfl_roster_continuity" in query:
            return _Result([])
        raise AssertionError(f"Unexpected SQL: {query}")


def test_p3_1_empty_aggregate_is_null_not_zero() -> None:
    empty = _aggregate_team_nowcast([])
    assert empty["impact_score"] is None
    assert empty["offense_multiplier"] is None
    assert empty["defense_multiplier"] is None
    assert empty["confidence"] is None
    assert empty["source"] is None
    assert FLAG_MISSING_KOSEDGE_INJURY_NOWCAST in empty["flags"]


def test_p3_2_fetch_no_rows_null_keys() -> None:
    nowcast = fetch_nfl_injury_nowcast(
        _EmptyInjurySession(), season_year=2023, home_team="KC", away_team="BUF"
    )
    assert nowcast["home"]["impact_score"] is None
    assert nowcast["away"]["impact_score"] is None
    home, away, diff = impact_triple(
        nowcast["home"]["impact_score"], nowcast["away"]["impact_score"]
    )
    assert home is None and away is None and diff is None
    assert FLAG_MISSING_KOSEDGE_INJURY_NOWCAST in nowcast["flags"]


def test_p3_3_4_5_drop_one_impact_nulls_diff() -> None:
    home, away, diff = impact_triple(0.2, None)
    assert home == 0.2 and away is None and diff is None
    home, away, diff = impact_triple(None, 0.3)
    assert home is None and away == 0.3 and diff is None
    home, away, diff = impact_triple(0.2, 0.05)
    assert diff == pytest.approx(0.15)
    home, away, diff = impact_triple(0.0, 0.0)
    assert home == 0.0 and away == 0.0 and diff == 0.0


def test_p3_6_severity_missing_team_week_is_null() -> None:
    empty = compute_team_week_injury_severity([])
    assert empty["impact_score"] is None
    assert empty["offense_impact"] is None
    home, away, diff = impact_triple(empty.get("impact_score"), None)
    assert home is None and diff is None


@pytest.mark.parametrize("field", INJURY_PATH_FIELDS)
def test_p3_7_framework_drop_one_skips_injuries_depth(field: str) -> None:
    complete = compute_nfl_projection_decomposition(**COMPLETE_FRAMEWORK)
    injuries = complete["factor_contributions"]["injuries_depth"]
    assert injuries["available"] is False
    assert injuries["margin_points"] is None
    assert injuries["total_points"] is None

    dropped = dict(COMPLETE_FRAMEWORK)
    dropped[field] = None
    out = compute_nfl_projection_decomposition(**dropped)
    inj = out["factor_contributions"]["injuries_depth"]
    assert inj["available"] is False
    assert inj["margin_points"] is None
    assert inj["total_points"] is None
    short = INJURY_FIELD_SHORT_NAME[field]
    assert short in inj["raw_signals"]["dropped_fields"]


@pytest.mark.parametrize("field", INJURY_PATH_FIELDS)
def test_p3_8_totals_drop_one_does_not_invent_injury_term(field: str) -> None:
    complete = NflGameInputs(
        game_id="p3-8",
        home_team="KC",
        away_team="BUF",
        home_off_epa_5g=0.12,
        away_off_epa_5g=0.10,
        home_pass_rate_5g=0.60,
        away_pass_rate_5g=0.58,
        **COMPLETE_SIM_INJURY,
    )
    dropped = NflGameInputs(
        game_id="p3-8",
        home_team="KC",
        away_team="BUF",
        home_off_epa_5g=0.12,
        away_off_epa_5g=0.10,
        home_pass_rate_5g=0.60,
        away_pass_rate_5g=0.58,
        **{**COMPLETE_SIM_INJURY, field: None},
    )
    complete_adj = _build_totals_adjustments(complete)
    dropped_adj = _build_totals_adjustments(dropped)
    assert "injury_total_signal" not in complete_adj["components"]
    assert "injury_total_signal" not in dropped_adj["components"]
    assert complete_adj["components"]["injury_total_signal_applied"] is False
    assert dropped_adj["components"]["injury_total_signal_applied"] is False
    short = INJURY_FIELD_SHORT_NAME[field]
    assert short in dropped_adj["components"]["injury_dropped_fields"]


def test_p3_9_simulator_missing_disclosure() -> None:
    out = simulate_nfl_game(
        NflGameInputs(game_id="p3-9", home_team="KC", away_team="BUF"),
        simulations=200,
        seed=3,
    )
    block = out["diagnostics"]["injury_nowcast"]
    assert block["disclosure"] == MISSING_DISCLOSURE
    assert block["applied"] is False
    assert block["home_impact"] is None
    assert block["away_impact"] is None


FULL_STRENGTH_INDICES = {
    "offense_home": 1.12,
    "offense_away": 0.94,
    "defense_home": 1.03,
    "defense_away": 0.88,
}


@pytest.mark.parametrize("field", INJURY_PATH_FIELDS)
def test_p3_10_12_index_scale_and_multiplier_default_absent(field: str) -> None:
    assert "float(offense_home) * float(home_off_mult)" not in TASKS_SRC
    assert 'home_nowcast.get("offense_multiplier")) or 1.0' not in TASKS_SRC
    assert 'home_nowcast.get("impact_score")) or 0.0' not in TASKS_SRC
    complete_fields = {key: 0.97 for key in INJURY_PATH_FIELDS}
    complete = resolve_unscaled_indices(
        full_strength=FULL_STRENGTH_INDICES, injury_fields=complete_fields
    )
    assert complete["index_scale_applied"] is False
    assert complete["indices_equal_full_strength"] is True
    assert complete["current"] == FULL_STRENGTH_INDICES
    dropped_fields = dict(complete_fields)
    dropped_fields[field] = None
    dropped = resolve_unscaled_indices(
        full_strength=FULL_STRENGTH_INDICES, injury_fields=dropped_fields
    )
    assert dropped["index_scale_applied"] is False
    assert dropped["indices_equal_full_strength"] is True
    assert dropped["current"] == complete["current"] == FULL_STRENGTH_INDICES
    assert dropped["fields"][field] is None
    assert dropped["fields"][field] != 1.0
    assert field in dropped["dropped_fields"]
    assert dropped["guards"]["index_scale_applied"] is False


def test_p3_11_residual_drop_one_unit_is_null() -> None:
    baseline = {"predicted_margin": 3.0, "predicted_total": 44.0, "spread_home": -3.0, "total_mean": 44.0}
    complete = apply_injury_residual_once(baseline_markets=baseline, components=COMPLETE_RESIDUAL)
    assert complete["complete"] is True
    assert complete["applied"] is False
    assert complete["adjusted_markets"] is not None

    dropped = dict(COMPLETE_RESIDUAL)
    dropped["off_home"] = None
    partial = apply_injury_residual_once(baseline_markets=baseline, components=dropped)
    assert partial["complete"] is False
    assert partial["applied"] is False
    assert partial["components"]["off_home"] is None
    assert partial["delta"]["margin"] is None
    assert FLAG_INJURY_PARTIAL_OFF in partial["flags"]
    assert FLAG_MISSING_KOSEDGE_INJURY_NOWCAST in partial["flags"]


def test_p3_13_tasks_supervised_no_or_zero() -> None:
    assert 'home_nowcast.get("impact_score")) or 0.0' not in TASKS_SRC
    assert 'away_nowcast.get("impact_score")) or 0.0' not in TASKS_SRC
    assert 'get("impact_score", 0.0)' not in TASKS_SRC


def test_p3_14_sealed_export_refuses_raw_maps(tmp_path) -> None:
    assert refuse_raw_injury_source("injuries_2026")
    assert refuse_raw_injury_source("/tmp/nflverse_injuries.parquet")
    assert refuse_raw_injury_source("raw_injury_report.csv")
    with pytest.raises(ValueError, match=FLAG_RAW_INJURIES_2026_REFUSED):
        write_sealed_injury_export(
            str(tmp_path / "injuries_2026.json"),
            games=[],
            players=[],
            code_sha="abc",
            config_hash_value="def",
            source_name="injuries_2026",
        )


def test_ledger_baseline_markets_applied_false() -> None:
    ledger = build_injury_accounting_ledger(
        baseline_markets={"spread_home": -3.0, "total_mean": 44.0, "home_win_prob": 0.58},
        home_nowcast=_aggregate_team_nowcast([]),
        away_nowcast=_aggregate_team_nowcast([]),
    )
    assert ledger["applied"] is False
    assert ledger["adjusted_markets"] is None
    assert ledger["baseline_markets"]["spread_home"] == -3.0
    assert ledger["keys"]["home_injury_impact"] is None
    assert ledger["keys"]["diff_injury_impact"] is None
    assert ledger["guards"] == GAME_LINE_INJURY_GUARDS
    assert ledger["disclosure"] == MISSING_DISCLOSURE
    assert FLAG_MISSING_KOSEDGE_INJURY_NOWCAST in ledger["flags"]


def test_config_hash_includes_nfl_totals_unset_or_finite(monkeypatch) -> None:
    monkeypatch.delenv("NFL_TOTALS_INJURY_WEIGHT", raising=False)
    monkeypatch.setenv("NFL_TOTALS_PASS_RATE_WEIGHT", "3.2")
    resolved = resolve_nfl_totals_env()
    assert resolved["NFL_TOTALS_INJURY_WEIGHT"] is None
    assert resolved["NFL_TOTALS_PASS_RATE_WEIGHT"] == 3.2
    digest = config_hash()
    assert len(digest) == 64
    monkeypatch.setenv("NFL_TOTALS_INJURY_WEIGHT", "nan")
    with pytest.raises(ValueError, match="STOP"):
        resolve_nfl_totals_env()


def test_sealed_export_writes_player_and_game(tmp_path) -> None:
    path = str(tmp_path / "sealed.json")
    out = write_sealed_injury_export(
        path,
        games=[{"game_id": "2023_01_KC_DET", "applied": False}],
        players=[{"player_id": "00-001", "unit": "off", "identity_resolved": True}],
        code_sha="code",
        config_hash_value="cfg",
        fit_years=[2021, 2022, 2023],
    )
    assert out["n_games"] == 1
    assert out["n_players"] == 1
    assert os.path.exists(path)
    assert os.path.exists(path + ".sha256")


def test_sealed_export_rejects_holdout_fit_years(tmp_path) -> None:
    with pytest.raises(ValueError, match="disjoint"):
        write_sealed_injury_export(
            str(tmp_path / "bad.json"),
            games=[],
            players=[],
            code_sha="c",
            config_hash_value="h",
            fit_years=[2023, 2024],
        )


def test_qb_premium_sql_joins_rosters_not_missing_columns() -> None:
    src = inspect.getsource(fetch_inactive_qb_ids)
    assert "LEFT JOIN nfl_dp_rosters" in src
    assert "COALESCE(position, '')" not in src or "r.position" in src
    assert "COALESCE(status, report_status" not in src


def test_overlay_defaults_remain_locked() -> None:
    assert "force_overlays_off: bool = True" in TASKS_SRC
    assert "unlock_overlays: bool = False" in TASKS_SRC


def test_kei_publish_identity_untouched() -> None:
    from src.services.nfl_kei_week1_reprice import WEEK1_KEI_PUBLISH_MUTATE_FAIR

    assert WEEK1_KEI_PUBLISH_MUTATE_FAIR is False
    beat = Path(__file__).resolve().parents[1] / "src" / "celerybeat_schedule.py"
    beat_text = beat.read_text().lower()
    assert "nfl_injury_kei" not in beat_text
    assert "kei_cadence" not in beat_text


CONTINUITY_COMPLETE = {
    "adjustment_count": 1,
    "offense_multiplier": 0.97,
    "defense_multiplier": 1.04,
    "confidence": 0.8,
    "impact_score": 0.11,
    "top_drivers": [{"kind": "roster_continuity", "player_name": "Star", "impact_score": -0.4}],
}


def test_g1_merge_roster_continuity_does_not_fill_empty_nowcast() -> None:
    empty = empty_nowcast_payload()
    merged = _merge_roster_continuity_into_nowcast(empty, CONTINUITY_COMPLETE)
    for key in GAME_LINE_NOWCAST_KEYS:
        assert merged[key] is None
    assert FLAG_MISSING_KOSEDGE_INJURY_NOWCAST in merged["flags"]
    assert merged["roster_continuity_adjustment_count"] == 1
    assert isinstance(merged.get("roster_continuity"), dict)
    assert GAME_LINE_INJURY_GUARDS["continuity_as_second_line"] is False


@pytest.mark.parametrize("field", GAME_LINE_NOWCAST_KEYS)
def test_g1_merge_roster_continuity_drop_one_does_not_fill(field: str) -> None:
    complete_nowcast = {
        "impact_score": 0.22,
        "offense_multiplier": 0.96,
        "defense_multiplier": 1.03,
        "confidence": 0.7,
        "flags": [],
        "top_drivers": [],
    }
    dropped = dict(complete_nowcast)
    dropped[field] = None
    merged = _merge_roster_continuity_into_nowcast(dropped, CONTINUITY_COMPLETE)
    assert merged[field] is None
    if field == "impact_score":
        assert merged["impact_score"] is None
    else:
        assert merged.get(field) is None


def test_g4_fit_kickoff_utc_normalized_and_missing_gametime_fails() -> None:
    edt = parse_fit_kickoff_utc("2018-09-09", "13:00:00")
    assert edt.tzinfo is not None
    assert edt.utcoffset().total_seconds() == 0
    assert edt.isoformat() == "2018-09-09T17:00:00+00:00"
    est = parse_fit_kickoff_utc("2018-12-09", "13:00:00")
    assert est.isoformat() == "2018-12-09T18:00:00+00:00"
    with pytest.raises(FitRowFailure, match="missing gametime"):
        parse_fit_kickoff_utc("2018-09-09", None)
    with pytest.raises(FitRowFailure, match="missing gametime"):
        parse_fit_kickoff_utc("2018-09-09", "")
    with pytest.raises(FitRowFailure, match="23:59:59"):
        parse_fit_kickoff_utc("2018-09-09", "23:59:59")
    ok = evaluate_fit_as_of(
        report_time="2018-09-08T12:00:00+00:00",
        gameday="2018-09-09",
        gametime="13:00",
    )
    assert ok["as_of_ok"] is True
    assert ok["kickoff_utc"].tzinfo is not None
    with pytest.raises(FitRowFailure, match="not before kickoff"):
        evaluate_fit_as_of(
            report_time="2018-09-09T18:00:00+00:00",
            gameday="2018-09-09",
            gametime="13:00",
        )


def test_g5_identity_rule_and_season_fallback_counts() -> None:
    roster_by_team = {"KC": {"00-001"}, "BUF": {"00-002"}}
    roster_season = {"00-001", "00-002", "00-003"}
    team = resolve_fit_player_identity(
        player_id="00-001",
        team="KC",
        roster_by_team=roster_by_team,
        roster_season=roster_season,
    )
    fallback = resolve_fit_player_identity(
        player_id="00-003",
        team="KC",
        roster_by_team=roster_by_team,
        roster_season=roster_season,
    )
    missing = resolve_fit_player_identity(
        player_id="00-999",
        team="KC",
        roster_by_team=roster_by_team,
        roster_season=roster_season,
    )
    assert team["identity_rule"] == IDENTITY_RULE_TEAM_MATCH
    assert fallback["identity_rule"] == IDENTITY_RULE_SEASON_FALLBACK
    assert missing["identity_rule"] == IDENTITY_RULE_UNRESOLVED
    assert missing["identity_resolved"] is False
    counts = count_identity_resolutions([team, fallback, missing])
    assert counts[IDENTITY_RULE_TEAM_MATCH] == 1
    assert counts[IDENTITY_RULE_SEASON_FALLBACK] == 1
    assert counts["season_fallback"] == 1
    assert counts[IDENTITY_RULE_UNRESOLVED] == 1


def test_k3_qb1_points_per_index_unit_is_named() -> None:
    from src.services.nfl_season_engine.injury_paths import (
        QB1_FLOOR_SPREAD_POINTS,
        QB1_INDEX_UNITS,
        QB1_POINTS_PER_INDEX_UNIT,
        player_offense_value,
    )
    from src.services.nfl_season_engine.types import PlayerRole

    assert QB1_POINTS_PER_INDEX_UNIT == 12.5
    assert QB1_INDEX_UNITS == 0.12
    assert QB1_FLOOR_SPREAD_POINTS == 1.5
    qb1 = PlayerRole(player_key="qb1", player_name="QB1", team="KC", position="QB", depth_order=1)
    assert player_offense_value(qb1) == QB1_INDEX_UNITS
    assert player_offense_value(qb1) * QB1_POINTS_PER_INDEX_UNIT == QB1_FLOOR_SPREAD_POINTS


def test_k2_bound_hash_reproduces_d4_v1_inputs(monkeypatch) -> None:
    for key in list(os.environ):
        if key.startswith("NFL_TOTALS_"):
            monkeypatch.delenv(key, raising=False)
    assert config_hash() == (
        "0d491abef53cb67e82106dda184fb40fbe21fc3883afd8313fd87108cf40d6cb"
    )
    assert bound_hash(code_sha="3fa9f024360efd70209b7348e6c812a588fe1c74") == (
        "638198a551ad192180d635a8edd1406b5aa8f1f47fbb026a98332ffee09e7db5"
    )
    assert FIT_PROTOCOL_ID == "injury-residual-cal-v2"
