#!/usr/bin/env python3
"""t5075u G2 — identity / pin / Alex-GO / no-regen guards.

Synthetic fixtures for outcome joins. Real 50bda875 is checksummed only.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

G2 = Path(__file__).resolve().parents[1]
PACKET = G2.parent
sys.path.insert(0, str(G2))

from constants import (  # noqa: E402
    IF_MUS_PATH,
    IF_MUS_SHA256,
    JOINT_JSON_PATH,
    JOINT_JSON_SHA256,
    JOINT_NPZ_PATH,
    JOINT_NPZ_SHA256,
    LOOK_CONSUMED_PATH,
    LOOK_CONSUMED_SHA256,
    LOOK_TIP,
    ACCEPT_TIP,
    N_GAMES,
    OUTCOMES_PATH,
    OUTCOMES_SHA256,
    Q2S_ROWS_PATH,
    Q2S_ROWS_SHA256,
    UNAVAILABLE,
)
from freeze import build_manifest, hash_inputs  # noqa: E402
from hashutil import sha256_file  # noqa: E402
from identities import (  # noqa: E402
    IdentityRefuse,
    assert_eligible_identity,
    assert_not_q2_eval_reopen,
    extract_forecast_identities,
    identity_boundary_cite,
    load_forecast_identities_from_disk,
    require_exact_141,
)
from load import (  # noqa: E402
    LoadRefuse,
    if_distribution_status,
    parse_score_only_restricted,
)
from metrics import refuse_if_distribution_regen  # noqa: E402
from run import DiagnosticRefuse, require_alex_go  # noqa: E402


def _sha_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _synth_identities(n: int = 141, season: int = 2099):
    recs = []
    counts = {w: 12 for w in range(7, 17)}
    counts[17] = 21
    i = 0
    for week, n_w in counts.items():
        for _ in range(n_w):
            recs.append(
                {
                    "game_id": f"{season}_{week:02d}_A{i:03d}_H{i:03d}",
                    "season": season,
                    "week": week,
                    "home": f"H{i:03d}",
                    "away": f"A{i:03d}",
                }
            )
            i += 1
            if i >= n:
                return recs
    return recs


def _write_outcomes(path: Path, rows, extra=None) -> str:
    fieldnames = ["season", "week", "home", "away", "home_score", "away_score"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for rec in rows:
            writer.writerow(
                {
                    "season": rec["season"],
                    "week": rec["week"],
                    "home": rec["home"],
                    "away": rec["away"],
                    "home_score": rec.get("home_score", 21.0),
                    "away_score": rec.get("away_score", 17.0),
                }
            )
        for rec in extra or []:
            writer.writerow(rec)
    return sha256_file(path)


class TestPinChecksumsOnThisBranch(unittest.TestCase):
    def test_five_pins_and_look_consumed(self) -> None:
        inputs = hash_inputs()
        self.assertTrue(inputs["joint_json"]["sha256"].startswith("5076421e"))
        self.assertTrue(inputs["joint_npz"]["sha256"].startswith("ce6b1244"))
        self.assertTrue(inputs["if_mus"]["sha256"].startswith("32e97434"))
        self.assertTrue(inputs["q2s_rows"]["sha256"].startswith("55d8c8bc"))
        self.assertTrue(inputs["outcomes_score_only"]["sha256"].startswith("50bda875"))
        self.assertTrue(inputs["look_consumed"]["sha256"].startswith("013d270a"))
        self.assertEqual(inputs["outcomes_score_only"]["parse"], "checksum_only")
        self.assertEqual(_sha_bytes(JOINT_JSON_PATH), JOINT_JSON_SHA256)
        self.assertEqual(_sha_bytes(JOINT_NPZ_PATH), JOINT_NPZ_SHA256)
        self.assertEqual(_sha_bytes(IF_MUS_PATH), IF_MUS_SHA256)
        self.assertEqual(_sha_bytes(Q2S_ROWS_PATH), Q2S_ROWS_SHA256)
        self.assertEqual(_sha_bytes(OUTCOMES_PATH), OUTCOMES_SHA256)
        self.assertEqual(_sha_bytes(LOOK_CONSUMED_PATH), LOOK_CONSUMED_SHA256)

    def test_forecast_identities_are_141_2017_w7w17(self) -> None:
        recs = load_forecast_identities_from_disk()
        self.assertEqual(len(recs), N_GAMES)
        self.assertEqual(len({r["game_id"] for r in recs}), N_GAMES)
        self.assertTrue(all(r["season"] == 2017 for r in recs))
        self.assertEqual({r["week"] for r in recs}, set(range(7, 18)))
        self.assertEqual(recs[0]["game_id"], "2017_07_ARI_LA")

    def test_if_mus_has_no_draws(self) -> None:
        payload = json.loads(IF_MUS_PATH.read_text())
        self.assertEqual(if_distribution_status(payload), UNAVAILABLE)
        self.assertNotIn("H", payload)
        self.assertNotIn("A", payload)
        self.assertNotIn("draws", payload)
        row0 = payload["rows"][0]
        self.assertIn("if_margin_mu", row0)
        self.assertNotIn("H", row0)


class TestIdentityGuards(unittest.TestCase):
    def test_other_season_refused(self) -> None:
        with self.assertRaises(IdentityRefuse):
            assert_eligible_identity((2016, 7, "NE", "NYJ"), context="test")
        with self.assertRaises(IdentityRefuse):
            assert_eligible_identity((2018, 7, "NE", "NYJ"), context="eval")
        with self.assertRaises(IdentityRefuse):
            assert_eligible_identity((2024, 7, "NE", "NYJ"), context="prot")
        with self.assertRaises(IdentityRefuse):
            assert_eligible_identity((2025, 1, "NE", "NYJ"), context="prot")

    def test_week_outside_and_n_mismatch(self) -> None:
        with self.assertRaises(IdentityRefuse):
            assert_eligible_identity((2017, 6, "NE", "NYJ"), context="w6")
        recs = _synth_identities(140)
        with self.assertRaises(IdentityRefuse):
            require_exact_141(
                [(r["season"], r["week"], r["home"], r["away"]) for r in recs],
                context="n140",
            )

    def test_q2_eval_reopen_refused(self) -> None:
        assert_not_q2_eval_reopen(False)
        with self.assertRaises(IdentityRefuse):
            assert_not_q2_eval_reopen(True)

    def test_forecast_triple_mismatch_refused(self) -> None:
        joint = json.loads(JOINT_JSON_PATH.read_text())
        q2s = json.loads(Q2S_ROWS_PATH.read_text())
        if_mus = json.loads(IF_MUS_PATH.read_text())
        q2s["rows"][0]["home"] = "XXX"
        with self.assertRaises(IdentityRefuse):
            extract_forecast_identities(joint, q2s, if_mus)

    def test_cited_boundary_no_look_invoke(self) -> None:
        cite = identity_boundary_cite()
        self.assertEqual(cite["look_tip"], LOOK_TIP)
        self.assertEqual(cite["accept_tip"], ACCEPT_TIP)
        self.assertIn("CLOSED", cite["q2_eval"])
        self.assertIn("No LOOK invocation", cite["note"])


class TestRestrictedOutcomesParse(unittest.TestCase):
    def test_other_season_rows_ignored_eligible_kept(self) -> None:
        recs = _synth_identities(141, season=2017)
        extra = [
            {
                "season": 2016,
                "week": 7,
                "home": "ZZ",
                "away": "YY",
                "home_score": 99,
                "away_score": 0,
            },
            {
                "season": 2018,
                "week": 10,
                "home": "AA",
                "away": "BB",
                "home_score": 1,
                "away_score": 2,
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            digest = _write_outcomes(path, recs, extra=extra)
            kept = parse_score_only_restricted(
                path, expected_sha=digest, eligible=recs
            )
            self.assertEqual(len(kept), 141)
            self.assertNotIn((2016, 7, "ZZ", "YY"), kept)
            self.assertNotIn((2018, 10, "AA", "BB"), kept)

    def test_eligible_other_season_refused(self) -> None:
        recs = _synth_identities(141, season=2016)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            digest = _write_outcomes(path, recs)
            with self.assertRaises(IdentityRefuse):
                parse_score_only_restricted(path, expected_sha=digest, eligible=recs)

    def test_missing_eligible_refused(self) -> None:
        recs = _synth_identities(141, season=2017)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            digest = _write_outcomes(path, recs[:-1])
            with self.assertRaises(LoadRefuse):
                parse_score_only_restricted(path, expected_sha=digest, eligible=recs)

    def test_wrong_sha_refused(self) -> None:
        recs = _synth_identities(141, season=2017)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            _write_outcomes(path, recs)
            with self.assertRaises(LoadRefuse):
                parse_score_only_restricted(
                    path, expected_sha="0" * 64, eligible=recs
                )

    def test_extra_columns_refused(self) -> None:
        recs = _synth_identities(141, season=2017)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            header = "season,week,home,away,home_score,away_score,epa\n"
            body = "".join(
                f"{r['season']},{r['week']},{r['home']},{r['away']},10,7,1\n" for r in recs
            )
            path.write_text(header + body)
            digest = sha256_file(path)
            with self.assertRaises(LoadRefuse):
                parse_score_only_restricted(
                    path,
                    expected_sha=digest,
                    eligible=recs,
                )


class TestAlexGoAndNoLook(unittest.TestCase):
    def test_missing_go_stops(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.json"
            with self.assertRaises(DiagnosticRefuse) as ctx:
                require_alex_go(manifest_sha="abc", go_path=missing)
            self.assertIn("STOP", str(ctx.exception))

    def test_mismatched_and_unauthorized_go(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ALEX.json"
            path.write_text(
                json.dumps(
                    {
                        "binds_frozen_manifest_sha256": "ffff",
                        "authorizes_g2_diagnostic_execute": True,
                        "cert": 0,
                    }
                )
            )
            with self.assertRaises(DiagnosticRefuse):
                require_alex_go(manifest_sha="abcd", go_path=path)
            path.write_text(
                json.dumps(
                    {
                        "binds_frozen_manifest_sha256": "abcd",
                        "authorizes_g2_diagnostic_execute": False,
                        "cert": 0,
                    }
                )
            )
            with self.assertRaises(DiagnosticRefuse):
                require_alex_go(manifest_sha="abcd", go_path=path)

    def test_matching_go_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ALEX.json"
            path.write_text(
                json.dumps(
                    {
                        "binds_frozen_manifest_sha256": "abcd" * 16,
                        "authorizes_g2_diagnostic_execute": True,
                        "cert": 0,
                    }
                )
            )
            rec = require_alex_go(manifest_sha="abcd" * 16, go_path=path)
            self.assertTrue(rec["authorizes_g2_diagnostic_execute"])

    def test_run_module_does_not_call_look(self) -> None:
        src = (G2 / "run.py").read_text()
        self.assertNotIn("look_real", src)
        self.assertNotIn("evaluate(", src)
        self.assertNotIn("03a4dd90 reopen", src)
        self.assertIn("require_alex_go", src)
        self.assertIn("refuse_if_distribution_regen", src)

    def test_no_if_regen_helper(self) -> None:
        with self.assertRaises(Exception):
            refuse_if_distribution_regen()

    def test_manifest_builder_does_not_parse_outcome_scores(self) -> None:
        # Freeze hashes outcomes as bytes and reads forecast JSON only.
        freeze_src = (G2 / "freeze.py").read_text()
        self.assertNotIn("home_score", freeze_src)
        self.assertNotIn("DictReader", freeze_src)
        manifest = build_manifest()
        self.assertFalse(manifest["executed"])
        self.assertEqual(manifest["status"], "PREVERIFY")
        self.assertEqual(manifest["identities"]["n"], 141)
        self.assertEqual(
            manifest["inputs"]["outcomes_score_only"]["parse"], "checksum_only"
        )

    def test_default_run_refuses_without_go(self) -> None:
        import run as run_mod

        rc = run_mod.main()
        self.assertEqual(rc, 2)
        self.assertFalse((G2 / "artifacts" / "G2_DIAGNOSTIC_RESULT.json").exists())
        self.assertFalse((G2 / "CURSOR_DONE.md").exists())


if __name__ == "__main__":
    unittest.main()
