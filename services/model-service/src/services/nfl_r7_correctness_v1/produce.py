"""Opt-in synthetic IF/Q2 producer for R7_CORRECTNESS_V1. CERT=0."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.services.nfl_r7_correctness_v1.packets import build_synthetic_r7_demo, refuse_if_real
from src.services.nfl_r7_correctness_v1.pins import (
    AUTHORITY,
    CALENDAR_ID,
    CALENDAR_TZ,
    CERT,
    CODE_FILES,
    EXPECTED_COMMAND,
    FRANCHISE_ALIASES,
    FW_SHA256,
    GATE_713_TIP,
    IF_TIP,
    OPS_REL,
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
from src.services.nfl_t5208u.pins import CANDIDATE_WEIGHT, C_FORMULA
from src.services.nfl_t5208u.validate import config_content_hash as r6_config_hash


class R7ProduceRefuse(ValueError):
    """Fail-closed R7 produce."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def r7_config_hash() -> str:
    return canonical_sha256(
        {
            "calendar_id": CALENDAR_ID,
            "calendar_tz": CALENDAR_TZ,
            "franchise_aliases": dict(sorted(FRANCHISE_ALIASES.items())),
            "fw_sha256": FW_SHA256,
            "if_tip": IF_TIP,
            "owner_clear": OWNER_CLEAR,
            "package": PACKAGE,
            "plan_fingerprint": PLAN_FINGERPRINT,
            "r6_a_tip": R6_A_TIP,
            "r6_b_tip": R6_B_TIP,
            "r6_config_hash": r6_config_hash(),
            "scope_id": SCOPE_ID,
            "sim_sha256": SIM_SHA256,
            "used_production_rest_days_from_schedule": False,
        }
    )


def r7_code_hash(root: Path | None = None) -> str:
    repo = repo_root() if root is None else Path(root)
    rows = []
    for rel in CODE_FILES:
        path = repo / rel
        if not path.is_file():
            raise R7ProduceRefuse(f"code bind missing {rel}")
        rows.append(f"{rel}={sha256_file(path)}")
    return canonical_sha256(rows)


def produce_r7_point_margin(*, mode: str = "SYNTHETIC") -> dict[str, Any]:
    refuse_if_real(mode)
    preflight = preflight_if_tree()
    demo = build_synthetic_r7_demo(mode=mode)
    rest = demo["rest_calendar"]
    if rest["used_production_rest_days_from_schedule"] is not False:
        raise R7ProduceRefuse("production rest helper leaked into R7 bind")
    if rest["rest_days_home"] == rest["utc_date_delta_home"]:
        # TNF control must differ ET vs UTC date delta on this slate.
        raise R7ProduceRefuse("ET/UTC rest control collapsed — slate is not the TNF probe")
    packet = demo["packet"]
    bound_home = float(packet["contract_27"]["rest_days_home"]["reconstructed_value"])
    bound_away = float(packet["contract_27"]["rest_days_away"]["reconstructed_value"])
    if bound_home != rest["rest_days_home"] or bound_away != rest["rest_days_away"]:
        raise R7ProduceRefuse("rest_days cells not bound from ET calendar")

    controls = []
    for row in demo["c_formula_controls"]:
        got = challenger_margin(row["if_margin"], row["q2_margin"], w=CANDIDATE_WEIGHT)
        controls.append({**row, "got_c": got, "ok": got == row["expected_c"]})
    if not all(item["ok"] for item in controls):
        raise R7ProduceRefuse(f"C formula controls failed: {controls}")

    result = call_r6_point_margin(packet, demo["history"], mode=mode)
    replay = replay_call(packet, demo["history"], mode=mode)
    cfg = r7_config_hash()
    code = r7_code_hash()
    if cfg == result["schema_hash"] or code == result["schema_hash"]:
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
        "if_preflight": preflight,
        "franchise_bind": demo["franchise_bind"],
        "rest_calendar": rest,
        "r6_point_margin": result,
        "r7_config_hash": cfg,
        "r7_code_hash": code,
        "r6_config_hash": result["config_hash"],
        "r6_code_hash": result["code_hash"],
        "r6_a_tip": R6_A_TIP,
        "r6_b_tip": R6_B_TIP,
        "gate_713_tip": GATE_713_TIP,
        "replay_ok": replay["replay_ok"],
        "c_formula": C_FORMULA,
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
        "demo": demo,
    }
    return out


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_produce_artifacts(result: dict[str, Any], *, root: Path | None = None) -> dict[str, str]:
    repo = repo_root() if root is None else Path(root)
    dest = repo / OPS_REL
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
