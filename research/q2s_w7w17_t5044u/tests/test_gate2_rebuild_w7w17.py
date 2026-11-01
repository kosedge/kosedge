#!/usr/bin/env python3
"""t5044u Gate 2 rebuild tests — PBP verified, no IF."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]
PBP_SHA = "84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710"
SEALED_T2 = {
    "2017_07_TB_BUF",
    "2017_07_DAL_SF",
    "2017_07_CIN_PIT",
    "2017_07_SEA_NYG",
    "2017_08_HOU_SEA",
    "2017_08_PIT_DET",
    "2017_09_ARI_SF",
    "2017_09_BAL_TEN",
    "2017_09_CIN_JAX",
    "2017_09_LA_NYG",
    "2017_09_DET_GB",
    "2017_10_CLE_DET",
    "2017_10_GB_CHI",
    "2017_10_LAC_JAX",
    "2017_10_MIN_WAS",
    "2017_10_NE_DEN",
    "2017_10_PIT_IND",
    "2017_11_BAL_GB",
    "2017_11_KC_NYG",
    "2017_11_NE_OAK",
    "2017_11_PHI_DAL",
    "2017_12_CAR_NYJ",
    "2017_12_SEA_SF",
    "2017_12_TEN_IND",
}


class Gate2RebuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.status = json.loads((PACKET / "gate2" / "RECON_STATUS.json").read_text())
        cls.pbp = json.loads((PACKET / "gate2" / "PBP_VERIFY_RECEIPT.json").read_text())
        cls.cov = json.loads((PACKET / "gate2" / "COVERAGE_W7W17.json").read_text())
        cls.wl = json.loads((PACKET / "gate2" / "WL_PARITY_50bda875.json").read_text())

    def test_pbp_verified_no_fetch(self) -> None:
        self.assertTrue(self.pbp["verified"])
        self.assertFalse(self.pbp["fetched"])
        self.assertEqual(self.pbp["sha256"], PBP_SHA)
        self.assertEqual(self.pbp["sha8"], "84eacd96")

    def test_no_if_q2s_look(self) -> None:
        self.assertFalse(self.status["if_invoked"])
        self.assertFalse(self.status["q2s_emitted"])
        self.assertFalse(self.status["look_run"])
        self.assertTrue(self.status["stop_for_alex_pre_if"])
        self.assertFalse(self.status["quarantined_1ee90fac_scored"])
        self.assertFalse(self.status["new_index_formula"])

    def test_completeness_141_and_24(self) -> None:
        self.assertEqual(self.cov["n_identity"], 165)
        self.assertEqual(self.cov["n_complete_27_of_27"], 141)
        self.assertEqual(self.cov["n_partial_t2"], 24)
        self.assertEqual(self.cov["n_cells"], 165 * 27)
        self.assertEqual(self.cov["n_unexpected_missing"], 0)
        self.assertEqual(self.cov["n_outcome_excluded"], 0)
        self.assertEqual({p["game_id"] for p in self.cov["partial"]}, SEALED_T2)
        self.assertEqual(len(self.cov["complete_game_ids"]), 141)

    def test_w7w8_parity(self) -> None:
        parity = self.cov["w7w8_parity_vs_stage_b"]
        self.assertTrue(parity["pass"])
        self.assertEqual(parity["n_cells"], 28 * 27)
        self.assertEqual(len(parity.get("asserted_fields", [])), 27)
        self.assertEqual(parity.get("n_exact_numeric_compared"), 138)
        self.assertEqual(parity.get("max_abs_delta_exact_numeric"), 0.0)
        self.assertEqual(parity.get("tolerances", {}).get("pass_rate_pressure_rz_def_epa_diff"), 0.0)
        self.assertEqual(parity.get("tolerances", {}).get("index"), 1e-6)
        self.assertEqual(parity.get("tolerances", {}).get("epa_success"), 1e-9)
        self.assertEqual(parity.get("tolerances", {}).get("rest"), 1e-9)

    def test_matrix_sha(self) -> None:
        path = PACKET / "gate2" / "RECON_MATRIX_W7W17.csv"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, self.cov["matrix_sha256"])
        self.assertEqual(digest, self.status["matrix_sha256"])

    def test_wl_parity_still_holds(self) -> None:
        self.assertTrue(self.wl["independent_parity_proven"])
        self.assertEqual(self.wl["outcomes_sha8"], "50bda875")


if __name__ == "__main__":
    unittest.main(verbosity=2)
