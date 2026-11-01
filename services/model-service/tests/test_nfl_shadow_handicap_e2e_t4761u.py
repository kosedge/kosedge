"""CLEAR-P1 shadow E2E tests (t4768u / DECISION 23c825de / plan 69b9ef5f).

Local D3 fixture only. No live callers, HF, DDL, Odds, Railway, overlays.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

REPO = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO / "scripts" / "nfl"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import shadow_handicap_e2e_t4761u as shadow  # noqa: E402
from src.services.nfl_handicap_ledger import (  # noqa: E402
    FORECAST_HANDICAPPED_FAIR,
    L0_LAYER,
    L1_LAYER,
    L4_LAYER,
    AppendOnlyHandicapLedger,
    HandicapLedgerReject,
    commit_l1_stage,
    validate_l0_row,
    validate_l4_row,
)
from src.services.nfl_simulator import NFL_INDEPENDENT_FAIR_PATH  # noqa: E402


def _run(tmp_path: Path) -> dict:
    return shadow.run_shadow_p1(tmp_path / "out")


def test_p1_happy_path_writes_l0_l1_l4_and_receipt(tmp_path: Path) -> None:
    receipt = _run(tmp_path)
    out = tmp_path / "out"
    assert (out / "receipt.json").is_file()
    assert (out / "ledger.jsonl").is_file()

    store = AppendOnlyHandicapLedger(out / "ledger.jsonl")
    layers = [row["layer"] for row in store.rows()]
    labels = [row["forecast_label"] for row in store.rows()]
    assert layers.count(L0_LAYER) == 1
    assert layers.count(L1_LAYER) == len(shadow.L1_ALLOWLIST_FACTORS)
    assert layers.count(L4_LAYER) == 1
    assert "independent_fair" in labels
    assert "handicap_delta" in labels
    assert "market_informed_fair" in labels
    assert "handicapped_fair" not in labels
    assert len({row["prediction_id"] for row in store.rows()}) == 1 + len(
        shadow.L1_ALLOWLIST_FACTORS
    ) + 1

    assert receipt["independent_fair"]["market_blend"] == 0
    assert receipt["independent_fair"]["nfl_independent_fair_path"] is False
    assert receipt["ledger"]["l1_missing"] is True
    assert receipt["ledger"]["hf_rows"] == 0
    assert receipt["market_compare"]["used_as_fair"] is False
    assert receipt["publication_control"]["coming_soon"] == "ON"
    assert receipt["publication_control"]["cert"] == "0"


def test_p1_d3ii_sha_unchanged(tmp_path: Path) -> None:
    receipt = _run(tmp_path)
    assert receipt["blended_default_path"]["sha256"] == shadow.D3II_BASELINE_SHA256
    assert receipt["blended_default_path"]["match"] is True
    assert NFL_INDEPENDENT_FAIR_PATH is False


def test_p1_if_mus_and_distribution(tmp_path: Path) -> None:
    receipt = _run(tmp_path)
    dist = receipt["distribution"]
    assert dist["sigma"] > 0
    assert dist["total_p10"] <= dist["total_p50"] <= dist["total_p90"]
    assert 0.0 < dist["home_win_prob"] < 1.0
    assert 0.0 < dist["away_win_prob"] < 1.0
    assert dist["market_blend"] == 0
    if_block = receipt["independent_fair"]
    assert if_block["margin_mu"] == dist["margin_mu"]
    assert if_block["total_mu"] == dist["total_mu"]


def test_p1_jsonl_reload_validates(tmp_path: Path) -> None:
    receipt = _run(tmp_path)
    ledger = tmp_path / "out" / "ledger.jsonl"
    first = AppendOnlyHandicapLedger(ledger)
    second = AppendOnlyHandicapLedger(ledger)
    assert len(first) == len(second) == receipt["ledger"]["row_count"]
    assert {row["prediction_id"] for row in first.rows()} == {
        row["prediction_id"] for row in second.rows()
    }


def test_p1_reproducible_prediction_ids(tmp_path: Path) -> None:
    a = _run(tmp_path / "a")
    b = _run(tmp_path / "b")
    assert a["ledger"]["l0_prediction_id"] == b["ledger"]["l0_prediction_id"]
    assert a["ledger"]["l1_prediction_ids"] == b["ledger"]["l1_prediction_ids"]
    assert a["ledger"]["l4_prediction_id"] == b["ledger"]["l4_prediction_id"]
    assert a["independent_fair"]["margin_mu"] == b["independent_fair"]["margin_mu"]
    assert a["independent_fair"]["total_mu"] == b["independent_fair"]["total_mu"]
    assert a["receipt_sha256"] == b["receipt_sha256"]


def test_p1_l0_contaminated_blend_rejects() -> None:
    dist = {
        "margin_mu": 0.16,
        "total_mu": 43.82,
        "sigma": 9.1,
    }
    bad = shadow.build_l0_row(dist)
    bad["market_blend"] = 0.3
    with pytest.raises(HandicapLedgerReject, match="market_blend"):
        validate_l0_row(bad)


def test_p1_l1_hf_label_rejects(tmp_path: Path) -> None:
    store = AppendOnlyHandicapLedger(tmp_path / "hf.jsonl")
    rows = shadow.build_l1_rows()
    rows[0]["forecast_label"] = FORECAST_HANDICAPPED_FAIR
    with pytest.raises(HandicapLedgerReject, match="handicap_delta"):
        commit_l1_stage(store, rows, decision_ts=shadow.DECISION_TS)
    assert len(store) == 0


def test_p1_l4_empty_snapshot_rejects() -> None:
    dist = {
        "margin_mu": 0.16,
        "total_mu": 43.82,
        "sigma": 9.1,
    }
    bad = shadow.build_l4_row(dist)
    bad["market_snapshot_id"] = ""
    with pytest.raises(HandicapLedgerReject, match="missing required"):
        validate_l4_row(bad, decision_ts=shadow.DECISION_TS)


def test_p1_fail_closed_missing_l0_field() -> None:
    dist = {
        "margin_mu": 0.16,
        "total_mu": 43.82,
        "sigma": 9.1,
    }
    bad = shadow.build_l0_row(dist)
    del bad["sigma"]
    with pytest.raises(HandicapLedgerReject, match="missing required"):
        validate_l0_row(bad)


def test_p1_fail_closed_missing_distribution_sigma() -> None:
    with pytest.raises(shadow.ShadowE2EReject, match="sigma"):
        shadow.assert_distribution_valid(
            {
                "forecast_label": "independent_fair",
                "independent_fair": {
                    "forecast_label": "independent_fair",
                    "market_blend": 0,
                    "margin_mu": 0.1,
                    "total_mu": 43.5,
                    "sigma": None,
                },
                "markets": {
                    "total_p10": 30.0,
                    "total_p50": 43.0,
                    "total_p90": 55.0,
                    "home_win_prob": 0.5,
                    "away_win_prob": 0.5,
                    "total_mean": 43.5,
                },
            }
        )


def test_p1_coming_soon_cert_zero_pins() -> None:
    pins = shadow.read_publication_control_pins()
    assert pins["coming_soon"] == "ON"
    assert pins["cert"] == "0"
    assert pins["public_paint"] == "closed"
    assert pins["source"] == "apps/web/lib/cfb-edge-board-public.ts"


def test_p1_publication_control_flipped_rejects(tmp_path: Path) -> None:
    fake = tmp_path / "cfb-edge-board-public.ts"
    fake.write_text("export const NFL_EDGE_BOARD_PUBLIC_ENABLED = true;\n", encoding="utf-8")
    with pytest.raises(shadow.ShadowE2EReject, match="publication control"):
        shadow.read_publication_control_pins(fake)


def test_p1_script_source_guards() -> None:
    shadow.assert_local_only_source()
    text = Path(shadow.__file__).read_text(encoding="utf-8")
    assert "ODDS_API_KEY" not in text
    assert "unlock_overlays=True" not in text
    assert "from src.services.odds_api" not in text
    assert "from src.tasks" not in text
    assert "from src.routes" not in text


def test_p1_cli_exit_zero(tmp_path: Path) -> None:
    code = shadow.main(["--out", str(tmp_path / "cli")])
    assert code == 0
    assert (tmp_path / "cli" / "receipt.json").is_file()


def test_p1_receipt_sha_matches_core_blob(tmp_path: Path) -> None:
    receipt = _run(tmp_path)
    on_disk = json.loads((tmp_path / "out" / "receipt.json").read_text(encoding="utf-8"))
    assert on_disk["receipt_sha256"] == receipt["receipt_sha256"]
    stable = {k: v for k, v in on_disk.items() if k not in {"receipt_sha256", "receipt_path"}}
    ledger_stable = dict(on_disk["ledger"])
    ledger_stable.pop("path", None)
    stable["ledger"] = ledger_stable
    blob = json.dumps(stable, sort_keys=True, indent=2, default=str) + "\n"
    assert hashlib.sha256(blob.encode("utf-8")).hexdigest() == on_disk["receipt_sha256"]
