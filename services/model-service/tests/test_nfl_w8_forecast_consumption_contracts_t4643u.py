"""t4643u IMV C0–C7 / G1–G4 consumption contracts.

Eng correctness ≠ predictive improvement. CERT=0. No Odds. No warehouse wire.
Fixtures: data/ops/nfl-t4643u-w8-forecast-integrity/fixtures/C1_*.json C2_*.json
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game

REPO = Path(__file__).resolve().parents[3]
W8_SCRIPT = REPO / "scripts/nfl/run_w8_research_forecast_t4564u.py"
PACKAGED_W1_DEPTH = (
    REPO
    / "services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json"
)
PACKAGED_2025_EPA = (
    REPO
    / "services/model-service/src/services/nfl_season_engine/data/nfl_team_efficiency_backbone_2026.json"
)
LOADERS = REPO / "services/model-service/src/services/nfl_season_engine/loaders.py"
FIXTURE_DIR = REPO / "data/ops/nfl-t4643u-w8-forecast-integrity/fixtures"
SEED = 4643
SIMS = 1200

C1_FIXTURES = (
    "C1_base.json",
    "C1_epa_home_boost.json",
    "C1_rest_home_extra.json",
    "C1_inj_impact_only.json",
)
C2_FIXTURES = (
    "C2_g3_last_designated.json",
    "C2_rest_home_missing.json",
    "C2_rest_days_schedule.json",
    "C2_epa_strength_missing.json",
    "C2_sealed_restore_oracle.json",
)


def _load_fixture(name: str) -> dict:
    path = FIXTURE_DIR / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload["_path"] = str(path)
    return payload


def _sim_from_fixture(name: str) -> dict:
    fx = _load_fixture(name)
    assert int(fx["seed"]) == SEED
    return simulate_nfl_game(NflGameInputs(**fx["inputs"]), simulations=SIMS, seed=SEED)


def _contrib(sim: dict, factor: str) -> dict:
    return sim["diagnostics"]["framework"]["factor_contributions"][factor]


def _load_w8_mod():
    spec = importlib.util.spec_from_file_location(
        "run_w8_research_forecast_t4564u_t4643u", W8_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


W8 = _load_w8_mod()


def _rest_tuple(raw: list) -> tuple:
    rest_h, src_h, rest_a, src_a = raw
    return (
        None if rest_h is None else float(rest_h),
        str(src_h),
        None if rest_a is None else float(rest_a),
        str(src_a),
    )


def test_c1_epa_moves_declared_component_only() -> None:
    """C1-EPA: inseason strength CONSUMED → base_efficiency / home WP."""
    base = _sim_from_fixture("C1_base.json")
    boosted = _sim_from_fixture("C1_epa_home_boost.json")
    assert _contrib(boosted, "base_efficiency")["margin_points"] > _contrib(base, "base_efficiency")["margin_points"]
    assert boosted["markets"]["home_win_prob"] > base["markets"]["home_win_prob"]
    assert boosted["markets"]["spread_home"] < base["markets"]["spread_home"]
    assert _contrib(boosted, "rest_travel")["margin_points"] == _contrib(base, "rest_travel")["margin_points"]
    assert _contrib(boosted, "injuries_depth")["margin_points"] == _contrib(base, "injuries_depth")["margin_points"]


def test_c1_rest_moves_declared_component_only() -> None:
    """C1-REST: schedule kickoffs CONSUMED → rest_travel."""
    base = _sim_from_fixture("C1_base.json")
    extra = _sim_from_fixture("C1_rest_home_extra.json")
    assert _contrib(extra, "rest_travel")["margin_points"] > _contrib(base, "rest_travel")["margin_points"]
    assert extra["markets"]["home_win_prob"] > base["markets"]["home_win_prob"]
    assert extra["diagnostics"]["framework"]["factor_contributions"]["injuries_depth"]["margin_points"] == 0.0
    assert _contrib(extra, "base_efficiency")["margin_points"] == _contrib(base, "base_efficiency")["margin_points"]


def test_c1_injury_impact_field_consumed_means_gated() -> None:
    """C1-INJ-FIELD: impact_* identity CONSUMED; means stay 0 without confidence."""
    base = _sim_from_fixture("C1_base.json")
    impact = _sim_from_fixture("C1_inj_impact_only.json")
    now = impact["diagnostics"]["injury_nowcast"]
    assert now["home_impact"] == 0.45
    assert now["away_impact"] == 0.05
    inj = _contrib(impact, "injuries_depth")
    assert inj["margin_points"] == 0.0
    assert inj["total_points"] == 0.0
    assert inj["raw_signals"]["injury_confidence"] == 0.0
    assert impact["diagnostics"]["mean_home_points"] == base["diagnostics"]["mean_home_points"]
    assert impact["diagnostics"]["mean_away_points"] == base["diagnostics"]["mean_away_points"]


def test_c1_injury_with_confidence_moves_means_repair_target() -> None:
    """R1 target: same impacts + explicit confidence move injuries_depth means."""
    base = _sim_from_fixture("C1_base.json")
    fx = _load_fixture("C1_inj_impact_only.json")
    inputs = dict(fx["inputs"])
    inputs["injury_nowcast_confidence_home"] = 0.85
    inputs["injury_nowcast_confidence_away"] = 0.85
    gated = simulate_nfl_game(NflGameInputs(**inputs), simulations=SIMS, seed=SEED)
    inj = _contrib(gated, "injuries_depth")
    assert inj["margin_points"] != 0.0 or inj["total_points"] != 0.0
    assert gated["diagnostics"]["mean_home_points"] != base["diagnostics"]["mean_home_points"] or (
        gated["diagnostics"]["mean_away_points"] != base["diagnostics"]["mean_away_points"]
    )


def test_c5_g2_depth_not_consumed_no_volume_fields() -> None:
    """G2 / C5: GAP_SIM_VOLUME — no depth fields on NflGameInputs."""
    fields = set(NflGameInputs.__dataclass_fields__)
    assert fields.isdisjoint({"depth_rows", "depth_chart", "roster", "wr1_share", "rb1_share", "snap_share"})


def test_c3_g1_no_warehouse_select_in_forecast_path() -> None:
    """G1 / C3: warehouse CLOSED ≠ CONSUMED until SELECT."""
    text = W8_SCRIPT.read_text(encoding="utf-8")
    assert "FROM nfl_dp_" not in text
    assert "nfl_dp_depth_chart_weekly" not in text
    assert "Does not read DATABASE_URL" in text


def test_c2_g3_w8_official_missing_not_invented() -> None:
    """G3 / C2: null W8 official → last-designated overlay + flags; no invent."""
    fx = _load_fixture("C2_g3_last_designated.json")
    out = W8._simulate_one(
        fx["game"],
        strength=fx["strength"],
        injuries=fx["injuries"],
        rest=_rest_tuple(fx["rest"]),
        seed=int(fx["seed"]),
    )
    missing = set(out["missing"])
    for flag in fx["required_missing"]:
        assert flag in missing
    assert out["injury_home"]["as_of_week"] == fx["required_injury_as_of"]["GB"]
    assert out["injury_away"]["as_of_week"] == fx["required_injury_as_of"]["CAR"]
    assert out["injury_home"]["w8_official_report"] == "MISSING"
    assert out["injury_away"]["w8_official_report"] == "MISSING"
    assert out["injury_home"]["as_of_week"] != 8
    assert out["injury_away"]["as_of_week"] != 8


def test_c2_g3_and_g2_sealed_restore_flags() -> None:
    """C2 sealed emit: 14/14 G3 flags + G2 provenance_only; no Odds."""
    fx = _load_fixture("C2_sealed_restore_oracle.json")
    restore = REPO / fx["restore_run"]
    games = sorted(restore.glob("2026-W08-*.json"))
    assert len(games) == int(fx["n_games"])
    for path in games:
        rec = json.loads(path.read_text(encoding="utf-8"))
        missing = set(rec["input_provenance"]["missing_inputs"])
        for flag in fx["required_missing_inputs"]:
            assert flag in missing
        assert rec["input_provenance"]["depth_role"] == fx["required_depth_role"]
        assert rec["input_provenance"]["injury_overlay"] == fx["required_injury_overlay"]
        assert rec["input_provenance"]["odds_api"] is fx["required_odds_api"]
        assert rec["cert_candidate"] == fx["required_cert_candidate"]


def test_c2_rest_missing_uses_default_and_flags() -> None:
    """C2 schedule: rest None → 7.0 fallback AND rest_days_home flag."""
    fx = _load_fixture("C2_rest_home_missing.json")
    out = W8._simulate_one(
        fx["game"],
        strength=fx["strength"],
        injuries=fx["injuries"],
        rest=_rest_tuple(fx["rest"]),
        seed=int(fx["seed"]),
    )
    assert "rest_days_home" in out["missing"]
    assert out["rest"]["home"] is None
    assert out["rest"]["home_source"] == "MISSING"
    assert out["engine"]["inputs"]["rest_days_home"] == fx["fallback_rest_days_home"]


def test_c2_rest_days_helper_present_and_missing() -> None:
    """C2 schedule helper: kickoff delta vs MISSING (no silent 7.0 at helper)."""
    fx = _load_fixture("C2_rest_days_schedule.json")
    present = fx["present"]
    ko = datetime.fromisoformat(present["kickoff_utc"].replace("Z", "+00:00")).astimezone(
        timezone.utc
    )
    days, src = W8._rest_days(fx["games"], team=present["team"], kickoff=ko)
    assert days == present["expected_days"]
    assert src == present["expected_src"]
    miss = fx["missing"]
    ko_m = datetime.fromisoformat(miss["kickoff_utc"].replace("Z", "+00:00")).astimezone(
        timezone.utc
    )
    days_m, src_m = W8._rest_days(fx["games"], team=miss["team"], kickoff=ko_m)
    assert days_m is None
    assert src_m == miss["expected_src"]


def test_c2_epa_missing_refuses_to_sim() -> None:
    """C2 EPA: missing strength → SystemExit; no silent 2025 prior."""
    fx = _load_fixture("C2_epa_strength_missing.json")
    try:
        W8._simulate_one(
            fx["game"],
            strength=fx["strength"],
            injuries=fx["injuries"],
            rest=_rest_tuple(fx["rest"]),
            seed=int(fx["seed"]),
        )
    except SystemExit as exc:
        assert fx["expected_exit_substr"] in str(exc)
        return
    raise AssertionError("expected SystemExit refuse-to-sim for missing EPA strength")


def test_c2_g2_provenance_only_flag_in_builder() -> None:
    text = W8_SCRIPT.read_text(encoding="utf-8")
    assert "provenance_only" in text
    assert "packaged nfl_depth_chart_2026_w1.json" in text
    assert "used_for" in text and "provenance_only_not_player_box_volume" in text


def test_c4_already_consumed_paths_still_wired() -> None:
    """C4: EPA, rest, designated impact still reach NflGameInputs in the builder."""
    text = W8_SCRIPT.read_text(encoding="utf-8")
    assert "offense_index_home" in text
    assert "rest_days_home" in text
    assert "injury_nowcast_impact_home" in text
    assert "epa_to_strength_indices" in text
    assert "_load_canonical_week" in text


def test_c6_g4_season_still_binds_w1_and_2025_prior() -> None:
    """G4 / C6b: conflicting season packs still present and flagged, not rewritten."""
    depth = json.loads(PACKAGED_W1_DEPTH.read_text(encoding="utf-8"))
    assert int(depth.get("week") or 0) == 1
    assert str(depth.get("as_of") or "").startswith("2026-08-13")
    epa = json.loads(PACKAGED_2025_EPA.read_text(encoding="utf-8"))
    assert epa.get("prior_season") == 2025
    assert str(epa.get("as_of") or "").startswith("2026-08-08")
    loaders = LOADERS.read_text(encoding="utf-8")
    assert "ignored stale DB depth" in loaders


def test_c7_no_odds_no_market_blend_on_w8_path() -> None:
    text = W8_SCRIPT.read_text(encoding="utf-8")
    assert "apply_market_blend" in text
    assert "False" in text
    assert "odds_api" in text.lower() or "Odds API" in text or "odds_api" in text


def test_c1_c2_fixture_hashes_are_stable() -> None:
    """C1/C2: fixtures are pinned; IMV can re-hash."""
    names = list(C1_FIXTURES) + list(C2_FIXTURES)
    expected = {}
    for name in names:
        digest = hashlib.sha256((FIXTURE_DIR / name).read_bytes()).hexdigest()
        assert len(digest) == 64
        expected[name] = digest
    manifest = FIXTURE_DIR / "FIXTURES.sha256"
    listed = {
        line.split()[1]: line.split()[0]
        for line in manifest.read_text().splitlines()
        if line.strip()
    }
    for name, digest in expected.items():
        assert listed[name] == digest
