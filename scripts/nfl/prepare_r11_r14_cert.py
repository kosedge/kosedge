#!/usr/bin/env python3
"""Prepare-only frozen R11 vs candidate R14 certification runner.

Provenance lane only. Default mode never imports the NFL simulator, never
scores games, and never reads held-out outcomes.

A compare is legal only when:
  * R11 and R14 lineage slots are status=EXACT and bind_allowed=true
  * every required lineage field is populated
  * the frozen gate set is BOUND with sourced thresholds

Until those are filed, the runner fail-closes. Hash prefixes and
PARTIAL_EXTERNAL Academy labels do not satisfy EXACT. Missing Academy
files keep the filed pack refuse-closed.

Holdout execution is refused even if lineage later becomes EXACT — that
requires a separate authorization outside this lane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "data" / "ops" / "nfl-r11-r13-independent-20260920"

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
FULL_SHA256 = re.compile(r"^[0-9a-f]{64}$")
FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
REJECTED_ALIASES = (
    "pe_drive_poss_v1",
    "pe_drive_poss_v2",
    "b5ee9d80494bbc13b989174af0676afb1831a4cb11e678f2f243ac469b92d36b",
    "153b6a884a8e8a66336fcfc3fa9907742ae978c3",
    "nfl_simulator.py",
    "personnel_efficiency.py",
)
ACADEMY_CANDIDATES = (
    {
        "rel": "permanent-engine/docs/ops/NFL_R11_R13_INDEPENDENT_PROVENANCE_2026-09-20.md",
        "sha256_prefix": "bb6ebda9",
    },
    {
        "rel": "permanent-engine/docs/ops/NFL_R11_R13_INDEPENDENT_PROVENANCE_2026-09-20.json",
        "sha256_prefix": "d1dfc752",
    },
)


class CertError(RuntimeError):
    """Fail-closed certification error."""


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CertError(f"missing required file: {path}")
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise CertError(f"{path} is not a JSON object")
    return data


def _populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _full_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(FULL_SHA256.match(value.lower()))


def _full_git_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(FULL_GIT_SHA.match(value.lower()))


def _runner_path(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict) and _populated(value.get("path")):
        return str(value["path"]).strip()
    return None


def inspect_academy_files(root: Path = ROOT) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for spec in ACADEMY_CANDIDATES:
        path = root / spec["rel"]
        row: dict[str, Any] = {
            "rel": spec["rel"],
            "sha256_prefix": spec["sha256_prefix"],
            "present": path.is_file(),
            "sha256": None,
            "prefix_match": None,
        }
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            row["sha256"] = digest
            row["prefix_match"] = digest.startswith(spec["sha256_prefix"])
        files.append(row)
    present = all(row["present"] for row in files)
    prefixes_ok = all(row["prefix_match"] is True for row in files) if present else False
    return {
        "present_in_checkout": present,
        "prefix_match": prefixes_ok if present else False,
        "files": files,
        "note": (
            "Academy files attached; prefixes match. Full sha256 still required for EXACT."
            if present and prefixes_ok
            else "Academy/research store files are not in this checkout. Prefixes only; full hashes not invented."
        ),
    }


def lineage_gaps(slot: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for field in REQUIRED_LINEAGE_FIELDS:
        if field not in slot:
            gaps.append(f"missing field {field}")
    git = slot.get("git") if isinstance(slot.get("git"), dict) else {}
    for key in REQUIRED_GIT:
        value = git.get(key)
        if key == "commit":
            if not _full_git_sha(value):
                gaps.append("git.commit")
        elif not _populated(value):
            gaps.append(f"git.{key}")
    if not _populated(slot.get("simulator_source_files")):
        gaps.append("simulator_source_files")
    if _runner_path(slot.get("experiment_runner")) is None:
        gaps.append("experiment_runner")
    if not _populated(slot.get("config_parameter_set")):
        gaps.append("config_parameter_set")
    inputs = slot.get("data_inputs") if isinstance(slot.get("data_inputs"), dict) else {}
    if not _populated(inputs.get("paths")):
        gaps.append("data_inputs.paths")
    hashes = inputs.get("hashes") if isinstance(inputs.get("hashes"), list) else []
    if not any(_full_sha256(item) for item in hashes):
        gaps.append("data_inputs.hashes")
    if not _populated(slot.get("random_seeds")):
        gaps.append("random_seeds")
    if not _populated(slot.get("command_used")):
        gaps.append("command_used")
    if not _populated(slot.get("calibration_artifacts")):
        gaps.append("calibration_artifacts")
    metrics = slot.get("metrics") if isinstance(slot.get("metrics"), dict) else {}
    for key in REQUIRED_METRICS:
        if not _populated(metrics.get(key)):
            gaps.append(f"metrics.{key}")
    return gaps


def assert_not_alias(slot: dict[str, Any]) -> None:
    blob = json.dumps(slot, sort_keys=True)
    notes = str(slot.get("notes") or "")
    if slot.get("status") != "EXACT" or slot.get("bind_allowed") is not True:
        return
    if "Do not alias" in notes:
        return
    for alias in REJECTED_ALIASES:
        if alias in blob:
            raise CertError(f"{slot.get('label')}: refusing to treat {alias} as an EXACT bind")


def slot_exact(slot: dict[str, Any]) -> bool:
    return (
        slot.get("status") == "EXACT"
        and slot.get("bind_allowed") is True
        and not lineage_gaps(slot)
    )


def gate_set_bound(gate: dict[str, Any]) -> bool:
    if gate.get("status") != "BOUND":
        return False
    if gate.get("execute_holdout") is True:
        return False
    if not _populated(gate.get("thresholds_source")):
        return False
    dims = gate.get("dimensions")
    if not isinstance(dims, list):
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
        if not _populated(row.get("threshold")):
            return False
        if not _populated(row.get("threshold_source")):
            return False
    return seen == set(REQUIRED_GATE_IDS)


def evaluate_pack(pack: Path = PACK, root: Path = ROOT) -> dict[str, Any]:
    r11 = load_json(pack / "r11.lineage.json")
    r13 = load_json(pack / "r13.lineage.json")
    r14 = load_json(pack / "r14.lineage.json")
    gates = load_json(pack / "frozen_gate_set.json")
    verdict_doc = load_json(pack / "verdict.json")
    alex_bind_path = pack / "alex_external_bind.json"
    alex_bind = load_json(alex_bind_path) if alex_bind_path.is_file() else None
    academy = inspect_academy_files(root)

    for slot in (r11, r13, r14):
        assert_not_alias(slot)

    if academy["present_in_checkout"] and academy["prefix_match"] is False:
        raise CertError("Academy files are present but sha256 prefixes do not match the filed bind")

    r11_exact = slot_exact(r11)
    r13_exact = slot_exact(r13)
    r14_exact = slot_exact(r14)
    gates_ok = gate_set_bound(gates)

    compare_legal = r11_exact and r14_exact and gates_ok
    reasons: list[str] = []
    if not r11_exact:
        reasons.append("R11 lineage is not EXACT: " + ", ".join(lineage_gaps(r11) or ["status/bind"]))
    if not r13_exact:
        reasons.append(
            "R13 lineage is not EXACT (prior experiment, informational): "
            + ", ".join(lineage_gaps(r13) or ["status/bind"])
        )
    if not r14_exact:
        reasons.append("R14 lineage is not EXACT: " + ", ".join(lineage_gaps(r14) or ["status/bind"]))
    if not gates_ok:
        reasons.append(
            "frozen gate set is not BOUND with sourced thresholds for key_3/key_7/ot/mae/total"
        )
    if gates.get("execute_holdout") is True:
        reasons.append("gate set execute_holdout=true is illegal in this lane")
    if alex_bind is not None and not academy["present_in_checkout"]:
        compare_legal = False
        reasons.append(
            "Academy/research store files are not in this checkout; refuse-closed until EXACT artifacts are attached"
        )
    if alex_bind and alex_bind.get("exact_reproduction_established") is True:
        compare_legal = False
        reasons.append("alex_external_bind.json must not claim EXACT while hashes remain prefixes")

    if compare_legal:
        status = "COMPARE_READY"
        exit_hint = 0
    else:
        status = "FAIL_CLOSED"
        exit_hint = 2

    return {
        "status": status,
        "exit_hint": exit_hint,
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
            "R11": lineage_gaps(r11),
            "R13": lineage_gaps(r13),
            "R14": lineage_gaps(r14),
        },
        "reasons": reasons,
        "packet_verdict": verdict_doc.get("verdict"),
        "academy_store": academy,
        "alex_external_bind_present": alex_bind is not None,
        "dimensions_requested": [
            row.get("id") for row in (gates.get("dimensions") or []) if isinstance(row, dict)
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
    parser.add_argument("--pack", type=Path, default=PACK, help="provenance pack directory")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        default=True,
        help="readiness check only (default)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="compare EXACT R11 vs EXACT R14 on a BOUND gate set; fail-closed otherwise",
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
