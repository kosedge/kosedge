"""R6 caller: real mode refuses before readers/model; synthetic consumes A's output.

This CLEAR grants no EXEC auth, no manifest-bound GO, and no permitted
real-data scope. Positive IF/C means come only from A's actual file.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from src.services.nfl_r6_caller.contract import (
    A_Q2,
    ALGORITHM_TIP,
    B_Q2,
    CONTRACT_27,
    C_WEIGHT_IF,
    C_WEIGHT_Q2,
    FW_SHA256,
    IF_TIP,
    OUTPUT_KIND,
    PACKAGE_ID,
    PRIOR_CARRY,
    RIDGE_LAMBDA,
    SCHEMA_VERSION,
    SIM_SHA256,
    SYNTHETIC_CHANNEL,
    R6Refuse,
    R6RefuseCode,
    expected_c_mean,
    pin_block,
)
from src.services.nfl_r6_caller.ledger import (
    PairedArmLedger,
    canonical_json,
    make_seal_record,
    sha256_hex,
)

A_SEARCH_PATHS = (
    Path("data/ops/t5208u-r6-a-synthetic/positive-output.json"),
    Path("/tmp/t5208u-a-synthetic/positive-output.json"),
)

PIN_KEYS = {
    "if_tip": IF_TIP,
    "sim_sha256": SIM_SHA256,
    "fw_sha256": FW_SHA256,
    "algorithm_tip": ALGORITHM_TIP,
}


def locate_a_output(explicit: Optional[Path] = None) -> Optional[Path]:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    env_path = os.environ.get("T5208U_A_SYNTHETIC_JSON")
    if env_path:
        candidates.append(Path(env_path))
    for path in A_SEARCH_PATHS:
        if path is not None:
            candidates.append(path)
    for path in candidates:
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def refuse_real_mode(mode: str) -> None:
    """Must run before any reader / model / ledger forecast write."""
    token = (mode or "").strip().upper()
    if token == SYNTHETIC_CHANNEL:
        return
    raise R6Refuse(
        R6RefuseCode.REFUSE_REAL_MODE,
        "t5208u CLEAR grants no EXEC auth + no manifest-bound GO + no real data scope",
    )


def _require_synthetic_packet(packet: Mapping[str, Any]) -> None:
    if packet.get("synthetic") is not True:
        raise R6Refuse(R6RefuseCode.REFUSE_SYNTHETIC, "packet.synthetic must be true")
    if packet.get("channel") != SYNTHETIC_CHANNEL:
        raise R6Refuse(R6RefuseCode.REFUSE_SYNTHETIC, "packet.channel must be SYNTHETIC")
    if packet.get("production_mode") is not False:
        raise R6Refuse(R6RefuseCode.REFUSE_REAL_MODE, "production_mode must be false")
    if packet.get("usable_by_real_mode") is True:
        raise R6Refuse(R6RefuseCode.REFUSE_REAL_MODE, "usable_by_real_mode cannot be true")


def _check_pins(packet: Mapping[str, Any]) -> None:
    for key, expected in PIN_KEYS.items():
        got = packet.get(key)
        if got is None:
            continue
        if str(got) != expected and not str(got).startswith(expected[:8]):
            raise R6Refuse(R6RefuseCode.REFUSE_PIN, f"{key} {got!r} != {expected}")
    fields = packet.get("contract_27")
    if fields is not None and tuple(fields) != CONTRACT_27:
        raise R6Refuse(R6RefuseCode.REFUSE_PIN, "contract_27 literal mismatch vs 455a8e43")


def consume_a_packet(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "A output must be an object")
    _require_synthetic_packet(raw)
    _check_pins(raw)
    games = raw.get("games")
    if not isinstance(games, list) or not games:
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "A output has no games")
    return raw


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, f"{label} is not a number")
    out = float(value)
    if not math.isfinite(out):
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, f"{label} is not finite")
    return out


def project_game(game: Mapping[str, Any]) -> Dict[str, Any]:
    game_id = str(game.get("game_id") or "").strip()
    if not game_id:
        raise R6Refuse(R6RefuseCode.REFUSE_IDENTITY, "game_id missing")
    pm = game.get("point_margin")
    if not isinstance(pm, dict):
        raise R6Refuse(R6RefuseCode.REFUSE_OUTPUT, "POINT_MARGIN block missing")
    if_mean = _finite(pm.get("if_mean"), "if_mean")
    q2_mean = _finite(pm.get("q2_mean"), "q2_mean")
    c_mean = _finite(pm.get("c_mean"), "c_mean")
    expected = expected_c_mean(if_mean, q2_mean)
    if abs(c_mean - expected) > 1e-9 * max(1.0, abs(expected)):
        raise R6Refuse(
            R6RefuseCode.REFUSE_FORMULA,
            f"c_mean {c_mean} != 0.5*IF+0.5*Q2 ({expected})",
        )
    for forbidden in ("moneyline", "total", "cover_probability", "win_prob"):
        if forbidden in game or forbidden in pm:
            raise R6Refuse(R6RefuseCode.REFUSE_OUTPUT, f"{forbidden} not authorized")
    return {
        "game_id": game_id,
        "if_mean": if_mean,
        "q2_mean": q2_mean,
        "c_mean": c_mean,
        "input_hash": str(game.get("input_hash") or sha256_hex(canonical_json({"game_id": game_id}))),
        "state_hash": str(game.get("state_hash") or ""),
        "config_hash": str(game.get("config_hash") or sha256_hex(canonical_json(pin_block()))),
        "cutoff": dict(game.get("cutoff") or {}),
    }


def seal_projected(
    ledger: PairedArmLedger,
    projected: Mapping[str, Any],
    *,
    manifest_id: str,
) -> Dict[str, Any]:
    arms = {
        "IF": {"status": "SEALED", "mean": projected["if_mean"], "kind": OUTPUT_KIND},
        "C": {"status": "SEALED", "mean": projected["c_mean"], "kind": OUTPUT_KIND},
    }
    record = make_seal_record(
        game_id=str(projected["game_id"]),
        input_hash=str(projected["input_hash"]),
        state_hash=str(projected["state_hash"]),
        config_hash=str(projected["config_hash"]),
        cutoff=projected["cutoff"],
        arms=arms,
        refusals=[],
        manifest_id=manifest_id,
        synthetic=True,
    )
    return ledger.seal(record)


def run_synthetic_e2e(
    *,
    ledger_root: Path,
    a_path: Optional[Path] = None,
    manifest_id: str = "t5208u-r6-synth-e2e",
) -> Dict[str, Any]:
    found = locate_a_output(a_path)
    if found is None:
        raise R6Refuse(
            R6RefuseCode.REFUSE_A_OUTPUT,
            "A synthetic output not present (no fabricated IF mean)",
        )
    packet = consume_a_packet(json.loads(found.read_text(encoding="utf-8")))
    ledger = PairedArmLedger(ledger_root)
    sealed: list[Dict[str, Any]] = []
    for game in packet["games"]:
        if not isinstance(game, Mapping):
            raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "game row is not an object")
        sealed.append(seal_projected(ledger, project_game(game), manifest_id=manifest_id))
    return {
        "status": "OK",
        "a_path": str(found),
        "sealed": sealed,
        "pins": pin_block(),
        "package_id": PACKAGE_ID,
        "schema_version": SCHEMA_VERSION,
        "q2_diagnostic_only": True,
        "c_weights": {"if": C_WEIGHT_IF, "q2": C_WEIGHT_Q2},
        "q2_coeffs": {"a": A_Q2, "b": B_Q2, "ridge": RIDGE_LAMBDA, "prior_carry": PRIOR_CARRY},
    }


def prove_real_mode_refuse() -> Dict[str, Any]:
    try:
        refuse_real_mode("REAL")
    except R6Refuse as exc:
        if exc.code != R6RefuseCode.REFUSE_REAL_MODE:
            raise
        return exc.to_dict()
    raise AssertionError("REAL mode leaked")


def prove_seal_refuses(ledger_root: Path) -> Dict[str, str]:
    """Duplicate / race / partial-write without inventing IF means."""
    ledger = PairedArmLedger(ledger_root)
    refuse_arms = {
        "IF": {"status": "REFUSE", "mean": None, "kind": OUTPUT_KIND},
        "C": {"status": "REFUSE", "mean": None, "kind": OUTPUT_KIND},
    }
    record = make_seal_record(
        game_id="2026_99_R6_SYN",
        input_hash="0" * 64,
        state_hash="0" * 64,
        config_hash=sha256_hex(canonical_json(pin_block())),
        cutoff={"decision_offset_minutes": 60, "note": "paper KO-60 not EXECed"},
        arms=refuse_arms,
        refusals=[R6RefuseCode.REFUSE_A_OUTPUT],
        manifest_id="t5208u-r6-refuse-proof",
        synthetic=True,
    )
    first = ledger.seal(record)
    dup = "unhit"
    try:
        ledger.seal(record)
    except R6Refuse as exc:
        if exc.code != R6RefuseCode.REFUSE_DUPLICATE:
            raise
        dup = exc.code
    incomplete = dict(record)
    incomplete.pop("seal_id", None)
    incomplete["game_id"] = "2026_99_R6_PARTIAL"
    incomplete["arms"] = {"IF": refuse_arms["IF"]}
    partial = "unhit"
    try:
        ledger.seal(incomplete)
    except R6Refuse as exc:
        if exc.code != R6RefuseCode.REFUSE_PARTIAL:
            raise
        partial = exc.code
    if ledger.path_for("2026_99_R6_PARTIAL").exists():
        raise R6Refuse(R6RefuseCode.REFUSE_PARTIAL, "partial dest leaked")

    race = "unhit"
    lock_fd = ledger._lock(blocking=False)
    try:
        raced = make_seal_record(
            game_id="2026_99_R6_RACE",
            input_hash="1" * 64,
            state_hash="1" * 64,
            config_hash=first["config_hash"],
            cutoff=record["cutoff"],
            arms=refuse_arms,
            refusals=[R6RefuseCode.REFUSE_A_OUTPUT],
            manifest_id="t5208u-r6-refuse-proof",
            synthetic=True,
        )
        try:
            ledger.seal(raced)
        except R6Refuse as exc:
            if exc.code != R6RefuseCode.REFUSE_RACE:
                raise
            race = exc.code
    finally:
        ledger._unlock(lock_fd)

    leftover = ledger.path_for("2026_99_R6_TMP")
    tmp = leftover.with_name(f".{leftover.name}.999.tmp")
    tmp.write_text("{", encoding="utf-8")
    leftover_code = "unhit"
    leftover_record = make_seal_record(
        game_id="2026_99_R6_TMP",
        input_hash="2" * 64,
        state_hash="2" * 64,
        config_hash=first["config_hash"],
        cutoff=record["cutoff"],
        arms=refuse_arms,
        refusals=[R6RefuseCode.REFUSE_A_OUTPUT],
        manifest_id="t5208u-r6-refuse-proof",
        synthetic=True,
    )
    try:
        ledger.seal(leftover_record)
    except R6Refuse as exc:
        if exc.code != R6RefuseCode.REFUSE_PARTIAL:
            raise
        leftover_code = exc.code
    finally:
        if tmp.exists():
            tmp.unlink()

    return {
        "duplicate": dup,
        "partial_write": partial,
        "race": race,
        "leftover_tmp": leftover_code,
        "first_seal_id": first["seal_id"],
    }
