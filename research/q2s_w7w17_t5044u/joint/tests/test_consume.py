#!/usr/bin/env python3
"""t5070u — research.q2s.joint.handoff consumer tests. CERT=0.

Does not regenerate 5076421e / ce6b1244. Does not open 50bda875 / LOOK.
"""

from __future__ import annotations

import builtins
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

JOINT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(JOINT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from consume import (  # noqa: E402
    ALLOWED_BASENAMES,
    CANONICAL_JSON_SHA256,
    CANONICAL_NPZ_SHA256,
    DEFAULT_JSON,
    DEFAULT_NPZ,
    HEADER_KEYS,
    NAMESPACE,
    NPZ_KEYS,
    _ordered_ids,
    _rederive_row,
    _validate_draws,
    _validate_header,
    allowed_file_set,
    consume_q2s_joint,
)
from pins import PinRefuse, sha256_file  # noqa: E402
from sim_q2s_joint import JointRefuse  # noqa: E402

OUTCOMES = JOINT.parent / "pins" / "outcomes_2013_2022_score_only.csv"


class OpenGuard:
    def __init__(self) -> None:
        self.opened: list[str] = []
        self.writes: list[str] = []
        self._open = builtins.open
        self._path_open = Path.open
        self._write_text = Path.write_text
        self._write_bytes = Path.write_bytes

    def _note_read(self, path: object) -> None:
        self.opened.append(str(path))

    def __enter__(self) -> "OpenGuard":
        guard = self

        def wrapped_open(file, *a, **k):
            mode = a[0] if a else k.get("mode", "r")
            if isinstance(mode, str) and any(c in mode for c in "wxa+"):
                guard.writes.append(str(file))
            else:
                guard._note_read(file)
            return guard._open(file, *a, **k)

        def wrapped_path_open(path_self, *a, **k):
            mode = a[0] if a else k.get("mode", "r")
            if isinstance(mode, str) and any(c in mode for c in "wxa+"):
                guard.writes.append(str(path_self))
            else:
                guard._note_read(path_self)
            return guard._path_open(path_self, *a, **k)

        def wrapped_write_text(path_self, *a, **k):
            guard.writes.append(str(path_self))
            return guard._write_text(path_self, *a, **k)

        def wrapped_write_bytes(path_self, *a, **k):
            guard.writes.append(str(path_self))
            return guard._write_bytes(path_self, *a, **k)

        builtins.open = wrapped_open  # type: ignore[assignment]
        Path.open = wrapped_path_open  # type: ignore[assignment]
        Path.write_text = wrapped_write_text  # type: ignore[assignment]
        Path.write_bytes = wrapped_write_bytes  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: object) -> None:
        builtins.open = self._open  # type: ignore[assignment]
        Path.open = self._path_open  # type: ignore[assignment]
        Path.write_text = self._write_text  # type: ignore[assignment]
        Path.write_bytes = self._write_bytes  # type: ignore[assignment]


def _handoff():
    return consume_q2s_joint(
        expected_json_sha256=CANONICAL_JSON_SHA256,
        expected_npz_sha256=CANONICAL_NPZ_SHA256,
    )


class TestCanonicalRoundTrip(unittest.TestCase):
    def test_real_141_round_trip(self) -> None:
        handoff = _handoff()
        self.assertEqual(handoff.namespace, NAMESPACE)
        self.assertEqual(len(handoff.game_ids), 141)
        self.assertEqual(len(set(handoff.game_ids)), 141)
        self.assertEqual(len(handoff.rows), 141)
        self.assertEqual(handoff.H.shape, (141, 4000))
        self.assertEqual(handoff.A.dtype, np.float64)
        self.assertFalse(handoff.H.flags.writeable)
        self.assertEqual(handoff.provenance["json_sha256"], CANONICAL_JSON_SHA256)
        self.assertEqual(handoff.provenance["npz_sha256"], CANONICAL_NPZ_SHA256)
        self.assertTrue(handoff.limitations["loaded_is_not_all_gates_pass"])
        self.assertTrue(handoff.limitations["loaded_is_not_calibrated_probabilities"])
        self.assertTrue(handoff.limitations["loaded_is_not_book_settlement"])
        self.assertTrue(handoff.limitations["loaded_is_not_operational_acceptance"])
        self.assertIn("AWAY", handoff.limitations["tie_convention"])
        self.assertEqual(handoff.game_ids[0], "2017_07_ARI_LA")
        self.assertEqual(handoff.rows[0]["home"], "LAR")
        self.assertEqual(handoff.rows[0]["away"], "ARI")

    def test_cond_and_j14_preserved(self) -> None:
        handoff = _handoff()
        self.assertEqual(handoff.cond_cell_count, 34)
        self.assertEqual(handoff.j14_not_emitted_count, 141)
        self.assertEqual(handoff.gate_counts_cellwise["COND"], 34)
        self.assertEqual(handoff.gate_counts_cellwise["NOT_EMITTED"], 141)
        self.assertEqual(handoff.worst_gate_counts["COND"], 27)
        cond = 0
        for row in handoff.rows:
            self.assertEqual(row["gates"]["J14"]["status"], "NOT_EMITTED")
            self.assertNotEqual(row["gates"]["J14"]["status"], "PASS")
            for gate in row["gates"].values():
                if gate["status"] == "COND":
                    cond += 1
        self.assertEqual(cond, 34)

    def test_artifacts_unregenerated(self) -> None:
        self.assertEqual(sha256_file(DEFAULT_JSON), CANONICAL_JSON_SHA256)
        self.assertEqual(sha256_file(DEFAULT_NPZ), CANONICAL_NPZ_SHA256)


class TestMutationIsolation(unittest.TestCase):
    def test_draws_readonly_and_not_shared(self) -> None:
        a = _handoff()
        b = _handoff()
        self.assertFalse(np.shares_memory(a.H, b.H))
        self.assertFalse(np.shares_memory(a.A, b.A))
        with self.assertRaises(ValueError):
            a.H[0, 0] = 99.0
        with self.assertRaises(ValueError):
            a.A[0, 0] = 99.0
        with self.assertRaises(TypeError):
            a.rows[0]["worst_gate"] = "PASS"
        with self.assertRaises(TypeError):
            a.rows[0]["gates"]["J7a"]["status"] = "PASS"
        self.assertEqual(a.rows[0]["gates"]["J7a"]["status"], "COND")
        self.assertEqual(b.rows[0]["gates"]["J7a"]["status"], "COND")


class TestRefusals(unittest.TestCase):
    def test_alternate_caller_digest_refused(self) -> None:
        with self.assertRaises(JointRefuse):
            consume_q2s_joint(
                expected_json_sha256="0" * 64,
                expected_npz_sha256=CANONICAL_NPZ_SHA256,
            )
        with self.assertRaises(JointRefuse):
            consume_q2s_joint(
                expected_json_sha256=CANONICAL_JSON_SHA256,
                expected_npz_sha256="f" * 64,
            )

    def test_missing_file_refused(self) -> None:
        missing = Path("/tmp/Q2S_JOINT_W7W17.json")
        if missing.exists():
            missing.unlink()
        with self.assertRaises(JointRefuse):
            consume_q2s_joint(
                expected_json_sha256=CANONICAL_JSON_SHA256,
                expected_npz_sha256=CANONICAL_NPZ_SHA256,
                json_path=missing,
                npz_path=DEFAULT_NPZ,
            )

    def test_corrupt_file_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "Q2S_JOINT_W7W17.json"
            bad.write_text("{}\n")
            with self.assertRaises(JointRefuse):
                consume_q2s_joint(
                    expected_json_sha256=CANONICAL_JSON_SHA256,
                    expected_npz_sha256=CANONICAL_NPZ_SHA256,
                    json_path=bad,
                    npz_path=DEFAULT_NPZ,
                )

    def test_forbidden_basename_refused(self) -> None:
        with self.assertRaises((JointRefuse, PinRefuse)):
            consume_q2s_joint(
                expected_json_sha256=CANONICAL_JSON_SHA256,
                expected_npz_sha256=CANONICAL_NPZ_SHA256,
                json_path=OUTCOMES,
                npz_path=DEFAULT_NPZ,
            )

    def test_header_pin_identity_order_shape_dtype(self) -> None:
        payload = json.loads(DEFAULT_JSON.read_text())
        live_npz = CANONICAL_NPZ_SHA256
        mutated = dict(payload)
        mutated["cert"] = 1
        with self.assertRaises(JointRefuse):
            _validate_header(mutated, live_npz)
        extra = dict(payload)
        extra["bonus"] = True
        with self.assertRaises(JointRefuse):
            _validate_header(extra, live_npz)
        missing = dict(payload)
        del missing["namespace"]
        with self.assertRaises(JointRefuse):
            _validate_header(missing, live_npz)
        self.assertEqual(set(payload), HEADER_KEYS)

        reordered = dict(payload)
        reordered["game_ids"] = list(reversed(payload["game_ids"]))
        with self.assertRaises(JointRefuse):
            _ordered_ids(reordered)
        dup = dict(payload)
        ids = list(payload["game_ids"])
        ids[1] = ids[0]
        dup["game_ids"] = ids
        rows = [dict(r) for r in payload["rows"]]
        rows[1] = dict(rows[0])
        dup["rows"] = rows
        with self.assertRaises(JointRefuse):
            _ordered_ids(dup)

        draws = np.load(DEFAULT_NPZ, allow_pickle=False)
        H = draws["H"]
        A = draws["A"]
        ids = [str(x) for x in draws["game_ids"]]
        with self.assertRaises(JointRefuse):
            _validate_draws(H.astype(np.float32), A, ids, ids)
        with self.assertRaises(JointRefuse):
            _validate_draws(H[:10], A, ids, ids)
        with self.assertRaises(JointRefuse):
            _validate_draws(H, A, list(reversed(ids)), ids)
        nanH = np.array(H, copy=True)
        nanH[0, 0] = np.nan
        with self.assertRaises(JointRefuse):
            _validate_draws(nanH, A, ids, ids)
        neg = np.array(H, copy=True)
        neg[3, 9] = -0.1
        with self.assertRaises(JointRefuse):
            _validate_draws(neg, A, ids, ids)

        row = payload["rows"][0]
        with self.assertRaises(JointRefuse):
            _rederive_row({**row, "draw_hash": "0" * 64}, H[0], A[0])
        with self.assertRaises(JointRefuse):
            _rederive_row({**row, "home_wins": 0}, H[0], A[0])
        with self.assertRaises(JointRefuse):
            _rederive_row({**row, "spread_home": 99.0}, H[0], A[0])

        self.assertEqual(set(draws.files), NPZ_KEYS)


class TestNoForbiddenReadOrSimOrWrite(unittest.TestCase):
    def test_consume_opens_only_allowlisted_joint_artifacts(self) -> None:
        allowed = {p.resolve() for p in allowed_file_set()}
        with OpenGuard() as guard:
            consume_q2s_joint(
                expected_json_sha256=CANONICAL_JSON_SHA256,
                expected_npz_sha256=CANONICAL_NPZ_SHA256,
            )
        opened = [Path(p).resolve() if Path(p).exists() or Path(p).name in ALLOWED_BASENAMES else Path(p) for p in guard.opened]
        for path in opened:
            name = Path(str(path)).name
            self.assertNotEqual(name, "outcomes_2013_2022_score_only.csv")
            self.assertNotIn("50bda875", str(path))
            self.assertNotIn("LOOK_CONSUMED", str(path))
            self.assertNotIn("LOOK_RESULT", str(path))
            self.assertNotIn("PROTOCOL_FREEZE", str(path))
            self.assertNotIn("FINAL_PRELOOK_FREEZE", str(path))
            if name in ALLOWED_BASENAMES:
                self.assertIn(Path(str(path)).name, ALLOWED_BASENAMES)
        self.assertEqual(guard.writes, [])
        self.assertTrue(any(Path(p).name == "Q2S_JOINT_W7W17.json" for p in guard.opened))
        self.assertTrue(any(Path(p).name == "Q2S_JOINT_DRAWS_W7W17.npz" for p in guard.opened))
        self.assertTrue(DEFAULT_JSON.resolve() in allowed)

    def test_source_has_no_sim_writer_or_outcome_join(self) -> None:
        src = (JOINT / "consume.py").read_text()
        self.assertNotIn("run_q2s_joint", src)
        self.assertNotIn("import_if", src)
        self.assertNotIn("simulate_nfl_game", src)
        self.assertNotIn("simulate_q2s_joint", src)
        self.assertNotIn("look_real", src)
        self.assertNotIn("assert_no_forbidden_open", src)
        self.assertNotIn("write_text", src)
        self.assertNotIn("savez", src)
        self.assertNotIn("PROTOCOL_FREEZE", src)
        self.assertNotIn("verify_input_pins", src)
        self.assertIn("allow_pickle=False", src)

    def test_consume_does_not_call_simulator_or_writer(self) -> None:
        import consume as consume_mod
        import sim_q2s_joint as sim_mod

        calls: list[str] = []

        def boom(*_a, **_k):
            calls.append("sim")
            raise AssertionError("simulator invoked")

        orig_load = sim_mod._load_sim
        orig_off = sim_mod.official_if_mus
        orig_run = getattr(sys.modules.get("run_q2s_joint"), "run", None)
        sim_mod._load_sim = boom  # type: ignore[assignment]
        sim_mod.official_if_mus = boom  # type: ignore[assignment]
        try:
            consume_mod.consume_q2s_joint(
                expected_json_sha256=CANONICAL_JSON_SHA256,
                expected_npz_sha256=CANONICAL_NPZ_SHA256,
            )
        finally:
            sim_mod._load_sim = orig_load
            sim_mod.official_if_mus = orig_off
        self.assertEqual(calls, [])
        self.assertIsNone(orig_run)


if __name__ == "__main__":
    unittest.main()
