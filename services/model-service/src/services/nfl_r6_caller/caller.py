"""R6 caller: real mode refuses before readers/model; live A invoke → B seal.

This CLEAR grants no EXEC auth, no manifest-bound GO, and no permitted
real-data scope. 79264 authorizes synthetic IF invocation only.
Positive IF/C means come from a live call_r6_point_margin result (or a
complete A context). No hardcoded demo means. No sha8-prefix pin match.
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
    C_WEIGHT_IF,
    C_WEIGHT_Q2,
    OUTPUT_KIND,
    PACKAGE_ID,
    PRIOR_CARRY,
    RIDGE_LAMBDA,
    SCHEMA_VERSION,
    SYNTHETIC_CHANNEL,
    R6Refuse,
    R6RefuseCode,
    cutoff_from_kickoff,
    expected_c_mean,
    pin_block,
    require_canonical_hash,
    require_full_pins,
    require_parsed_cutoff,
)
from src.services.nfl_r6_caller.ledger import (
    PairedArmLedger,
    canonical_json,
    make_seal_record,
    sha256_hex,
    verify_seal_record,
)

_REPO_ROOT = Path(__file__).resolve().parents[5]
A_DEMO_RESULT = _REPO_ROOT / "data/ops/t5218u-r6-timing-delta/demo_result.json"
A_DEMO_PACKET = _REPO_ROOT / "data/ops/t5218u-r6-timing-delta/synthetic_demo.json"
A_SEARCH_PATHS = (
    A_DEMO_PACKET,
    A_DEMO_RESULT,
    _REPO_ROOT / "data/ops/t5213u-r6-pure-function/synthetic_demo.json",
    _REPO_ROOT / "data/ops/t5213u-r6-pure-function/demo_result.json",
)
A_TIP = "54b08a301cf824c79ee3203180a51e2d832bb6f9"
PAPER_KICKOFF = "2018-10-14T17:00:00Z"
# Hash/cutoff binds from accepted A tip — not IF/Q2/C means, not schema_hash.
A_EXPECTED_BINDS = {
    "packet_hash": "ee71ffc65200e8ebbd59d9447bbede20b9cbab015af7deb5748bfc35b62efee8",
    "history_hash": "d194de4508a30a2baa09c2c7d96f8ee26d74bd0b22587430d4d936de4fd897e8",
    "config_hash": "01d61811a922f75701b080a57d00f6e0feea7e87cbe016c9e4d26903183cee29",
    "code_hash": "906ec8d395a5f17276b85abcea62af3729961842411138f9b1b70b42c3634b4a",
    "cutoff_utc": "2018-10-14T16:00:00Z",
    "seal_utc": "2018-10-14T16:00:00Z",
    "schema_hash": "ce3747cc7d5368dfbb60ebfa4fff87ae52890afd60ba3b596bc5baa5849e50d8",
}


class CallSpy:
    """Counts actual A caller / model invocations using A's 79264 spy."""

    def __init__(self) -> None:
        self.a_calls = 0

    def reset(self) -> None:
        self.a_calls = 0
        from src.services.nfl_t5208u.caller import reset_model_spy

        reset_model_spy()

    def install(self) -> "CallSpy":
        from src.services.nfl_t5208u.caller import model_spy_counts, reset_model_spy

        del model_spy_counts, reset_model_spy
        return self

    @property
    def model_calls(self) -> int:
        from src.services.nfl_t5208u.caller import model_spy_counts

        return int(model_spy_counts().get("produce_if_mu") or 0)

    def snapshot(self) -> Dict[str, int]:
        return {"a_calls": self.a_calls, "model_calls": self.model_calls}


SPY = CallSpy()


def locate_a_output(explicit: Optional[Path] = None) -> Optional[Path]:
    if explicit is not None:
        path = Path(explicit)
        return path if path.is_file() and path.stat().st_size > 0 else None
    env_path = os.environ.get("T5208U_A_SYNTHETIC_JSON") or os.environ.get(
        "T5208U_SYNTHETIC_DEMO"
    )
    if env_path:
        path = Path(env_path)
        if path.is_file() and path.stat().st_size > 0:
            return path
    for path in A_SEARCH_PATHS:
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def bind_a_api() -> str:
    """Import A's actual caller. Does not invoke until invoke_a_frozen_caller."""
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
        "t5213u CLEAR grants no EXEC auth + no manifest-bound GO + no real data scope",
    )


def load_synthetic_handoff(path: Optional[Path] = None) -> Dict[str, Any]:
    found = Path(path) if path is not None else locate_a_output(A_DEMO_PACKET)
    if found is None or not found.is_file():
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "synthetic packet/history file missing")
    if found.name == "demo_result.json":
        found = found.with_name("synthetic_demo.json")
    raw = json.loads(found.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "synthetic handoff must be an object")
    packet = raw.get("packet")
    history = raw.get("history")
    if not isinstance(packet, dict) or not isinstance(history, list) or not history:
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "synthetic handoff missing packet/history")
    return {"path": found, "packet": packet, "history": history, "raw": raw}


def _preflight_live_handoff(
    packet: Mapping[str, Any],
    history: Any,
    *,
    mode: str,
) -> None:
    refuse_real_mode(mode)
    if packet.get("usable_by_real_mode") is True or packet.get("real_mode_usable") is True:
        raise R6Refuse(R6RefuseCode.REFUSE_REAL_MODE, "usable_by_real_mode cannot be true")
    if packet.get("channel") not in (None, SYNTHETIC_CHANNEL) and packet.get("channel") != SYNTHETIC_CHANNEL:
        raise R6Refuse(R6RefuseCode.REFUSE_SYNTHETIC, "packet.channel must be SYNTHETIC")
    env = packet.get("envelope") if isinstance(packet.get("envelope"), Mapping) else {}
    cutoff_from_kickoff(env.get("kickoff_utc"))
    if not isinstance(history, list) or not history:
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "history missing")


def invoke_a_frozen_caller(
    packet: Mapping[str, Any],
    history: list[Mapping[str, Any]],
    *,
    mode: str = SYNTHETIC_CHANNEL,
) -> Dict[str, Any]:
    """79264: synthetic IF invocation authorized. Real mode never reaches A."""
    _preflight_live_handoff(packet, history, mode=mode)
    SPY.install()
    from src.services.nfl_t5208u.caller import call_r6_point_margin

    SPY.a_calls += 1
    result = call_r6_point_margin(packet, list(history), mode=mode)
    if not isinstance(result, dict):
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "A live result is not an object")
    return result


def bind_live_context(
    a_result: Mapping[str, Any],
    packet: Mapping[str, Any],
    history: list[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Bind A's actual packet/history/config/code hashes + parsed KO−60.

    Never copies schema_hash into input/config. Never fills empty state_hash.
    """
    from src.services.nfl_t5208u.validate import (
        code_content_hash,
        config_content_hash,
        history_content_hash,
        packet_content_hash,
    )

    schema_hash = str(a_result.get("schema_hash") or "")
    forbidden = frozenset([schema_hash]) if schema_hash else frozenset()
    packet_hash = require_canonical_hash(
        a_result.get("packet_hash"), label="packet_hash", forbidden=forbidden
    )
    history_hash = require_canonical_hash(
        a_result.get("history_hash"), label="history_hash", forbidden=forbidden
    )
    config_hash = require_canonical_hash(
        a_result.get("config_hash"), label="config_hash", forbidden=forbidden
    )
    code_hash = require_canonical_hash(
        a_result.get("code_hash"), label="code_hash", forbidden=forbidden
    )
    if packet_content_hash(packet) != packet_hash:
        raise R6Refuse(R6RefuseCode.REFUSE_HASH, "packet_hash != canonical packet")
    if history_content_hash(list(history)) != history_hash:
        raise R6Refuse(R6RefuseCode.REFUSE_HASH, "history_hash != canonical history")
    if config_content_hash() != config_hash:
        raise R6Refuse(R6RefuseCode.REFUSE_HASH, "config_hash != A's config bind")
    if code_content_hash() != code_hash:
        raise R6Refuse(R6RefuseCode.REFUSE_HASH, "code_hash != A's code bind")

    env = a_result.get("envelope") if isinstance(a_result.get("envelope"), Mapping) else {}
    if not env:
        env = packet.get("envelope") if isinstance(packet.get("envelope"), Mapping) else {}
    cutoff = cutoff_from_kickoff(env.get("kickoff_utc"))
    a_cutoff = a_result.get("cutoff_utc")
    if a_cutoff not in (None, "") and str(a_cutoff) != cutoff["cutoff_utc"]:
        raise R6Refuse(
            R6RefuseCode.REFUSE_CUTOFF,
            f"A cutoff_utc {a_cutoff!r} != parsed KO−60 {cutoff['cutoff_utc']}",
        )
    a_seal = a_result.get("seal_utc")
    if a_seal not in (None, "") and str(a_seal) != cutoff["seal_utc"]:
        raise R6Refuse(
            R6RefuseCode.REFUSE_CUTOFF,
            f"kickoff-as-seal refused: A seal_utc {a_seal!r} != KO−60 {cutoff['seal_utc']}",
        )
    game_id = str(a_result.get("game_id") or env.get("game_id") or "")
    if game_id == "SYNTHETIC_2018_W05_KC_NE":
        for key, expected in A_EXPECTED_BINDS.items():
            if key == "schema_hash":
                if schema_hash != expected:
                    raise R6Refuse(R6RefuseCode.REFUSE_HASH, "schema_hash identity drift")
                continue
            if key in ("cutoff_utc", "seal_utc"):
                if cutoff[key] != expected:
                    raise R6Refuse(R6RefuseCode.REFUSE_CUTOFF, f"{key} bind drift")
                continue
            got = {
                "packet_hash": packet_hash,
                "history_hash": history_hash,
                "config_hash": config_hash,
                "code_hash": code_hash,
            }[key]
            if got != expected:
                raise R6Refuse(R6RefuseCode.REFUSE_HASH, f"{key} != accepted A bind")

    out = dict(a_result)
    out.update(
        {
            "synthetic": True,
            "production_mode": False,
            "usable_by_real_mode": False,
            "channel": SYNTHETIC_CHANNEL,
            "algorithm_tip": ALGORITHM_TIP,
            "if_tip": a_result.get("if_tip")
            or (a_result.get("if_preflight") or {}).get("if_tip"),
            "sim_sha256": (a_result.get("if_preflight") or {}).get("sim_sha256")
            or a_result.get("sim_sha256"),
            "fw_sha256": (a_result.get("if_preflight") or {}).get("fw_sha256")
            or a_result.get("fw_sha256"),
            "input_hash": packet_hash,
            "state_hash": history_hash,
            "config_hash": config_hash,
            "code_hash": code_hash,
            "cutoff": cutoff,
            "means_source": "live call_r6_point_margin",
        }
    )
    require_full_pins(out)
    out["games"] = [
        {
            "game_id": game_id,
            "point_margin": {
                "if_mean": a_result.get("if_margin"),
                "q2_mean": a_result.get("q2_margin"),
                "c_mean": a_result.get("c_margin"),
            },
            "input_hash": packet_hash,
            "state_hash": history_hash,
            "config_hash": config_hash,
            "code_hash": code_hash,
            "cutoff": cutoff,
            "seed": a_result.get("seed"),
            "schema_hash": schema_hash,
            "source_artifact": "live_call_r6_point_margin",
        }
    ]
    return out


def _require_synthetic_packet(packet: Mapping[str, Any]) -> None:
    if packet.get("usable_by_real_mode") is True or packet.get("real_mode_usable") is True:
        raise R6Refuse(R6RefuseCode.REFUSE_REAL_MODE, "usable_by_real_mode cannot be true")
    if packet.get("channel") not in (None, SYNTHETIC_CHANNEL) and str(packet.get("channel")) != SYNTHETIC_CHANNEL:
        raise R6Refuse(R6RefuseCode.REFUSE_SYNTHETIC, "packet.channel must be SYNTHETIC")
    if packet.get("production_mode") is True:
        raise R6Refuse(R6RefuseCode.REFUSE_REAL_MODE, "production_mode must not be true")


def _schema_forbidden(raw: Mapping[str, Any]) -> frozenset[str]:
    schema_hash = raw.get("schema_hash")
    return frozenset([str(schema_hash)]) if schema_hash else frozenset()


def consume_a_packet(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "A output must be an object")
    _require_synthetic_packet(raw)
    require_full_pins(raw)
    games = raw.get("games")
    if not isinstance(games, list) or not games:
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "A output has no games")
    forbidden = _schema_forbidden(raw)
    for game in games:
        if not isinstance(game, Mapping):
            raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "game row is not an object")
        require_canonical_hash(game.get("input_hash"), label="input_hash", forbidden=forbidden)
        require_canonical_hash(game.get("state_hash"), label="state_hash", forbidden=forbidden)
        require_canonical_hash(game.get("config_hash"), label="config_hash", forbidden=forbidden)
        require_parsed_cutoff(game.get("cutoff") or raw.get("cutoff"))
    return raw


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, f"{label} is not a number")
    out = float(value)
    if not math.isfinite(out):
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, f"{label} is not finite")
    return out


def project_game(game: Mapping[str, Any], *, schema_hash: Any = None) -> Dict[str, Any]:
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
    for forbidden_key in ("moneyline", "total", "cover_probability", "win_prob"):
        if forbidden_key in game or forbidden_key in pm:
            raise R6Refuse(R6RefuseCode.REFUSE_OUTPUT, f"{forbidden_key} not authorized")
    forbidden = frozenset([str(schema_hash)]) if schema_hash else _schema_forbidden(game)
    return {
        "game_id": game_id,
        "if_mean": if_mean,
        "q2_mean": q2_mean,
        "c_mean": c_mean,
        "seed": game.get("seed"),
        "source_artifact": game.get("source_artifact"),
        "input_hash": require_canonical_hash(
            game.get("input_hash"), label="input_hash", forbidden=forbidden
        ),
        "state_hash": require_canonical_hash(
            game.get("state_hash"), label="state_hash", forbidden=forbidden
        ),
        "config_hash": require_canonical_hash(
            game.get("config_hash"), label="config_hash", forbidden=forbidden
        ),
        "cutoff": require_parsed_cutoff(game.get("cutoff")),
        "schema_hash": str(schema_hash) if schema_hash else game.get("schema_hash"),
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
        schema_hash=str(projected["schema_hash"]) if projected.get("schema_hash") else None,
    )
    return ledger.seal(record)


def run_live_a_e2e(
    *,
    ledger_root: Path,
    handoff_path: Optional[Path] = None,
    manifest_id: str = "t5213u-r6-live-e2e",
    replay: bool = True,
) -> Dict[str, Any]:
    SPY.install()
    SPY.reset()
    before = SPY.snapshot()
    handoff = load_synthetic_handoff(handoff_path)
    packet = handoff["packet"]
    history = handoff["history"]
    first = invoke_a_frozen_caller(packet, history)
    second = None
    if replay:
        second = invoke_a_frozen_caller(packet, history)
        for key in ("if_margin", "q2_margin", "c_margin", "seed"):
            if first.get(key) != second.get(key):
                raise R6Refuse(
                    R6RefuseCode.REFUSE_A_OUTPUT,
                    f"replay mismatch on {key}: {first.get(key)} vs {second.get(key)}",
                )
    context = bind_live_context(first, packet, history)
    packet = consume_a_packet(context)
    ledger = PairedArmLedger(ledger_root)
    sealed: list[Dict[str, Any]] = []
    projected_rows: list[Dict[str, Any]] = []
    for game in packet["games"]:
        projected = project_game(game, schema_hash=packet.get("schema_hash"))
        sealed.append(seal_projected(ledger, projected, manifest_id=manifest_id))
        projected_rows.append(projected)
    reread = ledger.read(projected_rows[0]["game_id"])
    if reread is None:
        raise R6Refuse(R6RefuseCode.REFUSE_PARTIAL, "sealed game missing on read")
    verify_seal_record(reread)
    after = SPY.snapshot()
    return {
        "status": "OK",
        "a_path": str(handoff["path"]),
        "a_api": bind_a_api(),
        "a_tip": A_TIP,
        "means_source": "live call_r6_point_margin",
        "a_calls": after["a_calls"] - before["a_calls"],
        "model_calls": after["model_calls"] - before["model_calls"],
        "replay_ok": bool(second),
        "projected": projected_rows,
        "sealed": sealed,
        "read": reread,
        "packet_hash": context.get("input_hash"),
        "history_hash": context.get("state_hash"),
        "input_hash": projected_rows[0]["input_hash"],
        "state_hash": projected_rows[0]["state_hash"],
        "config_hash": projected_rows[0]["config_hash"],
        "code_hash": context.get("code_hash"),
        "cutoff": projected_rows[0]["cutoff"],
        "pins": pin_block(),
        "package_id": PACKAGE_ID,
        "schema_version": SCHEMA_VERSION,
        "q2_diagnostic_only": True,
        "c_weights": {"if": C_WEIGHT_IF, "q2": C_WEIGHT_Q2},
        "q2_coeffs": {"a": A_Q2, "b": B_Q2, "ridge": RIDGE_LAMBDA, "prior_carry": PRIOR_CARRY},
    }


def run_synthetic_e2e(
    *,
    ledger_root: Path,
    a_path: Optional[Path] = None,
    manifest_id: str = "t5213u-r6-live-e2e",
    live: bool = True,
) -> Dict[str, Any]:
    if live:
        return run_live_a_e2e(ledger_root=ledger_root, handoff_path=a_path, manifest_id=manifest_id)
    found = locate_a_output(a_path)
    if found is None:
        raise R6Refuse(
            R6RefuseCode.REFUSE_A_OUTPUT,
            "A synthetic output not present (no fabricated IF mean)",
        )
    raw = json.loads(found.read_text(encoding="utf-8"))
    packet = consume_a_packet(raw)
    ledger = PairedArmLedger(ledger_root)
    sealed: list[Dict[str, Any]] = []
    projected_rows: list[Dict[str, Any]] = []
    for game in packet["games"]:
        if not isinstance(game, Mapping):
            raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "game row is not an object")
        projected = project_game(game, schema_hash=packet.get("schema_hash"))
        sealed.append(seal_projected(ledger, projected, manifest_id=manifest_id))
        projected_rows.append(projected)
    return {
        "status": "OK",
        "a_path": str(found),
        "a_api": bind_a_api(),
        "a_tip": A_TIP,
        "means_source": "A complete context file",
        "projected": projected_rows,
        "sealed": sealed,
        "pins": pin_block(),
        "package_id": PACKAGE_ID,
        "schema_version": SCHEMA_VERSION,
    }


def prove_real_mode_refuse() -> Dict[str, Any]:
    before = SPY.snapshot()
    try:
        refuse_real_mode("REAL")
    except R6Refuse as exc:
        if exc.code != R6RefuseCode.REFUSE_REAL_MODE:
            raise
        after = SPY.snapshot()
        if after["a_calls"] != before["a_calls"] or after["model_calls"] != before["model_calls"]:
            raise R6Refuse(R6RefuseCode.REFUSE_REAL_MODE, "model called on real-mode refuse")
        return exc.to_dict()
    raise AssertionError("REAL mode leaked")


def _refuse_code(fn: Any) -> str:
    try:
        fn()
    except R6Refuse as exc:
        return exc.code
    raise AssertionError("expected refuse")


def _base_game(**overrides: Any) -> Dict[str, Any]:
    game = {
        "game_id": "SYNTHETIC_2018_W05_KC_NE",
        "point_margin": {"if_mean": 3.0, "q2_mean": 1.0, "c_mean": 2.0},
        "input_hash": "a" * 64,
        "state_hash": "b" * 64,
        "config_hash": "c" * 64,
        "cutoff": cutoff_from_kickoff(PAPER_KICKOFF),
        "seed": 1,
    }
    game.update(overrides)
    return game


def _base_packet(**overrides: Any) -> Dict[str, Any]:
    packet = {
        "synthetic": True,
        "channel": SYNTHETIC_CHANNEL,
        "production_mode": False,
        "usable_by_real_mode": False,
        "if_tip": pin_block()["if_tip"],
        "sim_sha256": pin_block()["sim_sha256"],
        "fw_sha256": pin_block()["fw_sha256"],
        "algorithm_tip": ALGORITHM_TIP,
        "games": [_base_game()],
    }
    packet.update(overrides)
    return packet


def prove_ryan_cases(ledger_root: Path) -> Dict[str, str]:
    """Exact runtime-proven B cases from OWNER CLEAR t5213u."""
    SPY.install()
    SPY.reset()
    before = SPY.snapshot()

    missing = _refuse_code(lambda: consume_a_packet(_base_packet(if_tip=None)))
    wrong_if = IF_TIP_PREFIX_CORRUPT
    prefix = _refuse_code(lambda: consume_a_packet(_base_packet(if_tip=wrong_if)))
    schema = "ce3747cc7d5368dfbb60ebfa4fff87ae52890afd60ba3b596bc5baa5849e50d8"
    schema_as_hash = _refuse_code(
        lambda: consume_a_packet(
            _base_packet(
                schema_hash=schema,
                games=[_base_game(input_hash=schema, config_hash=schema, state_hash="d" * 64)],
            )
        )
    )
    empty_state = _refuse_code(
        lambda: consume_a_packet(_base_packet(games=[_base_game(state_hash="")]))
    )
    bad_time = _refuse_code(
        lambda: consume_a_packet(
            _base_packet(games=[_base_game(cutoff={"kickoff_utc": "not-a-time"})])
        )
    )
    kickoff_as_seal = _refuse_code(
        lambda: consume_a_packet(
            _base_packet(
                games=[
                    _base_game(
                        cutoff={
                            "kickoff_utc": PAPER_KICKOFF,
                            "cutoff_utc": "2018-10-14T16:00:00Z",
                            "seal_utc": PAPER_KICKOFF,
                        }
                    )
                ]
            )
        )
    )

    ledger = PairedArmLedger(ledger_root)
    ok = consume_a_packet(_base_packet())
    projected = project_game(ok["games"][0])
    first = seal_projected(ledger, projected, manifest_id="t5213u-ryan-tamper")
    dest = ledger.path_for(projected["game_id"])
    tampered = json.loads(dest.read_text(encoding="utf-8"))
    tampered["arms"]["C"]["mean"] = 999
    tampered["seal_id"] = "0" * 64
    dest.write_text(json.dumps(tampered, indent=2), encoding="utf-8")
    before_bytes = dest.read_bytes()
    read_code = _refuse_code(lambda: ledger.read(projected["game_id"]))
    seal_again = _refuse_code(
        lambda: seal_projected(ledger, projected, manifest_id="t5213u-ryan-tamper-2")
    )
    after_bytes = dest.read_bytes()
    if before_bytes != after_bytes:
        raise R6Refuse(R6RefuseCode.REFUSE_TAMPER, "tampered file was overwritten")
    after = SPY.snapshot()
    if after["a_calls"] != before["a_calls"] or after["model_calls"] != before["model_calls"]:
        raise R6Refuse(R6RefuseCode.REFUSE_A_OUTPUT, "model called on Ryan refuse cases")
    return {
        "missing_pins": missing,
        "prefix_if_pin": prefix,
        "schema_as_hash": schema_as_hash,
        "empty_state_hash": empty_state,
        "bad_kickoff": bad_time,
        "kickoff_as_seal": kickoff_as_seal,
        "tamper_read": read_code,
        "tamper_seal": seal_again,
        "first_seal_id": first["seal_id"],
    }


IF_TIP_PREFIX_CORRUPT = "6ca03716ffffffffffffffffffffffffffffffff"


def prove_seal_refuses(ledger_root: Path) -> Dict[str, str]:
    """Duplicate / race / partial-write without inventing IF means."""
    ledger = PairedArmLedger(ledger_root)
    refuse_arms = {
        "IF": {"status": "REFUSE", "mean": None, "kind": OUTPUT_KIND},
        "C": {"status": "REFUSE", "mean": None, "kind": OUTPUT_KIND},
    }
    cutoff = cutoff_from_kickoff(PAPER_KICKOFF)
    record = make_seal_record(
        game_id="2026_99_R6_SYN",
        input_hash="d" * 64,
        state_hash="e" * 64,
        config_hash=sha256_hex(canonical_json(pin_block())),
        cutoff=cutoff,
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
            state_hash="f" * 64,
            config_hash=first["config_hash"],
            cutoff=cutoff,
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
        state_hash="a" * 64,
        config_hash=first["config_hash"],
        cutoff=cutoff,
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
