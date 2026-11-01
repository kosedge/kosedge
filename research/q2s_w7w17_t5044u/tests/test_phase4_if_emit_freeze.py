#!/usr/bin/env python3
"""Phase 4 IF + Q2s emit + freeze tests. CERT=0. No look."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]
PHASE4 = PACKET / "phase4"
sys.path.insert(0, str(PHASE4))

from emit_q2s_w7w17 import Q2S_FIELDS, SEALED_A_Q2, SEALED_B_Q2  # noqa: E402
from freeze_protocol import (  # noqa: E402
    FreezeRefuse,
    MATRIX_SHA256,
    verify_freeze,
)
from score_if_w7w17 import (  # noqa: E402
    EXAMINED_70,
    IF_TIP,
    SEALED_T2,
    SIMULATIONS,
    assemble_sample,
    seed_for,
)
from q2s.blend import Q2S_WEIGHT, margin_mu_q2s  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Phase4AssembleAndPins(unittest.TestCase):
    def test_matrix_pin_unchanged(self) -> None:
        path = PACKET / "gate2" / "RECON_MATRIX_W7W17.csv"
        self.assertEqual(sha256_file(path), MATRIX_SHA256)
        self.assertTrue(MATRIX_SHA256.startswith("b56be146"))

    def test_assemble_141_and_24_disjoint_from_70(self) -> None:
        games, sealed = assemble_sample()
        self.assertEqual(len(games), 141)
        self.assertEqual({p["game_id"] for p in sealed}, SEALED_T2)
        ids = {g["game_id"] for g in games}
        self.assertFalse(ids & EXAMINED_70)
        self.assertFalse(ids & SEALED_T2)
        self.assertTrue(all(g["complete_27_27"] for g in games))
        self.assertTrue(all(g["rest_bind"] == "BIND_PACKET_ONLY" for g in games))

    def test_seed_formula_and_sims(self) -> None:
        self.assertEqual(SIMULATIONS, 4000)
        self.assertEqual(seed_for("2017_07_KC_OAK"), 201710 + (int(
            hashlib.sha256(b"2017_07_KC_OAK").hexdigest()[:12], 16
        ) % 1000003))

    def test_score_if_source_does_not_open_oos(self) -> None:
        src = (PHASE4 / "score_if_w7w17.py").read_text()
        self.assertNotIn("def load_oos", src)
        self.assertNotIn("OOS_PATH =", src)
        self.assertIn(IF_TIP, src)


class Phase4Artifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.if_path = PHASE4 / "artifacts" / "IF_MUS_W7W17.json"
        cls.q2s_path = PHASE4 / "artifacts" / "q2s_rows_w7w17.json"
        cls.freeze_path = PHASE4 / "artifacts" / "PROTOCOL_FREEZE.json"
        if not cls.if_path.is_file() or not cls.q2s_path.is_file() or not cls.freeze_path.is_file():
            raise unittest.SkipTest("Phase 4 artifacts not written yet")
        cls.if_payload = json.loads(cls.if_path.read_text())
        cls.q2s = json.loads(cls.q2s_path.read_text())
        cls.freeze = json.loads(cls.freeze_path.read_text())

    def test_if_mus_141_no_look(self) -> None:
        self.assertEqual(self.if_payload["n_scored"], 141)
        self.assertEqual(len(self.if_payload["rows"]), 141)
        self.assertEqual(self.if_payload["if_tip"], IF_TIP)
        self.assertEqual(self.if_payload["matrix_sha256"], MATRIX_SHA256)
        self.assertEqual(self.if_payload["market_blend"], 0)
        self.assertEqual(self.if_payload["simulations"], 4000)
        self.assertFalse(self.if_payload["look_run"])
        self.assertFalse(self.if_payload["realized_joined"])
        self.assertFalse(self.if_payload["opened_1ee90fac"])
        self.assertFalse(self.if_payload["examined_70_pooled"])
        ids = {r["game_id"] for r in self.if_payload["rows"]}
        self.assertFalse(ids & EXAMINED_70)
        self.assertFalse(ids & SEALED_T2)
        for row in self.if_payload["rows"]:
            self.assertEqual(row["status"], "SCORED")
            self.assertNotIn("realized_margin", row)
            self.assertFalse(row.get("realized_joined"))

    def test_q2s_blend_and_research_fields(self) -> None:
        self.assertEqual(self.q2s["n_emitted"], 141)
        self.assertEqual(self.q2s["w"], Q2S_WEIGHT)
        self.assertFalse(self.q2s["look_run"])
        self.assertFalse(self.q2s["bootstrap_run"])
        self.assertFalse(self.q2s["realized_joined_for_look"])
        self.assertTrue(self.q2s["fit_exclusion"]["ok"])
        for row in self.q2s["rows"]:
            q2s = row["research"]["q2s"]
            base = row["baseline"]
            for name in Q2S_FIELDS:
                self.assertIn(name, q2s)
            expected_pm = SEALED_A_Q2 + SEALED_B_Q2 * float(q2s["q2_rating_diff"])
            self.assertAlmostEqual(q2s["q2_pm_new"], expected_pm, places=12)
            expected = margin_mu_q2s(base["if_margin_mu"], q2s["q2_pm_new"])
            self.assertAlmostEqual(q2s["margin_mu_q2s"], expected, places=12)
            self.assertNotIn("realized_margin", row)
            self.assertNotIn("realized_margin", base)
            self.assertTrue(base["unchanged"])

    def test_freeze_binds_rows_and_rehash(self) -> None:
        self.assertFalse(self.freeze["existence_only"])
        self.assertFalse(self.freeze["look_run"])
        self.assertIn("if_mus", self.freeze["rows"])
        self.assertIn("q2s_rows", self.freeze["rows"])
        self.assertEqual(self.freeze["rows"]["if_mus"]["sha256"], sha256_file(self.if_path))
        self.assertEqual(self.freeze["rows"]["q2s_rows"]["sha256"], sha256_file(self.q2s_path))
        self.assertEqual(self.freeze["files"]["gate2/RECON_MATRIX_W7W17.csv"], MATRIX_SHA256)
        verify_freeze(self.freeze_path)

    def test_freeze_refuses_row_tamper(self) -> None:
        import copy
        import tempfile

        tampered = copy.deepcopy(self.freeze)
        tampered["rows"]["q2s_rows"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PROTOCOL_FREEZE.json"
            path.write_text(json.dumps(tampered))
            with self.assertRaises(FreezeRefuse):
                verify_freeze(path)

    def test_no_look_consumed(self) -> None:
        self.assertFalse((PHASE4 / "artifacts" / "LOOK_CONSUMED.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
