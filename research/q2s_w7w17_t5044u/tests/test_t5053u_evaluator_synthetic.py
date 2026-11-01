#!/usr/bin/env python3
"""t5053u — synthetic-only evaluator tests. No real 2017 outcomes join."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np

PACKET = Path(__file__).resolve().parents[1]
EVAL = PACKET / "evaluator"
sys.path.insert(0, str(EVAL))

from bootstrap import (  # noqa: E402
    BOOT_B,
    BOOT_SEED,
    WEEK_BLOCKS,
    paired_delta_mae,
    paired_game_bootstrap_ci,
)
from compare import EvalRefuse, evaluate, look_real  # noqa: E402
from verify_final_prelook import (  # noqa: E402
    ALEX_RECEIPT_PATH,
    IF_MUS_SHA,
    MATRIX_SHA,
    PARENT_FREEZE_SHA,
    Q2S_SHA,
    sha256_file,
    verify_complete_set,
    verify_parent_history,
)


def _load_fx() -> dict:
    return json.loads((EVAL / "fixtures" / "synthetic_w7w17.json").read_text())


def _arrays(fx: dict):
    return (
        list(fx["candidate"]),
        list(fx["baseline"]),
        list(fx["actual"]),
        list(fx["weeks"]),
        int(fx["expected_n"]),
    )


class SyntheticEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fx = _load_fx()
        cls.cand, cls.base, cls.act, cls.weeks, cls.n = _arrays(cls.fx)

    def test_protocol_constants(self) -> None:
        self.assertEqual(BOOT_B, 10000)
        self.assertEqual(BOOT_SEED, 20261102)
        self.assertEqual(tuple(WEEK_BLOCKS), tuple(range(7, 18)))
        self.assertEqual(len(WEEK_BLOCKS), 11)

    def test_known_delta_mae(self) -> None:
        result = evaluate(
            self.cand, self.base, self.act, self.weeks, expected_n=self.n
        )
        self.assertAlmostEqual(result["primary"]["delta_mae"], 5.0, places=12)
        self.assertAlmostEqual(result["primary"]["mae_baseline"], 0.0, places=12)
        self.assertAlmostEqual(result["primary"]["mae_candidate"], 5.0, places=12)
        self.assertEqual(result["B"], 10000)
        self.assertEqual(result["seed"], 20261102)
        self.assertFalse(result["look_run"])
        self.assertIsNone(result["realized_source"])

    def test_wrong_delta_mae_formula_caught(self) -> None:
        deltas = paired_delta_mae(self.cand, self.base, self.act)
        self.assertAlmostEqual(float(deltas.mean()), 5.0, places=12)
        reversed_d = paired_delta_mae(self.base, self.cand, self.act)
        self.assertAlmostEqual(float(reversed_d.mean()), -5.0, places=12)
        squared = (np.asarray(self.cand) - np.asarray(self.act)) ** 2
        self.assertNotAlmostEqual(float(np.mean(squared)), 5.0, places=12)
        result = evaluate(
            self.cand, self.base, self.act, self.weeks, expected_n=self.n
        )
        self.assertAlmostEqual(result["primary"]["delta_mae"], 5.0, places=12)
        self.assertNotAlmostEqual(result["primary"]["delta_mae"], -5.0, places=12)

    def test_wrong_seed_refused(self) -> None:
        with self.assertRaises(EvalRefuse):
            evaluate(
                self.cand,
                self.base,
                self.act,
                self.weeks,
                expected_n=self.n,
                seed=20261101,
            )
        with self.assertRaises(ValueError):
            paired_game_bootstrap_ci([1.0, 2.0], B=10000, seed=20261101)

    def test_wrong_B_refused(self) -> None:
        with self.assertRaises(EvalRefuse):
            evaluate(
                self.cand,
                self.base,
                self.act,
                self.weeks,
                expected_n=self.n,
                B=100,
            )
        with self.assertRaises(ValueError):
            paired_game_bootstrap_ci([1.0, 2.0], B=100, seed=20261102)

    def test_seed_20261102_ci_differs_from_20261101(self) -> None:
        irregular = np.array(
            [0.3, -1.1, 2.4, 0.0, -0.7, 1.8, 4.2, -3.3, 0.5, 1.0, -2.2],
            dtype=float,
        )
        a = paired_game_bootstrap_ci(irregular)
        rng_alt = np.random.default_rng(20261101)
        stats = np.empty(10000, dtype=float)
        n = int(irregular.size)
        for i in range(10000):
            take = rng_alt.integers(0, n, size=n)
            stats[i] = float(irregular[take].mean())
        alt_lo = float(np.quantile(stats, 0.025))
        self.assertEqual(a["seed"], 20261102.0)
        self.assertEqual(a["B"], 10000.0)
        self.assertNotAlmostEqual(a["ci_lo"], alt_lo, places=8)

    def test_week_blocks_eleven_w7_w17(self) -> None:
        result = evaluate(
            self.cand, self.base, self.act, self.weeks, expected_n=self.n
        )
        blocks = result["descriptive"]["week_blocks"]
        self.assertEqual(result["descriptive"]["n_week_blocks"], 11)
        self.assertEqual(set(blocks), {str(w) for w in range(7, 18)})
        expected = self.fx["expected_week_delta_mae"]
        for week, exp in expected.items():
            self.assertAlmostEqual(blocks[week]["delta_mae"], exp, places=12)
            self.assertEqual(blocks[week]["n"], 2.0)
            self.assertEqual(blocks[week]["bootstrap"]["seed"], 20261102.0)
            self.assertEqual(blocks[week]["bootstrap"]["B"], 10000.0)

    def test_week_block_miswire_refused(self) -> None:
        bad_weeks = [w - 6 for w in self.weeks]  # 1–11 instead of 7–17
        with self.assertRaises(EvalRefuse):
            evaluate(
                self.cand, self.base, self.act, bad_weeks, expected_n=self.n
            )
        dropped_week = [w if w != 17 else 16 for w in self.weeks]
        with self.assertRaises(EvalRefuse):
            evaluate(
                self.cand, self.base, self.act, dropped_week, expected_n=self.n
            )

    def test_missing_rows_refused(self) -> None:
        with self.assertRaises(EvalRefuse) as ctx:
            evaluate(
                self.cand[:-1],
                self.base[:-1],
                self.act[:-1],
                self.weeks[:-1],
                expected_n=self.n,
            )
        self.assertIn("missing/extra rows", str(ctx.exception))

    def test_fixture_is_not_real_outcomes(self) -> None:
        text = (EVAL / "fixtures" / "synthetic_w7w17.json").read_text()
        self.assertIn("Synthetic only", text)
        self.assertNotIn("50bda875", text)
        self.assertNotIn("1ee90fac", text)
        src = (EVAL / "compare.py").read_text()
        self.assertNotIn("def load_oos", src)
        self.assertNotIn("outcomes_2013_2022_score_only", src)

    def test_look_real_refuses(self) -> None:
        self.assertFalse(ALEX_RECEIPT_PATH.exists())
        self.assertFalse(
            (PACKET / "phase4" / "artifacts" / "LOOK_CONSUMED.json").exists()
        )
        with self.assertRaises(EvalRefuse):
            look_real()


class FinalFreezeAndParentHistoryTests(unittest.TestCase):
    def test_parent_row_hashes_unchanged(self) -> None:
        parent = verify_parent_history()
        self.assertEqual(sha256_file(PACKET / "phase4/artifacts/PROTOCOL_FREEZE.json"), PARENT_FREEZE_SHA)
        self.assertEqual(sha256_file(PACKET / "phase4/artifacts/IF_MUS_W7W17.json"), IF_MUS_SHA)
        self.assertEqual(sha256_file(PACKET / "phase4/artifacts/q2s_rows_w7w17.json"), Q2S_SHA)
        self.assertEqual(sha256_file(PACKET / "gate2/RECON_MATRIX_W7W17.csv"), MATRIX_SHA)
        self.assertEqual(parent["rows"]["if_mus"]["sha256"], IF_MUS_SHA)
        self.assertEqual(parent["rows"]["q2s_rows"]["sha256"], Q2S_SHA)

    def test_final_freeze_complete_set_when_present(self) -> None:
        path = EVAL / "FINAL_PRELOOK_FREEZE.json"
        if not path.is_file():
            self.skipTest("final freeze not written yet")
        final = verify_complete_set()
        self.assertFalse(final["parent_rewritten"])
        self.assertFalse(final["look_authorized"])
        self.assertFalse(final["look_run"])
        self.assertEqual(final["parent_freeze"]["sha256"], PARENT_FREEZE_SHA)
        self.assertEqual(final["rows"]["if_mus"]["sha256"], IF_MUS_SHA)
        self.assertEqual(final["rows"]["q2s_rows"]["sha256"], Q2S_SHA)
        self.assertIn("evaluator/METRIC_PROTOCOL.md", final["files"])
        self.assertIn("evaluator/bootstrap.py", final["files"])
        self.assertIn("phase4/artifacts/PROTOCOL_FREEZE.json", final["files"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
