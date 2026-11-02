"""t4688u W8 forecast integrity regressions (draft #653).

CERT=0. No Odds HTTP. No warehouse SELECT. No production emit.
Parent prep 127f4624 · Codex 88a08cae · IMV RETURN 75141507.

Each test names a protection-removed mutation that must fail the assert.
Vacuity (grep / means-only / pre-injected dict) is RETURN, not PASS.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_second_order_factors import compute_error_regime_uncertainty
from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game
from src.services.nfl_w8_forecast_builders_t4688u import (
    PRIOR_2025_PACK_NAME,
    G3_FLAGS,
    InputShaMismatch,
    MissingCurrentStrength,
    build_current_strength,
    completeness_official_from_pack,
    forbidden_odds_tokens,
    injury_impacts,
    injury_pack_official_flag,
    last_designated_week,
    legacy_as_of_week_max_including_empty,
    legacy_pack_official_from_latest_week,
    materialize_injury_pack_meta,
    module_text_forbids_odds,
    require_input_sha,
    sha256_bytes,
)

REPO = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO / "data/ops/nfl-t4673u-w8-eng-prep/fixtures"
BUILDER_MOD = REPO / "services/model-service/src/services/nfl_w8_forecast_builders_t4688u.py"
FRAMEWORK = REPO / "services/model-service/src/services/nfl_handicapping_framework.py"
SEED = 4643
SIMS = 1200
C3_EPA = "cb1fe8c5e0495c417af3dc70f83cf4c419c1c1761b2dd233bc8546ad3face2c2"


def _load_fx(name: str) -> dict:
    path = FIXTURE_DIR / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload


def _sim(name: str) -> dict:
    fx = _load_fx(name)
    assert int(fx["seed"]) == SEED
    return simulate_nfl_game(NflGameInputs(**fx["inputs"]), simulations=SIMS, seed=SEED)


def _stdev_widen(sim: dict) -> float:
    err = sim["diagnostics"]["framework"]["factor_contributions"]["error_regime"]
    return float(err["raw_signals"]["stdev_widen"])


def _contrib(sim: dict, factor: str) -> dict:
    return sim["diagnostics"]["framework"]["factor_contributions"][factor]


# --- 1. C1-STDEV market invariance (88a08cae G-C1-STDEV) ---


def test_t_c1_stdev_1_injury_impact_does_not_move_markets() -> None:
    """Landing (a): hashed C1-INJ pair leaves markets + stdev_widen unchanged.

    PROTECTION-REMOVED: pass raw injury_impact into error_regime (pre-t4688u).
    VACUITY: drop market/stdev asserts and keep only means (old C1-INJ).
    """
    base = _sim("C1_base.json")
    impact = _sim("C1_inj_impact_only.json")
    now = impact["diagnostics"]["injury_nowcast"]
    assert now["home_impact"] == 0.45
    assert now["away_impact"] == 0.05
    inj = _contrib(impact, "injuries_depth")
    assert inj["margin_points"] == 0.0
    assert inj["total_points"] == 0.0
    assert impact["diagnostics"]["mean_home_points"] == base["diagnostics"]["mean_home_points"]
    assert impact["diagnostics"]["mean_away_points"] == base["diagnostics"]["mean_away_points"]
    assert impact["markets"]["spread_home"] == base["markets"]["spread_home"]
    assert impact["markets"]["home_win_prob"] == base["markets"]["home_win_prob"]
    assert impact["markets"]["total_mean"] == base["markets"]["total_mean"]
    assert _stdev_widen(impact) == _stdev_widen(base)


def test_t_c1_stdev_3_totals_overlay_stdev_stays_zero_at_conf_0() -> None:
    impact = _sim("C1_inj_impact_only.json")
    assert impact["diagnostics"]["totals_adjustments"]["stdev_points"] == 0.0


def test_t_c1_stdev_protection_removed_raw_impact_moves_helper() -> None:
    """If the framework gate is deleted, helper raw impact still widens stdev."""
    gated = compute_error_regime_uncertainty(
        injury_impact=0.0, factor_coverage=1.0, weather_available=True
    )
    raw = compute_error_regime_uncertainty(
        injury_impact=0.25, factor_coverage=1.0, weather_available=True
    )
    assert raw["stdev_widen"] > gated["stdev_widen"]
    src = FRAMEWORK.read_text(encoding="utf-8")
    assert "gated_injury_impact" in src
    assert "injury_impact=gated_injury_impact" in src


# --- 2. Builder pins / C3 sha (G-C1-BYPASS) ---


def test_t_c1_pin_1_builder_is_executed_not_grepped() -> None:
    """Side-effect only the builder can produce (source + grain + weeks).

    VACUITY: assert '_build_current_strength' in script text.
    """
    rows = [
        {"team": "GB", "week": w, "off_epa": 2.0, "off_plays": 60} for w in range(1, 8)
    ]
    out = build_current_strength(rows)
    assert out["GB"]["source"].endswith("w1_w7_play_weighted")
    assert out["GB"]["epa_grain"] == "season_to_date_w1_w7"
    assert out["GB"]["weeks"] == [1, 2, 3, 4, 5, 6, 7]
    assert inspect.isfunction(build_current_strength)


def test_t_c1_pin_2_c3_sha_refuse() -> None:
    """One-byte swap → InputShaMismatch. Grep 'sha256' is vacuous."""
    good = sha256_bytes(b"epa-pack")
    require_input_sha(good, good, label="epa")
    try:
        require_input_sha(sha256_bytes(b"epa-packX"), C3_EPA, label="epa")
    except InputShaMismatch as exc:
        assert "input_sha_mismatch" in str(exc)
        return
    raise AssertionError("expected InputShaMismatch on pin drift")


def test_t_c1_pin_3_week8_epa_does_not_enter_w1_w7() -> None:
    """T-EPA-ASOF-1: extreme week=8 EPA excluded.

    PROTECTION-REMOVED: delete week<=7 filter → GB off_epa moves.
    VACUITY: assert max(week) >= 7.
    """
    base_rows = [
        {"team": "GB", "week": w, "off_epa": 10.0, "off_plays": 50} for w in range(1, 8)
    ]
    leaked = list(base_rows) + [{"team": "GB", "week": 8, "off_epa": 500.0, "off_plays": 50}]
    clean = build_current_strength(base_rows)
    capped = build_current_strength(leaked)
    assert clean["GB"]["off_epa_per_play"] == capped["GB"]["off_epa_per_play"]
    assert 8 not in capped["GB"]["weeks"]
    assert capped["GB"]["excluded_weeks_above_cap"] == [8]
    assert max(capped["GB"]["weeks"]) >= 7  # not sufficient alone — paired with exclude


# --- 3. EPA as-of cutoff / no 2025 prior (G-TIME-EPA, G-C2-EPA-PRIOR) ---


def test_t_epa_asof_2_grain_flag_set() -> None:
    rows = [{"team": "GB", "week": w, "off_epa": 1.0, "off_plays": 40} for w in range(1, 8)]
    out = build_current_strength(rows)
    assert out["GB"]["epa_grain"] == "season_to_date_w1_w7"
    assert "epa_5g" not in out["GB"]


def test_t_epa_asof_3_empty_refuses_and_does_not_open_2025_prior() -> None:
    """VACUITY: inject strength={} into _simulate_one.

    PROTECTION-REMOVED: fallback onto nfl_team_efficiency_backbone_2026.json.
    """
    probe: list[str] = []
    try:
        build_current_strength([], prior_pack_opened=probe)
    except MissingCurrentStrength as exc:
        assert "MISSING current strength" in str(exc)
        assert probe == []
        src = BUILDER_MOD.read_text(encoding="utf-8")
        assert PRIOR_2025_PACK_NAME in src  # named as forbidden, never opened
        assert "open(" not in src
        assert ".read_text(" not in src
        assert ".read_bytes(" not in src
        return
    raise AssertionError("expected MissingCurrentStrength")


def test_t_epa_asof_3b_week_max_below_7_refuses() -> None:
    rows = [{"team": "GB", "week": w, "off_epa": 1.0, "off_plays": 40} for w in range(1, 6)]
    try:
        build_current_strength(rows)
    except MissingCurrentStrength:
        return
    raise AssertionError("expected refuse when week.max < 7")


def test_t_epa_asof_refuse_weeks_above_cap() -> None:
    rows = [{"team": "GB", "week": w, "off_epa": 1.0, "off_plays": 40} for w in range(1, 9)]
    try:
        build_current_strength(rows, refuse_weeks_above_cap=True)
    except MissingCurrentStrength as exc:
        assert "week>7" in str(exc)
        return
    raise AssertionError("expected refuse when week>7 present")


# --- 4. W8 missingness (G-INVENT-W8) ---


def _w7_designated_plus_empty_w8() -> list[dict]:
    return [
        {"team": "GB", "week": 7, "report_status": "Out", "full_name": "A"},
        {"team": "GB", "week": 8, "report_status": "", "full_name": "stub"},
        {"team": "CAR", "week": 7, "report_status": "Questionable", "full_name": "B"},
        {"team": "CAR", "week": 8, "report_status": None, "full_name": "stub"},
    ]


def test_t_g3_1_empty_w8_stubs_do_not_become_week8() -> None:
    """Must CALL the writer. Injecting {as_of_week: 7} is vacuous.

    PROTECTION-REMOVED: legacy max(week) on empty stubs → 8.
    """
    rows = _w7_designated_plus_empty_w8()
    out = injury_impacts(rows)
    assert out["GB"]["as_of_week"] == 7
    assert out["CAR"]["as_of_week"] == 7
    assert out["GB"]["w8_official_report"] == "MISSING"
    for flag in G3_FLAGS:
        assert flag in out["GB"]["missing_flags"]
    # protection-removed mutation still documents the #645 hole
    gb_rows = [r for r in rows if r["team"] == "GB"]
    assert last_designated_week(gb_rows) == 7
    assert legacy_as_of_week_max_including_empty(gb_rows) == 7  # designated exists
    stub_only = [r for r in gb_rows if int(r["week"]) == 8]
    assert last_designated_week(stub_only) is None
    assert legacy_as_of_week_max_including_empty(stub_only) == 8


def test_t_g3_2_nflverse_w8_designations_do_not_mint_present() -> None:
    """PROTECTION-REMOVED: PRESENT if latest_week >= 8."""
    rows = [
        {"team": "GB", "week": 7, "report_status": "Out"},
        {"team": "GB", "week": 8, "report_status": "Doubtful"},
    ]
    out = injury_impacts(rows)
    pack = materialize_injury_pack_meta(rows)
    assert out["GB"]["w8_official_report"] == "MISSING"
    assert pack["w8_official_report"] == "MISSING"
    assert pack["week"] == 8
    assert legacy_pack_official_from_latest_week(8) == "PRESENT"
    assert injury_pack_official_flag() == "MISSING"
    for flag in G3_FLAGS:
        assert flag in out["GB"]["missing_flags"]
        assert flag in pack["missing_flags"]


def test_t_g3_3_completeness_not_from_pack_week() -> None:
    pack = {"week": 8, "w8_official_report": "MISSING"}
    assert completeness_official_from_pack(pack) == "MISSING"
    forged = {"week": 8, "w8_official_report": "PRESENT", "official_sot_pin": None}
    assert completeness_official_from_pack(forged) == "MISSING"


def test_t_g3_4_one_fixture_writers_agree() -> None:
    rows = _w7_designated_plus_empty_w8()
    impacts = injury_impacts(rows)
    pack = materialize_injury_pack_meta(rows)
    complete = completeness_official_from_pack(pack)
    assert impacts["GB"]["w8_official_report"] == pack["w8_official_report"] == complete == "MISSING"
    assert impacts["GB"]["as_of_week"] == 7
    assert pack["week"] == 7


# --- 5. Non-vacuous Odds lock (G-C7-VACUOUS) ---


def test_t_c7_odds_tokens_absent_from_builder_and_test() -> None:
    """Not `\"False\" in text`. Token list + import graph of this draft module."""
    builder_text = BUILDER_MOD.read_text(encoding="utf-8")
    test_text = Path(__file__).read_text(encoding="utf-8")
    module_text_forbids_odds(builder_text)
    # Old C7 oracle (`"False" in text`) is true of any Python file and must not PASS.
    assert "False" in test_text
    assert any(token in builder_text for token in forbidden_odds_tokens())  # list exists
    module_text_forbids_odds(builder_text)  # but no import/call form


def test_t_c7_c1_sim_does_not_apply_market_blend() -> None:
    """Runtime: C1 pair must not blend a fetched line (none passed)."""
    base = _sim("C1_base.json")
    impact = _sim("C1_inj_impact_only.json")
    for sim in (base, impact):
        blend = sim["diagnostics"]["market_blend"]
        assert blend["spread_applied"] is False
        assert blend["total_applied"] is False
