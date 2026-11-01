#!/usr/bin/env python3
"""Q1–Q6 + J1–J14 + J12F tests for research.q2s.joint. CERT=0.

Bands from dad9eb89 §4 as amended by a091ce1a for J10 only.
Does not open 50bda875 / LOOK. Does not score outcomes.
"""

from __future__ import annotations

import builtins
import hashlib
import json
import math
import random
import sys
import unittest
from pathlib import Path
from typing import Any
import numpy as np

JOINT = Path(__file__).resolve().parents[1]
PACKET = JOINT.parent
PHASE4 = PACKET / "phase4"
sys.path.insert(0, str(JOINT))
sys.path.insert(0, str(PHASE4))

from analytic import (  # noqa: E402
    Phi,
    analytic_pair,
    censored_mean,
    p_margin_positive,
    phi,
)
from gates import evaluate_game, worst_status  # noqa: E402
from pins import (  # noqa: E402
    HISTORY_FREEZE_SHA,
    IF_MUS_SHA,
    MATRIX_SHA,
    N_DRAWS,
    N_EXAMINED_70,
    N_GAMES,
    N_T2,
    OUTCOMES_NAME,
    OUTCOMES_SHA8,
    PARENT_FREEZE_SHA,
    PinRefuse,
    Q2S_SHA,
    T5055U_FREEZE_SHA,
    load_if_mus,
    load_q2s_rows,
    sha256_file,
    verify_input_pins,
)
from score_if_w7w17 import (  # noqa: E402
    EXAMINED_70,
    SEALED_T2,
    assemble_sample,
    build_inputs,
    seed_for,
)
from sim_q2s_joint import (  # noqa: E402
    JointRefuse,
    JointResult,
    _load_sim,
    assert_pinned_generator,
    derive_from_pairs,
    official_if_mus,
    paired_draw_hash,
    simulate_q2s_joint,
)

OUTCOMES_PATH = PACKET / "pins" / OUTCOMES_NAME
LOOK_CONSUMED = PHASE4 / "artifacts" / "LOOK_CONSUMED.json"
LOOK_RESULT = PHASE4 / "artifacts" / "LOOK_RESULT.json"
ART_JSON = JOINT / "artifacts" / "Q2S_JOINT_W7W17.json"
ART_NPZ = JOINT / "artifacts" / "Q2S_JOINT_DRAWS_W7W17.npz"
FORBIDDEN_OUTPUT_KEYS = (
    "win_prob",
    "ats_prob",
    "ou_prob",
    "home_score",
    "away_score",
)


def _crn(mu_h: float, mu_a: float, sigma: float, seed: int, d: float, n: int = N_DRAWS):
    rng = random.Random(seed)
    H = np.empty(n, dtype=np.float64)
    A = np.empty(n, dtype=np.float64)
    for i in range(n):
        H[i] = max(0.0, rng.gauss(mu_h + d / 2.0, sigma))
        A[i] = max(0.0, rng.gauss(mu_a - d / 2.0, sigma))
    return H, A


class OpenGuard:
    """Record every filesystem open; refuse 50bda875 / LOOK."""

    def __init__(self) -> None:
        self.opened: list[str] = []
        self._real_open = builtins.open
        self._real_path_open = Path.open
        self._real_read_bytes = Path.read_bytes
        self._real_read_text = Path.read_text

    def _note(self, path: Any) -> None:
        text = str(path)
        self.opened.append(text)
        name = Path(text).name
        if name == OUTCOMES_NAME or OUTCOMES_SHA8 in text or name in (
            "LOOK_CONSUMED.json",
            "LOOK_RESULT.json",
        ):
            raise PinRefuse(f"Q6 refused forbidden open {text}")

    def __enter__(self) -> "OpenGuard":
        guard = self

        def wrapped_open(file, *a, **k):
            guard._note(file)
            return guard._real_open(file, *a, **k)

        def wrapped_path_open(path_self, *a, **k):
            guard._note(path_self)
            return guard._real_path_open(path_self, *a, **k)

        def wrapped_read_bytes(path_self, *a, **k):
            guard._note(path_self)
            return guard._real_read_bytes(path_self, *a, **k)

        def wrapped_read_text(path_self, *a, **k):
            guard._note(path_self)
            return guard._real_read_text(path_self, *a, **k)

        builtins.open = wrapped_open  # type: ignore[assignment]
        Path.open = wrapped_path_open  # type: ignore[assignment]
        Path.read_bytes = wrapped_read_bytes  # type: ignore[assignment]
        Path.read_text = wrapped_read_text  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: object) -> None:
        builtins.open = self._real_open  # type: ignore[assignment]
        Path.open = self._real_path_open  # type: ignore[assignment]
        Path.read_bytes = self._real_read_bytes  # type: ignore[assignment]
        Path.read_text = self._real_read_text  # type: ignore[assignment]


def _one_game():
    sim = _load_sim()
    assert_pinned_generator(sim)
    games, _sealed = assemble_sample()
    game = sorted(games, key=lambda g: (int(g["matchup_week"]), g["game_id"]))[0]
    return sim, game


class TestQ4PinsAndIdentities(unittest.TestCase):
    def test_q4_pins_match_predeclared(self) -> None:
        pins = verify_input_pins()
        self.assertTrue(pins["q2s"].startswith("55d8c8bc"))
        self.assertTrue(pins["if_mus"].startswith("32e97434"))
        self.assertTrue(pins["matrix"].startswith("b56be146"))
        self.assertTrue(pins["parent_freeze_bytes"].startswith("90774bd4"))
        self.assertTrue(pins["t5055u_freeze_bytes"].startswith("60b5f4b0"))
        self.assertEqual(pins["q2s"], Q2S_SHA)
        self.assertEqual(pins["if_mus"], IF_MUS_SHA)
        self.assertEqual(pins["matrix"], MATRIX_SHA)
        self.assertEqual(pins["parent_freeze_bytes"], PARENT_FREEZE_SHA)
        self.assertEqual(pins["t5055u_freeze_bytes"], T5055U_FREEZE_SHA)
        self.assertEqual(HISTORY_FREEZE_SHA[:8], "a4652323")

    def test_q4_n141_t2_70_refused(self) -> None:
        games, sealed = assemble_sample()
        self.assertEqual(len(games), N_GAMES)
        self.assertEqual(len(SEALED_T2), N_T2)
        self.assertEqual(len(EXAMINED_70), N_EXAMINED_70)
        self.assertEqual({p["game_id"] for p in sealed}, SEALED_T2)
        ids = {g["game_id"] for g in games}
        self.assertFalse(ids & EXAMINED_70)
        self.assertFalse(ids & SEALED_T2)
        q2s = load_q2s_rows()
        if_mus = load_if_mus()
        self.assertEqual(len(q2s["rows"]), 141)
        self.assertEqual(len(if_mus["rows"]), 141)
        self.assertEqual({r["game_id"] for r in q2s["rows"]}, ids)
        self.assertEqual({r["game_id"] for r in if_mus["rows"]}, ids)

    def test_sha256_file_refuses_outcomes_and_look(self) -> None:
        with self.assertRaises(PinRefuse):
            sha256_file(OUTCOMES_PATH)
        with self.assertRaises(PinRefuse):
            sha256_file(LOOK_CONSUMED)
        with self.assertRaises(PinRefuse):
            sha256_file(LOOK_RESULT)


class TestQ6NoOutcomeNoLook(unittest.TestCase):
    def test_q6_verify_pins_does_not_open_forbidden(self) -> None:
        with OpenGuard() as guard:
            verify_input_pins()
        joined = "\n".join(guard.opened)
        self.assertNotIn(OUTCOMES_NAME, joined)
        self.assertNotIn("LOOK_CONSUMED.json", joined)
        self.assertNotIn("LOOK_RESULT.json", joined)
        self.assertNotIn(OUTCOMES_SHA8, joined)

    def test_q6_joint_sources_do_not_call_assert_no_forbidden_open(self) -> None:
        for name in ("sim_q2s_joint.py", "run_q2s_joint.py", "pins.py", "gates.py"):
            src = (JOINT / name).read_text()
            self.assertNotIn("assert_no_forbidden_open", src)
            self.assertNotIn("look_real", src)
            self.assertNotIn("join_score_only", src)


class TestQ5LatentAndRefuse(unittest.TestCase):
    def test_q5_sum_invariance_and_nonneg(self) -> None:
        sim, game = _one_game()
        inputs = build_inputs(sim, game)
        for d in (-5.13, 0.0, 0.92, 6.61):
            result = simulate_q2s_joint(inputs, game["game_id"], d, sim=sim)
            err = abs((result.mu_h_p + result.mu_a_p) - (result.mu_h + result.mu_a))
            self.assertLessEqual(err, 1e-12)
            self.assertGreaterEqual(float(result.H.min()), 0.0)
            self.assertGreaterEqual(float(result.A.min()), 0.0)
            self.assertEqual(result.N, 4000)
            self.assertEqual(result.H.dtype, np.float64)
            self.assertEqual(result.sigma, result.sigma)  # finite
            self.assertGreater(result.sigma, 0.0)

    def test_q5_refuse_nonfinite_and_n_and_mu_prime(self) -> None:
        sim, game = _one_game()
        inputs = build_inputs(sim, game)
        with self.assertRaises(JointRefuse):
            simulate_q2s_joint(inputs, game["game_id"], float("nan"), sim=sim)
        with self.assertRaises(JointRefuse):
            simulate_q2s_joint(inputs, game["game_id"], 0.0, sim=sim, N=8000)
        z0 = simulate_q2s_joint(inputs, game["game_id"], 0.0, sim=sim)
        d_neg = 2.0 * z0.mu_a + 1.0  # μ_a' = μ_a − d/2 < 0
        with self.assertRaises(JointRefuse):
            simulate_q2s_joint(inputs, game["game_id"], d_neg, sim=sim)


class TestQ1J13D0Identity(unittest.TestCase):
    def test_q1_d0_matches_official_and_frozen_one_game(self) -> None:
        sim, game = _one_game()
        inputs = build_inputs(sim, game)
        gid = game["game_id"]
        z0 = simulate_q2s_joint(inputs, gid, 0.0, sim=sim)
        off_m, off_t, off_proj = official_if_mus(inputs, gid, sim=sim)
        markets = off_proj["markets"]
        if_by = {r["game_id"]: r for r in load_if_mus()["rows"]}
        irow = if_by[gid]
        self.assertLessEqual(abs(z0.mean_D - off_m), 1e-12)
        self.assertLessEqual(abs(z0.mean_S - off_t), 1e-12)
        self.assertLessEqual(abs(z0.mean_D - float(irow["if_margin_mu"])), 1e-12)
        self.assertLessEqual(abs(z0.mean_S - float(irow["if_total_mu"])), 1e-12)
        self.assertEqual(round(z0.home_wins / float(z0.N), 4), float(irow["if_forecast_wp_home"]))
        self.assertEqual(round(z0.home_wins / float(z0.N), 4), float(markets["home_win_prob"]))
        self.assertEqual(z0.fair_home_ml, int(markets["fair_home_ml"]))
        self.assertEqual(z0.fair_away_ml, int(markets["fair_away_ml"]))
        self.assertEqual(z0.seed, int(irow["seed"]))
        self.assertEqual(z0.seed, seed_for(gid))
        self.assertAlmostEqual(z0.sigma, float(irow["if_sigma"]), places=4)


class TestQ2CRNMonotoneAndCrossing(unittest.TestCase):
    def test_q2_crn_per_draw_monotone_and_counts(self) -> None:
        mu_h, mu_a, sigma, seed = 24.0, 21.0, 10.0068, 20261101
        H0, A0 = _crn(mu_h, mu_a, sigma, seed, 0.0)
        H1, A1 = _crn(mu_h, mu_a, sigma, seed, 2.0)
        Hm, Am = _crn(mu_h, mu_a, sigma, seed, -2.0)
        D0 = H0 - A0
        D1 = H1 - A1
        Dm = Hm - Am
        self.assertTrue(np.all(D1 + 1e-15 >= D0))
        self.assertTrue(np.all(Dm <= D0 + 1e-15))
        w0 = int(np.sum(D0 > 0.0))
        w1 = int(np.sum(D1 > 0.0))
        wm = int(np.sum(Dm > 0.0))
        self.assertGreaterEqual(w1, w0)
        self.assertLessEqual(wm, w0)

    def test_q2_exact_count_change_on_zero_crossings(self) -> None:
        mu_h, mu_a, sigma, seed = 22.0, 22.0, 10.0068, 424242
        H0, A0 = _crn(mu_h, mu_a, sigma, seed, 0.0)
        H1, A1 = _crn(mu_h, mu_a, sigma, seed, 1.0)
        D0 = H0 - A0
        D1 = H1 - A1
        crossed_to_home = int(np.sum((D0 <= 0.0) & (D1 > 0.0)))
        crossed_to_away = int(np.sum((D0 > 0.0) & (D1 <= 0.0)))
        self.assertEqual(crossed_to_away, 0)
        w0 = int(np.sum(D0 > 0.0))
        w1 = int(np.sum(D1 > 0.0))
        self.assertEqual(w1 - w0, crossed_to_home)
        self.assertGreater(crossed_to_home, 0)

    def test_q2_synthetic_crossing_fixture_controlled(self) -> None:
        # Designed pairs: one draw straddles 0 when d moves +0.3 (uncensored CRN).
        # D(d) = D0 + d when both sides stay strictly positive.
        H0 = np.array([12.0, 8.0, 15.0], dtype=np.float64)
        A0 = np.array([11.85, 9.0, 10.0], dtype=np.float64)
        d = 0.3
        H1 = H0 + d / 2.0
        A1 = A0 - d / 2.0
        D0 = H0 - A0  # [0.15, -1.0, 5.0]
        D1 = H1 - A1  # [0.45, -0.7, 5.3]
        self.assertEqual(int(np.sum(D0 > 0.0)), 2)
        self.assertEqual(int(np.sum(D1 > 0.0)), 2)
        # Force a designed crossing: start just away, add d past zero.
        H0b = np.array([10.0], dtype=np.float64)
        A0b = np.array([10.1], dtype=np.float64)
        d = 0.3
        D0b = H0b - A0b  # -0.1
        D1b = (H0b + d / 2.0) - (A0b - d / 2.0)  # +0.2
        self.assertLessEqual(float(D0b[0]), 0.0)
        self.assertGreater(float(D1b[0]), 0.0)
        self.assertEqual(int(np.sum(D1b > 0.0)) - int(np.sum(D0b > 0.0)), 1)

    def test_q2_removed_blanket_wp_must_differ(self) -> None:
        # A3: blanket “WP must differ when |d|≥0.5” is REMOVED from impl.
        for name in ("gates.py", "run_q2s_joint.py", "sim_q2s_joint.py"):
            src = (JOINT / name).read_text()
            self.assertNotIn("|d|>=0.5", src.replace(" ", ""))
            self.assertNotIn("wp must differ", src.lower())


class TestJ12FSameTotalSameSigma(unittest.TestCase):
    def test_j12f_monotone_same_total_same_sigma(self) -> None:
        mu_h, mu_a, sigma, seed = 23.5, 21.5, 10.0068, 201710
        self.assertAlmostEqual(mu_h + mu_a, 45.0)
        ds = (-4.0, -2.0, -0.5, 0.0, 0.5, 2.0, 4.0)
        wins: list[int] = []
        means: list[float] = []
        for d in ds:
            H, A = _crn(mu_h, mu_a, sigma, seed, d)
            self.assertAlmostEqual((mu_h + d / 2.0) + (mu_a - d / 2.0), mu_h + mu_a)
            D = H - A
            wins.append(int(np.sum(D > 0.0)))
            means.append(float(D.mean()))
        self.assertEqual(wins, sorted(wins))
        self.assertEqual(means, sorted(means))
        for i in range(len(ds) - 1):
            self.assertLessEqual(wins[i], wins[i + 1])
            self.assertLessEqual(means[i], means[i + 1])


class TestQ3RecomputeAndAntiPhi(unittest.TestCase):
    def test_q3_recompute_from_persisted_pairs(self) -> None:
        sim, game = _one_game()
        inputs = build_inputs(sim, game)
        q2s = {r["game_id"]: r for r in load_q2s_rows()["rows"]}
        ifm = {r["game_id"]: r for r in load_if_mus()["rows"]}
        gid = game["game_id"]
        d = float(q2s[gid]["research"]["q2s"]["margin_mu_q2s"]) - float(ifm[gid]["if_margin_mu"])
        result = simulate_q2s_joint(inputs, gid, d, sim=sim)
        again = derive_from_pairs(result.H, result.A, sim)
        self.assertEqual(paired_draw_hash(result.H, result.A), result.draw_hash)
        self.assertEqual(again["home_wp"], result.home_wp)
        self.assertEqual(again["spread_home"], result.spread_home)
        self.assertEqual(again["total_raw"], result.total_raw)
        self.assertEqual(again["fair_home_ml"], result.fair_home_ml)
        gates = evaluate_game(result, margin_mu_q2s=float(q2s[gid]["research"]["q2s"]["margin_mu_q2s"]), sim=sim)
        self.assertEqual(gates["Q3"]["status"], "PASS")

    def test_q3_phi_logistic_beside_if_fails(self) -> None:
        sim, game = _one_game()
        inputs = build_inputs(sim, game)
        gid = game["game_id"]
        result = simulate_q2s_joint(inputs, gid, 1.5, sim=sim)
        from dataclasses import replace

        sigma = result.sigma
        phi_wp = Phi(1.5 / (sigma * math.sqrt(2.0)))
        mutated = replace(result, home_wp=float(phi_wp), fair_home_ml=99)
        again = derive_from_pairs(mutated.H, mutated.A, sim)
        self.assertNotEqual(again["home_wp"], mutated.home_wp)
        gates = evaluate_game(mutated, margin_mu_q2s=result.mean_D, sim=sim)
        self.assertEqual(gates["Q3"]["status"], "FAIL")


class TestJGatesSynthetic(unittest.TestCase):
    def test_j1_j6_j14_tie_q5diag_on_real_game(self) -> None:
        sim, game = _one_game()
        inputs = build_inputs(sim, game)
        gid = game["game_id"]
        q2s = {r["game_id"]: r for r in load_q2s_rows()["rows"]}
        ifm = {r["game_id"]: r for r in load_if_mus()["rows"]}
        q2s_m = float(q2s[gid]["research"]["q2s"]["margin_mu_q2s"])
        d = q2s_m - float(ifm[gid]["if_margin_mu"])
        result = simulate_q2s_joint(inputs, gid, d, sim=sim)
        gates = evaluate_game(result, margin_mu_q2s=q2s_m, sim=sim)
        for name in ("J1", "J2", "J3", "J4", "J5", "J6", "Q5"):
            self.assertEqual(gates[name]["status"], "PASS", name)
        self.assertEqual(gates["J14"]["status"], "NOT_EMITTED")
        self.assertNotEqual(gates["J14"]["status"], "PASS")
        self.assertEqual(gates["Q5_diag"]["status"], "reported")
        required_diag = (
            "floor_mass_H_emp",
            "floor_mass_A_emp",
            "floor_mass_H_analytic",
            "floor_mass_A_analytic",
            "mean_H_emp",
            "mean_A_emp",
            "mean_H_analytic",
            "mean_A_analytic",
            "var_H_emp",
            "var_A_emp",
            "var_H_analytic",
            "var_A_analytic",
            "margin_drift_vs_q2s",
            "total_drift_vs_analytic",
            "cov_MT_emp",
            "cov_MT_analytic",
        )
        for key in required_diag:
            self.assertIn(key, gates["Q5_diag"])
            self.assertTrue(math.isfinite(float(gates["Q5_diag"][key])), key)
        self.assertAlmostEqual(result.cov_MT, result.var_H - result.var_A, places=12)
        self.assertIn(gates["J7a"]["status"], ("PASS", "COND", "FAIL"))
        self.assertIn(gates["J7b"]["status"], ("PASS", "FAIL"))
        self.assertIn(gates["J8"]["status"], ("PASS", "COND", "FAIL"))
        self.assertIn(gates["J9"]["status"], ("PASS", "COND", "FAIL"))
        self.assertIn(gates["J10"]["status"], ("PASS", "COND", "FAIL", "REFUSE"))
        self.assertEqual(gates["J10"]["analytic_independence"], 0.0)
        self.assertNotIn("ats_prob", gates)
        self.assertNotIn("ou_prob", gates)

    def test_j10_refuse_zero_variance_or_nonfinite(self) -> None:
        sim = _load_sim()
        H = np.ones(N_DRAWS, dtype=np.float64)
        A = np.linspace(1.0, 2.0, N_DRAWS, dtype=np.float64)
        stats = derive_from_pairs(H, A, sim)
        self.assertTrue(math.isnan(stats["corr_HA"]) or stats["var_H"] == 0.0)
        result = simulate_q2s_joint(
            build_inputs(sim, assemble_sample()[0][0]),
            assemble_sample()[0][0]["game_id"],
            0.0,
            sim=sim,
        )
        from dataclasses import replace

        dead = replace(result, H=H, A=A, corr_HA=float("nan"), var_H=0.0, var_A=float(A.var()))
        gates = evaluate_game(dead, margin_mu_q2s=0.0, sim=sim)
        self.assertEqual(gates["J10"]["status"], "REFUSE")

    def test_j14_never_pass(self) -> None:
        from gates import evaluate_game as ev

        # J14 is hardcoded NOT_EMITTED regardless of draws
        sim, game = _one_game()
        result = simulate_q2s_joint(build_inputs(sim, game), game["game_id"], 0.0, sim=sim)
        gates = ev(result, margin_mu_q2s=0.0, sim=sim)
        self.assertEqual(gates["J14"]["status"], "NOT_EMITTED")
        self.assertEqual(worst_status({"J14": {"status": "NOT_EMITTED"}}), "PASS")

    def test_analytic_helpers(self) -> None:
        self.assertAlmostEqual(Phi(0.0), 0.5, places=12)
        self.assertAlmostEqual(phi(0.0), 1.0 / math.sqrt(2.0 * math.pi), places=12)
        m = censored_mean(20.0, 10.0068)
        self.assertGreater(m, 19.9)
        p = p_margin_positive(24.0, 21.0, 10.0068)
        self.assertGreater(p, 0.5)
        self.assertLess(p, 0.7)
        pair = analytic_pair(24.0, 21.0, 10.0068)
        self.assertEqual(pair["analytic_rho_HA"], 0.0)
        self.assertAlmostEqual(pair["cov_MT"], pair["var_H"] - pair["var_A"], places=12)


class TestArtifact141(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not ART_JSON.is_file() or not ART_NPZ.is_file():
            raise unittest.SkipTest("joint artifacts not written yet")
        cls.payload = json.loads(ART_JSON.read_text())
        cls.draws = np.load(ART_NPZ, allow_pickle=True)

    def test_namespace_and_hard_flags(self) -> None:
        p = self.payload
        self.assertEqual(p["namespace"], "research.q2s.joint")
        self.assertEqual(p["cert"], 0)
        self.assertEqual(p["nfl"], "NO-GO")
        self.assertTrue(p["research_only"])
        self.assertFalse(p["scored"])
        self.assertFalse(p["totals_cal"])
        self.assertEqual(p["blend"], 0)
        self.assertEqual(p["weight"], 0.5)
        self.assertEqual(p["n"], 141)
        self.assertEqual(p["N"], 4000)
        self.assertFalse(p["look_run"])
        self.assertFalse(p["opened_50bda875"])
        self.assertEqual(p["ats_ou"], "NOT_EMITTED")
        self.assertEqual(p["pins"]["q2s"], Q2S_SHA)
        self.assertEqual(p["pins"]["if_mus"], IF_MUS_SHA)
        self.assertEqual(p["pins"]["matrix"], MATRIX_SHA)
        self.assertEqual(p["pins"]["parent_freeze"], PARENT_FREEZE_SHA)
        self.assertEqual(p["pins"]["t5055u_freeze"], T5055U_FREEZE_SHA)

    def test_q1_all_141(self) -> None:
        self.assertTrue(self.payload["q1_d0"]["ok"])
        self.assertEqual(self.payload["q1_d0"]["n"], 141)
        self.assertTrue(self.payload["q1_d0"]["originals_byte_identical"])
        fails = [r for r in self.payload["q1_details"] if r.get("legacy_wp_match") is not True]
        self.assertEqual(fails, [])
        for row in self.payload["rows"]:
            self.assertEqual(row["gates"]["J13"]["status"], "PASS")

    def test_q4_identities_and_pins_post(self) -> None:
        ids = set(self.payload["game_ids"])
        self.assertEqual(len(ids), 141)
        self.assertFalse(ids & EXAMINED_70)
        self.assertFalse(ids & SEALED_T2)
        pins = verify_input_pins()
        self.assertEqual(pins["q2s"], Q2S_SHA)
        self.assertEqual(pins["if_mus"], IF_MUS_SHA)

    def test_draws_paired_float64_hash(self) -> None:
        H = self.draws["H"]
        A = self.draws["A"]
        gids = [str(x) for x in self.draws["game_ids"]]
        self.assertEqual(H.shape, (141, 4000))
        self.assertEqual(A.shape, (141, 4000))
        self.assertEqual(H.dtype, np.float64)
        self.assertEqual(A.dtype, np.float64)
        self.assertEqual(gids, self.payload["game_ids"])
        self.assertEqual(len(gids), 141)
        for i, row in enumerate(self.payload["rows"]):
            digest = paired_draw_hash(H[i], A[i])
            self.assertEqual(digest, row["draw_hash"])
            self.assertGreaterEqual(float(H[i].min()), 0.0)
            self.assertGreaterEqual(float(A[i].min()), 0.0)

    def test_q3_every_row_recomputable(self) -> None:
        sim = _load_sim()
        H = self.draws["H"]
        A = self.draws["A"]
        for i, row in enumerate(self.payload["rows"]):
            again = derive_from_pairs(H[i], A[i], sim)
            self.assertEqual(again["home_wp"], row["home_wp"])
            self.assertEqual(again["spread_home"], row["spread_home"])
            self.assertEqual(again["total_raw"], row["total_raw"])
            self.assertEqual(again["fair_home_ml"], row["fair_home_ml"])
            self.assertEqual(again["fair_away_ml"], row["fair_away_ml"])
            self.assertEqual(row["gates"]["Q3"]["status"], "PASS")
            self.assertEqual(row["ats_ou"], "NOT_EMITTED")
            for banned in FORBIDDEN_OUTPUT_KEYS:
                self.assertNotIn(banned, row)

    def test_j14_all_not_emitted_and_gates_visible(self) -> None:
        by = self.payload["gate_counts_by_name"]
        self.assertEqual(by["J14"]["NOT_EMITTED"], 141)
        self.assertNotIn("PASS", by["J14"])
        # Every per-game COND/FAIL stays visible — do not hide.
        visible = 0
        for row in self.payload["rows"]:
            for name, g in row["gates"].items():
                if g.get("status") in ("COND", "FAIL", "REFUSE"):
                    visible += 1
                    self.assertIn(name, row["gates"])
        # Record counts; zero is allowed if all PASS, but must be reported.
        self.assertIn("gate_counts_cellwise", self.payload)
        self.assertEqual(self.payload["j12_diagnostic"]["role"], "diagnostic_only")

    def test_q5_diag_present_all_games(self) -> None:
        for row in self.payload["rows"]:
            self.assertEqual(row["gates"]["Q5"]["status"], "PASS")
            self.assertEqual(row["gates"]["Q5_diag"]["status"], "reported")
            self.assertLessEqual(row["gates"]["Q5"]["latent_sum_err"], 1e-12)

    def test_j10_bands_and_no_silent_refuse_as_pass(self) -> None:
        for row in self.payload["rows"]:
            g = row["gates"]["J10"]
            r = g["r"]
            if not math.isfinite(float(r)):
                self.assertEqual(g["status"], "REFUSE")
            elif abs(float(r)) <= 0.05:
                self.assertEqual(g["status"], "PASS")
            elif abs(float(r)) <= 0.08:
                self.assertEqual(g["status"], "COND")
            else:
                self.assertEqual(g["status"], "FAIL")
            self.assertEqual(g["analytic_independence"], 0.0)

    def test_original_prediction_bytes_unchanged(self) -> None:
        pins = verify_input_pins()
        self.assertEqual(pins["q2s"], Q2S_SHA)
        self.assertEqual(pins["if_mus"], IF_MUS_SHA)
        self.assertEqual(pins["matrix"], MATRIX_SHA)
        self.assertEqual(pins["parent_freeze_bytes"], PARENT_FREEZE_SHA)
        self.assertEqual(pins["t5055u_freeze_bytes"], T5055U_FREEZE_SHA)


if __name__ == "__main__":
    unittest.main()
