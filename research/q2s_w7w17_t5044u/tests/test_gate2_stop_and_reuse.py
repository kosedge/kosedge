#!/usr/bin/env python3
"""t5044u Gate 2 tests — PBP stop, Stage B reuse, no IF."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]


class Gate2StopAndReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.status = json.loads((PACKET / "gate2" / "RECON_STATUS.json").read_text())
        cls.pbp = json.loads((PACKET / "gate2" / "PBP_STATUS.json").read_text())
        cls.wl = json.loads((PACKET / "gate2" / "WL_PARITY_50bda875.json").read_text())
        cls.cov = json.loads(
            (PACKET / "gate2" / "stage_b_w7w8" / "COVERAGE_SLICE.json").read_text()
        )

    def test_pbp_verified_on_resume(self) -> None:
        self.assertTrue(self.pbp["verified"])
        self.assertEqual(
            self.pbp["sha256"],
            "84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710",
        )
        self.assertFalse(self.pbp.get("fetched", False))

    def test_no_if_q2s_look(self) -> None:
        self.assertFalse(self.status["if_invoked"])
        self.assertFalse(self.status["q2s_emitted"])
        self.assertFalse(self.status["look_run"])
        self.assertTrue(self.status["stop_for_alex_pre_if"])
        self.assertFalse(self.status["quarantined_1ee90fac_scored"])
        self.assertFalse(self.status["new_index_formula"])

    def test_w7w8_reuse_counts(self) -> None:
        self.assertEqual(self.cov["n_games"], 28)
        self.assertEqual(self.cov["n_complete_27_of_27"], 22)
        self.assertEqual(self.cov["n_partial_t2"], 6)
        self.assertEqual(len(self.cov["complete_game_ids"]), 22)
        partial_ids = {p["game_id"] for p in self.cov["partial"]}
        self.assertEqual(
            partial_ids,
            {
                "2017_07_TB_BUF",
                "2017_07_DAL_SF",
                "2017_07_CIN_PIT",
                "2017_07_SEA_NYG",
                "2017_08_HOU_SEA",
                "2017_08_PIT_DET",
            },
        )

    def test_w9_w17_now_reconstructed(self) -> None:
        self.assertEqual(self.status["completeness"]["n_recon_not_attempted"], 0)
        self.assertEqual(self.status["completeness"]["n_unexpected_missing"], 0)
        self.assertEqual(self.status["completeness"]["n_outcome_excluded"], 0)
        self.assertEqual(self.status["completeness"]["n_complete_27_of_27"], 141)

    def test_transferred_matrix_pin(self) -> None:
        self.assertEqual(
            self.cov["source_full_matrix_sha256"],
            "cd9af2858e21fac5247a489051f0cc61b9490cb97ffdec9ac41a31a2d224d810",
        )
        path = PACKET / "gate2" / "stage_b_w7w8" / "RECON_MATRIX.csv"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, self.cov["slice_sha256"])

    def test_wl_parity_independent(self) -> None:
        self.assertTrue(
            self.wl["independent_parity_proven"],
            msg=json.dumps(self.wl.get("mismatches"), indent=2)[:800],
        )
        self.assertEqual(self.wl["n_compared"], 28)
        self.assertEqual(self.wl["outcomes_sha8"], "50bda875")
        self.assertTrue(self.wl["compared_to"].startswith("Stage B SAMPLE_MANIFEST"))
        self.assertTrue(self.wl["use_for_dependent_scoring"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
