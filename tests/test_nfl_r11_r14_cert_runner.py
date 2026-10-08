"""R11 vs R14 certification runner — fail-closed provenance lane."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from certify_r11_vs_r14 import (  # noqa: E402
    PACK,
    CertError,
    evaluate_pack,
    gate_set_bound,
    lineage_gaps,
    main,
    refuse_holdout,
    slot_exact,
)


def _load(name: str) -> dict:
    return json.loads((PACK / name).read_text())


def _write_pack(directory: Path, files: dict[str, dict]) -> None:
    for name, payload in files.items():
        (directory / name).write_text(json.dumps(payload))


def _exact_slot(label: str) -> dict:
    return {
        "label": label,
        "status": "EXACT",
        "bind_allowed": True,
        "git": {
            "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "branch": "example/not-real",
            "worktree": "/tmp/example",
        },
        "simulator_source_files": ["example_sim.py"],
        "experiment_runner": "example_runner.py",
        "config_parameter_set": {"seed_note": "fixture only"},
        "data_inputs": {
            "paths": ["example.csv"],
            "hashes": {"example.csv": "a" * 64},
        },
        "random_seeds": [1],
        "command_used": "python example_runner.py --seed 1",
        "calibration_artifacts": ["example.json"],
        "metrics": {
            "key_3": 0.0,
            "key_7": 0.0,
            "ot": 0.0,
            "mae": 0.0,
            "total": 0.0,
        },
        "uncommitted_or_external_dependencies": [],
        "evidence": ["fixture"],
        "notes": "synthetic EXACT fixture for runner tests only",
    }


def _bound_gates() -> dict:
    return {
        "gate_set_id": "fixture",
        "status": "BOUND",
        "execute_holdout": False,
        "dimensions": [
            {
                "id": dim,
                "requested": True,
                "threshold": 0.0,
                "threshold_source": "fixture",
            }
            for dim in ("key_3", "key_7", "ot", "mae", "total")
        ],
        "thresholds_source": "fixture",
        "notes": "synthetic",
    }


class TestNflR11R14CertRunner(unittest.TestCase):
    def test_pack_files_exist(self) -> None:
        for name in (
            "r11.lineage.json",
            "r13.lineage.json",
            "r14.lineage.json",
            "frozen_gate_set.json",
            "verdict.json",
            "search_log.json",
            "lineage.schema.json",
            "gate_set.schema.json",
        ):
            self.assertTrue((PACK / name).is_file(), name)

    def test_filed_slots_are_unbound(self) -> None:
        for name, label in (
            ("r11.lineage.json", "R11"),
            ("r13.lineage.json", "R13"),
            ("r14.lineage.json", "R14"),
        ):
            slot = _load(name)
            self.assertEqual(slot["label"], label)
            self.assertEqual(slot["status"], "UNBOUND")
            self.assertFalse(slot["bind_allowed"])
            self.assertFalse(slot_exact(slot))
            self.assertTrue(lineage_gaps(slot))

    def test_gate_set_is_dimensions_only(self) -> None:
        gates = _load("frozen_gate_set.json")
        self.assertEqual(gates["status"], "UNBOUND_DIMENSIONS_ONLY")
        self.assertFalse(gates["execute_holdout"])
        self.assertFalse(gate_set_bound(gates))
        ids = [row["id"] for row in gates["dimensions"]]
        self.assertEqual(ids, ["key_3", "key_7", "ot", "mae", "total"])
        self.assertTrue(all(row["threshold"] is None for row in gates["dimensions"]))

    def test_bound_gates_require_finite_numeric_thresholds(self) -> None:
        gates = _bound_gates()
        self.assertTrue(gate_set_bound(gates))
        gates["dimensions"][0]["threshold"] = False
        self.assertFalse(gate_set_bound(gates))

        gates = _bound_gates()
        gates["unexpected"] = "forbidden"
        self.assertFalse(gate_set_bound(gates))

        gates = _bound_gates()
        gates["dimensions"][0]["unexpected"] = "forbidden"
        self.assertFalse(gate_set_bound(gates))

    def test_evaluate_pack_fail_closed(self) -> None:
        report = evaluate_pack()
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertFalse(report["exact_reproduction_established"])
        self.assertFalse(report["compare_legal"])
        self.assertFalse(report["holdout_executed"])
        self.assertFalse(report["model_behavior_edited"])
        self.assertEqual(report["slots"]["R11"], "UNBOUND")
        self.assertEqual(report["slots"]["R13"], "UNBOUND")
        self.assertEqual(report["slots"]["R14"], "UNBOUND")

    def test_cli_default_exits_fail_closed(self) -> None:
        self.assertEqual(main([]), 2)
        self.assertEqual(main(["--prepare-only"]), 2)
        self.assertEqual(main(["--compare"]), 2)

    def test_cli_refuses_holdout(self) -> None:
        self.assertEqual(main(["--execute-holdout"]), 2)
        refused = refuse_holdout()
        self.assertEqual(refused["status"], "FAIL_CLOSED")
        self.assertFalse(refused["holdout_executed"])

    def test_does_not_alias_pe_drive_or_live_sha(self) -> None:
        r11 = _load("r11.lineage.json")
        self.assertIn("pe_drive_poss_v1", r11["notes"])
        self.assertIn("Do not alias", r11["notes"])
        search = _load("search_log.json")
        aliases = {row["id"] for row in search["near_misses_not_aliased"]}
        self.assertIn("pe_drive_poss_v1", aliases)
        self.assertIn("pe_drive_poss_v2", aliases)
        self.assertIn("live_model_sha_153b6a884a8e", aliases)
        self.assertIn("market_risk_R11", aliases)

    def test_zero_metric_values_are_complete(self) -> None:
        slot = _exact_slot("R11")
        self.assertFalse(
            any(gap.startswith("metrics.") for gap in lineage_gaps(slot)),
            "zero is a valid numeric metric value",
        )

        slot["metrics"]["key_3"] = None
        self.assertIn("metrics.key_3", lineage_gaps(slot))

        slot["metrics"]["key_3"] = False
        self.assertIn(
            "metrics.key_3 (must be finite number)",
            lineage_gaps(slot),
        )

    def test_exact_lineage_rejects_malformed_required_fields(self) -> None:
        slot = _exact_slot("R11")
        slot["git"]["commit"] = True
        slot["evidence"] = []
        slot["notes"] = ""
        slot["unexpected"] = "forbidden"
        gaps = lineage_gaps(slot, expected_label="R11")
        self.assertIn("git.commit", gaps)
        self.assertIn("evidence", gaps)
        self.assertIn("notes", gaps)
        self.assertIn("unexpected fields: unexpected", gaps)
        self.assertFalse(slot_exact(slot, expected_label="R11"))

    def test_compare_ready_only_when_exact_and_bound(self) -> None:
        bound_gates = _bound_gates()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write_pack(
                path,
                {
                    "r11.lineage.json": _exact_slot("R11"),
                    "r13.lineage.json": _exact_slot("R13"),
                    "r14.lineage.json": _exact_slot("R14"),
                    "frozen_gate_set.json": bound_gates,
                    "verdict.json": {
                        "verdict": "FAIL_CLOSED",
                        "exact_reproduction_established": False,
                    },
                },
            )
            ready = evaluate_pack(path)
            self.assertEqual(ready["status"], "COMPARE_READY")
            self.assertTrue(ready["compare_legal"])
            self.assertFalse(ready["holdout_executed"])
            self.assertEqual(main(["--pack", str(path), "--compare"]), 0)
            self.assertEqual(main(["--pack", str(path), "--execute-holdout"]), 2)

    def test_compare_requires_exact_r13_lineage(self) -> None:
        bound_gates = _bound_gates()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write_pack(
                path,
                {
                    "r11.lineage.json": _exact_slot("R11"),
                    "r13.lineage.json": _load("r13.lineage.json"),
                    "r14.lineage.json": _exact_slot("R14"),
                    "frozen_gate_set.json": bound_gates,
                    "verdict.json": {
                        "verdict": "FAIL_CLOSED",
                        "exact_reproduction_established": False,
                    },
                },
            )
            report = evaluate_pack(path)
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertFalse(report["compare_legal"])
            self.assertTrue(
                any(reason.startswith("R13 lineage is not EXACT:") for reason in report["reasons"])
            )

    def test_compare_requires_matching_lineage_slot_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write_pack(
                path,
                {
                    "r11.lineage.json": _exact_slot("R13"),
                    "r13.lineage.json": _exact_slot("R13"),
                    "r14.lineage.json": _exact_slot("R14"),
                    "frozen_gate_set.json": _bound_gates(),
                    "verdict.json": {
                        "verdict": "FAIL_CLOSED",
                        "exact_reproduction_established": False,
                    },
                },
            )
            report = evaluate_pack(path)
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertFalse(report["compare_legal"])
            self.assertIn("label (expected R11)", report["gaps"]["R11"])

    def test_incomplete_exact_status_still_fail_closed(self) -> None:
        slot = _exact_slot("R11")
        slot["git"]["commit"] = None
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write_pack(
                path,
                {
                    "r11.lineage.json": slot,
                    "r13.lineage.json": _load("r13.lineage.json"),
                    "r14.lineage.json": _load("r14.lineage.json"),
                    "frozen_gate_set.json": _load("frozen_gate_set.json"),
                    "verdict.json": _load("verdict.json"),
                },
            )
            report = evaluate_pack(path)
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertFalse(report["compare_legal"])
            self.assertIn("git.commit", report["gaps"]["R11"])

    def test_rejected_alias_cannot_become_exact_bind(self) -> None:
        for alias in (
            "pe_drive_poss_v1",
            "153b6a884a8e8a66336fcfc3fa9907742ae978c3",
            "market_risk_R11",
        ):
            slot = _exact_slot("R11")
            slot["git"]["commit"] = alias
            slot["simulator_source_files"] = [alias]
            slot["experiment_runner"] = alias
            slot["config_parameter_set"] = {"id": alias}
            slot["data_inputs"] = {"paths": [alias], "hashes": {alias: "b" * 64}}
            slot["command_used"] = alias
            slot["calibration_artifacts"] = [alias]
            slot["evidence"] = [alias]
            slot["notes"] = "Do not alias this attempted alias"
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                _write_pack(
                    path,
                    {
                        "r11.lineage.json": slot,
                        "r13.lineage.json": _exact_slot("R13"),
                        "r14.lineage.json": _exact_slot("R14"),
                        "frozen_gate_set.json": _bound_gates(),
                        "verdict.json": _load("verdict.json"),
                    },
                )
                with self.assertRaises(CertError):
                    evaluate_pack(path)


if __name__ == "__main__":
    unittest.main()
