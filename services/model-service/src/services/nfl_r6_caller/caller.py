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

_REPO_ROOT = Path(__file__).resolve().parents[5]
A_DEMO_RESULT = _REPO_ROOT / "data/ops/t5208u-r6-caller-v1/demo_result.json"
A_DEMO_PACKET = _REPO_ROOT / "data/ops/t5208u-r6-caller-v1/synthetic_demo.json"
A_SEARCH_PATHS = (
    A_DEMO_RESULT,
    _REPO_ROOT / "data/ops/t5208u-r6-a-synthetic/positive-output.json",
    Path("/tmp/t5208u-a-synthetic/positive-output.json"),
)

# A's reported demo binds (1487e9f0). B copies these from the artifact, does not invent.
A_DEMO_GAME_ID = "SYNTHETIC_2018_W05_KC_NE"
A_DEMO_IF = 0.8675824382397918
A_DEMO_Q2 = 1.2472862060776504
A_DEMO_C = 1.057434322158721
A_DEMO_SEED = 282632
A_SCHEMA_ID = "nfl-t5208u-r6-caller-v1"

PIN_KEYS = {
    "if_tip": IF_TIP,
    "sim_sha256": SIM_SHA256,
    "fw_sha256": FW_SHA256,
    "algorithm_tip": ALGORITHM_TIP,
}


def _resolve_a_file(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    if path.is_dir():
        sibling = path / "demo_result.json"
        return sibling if sibling.is_file() and sibling.stat().st_size > 0 else None
    if path.is_file() and path.stat().st_size > 0:
        if path.name == "synthetic_demo.json":
            result = path.with_name("demo_result.json")
            if result.is_file() and result.stat().st_size > 0:
                return result
        return path
    return None


def locate_a_output(explicit: Optional[Path] = None) -> Optional[Path]:
    if explicit is not None:
        return _resolve_a_file(Path(explicit))
    env_path = os.environ.get("T5208U_A_SYNTHETIC_JSON")
    if env_path:
        resolved = _resolve_a_file(Path(env_path))
        if resolved is not None:
            return resolved
    for path in A_SEARCH_PATHS:
        resolved = _resolve_a_file(path)
        if resolved is not None:
            return resolved
    return None


def bind_a_api() -> str:
    """Import A's actual caller. Does not invoke IF/Q2 produce (no science EXEC)."""
    from src.services.nfl_t5208u.caller import call_r6_point_margin

    if call_r6_point_margin is None:
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "call_r6_point_margin missing")
    return call_r6_point_margin.__name__


def refuse_real_mode(mode: str) -> None:
    """Must run before any reader / model / ledger forecast write."""
    token = (mode or "").strip().upper()
    if token == SYNTHETIC_CHANNEL:
        return
    raise R6Refuse(
        R6RefuseCode.REFUSE_REAL_MODE,
        "t5208u CLEAR grants no EXEC auth + no manifest-bound GO + no real data scope",
    )


def _is_a_demo_result(packet: Mapping[str, Any]) -> bool:
    return (
        packet.get("schema_id") == A_SCHEMA_ID
        and packet.get("channel") == SYNTHETIC_CHANNEL
        and packet.get("output_kind") == OUTPUT_KIND
        and "if_margin" in packet
        and "c_margin" in packet
    )


def _require_synthetic_packet(packet: Mapping[str, Any]) -> None:
    if packet.get("usable_by_real_mode") is True or packet.get("real_mode_usable") is True:
        raise R6Refuse(R6RefuseCode.REFUSE_REAL_MODE, "usable_by_real_mode cannot be true")
    if _is_a_demo_result(packet):
        return
    if packet.get("synthetic") is not True:
        raise R6Refuse(R6RefuseCode.REFUSE_SYNTHETIC, "packet.synthetic must be true")
    if packet.get("channel") != SYNTHETIC_CHANNEL:
        raise R6Refuse(R6RefuseCode.REFUSE_SYNTHETIC, "packet.channel must be SYNTHETIC")
    if packet.get("production_mode") is not False:
        raise R6Refuse(R6RefuseCode.REFUSE_REAL_MODE, "production_mode must be false")


def _check_pins(packet: Mapping[str, Any]) -> None:
    preflight = packet.get("if_preflight") if isinstance(packet.get("if_preflight"), dict) else {}
    for key, expected in PIN_KEYS.items():
        got = packet.get(key, preflight.get(key) if isinstance(preflight, dict) else None)
        if got is None:
            continue
        if str(got) != expected and not str(got).startswith(expected[:8]):
            raise R6Refuse(R6RefuseCode.REFUSE_PIN, f"{key} {got!r} != {expected}")
    fields = packet.get("contract_27")
    if isinstance(fields, (list, tuple)) and tuple(fields) != CONTRACT_27:
        raise R6Refuse(R6RefuseCode.REFUSE_PIN, "contract_27 literal mismatch vs 455a8e43")


def _games_from_a_demo_result(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    envelope = raw.get("envelope") if isinstance(raw.get("envelope"), dict) else {}
    return [
        {
            "game_id": raw.get("game_id") or envelope.get("game_id"),
            "point_margin": {
                "if_mean": raw.get("if_margin"),
                "q2_mean": raw.get("q2_margin"),
                "c_mean": raw.get("c_margin"),
            },
            "input_hash": raw.get("schema_hash") or "",
            "state_hash": "",
            "config_hash": raw.get("schema_hash") or "",
            "cutoff": dict(envelope),
            "seed": raw.get("seed"),
            "source_artifact": "demo_result.json",
        }
    ]


def consume_a_packet(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "A output must be an object")
    _require_synthetic_packet(raw)
    _check_pins(raw)
    if _is_a_demo_result(raw):
        games = _games_from_a_demo_result(raw)
        out = dict(raw)
        out["games"] = games
        out["synthetic"] = True
        out["production_mode"] = False
        return out
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
        "seed": game.get("seed"),
        "source_artifact": game.get("source_artifact"),
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
    a_api = bind_a_api()
    packet = consume_a_packet(json.loads(found.read_text(encoding="utf-8")))
    ledger = PairedArmLedger(ledger_root)
    sealed: list[Dict[str, Any]] = []
    projected_rows: list[Dict[str, Any]] = []
    for game in packet["games"]:
        if not isinstance(game, Mapping):
            raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "game row is not an object")
        projected = project_game(game)
        if projected["game_id"] == A_DEMO_GAME_ID:
            if abs(projected["if_mean"] - A_DEMO_IF) > 1e-12:
                raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "IF mean is not A's demo_result bind")
            if abs(projected["q2_mean"] - A_DEMO_Q2) > 1e-12:
                raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "Q2 mean is not A's demo_result bind")
            if abs(projected["c_mean"] - A_DEMO_C) > 1e-12:
                raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "C mean is not A's demo_result bind")
            if projected.get("seed") not in (None, A_DEMO_SEED) and int(projected["seed"]) != A_DEMO_SEED:
                raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "seed is not A's demo_result bind")
        sealed.append(seal_projected(ledger, projected, manifest_id=manifest_id))
        projected_rows.append(projected)
    return {
        "status": "OK",
        "a_path": str(found),
        "a_api": a_api,
        "a_tip": "1487e9f0195132916d9a6742d9d36d1493610e9d",
        "means_source": "A demo_result.json artifact only",
        "projected": projected_rows,
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
