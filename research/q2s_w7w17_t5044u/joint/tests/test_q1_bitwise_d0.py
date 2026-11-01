#!/usr/bin/env python3
"""t5067u — Q1/J13 bitwise H0/A0 vs d=0 joint replay.

Traces unmodified pinned IF gauss (6ca03716 / 52d9e909 / a0051cc4),
floors in original H/A order, compares float64 arrays and draw hashes
to simulate_q2s_joint(..., d=0) for all 141 games.

Does not regenerate joint artifacts. Does not open 50bda875 / LOOK.
CERT=0. Research-test only.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

JOINT = Path(__file__).resolve().parents[1]
PACKET = JOINT.parent
PHASE4 = PACKET / "phase4"
sys.path.insert(0, str(JOINT))
sys.path.insert(0, str(PHASE4))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from if_draw_trace import trace_official_if_floored_pairs  # noqa: E402
from pins import (  # noqa: E402
    IF_MUS_SHA,
    N_DRAWS,
    N_GAMES,
    Q2S_SHA,
    load_if_mus,
    sha256_file,
    verify_input_pins,
)
from score_if_w7w17 import assemble_sample, build_inputs, seed_for  # noqa: E402
from sim_q2s_joint import (  # noqa: E402
    _load_sim,
    assert_pinned_generator,
    paired_draw_hash,
    simulate_q2s_joint,
)

ART_JSON = JOINT / "artifacts" / "Q2S_JOINT_W7W17.json"
ART_NPZ = JOINT / "artifacts" / "Q2S_JOINT_DRAWS_W7W17.npz"
ART_JSON_SHA = "5076421ef1fba943df9c1e8eeaefede4f7a7e30a36ae2ed792a7f2bc295c4e27"
ART_NPZ_SHA = "ce6b1244895df065ea8428851261becbb8012c7379d6184770116a7dfbcb0fc5"


def _legacy_summary_ok(z0, meta: dict, irow: dict) -> bool:
    raw_wp = z0.home_wins / float(z0.N)
    legacy_wp = round(raw_wp, 4)
    return all(
        [
            abs(z0.mean_D - float(meta["official_margin_mu"])) <= 1e-12,
            abs(z0.mean_S - float(meta["official_total_mu"])) <= 1e-12,
            abs(z0.mean_D - float(irow["if_margin_mu"])) <= 1e-12,
            abs(z0.mean_S - float(irow["if_total_mu"])) <= 1e-12,
            legacy_wp == float(irow["if_forecast_wp_home"]),
            legacy_wp == float(meta["official_wp_home"]),
            z0.fair_home_ml == int(meta["official_ml_home"]),
            z0.fair_away_ml == int(meta["official_ml_away"]),
        ]
    )


class TestPriorArtifactsUnregenerated(unittest.TestCase):
    def test_joint_outputs_still_5076421e_ce6b1244(self) -> None:
        self.assertEqual(sha256_file(ART_JSON), ART_JSON_SHA)
        self.assertEqual(sha256_file(ART_NPZ), ART_NPZ_SHA)
        self.assertTrue(ART_JSON_SHA.startswith("5076421e"))
        self.assertTrue(ART_NPZ_SHA.startswith("ce6b1244"))
        pins = verify_input_pins()
        self.assertEqual(pins["q2s"], Q2S_SHA)
        self.assertEqual(pins["if_mus"], IF_MUS_SHA)


class TestQ1BitwiseD0(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sim = _load_sim()
        assert_pinned_generator(cls.sim)
        games, _sealed = assemble_sample()
        cls.games = sorted(games, key=lambda g: (int(g["matchup_week"]), g["game_id"]))
        cls.if_by = {r["game_id"]: r for r in load_if_mus()["rows"]}
        if len(cls.games) != N_GAMES:
            raise AssertionError(f"assembled {len(cls.games)} != {N_GAMES}")

    def test_one_game_traced_if_equals_d0_replay(self) -> None:
        game = self.games[0]
        gid = game["game_id"]
        inputs = build_inputs(self.sim, game)
        H0, A0, meta = trace_official_if_floored_pairs(self.sim, inputs, gid)
        z0 = simulate_q2s_joint(inputs, gid, 0.0, sim=self.sim)
        self.assertEqual(H0.dtype, np.float64)
        self.assertEqual(A0.dtype, np.float64)
        self.assertEqual(H0.shape, (N_DRAWS,))
        self.assertTrue(np.array_equal(H0, z0.H))
        self.assertTrue(np.array_equal(A0, z0.A))
        self.assertEqual(H0.tobytes(), z0.H.tobytes())
        self.assertEqual(A0.tobytes(), z0.A.tobytes())
        self.assertEqual(paired_draw_hash(H0, A0), z0.draw_hash)
        self.assertTrue(_legacy_summary_ok(z0, meta, self.if_by[gid]))
        self.assertEqual(z0.seed, seed_for(gid))

    def test_all_141_exact_array_and_hash_separate_from_summary(self) -> None:
        array_pass = 0
        hash_pass = 0
        summary_pass = 0
        array_fail: list[str] = []
        hash_fail: list[str] = []
        summary_fail: list[str] = []
        for game in self.games:
            gid = game["game_id"]
            inputs = build_inputs(self.sim, game)
            H0, A0, meta = trace_official_if_floored_pairs(self.sim, inputs, gid)
            z0 = simulate_q2s_joint(inputs, gid, 0.0, sim=self.sim)
            exact = bool(np.array_equal(H0, z0.H) and np.array_equal(A0, z0.A))
            same_hash = paired_draw_hash(H0, A0) == z0.draw_hash
            summary = _legacy_summary_ok(z0, meta, self.if_by[gid])
            if exact:
                array_pass += 1
            else:
                array_fail.append(gid)
            if same_hash:
                hash_pass += 1
            else:
                hash_fail.append(gid)
            if summary:
                summary_pass += 1
            else:
                summary_fail.append(gid)
        # Report separately — do not treat summary PASS as bitwise PASS.
        self.assertEqual(array_pass, N_GAMES, f"exact-array FAIL {array_fail}")
        self.assertEqual(hash_pass, N_GAMES, f"hash FAIL {hash_fail}")
        self.assertEqual(summary_pass, N_GAMES, f"legacy-summary FAIL {summary_fail}")
        self.assertEqual(array_fail, [])
        self.assertEqual(hash_fail, [])
        self.assertEqual(summary_fail, [])

    def test_q6_trace_does_not_hash_outcomes_path(self) -> None:
        src = (Path(__file__).parent / "if_draw_trace.py").read_text()
        self.assertNotIn("assert_no_forbidden_open", src)
        self.assertNotIn("look_real", src)
        self.assertNotIn("outcomes_2013_2022_score_only.csv", src)


if __name__ == "__main__":
    unittest.main()
