#!/usr/bin/env python3
"""t5055u — week-cluster bootstrap + complete look_real path.

Synthetic fixtures only. Does not join real 2017 outcomes / 50bda875.
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PACKET = Path(__file__).resolve().parents[1]
EVAL = PACKET / "evaluator"
sys.path.insert(0, str(EVAL))

from bootstrap import (  # noqa: E402
    BOOT_B,
    BOOT_SEED,
    N_CLUSTERS,
    WEEK_BLOCKS,
    cluster_week_sums,
    paired_delta_mae,
    paired_game_bootstrap_ci,
    paired_week_cluster_bootstrap_ci,
    week_cluster_stat,
)
from compare import (  # noqa: E402
    OUTCOMES_JOINS,
    OUTCOMES_PIN_PATH,
    EvalRefuse,
    LookContext,
    evaluate,
    join_score_only_identity,
    look_real,
    require_look_gates,
    verdict_from_uncertainty,
)
from verify_final_prelook import (  # noqa: E402
    ALEX_RECEIPT_PATH,
    COS_EXECUTE_PATH,
    HISTORY_FREEZE_SHA,
    IF_MUS_SHA,
    MATRIX_SHA,
    PARENT_FREEZE_SHA,
    Q2S_SHA,
    T5055U_FREEZE_PATH,
    sha256_file,
    verify_complete_set,
    verify_history_freeze_a4652323,
    verify_parent_history,
)


def _load_unequal() -> dict:
    return json.loads((EVAL / "fixtures" / "synthetic_unequal_clusters.json").read_text())


def _synth_141() -> tuple[list[dict], list[tuple]]:
    """141 synthetic identities. Season 2099 — not 2017."""
    rows: list[dict] = []
    outcomes: list[tuple] = []
    counts = {w: 12 for w in range(7, 17)}
    counts[17] = 21
    n = 0
    for week, n_w in counts.items():
        for _i in range(n_w):
            home = f"H{n:03d}"
            away = f"A{n:03d}"
            rows.append(
                {
                    "game_id": f"2099_{week:02d}_{away}_{home}",
                    "season": 2099,
                    "week": week,
                    "home": home,
                    "away": away,
                    "baseline": {"if_margin_mu": 0.0},
                    "research": {"q2s": {"margin_mu_q2s": 1.0}},
                }
            )
            outcomes.append((2099, week, home, away, 10.0, 7.0))
            n += 1
    assert n == 141
    assert all(r["season"] == 2099 for r in rows)
    return rows, outcomes


def _write_synth_look_files(tmp: Path, rows, outcomes):
    q2s_path = tmp / "q2s.json"
    out_path = tmp / "outcomes.csv"
    q2s_path.write_text(json.dumps({"rows": rows}, sort_keys=True))
    with out_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["season", "week", "home", "away", "home_score", "away_score"],
        )
        writer.writeheader()
        for season, week, home, away, hs, aws in outcomes:
            writer.writerow(
                {
                    "season": season,
                    "week": week,
                    "home": home,
                    "away": away,
                    "home_score": hs,
                    "away_score": aws,
                }
            )
    return q2s_path, out_path


def _plant_receipts(tmp: Path, freeze_sha: str) -> tuple[Path, Path]:
    alex = tmp / "ALEX.json"
    cos = tmp / "COS.json"
    alex.write_text(
        json.dumps(
            {
                "binds_final_freeze_sha256": freeze_sha,
                "authorizes_look": True,
                "synthetic": True,
            },
            indent=2,
        )
        + "\n"
    )
    cos.write_text(
        json.dumps(
            {
                "binds_final_freeze_sha256": freeze_sha,
                "authorizes_execute": True,
                "synthetic": True,
            },
            indent=2,
        )
        + "\n"
    )
    return alex, cos


class WeekClusterBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fx = _load_unequal()
        cls.cand = list(cls.fx["candidate"])
        cls.base = list(cls.fx["baseline"])
        cls.act = list(cls.fx["actual"])
        cls.weeks = list(cls.fx["weeks"])
        cls.n = int(cls.fx["expected_n"])
        cls.deltas = paired_delta_mae(cls.cand, cls.base, cls.act)

    def test_observed_game_weighted_unequal_clusters(self) -> None:
        result = evaluate(
            self.cand, self.base, self.act, self.weeks, expected_n=self.n
        )
        expected = 10.0 / 31.0
        self.assertAlmostEqual(result["primary"]["delta_mae"], expected, places=12)
        self.assertAlmostEqual(
            result["uncertainty"]["week_cluster_bootstrap"]["mean"],
            expected,
            places=12,
        )
        self.assertEqual(result["descriptive"]["week_blocks"]["7"]["n"], 1.0)
        self.assertEqual(result["descriptive"]["week_blocks"]["8"]["n"], 3.0)
        self.assertNotIn("bootstrap", result["descriptive"]["week_blocks"]["7"])

    def test_repeated_cluster_draw(self) -> None:
        sums, ns = cluster_week_sums(self.deltas, self.weeks)
        all_week7 = np.zeros(N_CLUSTERS, dtype=int)  # index 0 == week 7
        stat = week_cluster_stat(sums, ns, all_week7)
        self.assertAlmostEqual(stat, 10.0, places=12)

    def test_omitted_cluster_draw(self) -> None:
        sums, ns = cluster_week_sums(self.deltas, self.weeks)
        all_week8 = np.ones(N_CLUSTERS, dtype=int)  # index 1 == week 8
        stat = week_cluster_stat(sums, ns, all_week8)
        self.assertAlmostEqual(stat, 0.0, places=12)

    def test_mixed_repeat_omit_draw(self) -> None:
        sums, ns = cluster_week_sums(self.deltas, self.weeks)
        # one week-7 + ten week-8 → (10 + 0) / (1 + 30) = 10/31
        take = np.array([0] + [1] * 10, dtype=int)
        stat = week_cluster_stat(sums, ns, take)
        self.assertAlmostEqual(stat, 10.0 / 31.0, places=12)
        # two week-7 + nine week-8 → 20 / (2 + 27) = 20/29
        take2 = np.array([0, 0] + [1] * 9, dtype=int)
        stat2 = week_cluster_stat(sums, ns, take2)
        self.assertAlmostEqual(stat2, 20.0 / 29.0, places=12)

    def test_week_cluster_ci_differs_from_game_bootstrap(self) -> None:
        game = paired_game_bootstrap_ci(self.deltas)
        week = paired_week_cluster_bootstrap_ci(self.deltas, self.weeks)
        self.assertEqual(game["seed"], float(BOOT_SEED))
        self.assertEqual(week["seed"], float(BOOT_SEED))
        self.assertEqual(game["B"], float(BOOT_B))
        self.assertEqual(week["B"], float(BOOT_B))
        self.assertEqual(week["n_clusters"], 11.0)
        self.assertEqual(week["method"], "week_cluster")
        self.assertEqual(game["method"], "game")
        # Unequal clusters: the two percentile CIs must not be identical.
        self.assertTrue(
            abs(game["ci_lo"] - week["ci_lo"]) > 1e-12
            or abs(game["ci_hi"] - week["ci_hi"]) > 1e-12
        )

    def test_mixed_week_signs_do_not_force_inconclusive(self) -> None:
        # 10 strongly-negative weeks (cand closer to act than base),
        # one small positive week. Per-week signs must not flip verdict.
        weeks = []
        cand = []
        base = []
        act = []
        for week in range(7, 17):
            weeks.extend([week, week])
            cand.extend([0.0, 0.0])
            base.extend([5.0, 5.0])
            act.extend([0.0, 0.0])
        weeks.extend([17, 17])
        cand.extend([1.0, 1.0])
        base.extend([0.0, 0.0])
        act.extend([0.0, 0.0])
        result = evaluate(cand, base, act, weeks, expected_n=22)
        signs = {w: result["descriptive"]["week_blocks"][w]["delta_mae"] for w in result["descriptive"]["week_blocks"]}
        self.assertTrue(any(v > 0 for v in signs.values()))
        self.assertTrue(any(v < 0 for v in signs.values()))
        self.assertFalse(result["uncertainty"]["game_ci_includes_zero"])
        self.assertFalse(result["uncertainty"]["week_cluster_ci_includes_zero"])
        self.assertFalse(result["uncertainty"]["direction_disagree"])
        self.assertTrue(result["verdict"].startswith("POINT_IMPROVEMENT"))

    def test_verdict_either_ci_includes_zero(self) -> None:
        game = {"mean": -1.0, "ci_lo": -2.0, "ci_hi": 0.1}
        week = {"mean": -1.0, "ci_lo": -1.5, "ci_hi": -0.2}
        verdict, meta = verdict_from_uncertainty(game, week)
        self.assertTrue(verdict.startswith("INCONCLUSIVE"))
        self.assertTrue(meta["game_ci_includes_zero"])
        game2 = {"mean": -1.0, "ci_lo": -2.0, "ci_hi": -0.1}
        week2 = {"mean": -1.0, "ci_lo": -0.5, "ci_hi": 0.2}
        verdict2, meta2 = verdict_from_uncertainty(game2, week2)
        self.assertTrue(verdict2.startswith("INCONCLUSIVE"))
        self.assertTrue(meta2["week_cluster_ci_includes_zero"])

    def test_verdict_direction_disagree(self) -> None:
        game = {"mean": -1.0, "ci_lo": -2.0, "ci_hi": -0.1}
        week = {"mean": -1.0, "ci_lo": 0.1, "ci_hi": 0.8}
        verdict, meta = verdict_from_uncertainty(game, week)
        self.assertIn("disagree in direction", verdict)
        self.assertTrue(meta["direction_disagree"])

    def test_wrong_seed_and_B_refused(self) -> None:
        with self.assertRaises(ValueError):
            paired_week_cluster_bootstrap_ci(self.deltas, self.weeks, seed=20261101)
        with self.assertRaises(ValueError):
            paired_week_cluster_bootstrap_ci(self.deltas, self.weeks, B=100)


class LookRealCompletePathTests(unittest.TestCase):
    def setUp(self) -> None:
        OUTCOMES_JOINS.clear()

    def tearDown(self) -> None:
        OUTCOMES_JOINS.clear()

    def test_production_look_real_refuses_without_receipts(self) -> None:
        self.assertFalse(ALEX_RECEIPT_PATH.exists())
        self.assertFalse(COS_EXECUTE_PATH.exists())
        self.assertFalse((PACKET / "phase4" / "artifacts" / "LOOK_CONSUMED.json").exists())
        before = list(OUTCOMES_JOINS)
        with self.assertRaises(EvalRefuse) as ctx:
            look_real()
        self.assertEqual(OUTCOMES_JOINS, before)
        self.assertFalse((PACKET / "phase4" / "artifacts" / "LOOK_CONSUMED.json").exists())
        self.assertNotIn(str(OUTCOMES_PIN_PATH.resolve()), OUTCOMES_JOINS)
        msg = str(ctx.exception).lower()
        self.assertTrue(
            "receipt" in msg or "freeze" in msg or "look_consumed" in msg
        )

    def test_join_141_unique_finite_synthetic(self) -> None:
        rows, outcomes = _synth_141()
        omap = {
            (s, w, h, a): (hs, aws) for s, w, h, a, hs, aws in outcomes
        }
        paired = join_score_only_identity(rows, omap, expected_n=141)
        self.assertEqual(len(paired["candidate"]), 141)
        self.assertEqual(len(set(zip(paired["weeks"], range(141)))), 141)
        self.assertTrue(all(np.isfinite(paired["actual"])))
        # act = 10-7 = 3; cand=1; base=0 → δ = |1-3|-|0-3| = -1
        self.assertAlmostEqual(float(np.mean(paired_delta_mae(
            paired["candidate"], paired["baseline"], paired["actual"]
        ))), -1.0, places=12)

    def test_join_refuses_subset_duplicate_nan(self) -> None:
        rows, outcomes = _synth_141()
        omap = {
            (s, w, h, a): (hs, aws) for s, w, h, a, hs, aws in outcomes
        }
        with self.assertRaises(EvalRefuse):
            join_score_only_identity(rows[:-1], omap, expected_n=141)
        missing = dict(omap)
        del missing[_identity_from_row(rows[0])]
        with self.assertRaises(EvalRefuse):
            join_score_only_identity(rows, missing, expected_n=141)
        dup = list(rows) + [rows[0]]
        with self.assertRaises(EvalRefuse):
            join_score_only_identity(dup, omap, expected_n=142)
        bad = dict(omap)
        key = _identity_from_row(rows[0])
        bad[key] = (float("nan"), 0.0)
        with self.assertRaises(EvalRefuse):
            join_score_only_identity(rows, bad, expected_n=141)

    def test_look_real_complete_path_synthetic_only(self) -> None:
        if not T5055U_FREEZE_PATH.is_file():
            self.skipTest("t5055u freeze not written yet")
        verify_complete_set()
        freeze_sha = sha256_file(T5055U_FREEZE_PATH)
        rows, outcomes = _synth_141()
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            q2s_path, out_path = _write_synth_look_files(tmp, rows, outcomes)
            self.assertNotEqual(out_path.resolve(), OUTCOMES_PIN_PATH.resolve())
            self.assertNotIn("2017", q2s_path.read_text())
            alex, cos = _plant_receipts(tmp, freeze_sha)
            consumed = tmp / "LOOK_CONSUMED.json"
            ctx = LookContext(
                q2s_path=q2s_path,
                outcomes_path=out_path,
                expected_outcomes_sha=sha256_file(out_path),
                expected_q2s_sha=sha256_file(q2s_path),
                expected_n=141,
                alex_path=alex,
                cos_path=cos,
                consumed_path=consumed,
                final_freeze_path=T5055U_FREEZE_PATH,
                write_consumed=True,
            )
            OUTCOMES_JOINS.clear()
            result = look_real(ctx)
            self.assertTrue(result["look_run"])
            self.assertEqual(result["n"], 141)
            self.assertAlmostEqual(result["primary"]["delta_mae"], -1.0, places=12)
            self.assertTrue(consumed.is_file())
            self.assertFalse(
                (PACKET / "phase4" / "artifacts" / "LOOK_CONSUMED.json").exists()
            )
            self.assertIn(str(out_path.resolve()), OUTCOMES_JOINS)
            self.assertNotIn(str(OUTCOMES_PIN_PATH.resolve()), OUTCOMES_JOINS)

    def test_second_look_refused_after_consumed(self) -> None:
        if not T5055U_FREEZE_PATH.is_file():
            self.skipTest("t5055u freeze not written yet")
        freeze_sha = sha256_file(T5055U_FREEZE_PATH)
        rows, outcomes = _synth_141()
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            q2s_path, out_path = _write_synth_look_files(tmp, rows, outcomes)
            alex, cos = _plant_receipts(tmp, freeze_sha)
            consumed = tmp / "LOOK_CONSUMED.json"
            ctx = LookContext(
                q2s_path=q2s_path,
                outcomes_path=out_path,
                expected_outcomes_sha=sha256_file(out_path),
                expected_q2s_sha=sha256_file(q2s_path),
                expected_n=141,
                alex_path=alex,
                cos_path=cos,
                consumed_path=consumed,
                final_freeze_path=T5055U_FREEZE_PATH,
                write_consumed=True,
            )
            look_real(ctx)
            with self.assertRaises(EvalRefuse) as err:
                look_real(ctx)
            self.assertIn("LOOK_CONSUMED", str(err.exception))

    def test_mismatched_receipts_refuse_before_join(self) -> None:
        if not T5055U_FREEZE_PATH.is_file():
            self.skipTest("t5055u freeze not written yet")
        freeze_sha = sha256_file(T5055U_FREEZE_PATH)
        rows, outcomes = _synth_141()
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            q2s_path, out_path = _write_synth_look_files(tmp, rows, outcomes)
            alex, cos = _plant_receipts(tmp, "0" * 64)
            ctx = LookContext(
                q2s_path=q2s_path,
                outcomes_path=out_path,
                expected_outcomes_sha=sha256_file(out_path),
                expected_q2s_sha=sha256_file(q2s_path),
                expected_n=141,
                alex_path=alex,
                cos_path=cos,
                consumed_path=tmp / "LOOK_CONSUMED.json",
                final_freeze_path=T5055U_FREEZE_PATH,
                write_consumed=True,
            )
            OUTCOMES_JOINS.clear()
            with self.assertRaises(EvalRefuse):
                look_real(ctx)
            self.assertEqual(OUTCOMES_JOINS, [])
            # Alex binds live freeze but CoS missing
            alex2, _ = _plant_receipts(tmp, freeze_sha)
            ctx2 = LookContext(
                q2s_path=q2s_path,
                outcomes_path=out_path,
                expected_outcomes_sha=sha256_file(out_path),
                expected_q2s_sha=sha256_file(q2s_path),
                expected_n=141,
                alex_path=alex2,
                cos_path=tmp / "missing_cos.json",
                consumed_path=tmp / "LOOK_CONSUMED.json",
                final_freeze_path=T5055U_FREEZE_PATH,
            )
            with self.assertRaises(EvalRefuse) as err:
                require_look_gates(ctx2)
            self.assertIn("CoS", str(err.exception))
            self.assertEqual(OUTCOMES_JOINS, [])


def _identity_from_row(row: dict) -> tuple[int, int, str, str]:
    return (int(row["season"]), int(row["week"]), str(row["home"]), str(row["away"]))


class HistoryAndFreezeTests(unittest.TestCase):
    def test_parent_and_history_unchanged(self) -> None:
        parent = verify_parent_history()
        hist = verify_history_freeze_a4652323()
        self.assertEqual(
            sha256_file(PACKET / "phase4/artifacts/PROTOCOL_FREEZE.json"),
            PARENT_FREEZE_SHA,
        )
        self.assertEqual(
            sha256_file(PACKET / "evaluator/FINAL_PRELOOK_FREEZE.json"),
            HISTORY_FREEZE_SHA,
        )
        self.assertEqual(sha256_file(PACKET / "phase4/artifacts/IF_MUS_W7W17.json"), IF_MUS_SHA)
        self.assertEqual(sha256_file(PACKET / "phase4/artifacts/q2s_rows_w7w17.json"), Q2S_SHA)
        self.assertEqual(sha256_file(PACKET / "gate2/RECON_MATRIX_W7W17.csv"), MATRIX_SHA)
        self.assertEqual(parent["rows"]["if_mus"]["sha256"], IF_MUS_SHA)
        self.assertEqual(hist["rows"]["q2s_rows"]["sha256"], Q2S_SHA)

    def test_t5055u_freeze_complete_set_when_present(self) -> None:
        if not T5055U_FREEZE_PATH.is_file():
            self.skipTest("t5055u freeze not written yet")
        final = verify_complete_set()
        self.assertFalse(final["parent_rewritten"])
        self.assertFalse(final["look_authorized"])
        self.assertFalse(final["look_run"])
        self.assertEqual(final["parent_freeze"]["sha256"], PARENT_FREEZE_SHA)
        self.assertEqual(final["history_freeze"]["sha256"], HISTORY_FREEZE_SHA)
        self.assertEqual(final["rows"]["if_mus"]["sha256"], IF_MUS_SHA)
        self.assertEqual(final["rows"]["q2s_rows"]["sha256"], Q2S_SHA)
        self.assertIn("evaluator/bootstrap.py", final["files"])
        self.assertIn("evaluator/FINAL_PRELOOK_FREEZE.json", final["files"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
