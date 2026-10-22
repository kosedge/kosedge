"""DR-1 end-to-end rehearsal and DR-2..DR-6 tamper detections.

Synthetic W8 slate only. No production credentials, no live Odds pull,
no publish, no grade.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.services.nfl_w8_capture.chain import open_log, verify_chain
from src.services.nfl_w8_capture.constants import (
    DEFAULT_SEAL_BY_ET,
    ET,
    MIN_LEAD_MINUTES,
    STATUS_FAIL,
    STATUS_OFFICIAL,
    STATUS_SEALED,
)
from src.services.nfl_w8_capture.seal import (
    CaptureError,
    build_and_seal,
    record_custodian_receipt,
    refuse_credentials,
    refuse_publish,
    verify_sealed_bundle,
)
from src.services.nfl_w8_capture.timeutil import et_to_utc, to_iso


KICKOFF_ET = datetime(2026, 10, 29, 20, 20, tzinfo=ET)
NOW_ET = datetime(2026, 10, 29, 18, 0, tzinfo=ET)
CAPTURE_ET = datetime(2026, 10, 29, 17, 0, tzinfo=ET)
CODE_SHA = "dry-run-not-a-git-sha"
MODEL_VERSION = "nfl-handicap-core-v3.1"


def _iso(dt: datetime) -> str:
    return to_iso(et_to_utc(dt))


def _slate() -> dict[str, Any]:
    kick = _iso(KICKOFF_ET)
    captured = _iso(CAPTURE_ET)
    games = [
        {"game_id": "SYN-W8-G01", "kickoff_utc": kick, "home": "AAA", "away": "BBB"},
        {"game_id": "SYN-W8-G02", "kickoff_utc": kick, "home": "CCC", "away": "DDD"},
    ]
    market_preds = [
        {"game_id": "SYN-W8-G01", "spread_home": -2.5, "total": 44.5, "home_win_prob": 0.56},
        {"game_id": "SYN-W8-G02", "spread_home": 3.0, "total": 47.0, "home_win_prob": 0.44},
    ]
    independent_preds = [
        {"game_id": "SYN-W8-G01", "spread_home": -1.0, "total": 45.0, "home_win_prob": 0.53},
        {"game_id": "SYN-W8-G02", "spread_home": 1.5, "total": 46.0, "home_win_prob": 0.47},
    ]
    market_inputs = [
        {
            "game_id": "SYN-W8-G01",
            "home_off_epa_5g": 0.04,
            "market_spread_home": -3.0,
        },
        {
            "game_id": "SYN-W8-G02",
            "home_off_epa_5g": -0.02,
            "market_spread_home": 2.5,
        },
    ]
    independent_inputs = [
        {"game_id": "SYN-W8-G01", "home_off_epa_5g": 0.04},
        {"game_id": "SYN-W8-G02", "home_off_epa_5g": -0.02},
    ]

    def proofs(game_id: str, input_name: str) -> dict[str, Any]:
        return {
            "game_id": game_id,
            "input_name": input_name,
            "as_of_utc": captured,
            "source_captured_at_utc": captured,
            "kickoff_utc": kick,
            "source": "archive:dry-run",
        }

    market_proofs = [
        proofs("SYN-W8-G01", "home_off_epa_5g"),
        proofs("SYN-W8-G01", "market_spread_home"),
        proofs("SYN-W8-G02", "home_off_epa_5g"),
        proofs("SYN-W8-G02", "market_spread_home"),
    ]
    independent_proofs = [
        proofs("SYN-W8-G01", "home_off_epa_5g"),
        proofs("SYN-W8-G02", "home_off_epa_5g"),
    ]
    odds = [
        {
            "game_id": "SYN-W8-G01",
            "book": "draftkings",
            "captured_at_utc": captured,
            "source_captured_at_utc": captured,
            "market": "spread",
            "price": -3.0,
            "kickoff_utc": kick,
        },
        {
            "game_id": "SYN-W8-G02",
            "book": None,
            "captured_at_utc": None,
            "market": None,
            "price": None,
            "kickoff_utc": kick,
        },
    ]
    return {
        "games": games,
        "market_predictions": market_preds,
        "independent_predictions": independent_preds,
        "market_inputs": market_inputs,
        "independent_inputs": independent_inputs,
        "market_proofs": market_proofs,
        "independent_proofs": independent_proofs,
        "odds_snapshots": odds,
    }


def run_dry_run(root: Path | str) -> dict[str, Any]:
    """DR-1: end-to-end rehearsal with a synthetic custodian."""
    refuse_credentials(dry_run=True)
    refuse_publish(False)
    payload = _slate()
    built = build_and_seal(
        root,
        **payload,
        model_version=MODEL_VERSION,
        code_sha=CODE_SHA,
        now_utc=et_to_utc(NOW_ET),
        dry_run=True,
        min_lead_minutes=MIN_LEAD_MINUTES,
        default_seal_by_et=DEFAULT_SEAL_BY_ET,
    )
    if built.status != STATUS_SEALED:
        return {"dr": "DR-1", "ok": False, "result": built.to_dict()}
    receipt = record_custodian_receipt(
        root,
        received_sha256sums=built.sha256sums,
        received_at_utc=et_to_utc(NOW_ET + timedelta(minutes=10)),
        custodian_id="dry-run-custodian",
        games=payload["games"],
    )
    verified = verify_sealed_bundle(root)
    return {
        "dr": "DR-1",
        "ok": receipt.status == STATUS_OFFICIAL and verified.status == STATUS_OFFICIAL,
        "build": built.to_dict(),
        "receipt": receipt.to_dict(),
        "verify": verified.to_dict(),
    }


def _dr2_edit_after_seal(root: Path) -> dict[str, Any]:
    run_dry_run(root)
    target = root / "market_informed" / "predictions.jsonl"
    target.write_text(target.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    result = verify_sealed_bundle(root)
    detected = any("sha256_mismatch" in str(f.get("reason")) for f in result.failures)
    return {"dr": "DR-2", "ok": detected, "failures": result.failures}


def _dr3_late_timestamp(root: Path) -> dict[str, Any]:
    payload = _slate()
    late = _iso(KICKOFF_ET - timedelta(minutes=10))
    payload["market_proofs"][0]["as_of_utc"] = late
    payload["market_proofs"][0]["source_captured_at_utc"] = late
    built = build_and_seal(
        root,
        **payload,
        model_version=MODEL_VERSION,
        code_sha=CODE_SHA,
        now_utc=et_to_utc(NOW_ET),
        dry_run=True,
    )
    detected = built.status == STATUS_FAIL and any(
        f.get("reason") == "late_as_of" for f in built.failures
    )
    return {"dr": "DR-3", "ok": detected, "failures": built.failures}


def _dr4_missing_snapshot(root: Path) -> dict[str, Any]:
    payload = _slate()
    payload["odds_snapshots"] = [payload["odds_snapshots"][0]]
    built = build_and_seal(
        root,
        **payload,
        model_version=MODEL_VERSION,
        code_sha=CODE_SHA,
        now_utc=et_to_utc(NOW_ET),
        dry_run=True,
    )
    detected = built.status == STATUS_FAIL and any(
        f.get("reason") == "missing_snapshot" for f in built.failures
    )
    return {"dr": "DR-4", "ok": detected, "failures": built.failures}


def _dr5_log_edit(root: Path) -> dict[str, Any]:
    run_dry_run(root)
    log_path = root / "evidence_log.jsonl"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return {"dr": "DR-5", "ok": False, "failures": [{"reason": "empty_log"}]}
    lines[0] = lines[0].replace("STREAM_WRITE", "STREAM_WRITTEN_TAMPER")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    chain_err = verify_chain(open_log(log_path))
    result = verify_sealed_bundle(root)
    detected = chain_err is not None or any("chain_" in str(f.get("reason")) for f in result.failures)
    return {"dr": "DR-5", "ok": detected, "chain_err": chain_err, "failures": result.failures}


def _dr6_market_in_independent(root: Path) -> dict[str, Any]:
    payload = _slate()
    payload["independent_inputs"][0]["market_spread_home"] = -3.0
    try:
        built = build_and_seal(
            root,
            **payload,
            model_version=MODEL_VERSION,
            code_sha=CODE_SHA,
            now_utc=et_to_utc(NOW_ET),
            dry_run=True,
        )
        detected = built.status == STATUS_FAIL and any(
            "forbidden" in str(f.get("reason")) for f in built.failures
        )
        return {"dr": "DR-6", "ok": detected, "failures": built.failures}
    except CaptureError as exc:
        return {"dr": "DR-6", "ok": "forbidden" in str(exc).lower() or "AC-6" in str(exc), "error": str(exc)}


def run_tamper_suite(root: Path | str) -> dict[str, Any]:
    base = Path(root)
    results = [
        run_dry_run(base / "DR-1"),
        _dr2_edit_after_seal(base / "DR-2"),
        _dr3_late_timestamp(base / "DR-3"),
        _dr4_missing_snapshot(base / "DR-4"),
        _dr5_log_edit(base / "DR-5"),
        _dr6_market_in_independent(base / "DR-6"),
    ]
    return {
        "suite": "W8_DRY_RUN",
        "all_ok": all(bool(item.get("ok")) for item in results),
        "results": results,
        "published": False,
        "graded": False,
    }
