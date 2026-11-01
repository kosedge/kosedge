#!/usr/bin/env python3
"""t5075u G2 — synthetic metric tests. No real 50bda875 parse."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

G2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(G2))

from constants import COVERAGE_LEVELS, LOGLOSS_EPS, LOGLOSS_N, N_DRAWS, UNAVAILABLE  # noqa: E402
from metrics import (  # noqa: E402
    MetricRefuse,
    brier_score,
    draw_diagnostics,
    empirical_crps,
    empirical_crps_one,
    equal_tail_coverage_width,
    exclude_actual_ties,
    log_loss_with_clip,
    mae,
    mae_rmse_bundle,
    paired_mae_diff,
    per_week_summaries,
    refuse_if_distribution_regen,
    rmse,
)


class TestPointMetrics(unittest.TestCase):
    def test_mae_rmse_known(self) -> None:
        pred = [1.0, 2.0, 3.0]
        actual = [1.0, 0.0, 6.0]
        self.assertAlmostEqual(mae(pred, actual), (0 + 2 + 3) / 3.0)
        self.assertAlmostEqual(rmse(pred, actual), math.sqrt((0 + 4 + 9) / 3.0))

    def test_paired_mae_diff_equals_mae_minus(self) -> None:
        a = [0.0, 0.0, 0.0]
        b = [3.0, 3.0, 3.0]
        y = [1.0, 1.0, 1.0]
        self.assertAlmostEqual(paired_mae_diff(a, b, y), mae(a, y) - mae(b, y))
        self.assertAlmostEqual(paired_mae_diff(a, b, y), -1.0)


class TestLogLossClip(unittest.TestCase):
    def test_clip_interval_and_originals(self) -> None:
        p = [0.0, 1.0, 0.5]
        y = [1.0, 0.0, 1.0]
        out = log_loss_with_clip(p, y)
        self.assertEqual(out["n_draws"], LOGLOSS_N)
        self.assertEqual(out["n_draws"], N_DRAWS)
        self.assertEqual(out["eps"], LOGLOSS_EPS)
        self.assertEqual(out["clip_interval"], [LOGLOSS_EPS, 1.0 - LOGLOSS_EPS])
        self.assertTrue(out["originals_retained"])
        self.assertEqual(out["n_probs_clipped"], 2)
        self.assertEqual(out["prob_original"], p)
        self.assertAlmostEqual(out["prob_clipped"][0], LOGLOSS_EPS)
        self.assertAlmostEqual(out["prob_clipped"][1], 1.0 - LOGLOSS_EPS)
        self.assertTrue(math.isinf(out["log_loss_original"]))
        self.assertTrue(math.isfinite(out["log_loss_clipped"]))

    def test_wrong_n_refused(self) -> None:
        with self.assertRaises(MetricRefuse):
            log_loss_with_clip([0.5], [1.0], n_draws=100)


class TestTiesAndBrier(unittest.TestCase):
    def test_ties_excluded_and_counted(self) -> None:
        p = [0.9, 0.2, 0.6]
        m = [7.0, 0.0, -3.0]
        filtered = exclude_actual_ties(p, m)
        self.assertEqual(filtered["n_ties"], 1)
        self.assertEqual(filtered["n_binary"], 2)
        self.assertEqual(list(filtered["y"]), [1.0, 0.0])
        self.assertAlmostEqual(
            brier_score(filtered["prob"], filtered["y"]),
            ((0.9 - 1) ** 2 + (0.6 - 0) ** 2) / 2.0,
        )

    def test_brier_rejects_non_binary(self) -> None:
        with self.assertRaises(MetricRefuse):
            brier_score([0.5], [0.5])


class TestCRPSAndCoverage(unittest.TestCase):
    def test_empirical_crps_three_point(self) -> None:
        # draws 1,2,3 vs y=2 → 2/9
        self.assertAlmostEqual(empirical_crps_one([1.0, 2.0, 3.0], 2.0), 2.0 / 9.0)
        arr = empirical_crps(np.array([[1.0, 2.0, 3.0]]), [2.0])
        self.assertAlmostEqual(float(arr[0]), 2.0 / 9.0)

    def test_equal_tail_levels_and_width(self) -> None:
        draws = np.tile(np.arange(100, dtype=np.float64), (3, 1))
        actual = np.array([50.0, -10.0, 50.0])
        cov = equal_tail_coverage_width(draws, actual)
        self.assertEqual(set(cov), {"50pct", "80pct", "90pct"})
        self.assertEqual(tuple(COVERAGE_LEVELS), (0.50, 0.80, 0.90))
        self.assertEqual(cov["50pct"]["equal_tail"], [0.25, 0.75])
        self.assertAlmostEqual(cov["80pct"]["equal_tail"][0], 0.10)
        self.assertAlmostEqual(cov["80pct"]["equal_tail"][1], 0.90)
        self.assertAlmostEqual(cov["90pct"]["equal_tail"][0], 0.05)
        self.assertAlmostEqual(cov["90pct"]["equal_tail"][1], 0.95)
        self.assertGreater(cov["90pct"]["mean_width"], cov["50pct"]["mean_width"])
        self.assertAlmostEqual(cov["50pct"]["coverage"], 2.0 / 3.0)

    def test_draw_diagnostics_marks_if_unavailable(self) -> None:
        rng = np.random.default_rng(0)
        H = rng.normal(24.0, 3.0, size=(11, N_DRAWS))
        A = rng.normal(20.0, 3.0, size=(11, N_DRAWS))
        H = np.maximum(H, 0.0)
        A = np.maximum(A, 0.0)
        weeks_actual_m = np.full(11, 3.0)
        weeks_actual_t = np.full(11, 44.0)
        out = draw_diagnostics(
            H=H,
            A=A,
            actual_margin=weeks_actual_m,
            actual_total=weeks_actual_t,
        )
        self.assertEqual(out["if_distribution"], UNAVAILABLE)
        self.assertTrue(math.isfinite(out["crps_margin_mean"]))
        self.assertIn("50pct", out["coverage_width_margin"])

    def test_if_regen_refused(self) -> None:
        with self.assertRaises(MetricRefuse):
            refuse_if_distribution_regen()


class TestPerWeekAndBundle(unittest.TestCase):
    def _week_arrays(self):
        weeks = []
        for w in range(7, 18):
            weeks.extend([w, w])
        n = len(weeks)
        actual_m = np.zeros(n)
        actual_t = np.full(n, 40.0)
        joint_m = np.full(n, 1.0)
        if_m = np.full(n, 2.0)
        point_m = np.full(n, 0.0)
        joint_t = np.full(n, 41.0)
        if_t = np.full(n, 42.0)
        return weeks, actual_m, actual_t, {
            "joint": {"margin": joint_m, "total": joint_t},
            "if": {"margin": if_m, "total": if_t},
            "point": {"margin": point_m, "total": None},
        }

    def test_per_week_requires_w7_w17(self) -> None:
        weeks, am, at, preds = self._week_arrays()
        tbl = per_week_summaries(weeks=weeks, actual_margin=am, actual_total=at, preds=preds)
        self.assertEqual(tbl["n_week_blocks"], 11)
        self.assertEqual(set(tbl["blocks"]), {str(w) for w in range(7, 18)})
        self.assertEqual(tbl["blocks"]["7"]["point_total"], UNAVAILABLE)
        with self.assertRaises(MetricRefuse):
            per_week_summaries(
                weeks=weeks[:-2],
                actual_margin=am[:-2],
                actual_total=at[:-2],
                preds={
                    k: {
                        "margin": v["margin"][:-2],
                        "total": None if v["total"] is None else v["total"][:-2],
                    }
                    for k, v in preds.items()
                },
            )

    def test_bundle_marks_missing_point_total(self) -> None:
        weeks, am, at, preds = self._week_arrays()
        bundle = mae_rmse_bundle(actual_margin=am, actual_total=at, preds=preds)
        self.assertEqual(bundle["total"]["point"]["mae"], UNAVAILABLE)
        self.assertEqual(bundle["paired_mae_diff_total"]["joint_minus_point"], UNAVAILABLE)
        self.assertNotEqual(bundle["paired_mae_diff_margin"]["joint_minus_if"], UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()
