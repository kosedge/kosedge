#!/usr/bin/env python3
"""Deterministic R11 vs R14 certification runner — provenance lane only.

Default mode is prepare-only. It never imports the NFL simulator, never
scores games, and never reads held-out outcomes.

Compare is legal only when:
  * R11, R13, and R14 lineage slots are status=EXACT and bind_allowed=true
  * each lineage slot's label matches its R11/R13/R14 file
  * every required lineage field is populated
  * the frozen gate set is BOUND with sourced thresholds

Until those are filed, the runner fail-closes.

Holdout execution is refused even if lineage later becomes EXACT — that
requires a separate authorization outside this lane.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "data" / "ops" / "nfl-r11-r13-provenance-20260920"

REQUIRED_LINEAGE_FIELDS = (
    "label",
    "status",
    "bind_allowed",
    "git",
    "simulator_source_files",
    "experiment_runner",
    "config_parameter_set",
    "data_inputs",
    "random_seeds",
    "command_used",
    "calibration_artifacts",
    "metrics",
    "uncommitted_or_external_dependencies",
    "evidence",
    "notes",
)
REQUIRED_GIT = ("commit", "branch", "worktree")
REQUIRED_METRICS = ("key_3", "key_7", "ot", "mae", "total")
REQUIRED_GATE_IDS = ("key_3", "key_7", "ot", "mae", "total")
REJECTED_ALIASES = (
    "pe_drive_poss_v1",
    "pe_drive_poss_v2",
    "b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b",
    "153b6a884a8e8a66336fcfc3fa9907742ae978c3",
)


class CertError(RuntimeError):
    """Fail-closed certification error."""


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CertError(f"missing required file: {path.relative_to(ROOT)}")
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise CertError(f"{path.relative_to(ROOT)} is not a JSON object")
    return data


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_string_list(value: Any, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_nonempty_string(item) for item in value)
    )


def _nonempty_string_map(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and bool(value)
        and all(
            _nonempty_string(key) and _nonempty_string(item)
            for key, item in value.items()
        )
    )


def _valid_seed_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        (isinstance(seed, int) and not isinstance(seed, bool)) or _nonempty_string(seed)
        for seed in value
    )


def _numeric_value_supplied(values: dict[str, Any], key: str) -> bool:
    """Only an absent or null numeric field is missing; zero is valid."""
    return key in values and values[key] is not None


def _valid_numeric_value(values: dict[str, Any], key: str) -> bool:
    if not _numeric_value_supplied(values, key):
        return False
    value = values[key]
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def lineage_gaps(
    slot: dict[str, Any], *, expected_label: str | None = None
) -> list[str]:
    gaps: list[str] = []
    for field in REQUIRED_LINEAGE_FIELDS:
        if field not in slot:
            gaps.append(f"missing field {field}")
    if expected_label is not None and slot.get("label") != expected_label:
        gaps.append(f"label (expected {expected_label})")
    git = slot.get("git") if isinstance(slot.get("git"), dict) else {}
    for key in REQUIRED_GIT:
        if not _nonempty_string(git.get(key)):
            gaps.append(f"git.{key}")
    if not _nonempty_string_list(slot.get("simulator_source_files")):
        gaps.append("simulator_source_files")
    if not _nonempty_string(slot.get("experiment_runner")):
        gaps.append("experiment_runner")
    config = slot.get("config_parameter_set")
    if not (
        _nonempty_string(config) or (isinstance(config, dict) and bool(config))
    ):
        gaps.append("config_parameter_set")
    inputs = slot.get("data_inputs") if isinstance(slot.get("data_inputs"), dict) else {}
    if not _nonempty_string_list(inputs.get("paths")):
        gaps.append("data_inputs.paths")
    if not _nonempty_string_map(inputs.get("hashes")):
        gaps.append("data_inputs.hashes")
    if not _valid_seed_list(slot.get("random_seeds")):
        gaps.append("random_seeds")
    if not _nonempty_string(slot.get("command_used")):
        gaps.append("command_used")
    if not _nonempty_string_list(slot.get("calibration_artifacts")):
        gaps.append("calibration_artifacts")
    metrics = slot.get("metrics") if isinstance(slot.get("metrics"), dict) else {}
    for key in REQUIRED_METRICS:
        if not _numeric_value_supplied(metrics, key):
            gaps.append(f"metrics.{key}")
        elif not _valid_numeric_value(metrics, key):
            gaps.append(f"metrics.{key} (must be finite number)")
    if not _nonempty_string_list(
        slot.get("uncommitted_or_external_dependencies"), allow_empty=True
    ):
        gaps.append("uncommitted_or_external_dependencies")
    if not _nonempty_string_list(slot.get("evidence")):
        gaps.append("evidence")
    if not _nonempty_string(slot.get("notes")):
        gaps.append("notes")
    return gaps


def assert_not_alias(slot: dict[str, Any]) -> None:
    blob = json.dumps(slot, sort_keys=True)
    for alias in REJECTED_ALIASES:
        if (
            slot.get("status") == "EXACT"
            and alias in blob
            and slot.get("bind_allowed") is True
        ):
            # EXACT bind that only restates a rejected/unrelated artifact is illegal.
            raise CertError(
                f"{slot.get('label')}: refusing to treat {alias} as an EXACT bind"
            )


def slot_exact(slot: dict[str, Any], *, expected_label: str | None = None) -> bool:
    return (
        slot.get("status") == "EXACT"
        and slot.get("bind_allowed") is True
        and not lineage_gaps(slot, expected_label=expected_label)
    )


def gate_set_bound(gate: dict[str, Any]) -> bool:
    if gate.get("status") != "BOUND":
        return False
    if gate.get("execute_holdout") is True:
        return False
    if not _nonempty_string(gate.get("thresholds_source")):
        return False
    dims = gate.get("dimensions")
    if not isinstance(dims, list) or len(dims) != len(REQUIRED_GATE_IDS):
        return False
    seen: set[str] = set()
    for row in dims:
        if not isinstance(row, dict):
            return False
        dim_id = row.get("id")
        if dim_id not in REQUIRED_GATE_IDS:
            return False
        seen.add(str(dim_id))
        if row.get("requested") is not True:
            return False
        if not _valid_numeric_value(row, "threshold"):
            return False
        if not _nonempty_string(row.get("threshold_source")):
            return False
    return seen == set(REQUIRED_GATE_IDS)


def evaluate_pack(pack: Path = PACK) -> dict[str, Any]:
    r11 = load_json(pack / "r11.lineage.json")
    r13 = load_json(pack / "r13.lineage.json")
    r14 = load_json(pack / "r14.lineage.json")
    gates = load_json(pack / "frozen_gate_set.json")
    verdict_doc = load_json(pack / "verdict.json")

    for slot in (r11, r13, r14):
        assert_not_alias(slot)

    r11_exact = slot_exact(r11, expected_label="R11")
    r13_exact = slot_exact(r13, expected_label="R13")
    r14_exact = slot_exact(r14, expected_label="R14")
    gates_ok = gate_set_bound(gates)

    compare_legal = r11_exact and r13_exact and r14_exact and gates_ok
    reasons: list[str] = []
    if not r11_exact:
        reasons.append(
            "R11 lineage is not EXACT: "
            + ", ".join(lineage_gaps(r11, expected_label="R11") or ["status/bind"])
        )
    if not r13_exact:
        reasons.append(
            "R13 lineage is not EXACT: "
            + ", ".join(lineage_gaps(r13, expected_label="R13") or ["status/bind"])
        )
    if not r14_exact:
        reasons.append(
            "R14 lineage is not EXACT: "
            + ", ".join(lineage_gaps(r14, expected_label="R14") or ["status/bind"])
        )
    if not gates_ok:
        reasons.append(
            "frozen gate set is not BOUND with sourced thresholds for key_3/key_7/ot/mae/total"
        )
    if gates.get("execute_holdout") is True:
        reasons.append("gate set execute_holdout=true is illegal in this lane")

    if compare_legal:
        status = "COMPARE_READY"
        exit_hint = 0
    else:
        status = "FAIL_CLOSED"
        exit_hint = 2

    return {
        "status": status,
        "exact_reproduction_established": r11_exact and r13_exact,
        "compare_legal": compare_legal,
        "holdout_executed": False,
        "model_behavior_edited": False,
        "slots": {
            "R11": r11.get("status"),
            "R13": r13.get("status"),
            "R14": r14.get("status"),
            "gate_set": gates.get("status"),
        },
        "gaps": {
            "R11": lineage_gaps(r11, expected_label="R11"),
            "R13": lineage_gaps(r13, expected_label="R13"),
            "R14": lineage_gaps(r14, expected_label="R14"),
        },
        "reasons": reasons,
        "packet_verdict": verdict_doc.get("verdict"),
        "dimensions_requested": [
            row.get("id")
            for row in (gates.get("dimensions") or [])
            if isinstance(row, dict)
        ],
    }


def refuse_holdout() -> dict[str, Any]:
    return {
        "status": "FAIL_CLOSED",
        "reason": "holdout execution is refused in this lane",
        "holdout_executed": False,
        "compare_legal": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare (do not execute) frozen R11 vs candidate R14 certification"
    )
    parser.add_argument(
        "--pack",
        type=Path,
        default=PACK,
        help="provenance pack directory",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        default=True,
        help="readiness check only (default)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="compare EXACT R11/R13/R14 lineage on a BOUND gate set; fail-closed otherwise",
    )
    parser.add_argument(
        "--execute-holdout",
        action="store_true",
        help="refused — this lane does not run held-out data",
    )
    args = parser.parse_args(argv)

    if args.execute_holdout:
        report = refuse_holdout()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2

    try:
        report = evaluate_pack(args.pack)
    except CertError as exc:
        report = {
            "status": "FAIL_CLOSED",
            "reason": str(exc),
            "holdout_executed": False,
            "compare_legal": False,
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2

    if args.compare and not report["compare_legal"]:
        report["compare_attempted"] = True
        report["status"] = "FAIL_CLOSED"

    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] == "FAIL_CLOSED":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
