#!/usr/bin/env python3
"""t5033u mechanical guards: B1, corrected B2, B3–B8.

CERT=0 · DEV_RESEARCH · research-consumed only.
#684 2013 fixtures, if touched, are mechanical-only — never outcome scoring.
"""

from __future__ import annotations

import ast
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emit_q2s_adapter import (  # noqa: E402
    FORBIDDEN_OUTPUT_KEYS,
    SEALED_A_Q2,
    SEALED_ASOF_RULE,
    SEALED_B_Q2,
    SEALED_CONFIG_SHA,
    SEALED_FIT_SHA,
    SEALED_GAMES_PIN,
    SEALED_GAMES_SHA,
    SEALED_IF_TIP,
    SEALED_OUTCOMES_SHA,
    SEALED_SCORE_RESULTS_SHA,
    AdapterRefuse,
    emit_adapter,
    load_json_object,
    verify_pins,
)
from q2pb.constants import DEV_SEASONS, HISTORY_ONLY_SEASONS  # noqa: E402
from q2pb.data import sha256_file  # noqa: E402
from q2s.blend import (  # noqa: E402
    Q2S_WEIGHT,
    BlendRefuse,
    coordinate_reverse_same_game,
    margin_mu_q2s,
    venue_swap_q2_pm,
)
from q2s.bootstrap import BOOT_B, BOOT_SEED, paired_delta_mae, paired_game_bootstrap_ci  # noqa: E402
from q2s.coverage import CoverageRefuse, prove_fit_exclusion  # noqa: E402

GAMES = ROOT / "data" / "games_4fe1cdd7.csv"
OUTCOMES = ROOT / "data" / "outcomes_2013_2022_score_only.csv"
FROZEN = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.json"
FROZEN_MD = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.md"
SCORE = ROOT / "pins" / "t4910u" / "SCORE_RESULTS.json"
MANIFEST = ROOT / "pins" / "t4910u" / "SAMPLE_MANIFEST_70.json"
ADAPTER = ROOT / "emit_q2s_adapter.py"
COMPARE = ROOT / "compare_appendix_o.py"

FORECAST_PATH_FILES = (
    Path("services/model-service/src/services/nfl_simulator.py"),
    Path("services/model-service/src/routes/nfl.py"),
    Path("services/model-service/src/tasks.py"),
    Path("services/model-service/src/services/nfl_handicap_ledger/schema.py"),
    Path("data/ops/nfl-hist-diag-score-70-t4910u/score_t4910u.py"),
    Path("research/q2_phase_b_t5009u/emit_q2_asof_sidecar.py"),
)

FORBIDDEN_IMPORT_NEEDLES = (
    "nfl_simulator",
    "simulate_nfl_game",
    "simulate_nfl_game_independent_fair",
    "run_nfl_market_simulations",
    "NflGameInputs",
    "nfl_handicap_ledger",
    "independent_fair_mus",
    "score_t4910u",
    "emit_q2_asof_sidecar",
)

REPO_ROOT = ROOT.parents[1]


def _emit(**kwargs):
    defaults = dict(
        games_path=GAMES,
        outcomes_path=OUTCOMES,
        frozen_path=FROZEN,
        frozen_md_path=FROZEN_MD,
        score_path=SCORE,
        manifest_path=MANIFEST,
        write_files=False,
    )
    defaults.update(kwargs)
    return emit_adapter(**defaults)


class TestB1BlendFormula(unittest.TestCase):
    """B1 — two complete margins; w=0.5 predeclared; no extra HFA."""

    def test_blend_is_half_if_plus_half_q2(self) -> None:
        self.assertEqual(Q2S_WEIGHT, 0.5)
        self.assertEqual(margin_mu_q2s(4.0, 2.0), 3.0)
        self.assertEqual(margin_mu_q2s(-1.0, 5.0), 2.0)

    def test_extra_hfa_refused(self) -> None:
        with self.assertRaises(BlendRefuse):
            margin_mu_q2s(1.0, 2.0, extra_hfa=0.1)

    def test_alternate_weight_refused(self) -> None:
        with self.assertRaises(BlendRefuse):
            margin_mu_q2s(1.0, 2.0, w=0.4)

    def test_non_finite_refused(self) -> None:
        with self.assertRaises(BlendRefuse):
            margin_mu_q2s(float("nan"), 1.0)


class TestB2CorrectedSymmetry(unittest.TestCase):
    """B2 CORRECTED — do not use the old antisymmetric venue-swap test.

    Same-game reporting-coordinate reverse flips the whole complete margin.
    Venue swap is a different event: keep the home intercept; a+b*d vs a−b*d
    sum to 2a.
    """

    def test_same_game_coordinate_reverse_flips_complete_margins(self) -> None:
        if_m = 3.5
        q2_m = 1.5
        blended = margin_mu_q2s(if_m, q2_m)
        flipped = margin_mu_q2s(
            coordinate_reverse_same_game(if_m),
            coordinate_reverse_same_game(q2_m),
        )
        self.assertEqual(flipped, -blended)
        self.assertEqual(coordinate_reverse_same_game(blended), -blended)

    def test_venue_swap_keeps_q2_intercept_sum_2a(self) -> None:
        d = 2.0
        orig, swapped = venue_swap_q2_pm(SEALED_A_Q2, SEALED_B_Q2, d)
        self.assertAlmostEqual(orig, SEALED_A_Q2 + SEALED_B_Q2 * d)
        self.assertAlmostEqual(swapped, SEALED_A_Q2 - SEALED_B_Q2 * d)
        self.assertAlmostEqual(orig + swapped, 2.0 * SEALED_A_Q2)
        # Old antisymmetric test would require swapped == -orig. That is WRONG
        # for an intercept-bearing forecast.
        self.assertNotAlmostEqual(swapped, -orig)
        self.assertAlmostEqual(swapped + orig, 2.0 * SEALED_A_Q2)

    def test_venue_swap_if_complete_margin_is_not_forced_antisymmetric(self) -> None:
        """IF complete margin may include HFA; venue swap ≠ coordinate reverse."""
        if_with_hfa = 2.0  # already a complete home−away margin
        q2_orig, q2_swap = venue_swap_q2_pm(SEALED_A_Q2, SEALED_B_Q2, 1.25)
        blend_orig = margin_mu_q2s(if_with_hfa, q2_orig)
        # Different event: keep a home intercept on the IF side as well
        # (do not force -if). Blend of swapped Q2 + same-home-intercept IF
        # is a different game, not -blend_orig.
        blend_swap = margin_mu_q2s(if_with_hfa, q2_swap)
        self.assertNotAlmostEqual(blend_swap, -blend_orig)


class TestB3IsolationUnchangedBaseline(unittest.TestCase):
    """B3 — baseline IF mus/sigma/MC draws unchanged; research.q2s.* only."""

    def test_emitted_rows_copy_if_fields_and_do_not_overwrite(self) -> None:
        result = _emit()
        self.assertFalse(result.refused, result.blocker)
        self.assertEqual(len(result.rows), 70)
        score = json.loads(SCORE.read_text())
        by_id = {r["game_id"]: r for r in score["rows"]}
        for row in result.rows:
            sealed = by_id[row["game_id"]]
            bl = row["baseline"]
            q2s = row["research"]["q2s"]
            self.assertEqual(bl["if_margin_mu"], sealed["forecast_margin"])
            self.assertEqual(bl["if_total_mu"], sealed["forecast_total"])
            self.assertEqual(bl["if_sigma"], sealed["if_sigma"])
            self.assertTrue(bl["unchanged"])
            self.assertTrue(bl["mc_draws_unchanged"])
            self.assertTrue(bl["no_candidate_probabilities"])
            self.assertNotIn("win_prob", q2s)
            self.assertNotIn("ats_prob", q2s)
            self.assertNotIn("ou_prob", q2s)
            self.assertNotIn("margin_mu", row)
            self.assertNotIn("total_mu", row)
            self.assertNotIn("sigma", row)
            extra = set(q2s) & set(FORBIDDEN_OUTPUT_KEYS)
            self.assertEqual(extra, set())
            expected = 0.5 * bl["if_margin_mu"] + 0.5 * q2s["q2_pm_new"]
            self.assertTrue(math.isclose(q2s["margin_mu_q2s"], expected, abs_tol=1e-12))
            # Isolation: IF copy != research field object
            self.assertIsNot(bl, q2s)


class TestB4PinRefuse(unittest.TestCase):
    """B4 — pin sha refuse-on-mismatch."""

    def test_sealed_pins_match(self) -> None:
        cfg = load_json_object(FROZEN)
        pins = verify_pins(GAMES, OUTCOMES, cfg, FROZEN_MD, SCORE, MANIFEST)
        self.assertEqual(pins.games_sha256, SEALED_GAMES_SHA)
        self.assertEqual(pins.outcomes_sha256, SEALED_OUTCOMES_SHA)
        self.assertEqual(pins.score_results_sha256, SEALED_SCORE_RESULTS_SHA)
        self.assertTrue(pins.score_results_sha256.startswith("2b9f302e"))
        self.assertEqual(pins.fit_sha, SEALED_FIT_SHA)
        self.assertTrue(pins.fit_sha.startswith("70db070d"))
        self.assertEqual(pins.config_sha, SEALED_CONFIG_SHA)
        self.assertTrue(pins.config_sha.startswith("aa2b47b3"))
        self.assertEqual(pins.asof_rule, SEALED_ASOF_RULE)
        self.assertTrue(pins.frozen_md_sha256.startswith("28c582a1"))
        self.assertEqual(pins.a_q2, SEALED_A_Q2)
        self.assertEqual(pins.b_q2, SEALED_B_Q2)

    def test_wrong_fit_sha_refuses(self) -> None:
        cfg = dict(load_json_object(FROZEN))
        cfg["fit_object_sha256"] = "deadbeef" + cfg["fit_object_sha256"][8:]
        with self.assertRaises(AdapterRefuse):
            verify_pins(GAMES, OUTCOMES, cfg, FROZEN_MD, SCORE, MANIFEST)

    def test_wrong_score_results_sha_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dirty = Path(tmp) / "SCORE_RESULTS.json"
            payload = json.loads(SCORE.read_text())
            payload["n"] = 69
            dirty.write_text(json.dumps(payload))
            cfg = load_json_object(FROZEN)
            with self.assertRaises(AdapterRefuse) as ctx:
                verify_pins(GAMES, OUTCOMES, cfg, FROZEN_MD, dirty, MANIFEST)
            self.assertIn("2b9f302e", str(ctx.exception))


class TestB5AsOfLeakage(unittest.TestCase):
    """B5 — strict prior-game cutoffs; reuse assert_asof_leakage."""

    def test_asof_n_is_prior_2017_only(self) -> None:
        result = _emit()
        self.assertFalse(result.refused, result.blocker)
        week2 = [r for r in result.rows if r["week"] == 2]
        self.assertGreaterEqual(len(week2), 1)
        for row in week2:
            # 2017 W2 as-of can only see W1 (and not same-kickoff W2).
            self.assertLess(row["research"]["q2s"]["q2_n_asof_games"], 32)
            self.assertGreaterEqual(row["research"]["q2s"]["q2_n_asof_games"], 1)
            self.assertEqual(row["research"]["q2s"]["q2_asof_rule"], "cf514078")


class TestB6NoCandidateProbabilities(unittest.TestCase):
    """B6 — no candidate win/ATS/OU from unchanged draws."""

    def test_compare_source_forbids_probability_claims(self) -> None:
        src = COMPARE.read_text()
        ast.parse(src)
        self.assertIn("no candidate win/ats/ou", src.lower())
        self.assertIn("win_prob", src)
        self.assertNotIn("norm.cdf", src)
        self.assertNotIn("simulate_nfl_game", src)


class TestB7FitExclusion(unittest.TestCase):
    """B7 — prove the 70 targets were excluded from a_q2/b_q2 (70db070d)."""

    def test_2017_is_history_only_never_fit(self) -> None:
        self.assertEqual(HISTORY_ONLY_SEASONS, (2017,))
        self.assertEqual(DEV_SEASONS, (2013, 2014, 2015, 2016))

    def test_prove_fit_exclusion_on_manifest(self) -> None:
        frozen = load_json_object(FROZEN)
        score = json.loads(SCORE.read_text())
        targets = [
            {
                "game_id": r["game_id"],
                "season": 2017,
                "week": r["matchup_week"],
                "home": r["home_team"],
                "away": r["away_team"],
            }
            for r in score["rows"]
        ]
        proof = prove_fit_exclusion(targets, frozen, history_game_ids_dev=set())
        self.assertTrue(proof["ok"])
        self.assertEqual(proof["n_targets"], 70)
        self.assertTrue(proof["fit_sha"].startswith("70db070d"))
        self.assertEqual(proof["n_fit"], 960)

    def test_leaked_dev_id_refuses(self) -> None:
        frozen = load_json_object(FROZEN)
        targets = [{"game_id": "2017_02_ARI_IND", "season": 2017}]
        with self.assertRaises(CoverageRefuse):
            prove_fit_exclusion(
                targets, frozen, history_game_ids_dev={"2017_02_ARI_IND"}
            )


class TestB8FailClosedCoverage(unittest.TestCase):
    """B8 — missing coverage refuses; no synthetic fallback / silent subset."""

    def test_truncated_manifest_refuses_before_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            man = json.loads(MANIFEST.read_text())
            man["n"] = 69
            man["games"] = man["games"][:69]
            path = Path(tmp) / "SAMPLE_MANIFEST_70.json"
            path.write_text(json.dumps(man))
            with self.assertRaises(AdapterRefuse):
                _emit(manifest_path=path)

    def test_complete_70_or_refuse_flag(self) -> None:
        result = _emit()
        if result.refused:
            self.assertEqual(result.rows, [])
            self.assertTrue(result.blocker)
        else:
            self.assertEqual(len(result.rows), 70)
            self.assertEqual(result.missing, [])


class TestSourceGateAndIsolationAST(unittest.TestCase):
    def test_score_results_control_sha(self) -> None:
        self.assertEqual(sha256_file(SCORE), SEALED_SCORE_RESULTS_SHA)
        payload = json.loads(SCORE.read_text())
        self.assertEqual(payload["n"], 70)
        self.assertEqual(payload["if_tip"], SEALED_IF_TIP)

    def test_adapter_does_not_import_forecast_path(self) -> None:
        tree = ast.parse(ADAPTER.read_text())
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        blob = " ".join(imported)
        for needle in FORBIDDEN_IMPORT_NEEDLES:
            self.assertNotIn(needle, blob)

    def test_repo_forecast_paths_untouched_on_this_branch_tree(self) -> None:
        """Diff isolation: those files are not part of this research tree."""
        for rel in FORECAST_PATH_FILES:
            # Sealed callers are not copied into this package.
            self.assertFalse((ROOT / rel.name).exists())

    def test_684_accept_note_present(self) -> None:
        note = (ROOT / "authority" / "ANNOTATE_684_ACCEPT_9982d42f.md").read_text()
        self.assertIn("9982d42f", note)
        self.assertIn("undisturbed", note.lower())
        self.assertIn("mechanical", note.lower())

    def test_retro_label_on_rows(self) -> None:
        result = _emit()
        self.assertFalse(result.refused, result.blocker)
        for row in result.rows:
            self.assertIn("RETRO_FIT", row["label"])
            self.assertIn("DEV_RESEARCH", row["label"])


class TestBootstrapMechanics(unittest.TestCase):
    def test_seed_and_b_frozen(self) -> None:
        self.assertEqual(BOOT_B, 10_000)
        self.assertEqual(BOOT_SEED, 20261101)

    def test_delta_negative_means_point_improvement(self) -> None:
        deltas = paired_delta_mae([0.0, 0.0], [2.0, 2.0], [0.0, 0.0])
        self.assertTrue((deltas < 0).all())
        ci = paired_game_bootstrap_ci(deltas, B=200, seed=BOOT_SEED)
        self.assertLess(ci["ci_hi"], 0.0)


if __name__ == "__main__":
    unittest.main()
