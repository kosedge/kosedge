"""CLEAR-A D3 reject tests (t4740u / paper 243a384e).

(i) blend=0 ⇒ IF margin_mu/total_mu equal pre_blend helper within 0.01 pts
(ii) flag OFF ⇒ blended prod-path output sha256 matches pinned baseline
(iii) missing required L1 field OR as_of_ts > decision_ts ⇒ REJECT, no impute

No capture, no overlay ON, no scoring, no production caller changes.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.nfl_handicap_ledger import (
    FORECAST_HANDICAPPED_FAIR,
    FORECAST_INDEPENDENT_FAIR,
    FORECAST_MARKET_INFORMED_FAIR,
    L0_LAYER,
    L1_LAYER,
    L1_REQUIRED_FIELDS,
    L4_LAYER,
    LEDGER_SCHEMA_VERSION,
    AppendOnlyHandicapLedger,
    HandicapLedgerReject,
    commit_l1_stage,
    make_prediction_id,
    validate_l1_row,
)
from src.services.nfl_model_handicap import pre_blend_model_markets_from_diagnostics
from src.services.nfl_simulator import (
    INDEPENDENT_FAIR_FORECAST_LABEL,
    NFL_INDEPENDENT_FAIR_PATH,
    NflGameInputs,
    independent_fair_mus,
    simulate_nfl_game,
    simulate_nfl_game_independent_fair,
)

# Pinned on deploy-vercel 209e90aa before CLEAR-A edits (same fixture below).
D3II_FIXED_SEED = 47401
D3II_SIMULATIONS = 800
D3II_MARKET_SPREAD_HOME = 3.5
D3II_MARKET_TOTAL = 43.5
D3II_BASELINE_SHA256 = "75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224"


def _d3_inputs() -> NflGameInputs:
    return NflGameInputs(
        game_id="d3ii-clear-a-baseline",
        home_team="CLE",
        away_team="BAL",
        offense_index_home=0.96,
        offense_index_away=1.05,
        defense_index_home=1.04,
        defense_index_away=0.98,
        rest_days_home=7.0,
        rest_days_away=6.0,
        matchup_season=2026,
        matchup_week=8,
    )


def _canonical_sha256(obj: object) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(blob).hexdigest()


def _sim_kwargs() -> dict:
    return {
        "simulations": D3II_SIMULATIONS,
        "seed": D3II_FIXED_SEED,
        "market_spread_home": D3II_MARKET_SPREAD_HOME,
        "market_total": D3II_MARKET_TOTAL,
    }


def test_d3_i_if_mus_match_pre_blend_helper_within_tol() -> None:
    """(i) Independent Fair mus == pre_blend_model_markets_from_diagnostics."""
    inputs = _d3_inputs()
    blended = simulate_nfl_game(inputs, **_sim_kwargs())
    if_out = simulate_nfl_game_independent_fair(inputs, **_sim_kwargs())

    assert NFL_INDEPENDENT_FAIR_PATH is False
    assert if_out["forecast_label"] == INDEPENDENT_FAIR_FORECAST_LABEL
    assert if_out["independent_fair"]["market_blend"] == 0
    assert if_out["diagnostics"]["market_blend"]["spread_weight"] == 0.0
    assert if_out["diagnostics"]["market_blend"]["total_weight"] == 0.0

    derived = pre_blend_model_markets_from_diagnostics(blended)
    assert derived is not None
    margin_mu, total_mu = independent_fair_mus(if_out)
    helper_margin = -float(derived["spread_home"])
    helper_total = float(derived["total_mean"])
    assert abs(margin_mu - helper_margin) <= 0.01
    assert abs(total_mu - helper_total) <= 0.01

    derived_if = pre_blend_model_markets_from_diagnostics(if_out)
    assert derived_if is not None
    assert abs(margin_mu - (-float(derived_if["spread_home"]))) <= 0.01
    assert abs(total_mu - float(derived_if["total_mean"])) <= 0.01


def test_d3_ii_flag_off_prod_path_byte_identical_to_baseline() -> None:
    """(ii) flag OFF ⇒ current blended output sha256 matches pinned baseline."""
    assert NFL_INDEPENDENT_FAIR_PATH is False
    inputs = _d3_inputs()
    out_default = simulate_nfl_game(inputs, **_sim_kwargs())
    out_explicit_off = simulate_nfl_game(
        inputs, independent_fair=False, **_sim_kwargs()
    )

    digest_default = _canonical_sha256(out_default)
    digest_off = _canonical_sha256(out_explicit_off)
    assert digest_default == D3II_BASELINE_SHA256
    assert digest_off == D3II_BASELINE_SHA256
    assert "independent_fair" not in out_default
    assert "forecast_label" not in out_default
    assert out_default["diagnostics"]["market_blend"]["spread_applied"] is True
    assert out_default["diagnostics"]["market_blend"]["spread_weight"] != 0.0


def test_d3_iii_missing_required_l1_field_or_future_as_of_rejects(
    tmp_path: Path,
) -> None:
    """(iii) missing required L1 field or as_of_ts > decision_ts ⇒ REJECT."""
    decision_ts = "2026-10-29T16:00:00Z"
    base = {
        "game_id": "d3iii-l1",
        "capture_id": "cap-d3iii-1",
        "as_of_ts": "2026-10-29T15:00:00Z",
        "baseline_ref": "baseline-personnel-ref-dev",
        "registry_id": "reg-clear-a-l1",
        "source_snapshot_id": "snap-d3iii-1",
        "factor": "injury_availability",
        "entry_point": "points",
        "delta": 0.0,
        "uncertainty": 0.0,
        "missing": True,
        "decision_ts": decision_ts,
    }

    for field in L1_REQUIRED_FIELDS:
        store = AppendOnlyHandicapLedger(tmp_path / f"miss_{field}.jsonl")
        bad = dict(base)
        bad.pop(field)
        with pytest.raises(HandicapLedgerReject, match="REJECT"):
            validate_l1_row(bad, decision_ts=decision_ts)
        with pytest.raises(HandicapLedgerReject, match="REJECT"):
            commit_l1_stage(store, [bad], decision_ts=decision_ts)
        assert len(store) == 0
        assert store.rows() == []

    future = dict(base)
    future["as_of_ts"] = "2026-10-29T17:00:00Z"
    store = AppendOnlyHandicapLedger(tmp_path / "future_as_of.jsonl")
    with pytest.raises(HandicapLedgerReject, match="as_of_ts > decision_ts"):
        validate_l1_row(future, decision_ts=decision_ts)
    with pytest.raises(HandicapLedgerReject, match="as_of_ts > decision_ts"):
        commit_l1_stage(store, [future], decision_ts=decision_ts)
    assert len(store) == 0


def test_d3_iii_valid_l1_appends_and_never_overwrites(tmp_path: Path) -> None:
    decision_ts = "2026-10-29T16:00:00Z"
    row = {
        "game_id": "d3iii-l1-ok",
        "capture_id": "cap-d3iii-ok",
        "as_of_ts": "2026-10-29T15:00:00Z",
        "baseline_ref": "baseline-personnel-ref-dev",
        "registry_id": "reg-clear-a-l1",
        "source_snapshot_id": "snap-d3iii-ok",
        "factor": "injury_availability",
        "entry_point": "points",
        "delta": 0.0,
        "uncertainty": 0.0,
        "missing": True,
        "missingness": {"injury_availability": True},
        "decision_ts": decision_ts,
    }
    store = AppendOnlyHandicapLedger(tmp_path / "ok.jsonl")
    written = commit_l1_stage(store, [row], decision_ts=decision_ts)
    assert len(written) == 1
    assert len(store) == 1
    pid = written[0]["prediction_id"]
    assert pid.startswith("hl_")
    with pytest.raises(HandicapLedgerReject, match="never overwrite"):
        store.append(written[0])
    assert len(store) == 1


def test_if_hf_mif_coexist_without_overwrite(tmp_path: Path) -> None:
    """IF / HF / MIF are separate identities; append-only across labels."""
    store = AppendOnlyHandicapLedger(tmp_path / "three.jsonl")
    decision_ts = "2026-10-29T16:00:00Z"
    shared = {
        "game_id": "g-if-hf-mif",
        "as_of_ts": "2026-10-29T15:00:00Z",
        "capture_id": "cap-triple",
        "source_snapshot_id": "snap-triple",
        "registry_id": "reg-clear-a",
        "baseline_ref": "baseline-personnel-ref-dev",
        "baseline_personnel_ref": "baseline-personnel-ref-dev",
        "model_version": "nfl-v1.5-matchup-sim",
        "decision_ts": decision_ts,
    }
    l0 = {
        **shared,
        "forecast_label": FORECAST_INDEPENDENT_FAIR,
        "market_blend": 0,
        "margin_mu": 0.16,
        "total_mu": 43.82,
        "sigma": 9.1,
    }
    l1 = {
        **shared,
        "factor": "weather",
        "entry_point": "points",
        "delta": 0.0,
        "uncertainty": 0.0,
        "missing": True,
    }
    l4 = {
        **shared,
        "forecast_label": FORECAST_MARKET_INFORMED_FAIR,
        "market_snapshot_id": "mkt-triple",
        "captured_at": "2026-10-29T15:30:00Z",
        "blend_weight_spread": 0.30,
        "blend_weight_total": 0.30,
        "week_scale": 1.0,
    }
    store.append_layer(
        l0,
        layer=L0_LAYER,
        forecast_label=FORECAST_INDEPENDENT_FAIR,
        decision_ts=decision_ts,
    )
    store.append_layer(
        l1,
        layer=L1_LAYER,
        forecast_label=FORECAST_HANDICAPPED_FAIR,
        decision_ts=decision_ts,
    )
    store.append_layer(
        l4,
        layer=L4_LAYER,
        forecast_label=FORECAST_MARKET_INFORMED_FAIR,
        decision_ts=decision_ts,
    )
    labels = {row["forecast_label"] for row in store.rows()}
    layers = {row["layer"] for row in store.rows()}
    assert labels == {
        FORECAST_INDEPENDENT_FAIR,
        FORECAST_HANDICAPPED_FAIR,
        FORECAST_MARKET_INFORMED_FAIR,
    }
    assert layers == {L0_LAYER, L1_LAYER, L4_LAYER}
    assert len({row["prediction_id"] for row in store.rows()}) == 3
    assert LEDGER_SCHEMA_VERSION == "handicap-ledger-v0-clear-a"
    assert make_prediction_id(
        layer=L0_LAYER,
        forecast_label=FORECAST_INDEPENDENT_FAIR,
        game_id="g-if-hf-mif",
        as_of_ts="2026-10-29T15:00:00Z",
        capture_id="cap-triple",
        schema_version=LEDGER_SCHEMA_VERSION,
        payload=l0,
    ).startswith("hl_")
