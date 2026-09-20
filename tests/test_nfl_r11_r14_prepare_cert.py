"""Prepare-only R11 vs R14 cert runner — fail-closed while lineage is UNBOUND."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))

from prepare_r11_r14_cert import (  # noqa: E402
    CertError,
    assert_not_alias,
    evaluate_pack,
    gate_set_bound,
    lineage_gaps,
    main,
    refuse_holdout,
    slot_exact,
)


PACK = ROOT / "data" / "ops" / "nfl-r11-r13-independent-20260920"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _exact_slot(label: str) -> dict:
    return {
        "label": label,
        "status": "EXACT",
        "bind_allowed": True,
        "git": {
            "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "branch": "research/example",
            "worktree": "/tmp/example",
        },
        "simulator_source_files": ["services/model-service/src/services/nfl_simulator.py"],
        "experiment_runner": "scripts/nfl/example_runner.py",
        "config_parameter_set": "data/ops/example-config.json",
        "data_inputs": {
            "paths": ["data/ops/example-inputs.parquet"],
            "hashes": ["0" * 64],
        },
        "random_seeds": [1],
        "command_used": "python3 scripts/nfl/example_runner.py --seed 1",
        "calibration_artifacts": ["data/ops/example-cal.json"],
        "metrics": {
            "key_3": 0.0,
            "key_7": 0.0,
            "ot": 0.0,
            "mae": 0.0,
            "total": 0.0,
        },
        "uncommitted_or_external_dependencies": ["none"],
        "evidence": ["fixture"],
        "notes": "fixture only — not a real bind",
    }


def _bound_gates() -> dict:
    return {
        "id": "fixture-gate-set",
        "status": "BOUND",
        "bind_allowed": True,
        "execute_holdout": False,
        "thresholds_source": "fixture",
        "dimensions": [
            {
                "id": dim,
                "requested": True,
                "threshold": 0.0,
                "threshold_source": "fixture",
            }
            for dim in ("key_3", "key_7", "ot", "mae", "total")
        ],
    }


class TestFiledPackFailClosed(unittest.TestCase):
    def test_filed_pack_is_fail_closed(self) -> None:
        report = evaluate_pack(PACK)
        self.assertEqual(report["status"], "FAIL_CLOSED")
        self.assertFalse(report["compare_legal"])
        self.assertFalse(report["exact_reproduction_established"])
        self.assertFalse(report["holdout_executed"])
        self.assertFalse(report["model_behavior_edited"])
        self.assertEqual(report["slots"]["R11"], "UNBOUND")
        self.assertEqual(report["slots"]["R13"], "UNBOUND")
        self.assertEqual(report["slots"]["R14"], "UNBOUND")
        self.assertTrue(report["gaps"]["R11"])
        self.assertIn("key_3", report["dimensions_requested"])

    def test_cli_default_exits_2(self) -> None:
        self.assertEqual(main([]), 2)

    def test_cli_compare_stays_fail_closed(self) -> None:
        self.assertEqual(main(["--compare"]), 2)

    def test_cli_execute_holdout_refused(self) -> None:
        self.assertEqual(main(["--execute-holdout"]), 2)
        refused = refuse_holdout()
        self.assertEqual(refused["status"], "FAIL_CLOSED")
        self.assertFalse(refused["holdout_executed"])


class TestLineageAndGates(unittest.TestCase):
    def test_unbound_slot_is_not_exact(self) -> None:
        slot = json.loads((PACK / "r11.lineage.json").read_text())
        self.assertFalse(slot_exact(slot))
        gaps = lineage_gaps(slot)
        self.assertIn("git.commit", gaps)
        self.assertIn("metrics.key_3", gaps)

    def test_filed_gate_set_is_not_bound(self) -> None:
        gates = json.loads((PACK / "frozen_gate_set.json").read_text())
        self.assertFalse(gate_set_bound(gates))

    def test_rejected_alias_cannot_bind_exact(self) -> None:
        slot = _exact_slot("R11")
        slot["notes"] = "binds pe_drive_poss_v1"
        slot["command_used"] = "pe_drive_poss_v1"
        with self.assertRaises(CertError):
            assert_not_alias(slot)

    def test_do_not_alias_note_allows_mention_without_bind(self) -> None:
        slot = json.loads((PACK / "r11.lineage.json").read_text())
        slot["notes"] = "Do not alias pe_drive_poss_v1"
        assert_not_alias(slot)

    def test_compare_ready_only_when_all_exact_and_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp)
            _write_json(pack / "r11.lineage.json", _exact_slot("R11"))
            _write_json(pack / "r13.lineage.json", _exact_slot("R13"))
            _write_json(pack / "r14.lineage.json", _exact_slot("R14"))
            _write_json(pack / "frozen_gate_set.json", _bound_gates())
            _write_json(pack / "verdict.json", {"verdict": "COMPARE_READY"})
            report = evaluate_pack(pack)
            self.assertEqual(report["status"], "COMPARE_READY")
            self.assertTrue(report["compare_legal"])
            self.assertTrue(report["exact_reproduction_established"])
            self.assertFalse(report["holdout_executed"])

    def test_missing_r14_keeps_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp)
            _write_json(pack / "r11.lineage.json", _exact_slot("R11"))
            _write_json(pack / "r13.lineage.json", _exact_slot("R13"))
            unbound = _exact_slot("R14")
            unbound["status"] = "UNBOUND"
            unbound["bind_allowed"] = False
            unbound["git"] = {"commit": None, "branch": None, "worktree": None}
            _write_json(pack / "r14.lineage.json", unbound)
            _write_json(pack / "frozen_gate_set.json", _bound_gates())
            _write_json(pack / "verdict.json", {"verdict": "FAIL_CLOSED"})
            report = evaluate_pack(pack)
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertFalse(report["compare_legal"])


if __name__ == "__main__":
    unittest.main()
