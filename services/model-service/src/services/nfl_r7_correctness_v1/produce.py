"""Opt-in synthetic IF/Q2 producer for R7_CORRECTNESS_V1. CERT=0."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional

from src.services.nfl_ops_v1_evidence.spy import ForbiddenSurfaceSpy, OutcomeReadSpy
from src.services.nfl_r7_correctness_v1.config_adapter import (
    ADAPTER_VERSION,
    APPLY_LINEAR_TOTALS_CALIBRATION,
    resolve_immutable_config,
    totals_adjustment_settings,
)
from src.services.nfl_r7_correctness_v1.franchise import (
    key_packet_and_history_for_q2,
    q2_consumed_franchise_aliases,
)
from src.services.nfl_r7_correctness_v1.packets import require_typed_synthetic_input, refuse_if_real
from src.services.nfl_r7_correctness_v1.pins import (
    AUTHORITY,
    CALENDAR_ID,
    CALENDAR_TZ,
    CERT,
    CODE_FILES,
    EXPECTED_COMMAND,
    FRANCHISE_ALIASES,
    FROZEN_FRAMEWORK_SETTINGS,
    FROZEN_SIMULATOR_SETTINGS,
    FW_SHA256,
    GATE_713_TIP,
    IF_TIP,
    KO_MINUS_MINUTES,
    LA_SOURCE_MAP,
    OWNER_CLEAR,
    PACKAGE,
    PLAN_FINGERPRINT,
    R6_A_TIP,
    R6_B_TIP,
    SCHEMA_ID,
    SCOPE_ID,
    SIM_SHA256,
    WORKER_A_ID,
)
from src.services.nfl_t5107u.builder import challenger_margin
from src.services.nfl_t5208u.caller import call_r6_point_margin, replay_call
from src.services.nfl_t5208u.hashing import canonical_sha256, sha256_file
from src.services.nfl_t5208u.if_tree import preflight_if_tree
from src.services.nfl_t5208u.pins import (
    A_Q2,
    B_Q2,
    CANDIDATE_WEIGHT,
    C_FORMULA,
    MARKET_BLEND,
    PRIOR_CARRY,
    RIDGE,
    SEED_BASE,
    SEED_MOD,
    SIMULATIONS,
)
from src.services.nfl_t5208u.validate import config_content_hash as r6_config_hash


class R7ProduceRefuse(ValueError):
    """Fail-closed R7 produce."""


NUMERICAL_ENV_KEYS = (
    "T5108U_IF_TREE",
    "SIMULATIONS",
    "NFL_SIMULATIONS",
    "MARKET_BLEND",
    "CANDIDATE_WEIGHT",
    "KO_MINUS_MINUTES",
    "A_Q2",
    "B_Q2",
    "RIDGE",
    "PRIOR_CARRY",
    "SEED_BASE",
    "SEED_MOD",
)
NUMERICAL_ENV_PREFIXES = (
    "NFL_FRAMEWORK_",
    "NFL_TOTALS_",
)


def ambient_numerical_env_hits(environ_keys: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Name-only denylist. Never reads or returns environment values."""
    hits: list[str] = []
    for key in environ_keys:
        if key in NUMERICAL_ENV_KEYS or key.startswith(NUMERICAL_ENV_PREFIXES):
            hits.append(key)
    return tuple(hits)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _freeze(obj: Any) -> Any:
    if isinstance(obj, dict):
        return MappingProxyType({key: _freeze(value) for key, value in obj.items()})
    if isinstance(obj, list):
        return tuple(_freeze(value) for value in obj)
    return obj


def _unfreeze(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {key: _unfreeze(value) for key, value in obj.items()}
    if isinstance(obj, tuple):
        return [_unfreeze(value) for value in obj]
    return obj


def refuse_ambient_numerical_env(environ_keys: list[str] | tuple[str, ...] | None = None) -> None:
    keys = tuple(os.environ.keys()) if environ_keys is None else tuple(environ_keys)
    present = ambient_numerical_env_hits(keys)
    if present:
        raise R7ProduceRefuse(f"ambient numerical env reread refused: {list(present)}")


def consume_effective_config() -> MappingProxyType:
    """Immutable framework/simulator/helper settings. No ambient numerical env rereads."""
    refuse_ambient_numerical_env()
    preflight = preflight_if_tree()
    if preflight["sim_sha256"] != SIM_SHA256 or preflight["fw_sha256"] != FW_SHA256:
        raise R7ProduceRefuse("consumed IF tree pin mismatch")
    if preflight["if_tip"] != IF_TIP:
        raise R7ProduceRefuse("consumed IF tip mismatch")
    adapter = dict(resolve_immutable_config())
    if adapter["framework_name_count"] != 83 or adapter["simulator_name_count"] != 13:
        raise R7ProduceRefuse("adapter catalog count drifted from 83 FW / 13 SIM")
    if adapter["apply_linear_totals_calibration"] is not False:
        raise R7ProduceRefuse("R7 adapter must record apply_linear_totals_calibration=False")
    if adapter["ambient_env_reread"] is not False:
        raise R7ProduceRefuse("adapter ambient env reread must be False")
    forwarded = totals_adjustment_settings(adapter)
    body = {
        "adapter": adapter,
        "framework": {
            "fw_sha256": FW_SHA256,
            "if_tip": IF_TIP,
            "observed_fw_sha256": preflight["fw_sha256"],
            "settings": dict(FROZEN_FRAMEWORK_SETTINGS),
            "name_count": 83,
            "names": list(adapter["framework"]),
            "values": dict(adapter["framework_values"]),
            "active": list(adapter["active_framework"]),
            "disabled": list(adapter["disabled_framework"]),
        },
        "simulator": {
            "sim_sha256": SIM_SHA256,
            "simulations": SIMULATIONS,
            "market_blend": MARKET_BLEND,
            "seed_base": SEED_BASE,
            "seed_mod": SEED_MOD,
            "observed_sim_sha256": preflight["sim_sha256"],
            "settings": dict(FROZEN_SIMULATOR_SETTINGS),
            "name_count": 13,
            "names": list(adapter["simulator"]),
            "values": dict(adapter["simulator_values"]),
            "active": list(adapter["active_simulator"]),
            "unavailable": list(adapter["unavailable_simulator"]),
            "apply_linear_totals_calibration": APPLY_LINEAR_TOTALS_CALIBRATION,
            "totals_settings_forwarded": True,
            "totals_settings_names": sorted(forwarded.keys()),
        },
        "helper": {
            "c_formula": C_FORMULA,
            "candidate_weight": CANDIDATE_WEIGHT,
            "ko_minus_minutes": KO_MINUS_MINUTES,
            "a_q2": A_Q2,
            "b_q2": B_Q2,
            "ridge": RIDGE,
            "prior_carry": PRIOR_CARRY,
            "calendar_id": CALENDAR_ID,
            "calendar_tz": CALENDAR_TZ,
            "franchise_aliases": dict(sorted(FRANCHISE_ALIASES.items())),
            "la_source_map": dict(sorted(LA_SOURCE_MAP.items())),
            "q2_consumed_franchise_aliases": q2_consumed_franchise_aliases(),
            "used_production_rest_days_from_schedule": False,
            "q2_consumes_franchise_keys": True,
            "canonical_state_slots": True,
        },
        "r6": {
            "config_hash": r6_config_hash(),
            "r6_a_tip": R6_A_TIP,
            "r6_b_tip": R6_B_TIP,
        },
        "meta": {
            "package": PACKAGE,
            "owner_clear": OWNER_CLEAR,
            "scope_id": SCOPE_ID,
            "plan_fingerprint": PLAN_FINGERPRINT,
            "consumed": True,
            "immutable": True,
            "ambient_env_reread": False,
            "adapter_version": ADAPTER_VERSION,
            "apply_linear_totals_calibration": APPLY_LINEAR_TOTALS_CALIBRATION,
        },
    }
    return _freeze(body)


def r7_config_hash(cfg: Mapping[str, Any] | None = None) -> str:
    consumed = _unfreeze(cfg) if cfg is not None else _unfreeze(consume_effective_config())
    return canonical_sha256(consumed)


def r7_code_hash(root: Path | None = None) -> str:
    repo = repo_root() if root is None else Path(root)
    rows = []
    for rel in CODE_FILES:
        path = repo / rel
        if not path.is_file():
            raise R7ProduceRefuse(f"code bind missing {rel}")
        rows.append(f"{rel}={sha256_file(path)}")
    return canonical_sha256(rows)


def assert_consumed_config_bound(result: Mapping[str, Any], cfg: Mapping[str, Any]) -> None:
    if int(result.get("simulations", -1)) != int(cfg["simulator"]["simulations"]):
        raise R7ProduceRefuse("R6 simulations did not bind consumed simulator settings")
    if int(result.get("market_blend", -1)) != int(cfg["simulator"]["market_blend"]):
        raise R7ProduceRefuse("R6 market_blend did not bind consumed simulator settings")
    if result.get("config_hash") != cfg["r6"]["config_hash"]:
        raise R7ProduceRefuse("R6 config_hash did not bind consumed r6 settings")
    if result.get("c_formula") != cfg["helper"]["c_formula"]:
        raise R7ProduceRefuse("R6 c_formula did not bind consumed helper settings")
    if float(result.get("candidate_weight")) != float(cfg["helper"]["candidate_weight"]):
        raise R7ProduceRefuse("R6 candidate_weight did not bind consumed helper settings")
    if cfg["simulator"].get("apply_linear_totals_calibration") is not False:
        raise R7ProduceRefuse("consumed simulator must record apply_linear_totals_calibration=False")
    if result.get("linear_cal_flag") is not False:
        raise R7ProduceRefuse("R7 apply_linear_totals_calibration must be False")
    if result.get("settings_forwarded") is not True:
        raise R7ProduceRefuse("R7 totals settings were not forwarded")
    adapter = cfg.get("adapter")
    if not isinstance(adapter, Mapping):
        raise R7ProduceRefuse("consumed adapter missing")
    if int(adapter.get("framework_name_count", -1)) != 83:
        raise R7ProduceRefuse("consumed adapter framework_name_count != 83")
    if int(adapter.get("simulator_name_count", -1)) != 13:
        raise R7ProduceRefuse("consumed adapter simulator_name_count != 13")
    decomp = result.get("consumed_value_decomposition")
    if not isinstance(decomp, Mapping):
        raise R7ProduceRefuse("consumed-value decomposition missing")
    if decomp.get("apply_linear_totals_calibration") is not False:
        raise R7ProduceRefuse("decomposition apply_linear_totals_calibration must be False")
    if int(decomp.get("framework_name_count", -1)) != 83 or int(decomp.get("simulator_name_count", -1)) != 13:
        raise R7ProduceRefuse("decomposition catalog counts drifted from 83/13")


def produce_r7_point_margin(
    *,
    mode: str = "SYNTHETIC",
    surface: Optional[ForbiddenSurfaceSpy] = None,
    outcome_spy: Optional[OutcomeReadSpy] = None,
    synthetic_input: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    refuse_if_real(mode)
    if outcome_spy is not None and getattr(outcome_spy, "reads", 0) not in (None, 0):
        raise R7ProduceRefuse("outcome loader already read before produce")
    cfg = consume_effective_config()
    demo = require_typed_synthetic_input(synthetic_input, mode=mode)
    rest = demo["rest_calendar"]
    if rest["used_production_rest_days_from_schedule"] is not False:
        raise R7ProduceRefuse("production rest helper leaked into R7 bind")
    if rest.get("q2_history_used_for_rest") is not False:
        raise R7ProduceRefuse("Q2 history leaked into physical rest bind")
    if rest.get("predecessor_bound_to") != "KO_MINUS_60_CUTOFF":
        raise R7ProduceRefuse("calendar predecessor not bound to KO−60 cutoff")
    packet = demo["packet"]
    bound_home = float(packet["contract_27"]["rest_days_home"]["reconstructed_value"])
    bound_away = float(packet["contract_27"]["rest_days_away"]["reconstructed_value"])
    if bound_home != rest["rest_days_home"] or bound_away != rest["rest_days_away"]:
        raise R7ProduceRefuse("rest_days cells not bound from ET calendar")

    weight = float(cfg["helper"]["candidate_weight"])
    controls = []
    for row in demo["c_formula_controls"]:
        got = challenger_margin(row["if_margin"], row["q2_margin"], w=weight)
        controls.append({**row, "got_c": got, "ok": got == row["expected_c"]})
    if not all(item["ok"] for item in controls):
        raise R7ProduceRefuse(f"C formula controls failed: {controls}")

    keyed_packet, keyed_history = key_packet_and_history_for_q2(packet, demo["history"])
    if surface is not None:
        surface.note("call_r6_point_margin")
    result = call_r6_point_margin(
        keyed_packet, keyed_history, mode=mode, effective_config=cfg
    )
    replay = replay_call(
        keyed_packet, keyed_history, mode=mode, effective_config=cfg
    )
    assert_consumed_config_bound(result, cfg)
    digest = r7_config_hash(cfg)
    code = r7_code_hash()
    if digest == result["schema_hash"] or code == result["schema_hash"]:
        raise R7ProduceRefuse("R7 config/code hash collapsed onto schema_hash")
    out = {
        "package": PACKAGE,
        "schema_id": SCHEMA_ID,
        "authority": AUTHORITY,
        "owner_clear": OWNER_CLEAR,
        "scope_id": SCOPE_ID,
        "worker_id": WORKER_A_ID,
        "cert": CERT,
        "channel": "SYNTHETIC",
        "opt_in": True,
        "implemented_ne_verified": True,
        "command": EXPECTED_COMMAND,
        "if_preflight": {
            "status": "PRESENT_PIN_MATCH",
            "if_tip": cfg["framework"]["if_tip"],
            "sim_sha256": cfg["simulator"]["observed_sim_sha256"],
            "fw_sha256": cfg["framework"]["observed_fw_sha256"],
        },
        "effective_config": _unfreeze(cfg),
        "franchise_bind": demo["franchise_bind"],
        "rest_calendar": rest,
        "r6_point_margin": result,
        "r7_config_hash": digest,
        "r7_code_hash": code,
        "r6_config_hash": result["config_hash"],
        "r6_code_hash": result["code_hash"],
        "r6_a_tip": R6_A_TIP,
        "r6_b_tip": R6_B_TIP,
        "gate_713_tip": GATE_713_TIP,
        "replay_ok": replay["replay_ok"],
        "c_formula": cfg["helper"]["c_formula"],
        "c_formula_controls": controls,
        "output_kind": "POINT_MARGIN",
        "if_margin": result["if_margin"],
        "q2_margin": result["q2_margin"],
        "c_margin": result["c_margin"],
        "game_id": result["game_id"],
        "packet_hash": result["packet_hash"],
        "history_hash": result["history_hash"],
        "cutoff_utc": result["cutoff_utc"],
        "seal_utc": result["seal_utc"],
        "kickoff_utc": result["kickoff_utc"],
        "q2_franchise_keyed": True,
        "q2_canonical_state_slots": True,
        "q2_consumed_franchise_aliases": q2_consumed_franchise_aliases(),
        "linear_cal_flag": result.get("linear_cal_flag"),
        "apply_linear_totals_calibration": result.get("linear_cal_flag"),
        "settings_forwarded": result.get("settings_forwarded"),
        "consumed_value_decomposition": result.get("consumed_value_decomposition"),
        "demo": demo,
    }
    return out


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_json(path: Path, payload: Any) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    atomic_write_bytes(path, data)


def atomic_replace_file(src: Path, dest: Path) -> None:
    atomic_write_bytes(dest, Path(src).read_bytes())


def write_produce_artifacts(result: dict[str, Any], *, dest: Path) -> dict[str, str]:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    demo = result["demo"]
    write_json(dest / "synthetic_demo.json", demo)
    write_json(
        dest / "demo_result.json",
        {key: value for key, value in result.items() if key != "demo"},
    )
    return {
        "synthetic_demo": (dest / "synthetic_demo.json").as_posix(),
        "demo_result": (dest / "demo_result.json").as_posix(),
    }


def load_produce_artifacts(dest: Path) -> dict[str, Any]:
    dest = Path(dest)
    result = json.loads((dest / "demo_result.json").read_text(encoding="utf-8"))
    demo = json.loads((dest / "synthetic_demo.json").read_text(encoding="utf-8"))
    result["demo"] = demo
    return result


def produce_only_main(argv: list[str] | None = None) -> int:
    """Child process for observed produce exit. Parent binds proc.returncode."""
    parser = argparse.ArgumentParser(prog="run_nfl_r7_produce_only")
    parser.add_argument("--dest", required=True)
    parser.add_argument("--mode", default="SYNTHETIC")
    args = parser.parse_args(argv)
    try:
        result = produce_r7_point_margin(mode=args.mode)
        write_produce_artifacts(result, dest=Path(args.dest))
        print(
            json.dumps(
                {
                    "ok": True,
                    "game_id": result["game_id"],
                    "if_margin": result["if_margin"],
                    "q2_margin": result["q2_margin"],
                    "c_margin": result["c_margin"],
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
