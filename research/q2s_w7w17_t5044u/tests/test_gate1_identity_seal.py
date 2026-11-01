#!/usr/bin/env python3
"""t5044u Gate 1 tests — identity seal, no PBP."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / "gate1"))

from seal_identities import (  # noqa: E402
    EXPECTED_BY_WEEK,
    EXPECTED_N,
    GAMES_SHA256,
    SEALED_T2_RISKS,
    STAGE_B_W7_HASH,
    STAGE_B_W8_HASH,
    selection_hash,
)


class Gate1IdentitySealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seal = json.loads((PACKET / "gate1" / "SELECTION_HASH_SEAL.json").read_text())
        cls.manifest = json.loads((PACKET / "gate1" / "IDENTITY_MANIFEST.json").read_text())
        cls.t2 = json.loads((PACKET / "gate1" / "T2_BYE_RETURN_RISKS.json").read_text())

    def test_games_pin(self) -> None:
        path = PACKET / "pins" / "games_4fe1cdd7.csv"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(digest, GAMES_SHA256)
        self.assertEqual(self.seal["games_csv_pin"]["sha256"], GAMES_SHA256)

    def test_n_165_and_week_counts(self) -> None:
        games = self.manifest["games"]
        self.assertEqual(len(games), EXPECTED_N)
        self.assertEqual(self.seal["n_identity_sealed"], 165)
        by_week = {}
        for row in games:
            by_week[row["week"]] = by_week.get(row["week"], 0) + 1
        self.assertEqual(by_week, EXPECTED_BY_WEEK)

    def test_selection_hash_recipe(self) -> None:
        ids = [g["game_id"] for g in self.manifest["games"]]
        self.assertEqual(self.manifest["selection_hash"], selection_hash(ids))
        self.assertEqual(self.seal["selection_hash_combined"], selection_hash(ids))
        self.assertEqual(self.seal["selection_hash_by_week"]["7"], STAGE_B_W7_HASH)
        self.assertEqual(self.seal["selection_hash_by_week"]["8"], STAGE_B_W8_HASH)

    def test_t2_24_preserved(self) -> None:
        ids = [r["game_id"] for r in self.t2["risks"]]
        self.assertEqual(ids, [s["game_id"] for s in SEALED_T2_RISKS])
        self.assertEqual(len(ids), 24)
        self.assertTrue(all(not r["selection_excluded"] for r in self.t2["risks"]))
        self.assertTrue(all(r["retained"] and not r["substituted"] for r in self.t2["risks"]))

    def test_no_outcome_exclusion_or_fills(self) -> None:
        self.assertEqual(self.seal["n_outcome_excluded"], 0)
        self.assertEqual(self.seal["n_replaced"], 0)
        self.assertEqual(self.seal["n_filled"], 0)
        for game in self.manifest["games"]:
            self.assertEqual(game["wl_count_status"], "UNRESOLVED")
            self.assertIsNone(game["record_asof_home"])
            self.assertIsNone(game["completed_same_season_games_home"])

    def test_pbp_not_opened_and_1ee90fac_not_scored(self) -> None:
        self.assertTrue(self.seal["sealed_before_pbp_open"])
        self.assertFalse(self.seal["pbp_opened_at_seal"])
        self.assertTrue(self.seal["pbp_absent_at_seal_start"])
        self.assertFalse(self.seal["quarantined_index"]["opened"])
        self.assertFalse(self.seal["quarantined_index"]["scored_from"])
        self.assertFalse(self.seal["if_authorized"])
        self.assertFalse(self.seal["look_authorized"])

    def test_rest_bind_and_labels(self) -> None:
        self.assertEqual(self.seal["rest"]["bind"], "BIND_PACKET_ONLY")
        self.assertEqual(self.seal["rest"]["heuristic"], "155d3ca0_ET_DOW")
        self.assertIn("RETRO_FIT", self.seal["labels"])
        self.assertIn("A1", self.seal["labels"])
        self.assertEqual(self.seal["cert"], 0)
        for game in self.manifest["games"]:
            self.assertEqual(game["rest_bind"], "BIND_PACKET_ONLY")
            self.assertIn(game["rest_days_et"], (4.0, 6.0, 7.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
