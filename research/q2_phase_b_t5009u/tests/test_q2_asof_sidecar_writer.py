#!/usr/bin/env python3
"""t5018u writer guards: pin sha, leakage, fail-closed, isolation.

CERT=0 · DEV_RESEARCH · research-consumed only. No forecast-path imports.
"""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emit_q2_asof_sidecar import (
    FORBIDDEN_OUTPUT_KEYS,
    ROW_FIELDS,
    SEALED_A_Q2,
    SEALED_ASOF_RULE,
    SEALED_B_Q2,
    SEALED_CONFIG_SHA,
    SEALED_FIT_SHA,
    SEALED_GAMES_PIN,
    SEALED_GAMES_SHA,
    SEALED_OUTCOMES_SHA,
    SidecarRefuse,
    emit_sidecar,
    load_frozen_config,
    row_from_feat,
    validate_row,
    verify_pins,
)
from q2pb.data import Game
from q2pb.strength import AsOfFeatures, assert_asof_leakage

GAMES = ROOT / "data" / "games_4fe1cdd7.csv"
OUTCOMES = ROOT / "data" / "outcomes_2013_2022_score_only.csv"
FROZEN = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.json"
FROZEN_MD = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.md"
WRITER = ROOT / "emit_q2_asof_sidecar.py"

FORECAST_PATH_FILES = (
    Path("services/model-service/src/services/nfl_simulator.py"),
    Path("services/model-service/src/tasks.py"),
    Path("services/model-service/src/services/nfl_handicap_ledger/schema.py"),
    Path("services/model-service/src/routes/nfl.py"),
)

FORBIDDEN_IMPORT_NEEDLES = (
    "nfl_simulator",
    "simulate_nfl_game",
    "simulate_nfl_game_independent_fair",
    "run_nfl_market_simulations",
    "NflGameInputs",
    "nfl_handicap_ledger",
    "independent_fair_mus",
)

REPO_ROOT = ROOT.parents[1]


def _valid_row(**overrides):
    row = {
        "game_id": "2013_02_NYJ_NE",
        "season": 2013,
        "week": 2,
        "home": "NE",
        "away": "NYJ",
        "kickoff_utc": "2013-09-13T00:25:00+00:00",
        "q2_home_s": 1.0,
        "q2_away_s": -0.5,
        "q2_rating_diff": 1.5,
        "q2_hfa": 2.2,
        "q2_n_asof_games": 16,
        "q2_asof_wl_diff": 0.0,
        "q2_pm_new": SEALED_A_Q2 + SEALED_B_Q2 * 1.5,
        "q2_fit_sha": SEALED_FIT_SHA,
        "q2_config_sha": SEALED_CONFIG_SHA,
        "q2_asof_rule": SEALED_ASOF_RULE,
        "q2_games_pin": SEALED_GAMES_PIN,
    }
    row.update(overrides)
    return row


class TestPinShaMatch(unittest.TestCase):
    def test_sealed_pins_match_frozen_and_files(self) -> None:
        cfg = load_frozen_config(FROZEN)
        pins = verify_pins(GAMES, OUTCOMES, cfg, FROZEN_MD)
        self.assertEqual(pins.games_sha256, SEALED_GAMES_SHA)
        self.assertTrue(pins.games_sha256.startswith("4fe1cdd7"))
        self.assertEqual(pins.outcomes_sha256, SEALED_OUTCOMES_SHA)
        self.assertTrue(pins.outcomes_sha256.startswith("50bda875"))
        self.assertEqual(pins.fit_sha, SEALED_FIT_SHA)
        self.assertTrue(pins.fit_sha.startswith("70db070d"))
        self.assertEqual(pins.config_sha, SEALED_CONFIG_SHA)
        self.assertTrue(pins.config_sha.startswith("aa2b47b3"))
        self.assertEqual(pins.asof_rule, "cf514078")
        self.assertTrue(pins.frozen_md_sha256.startswith("28c582a1"))
        self.assertEqual(pins.lam, 20.0)
        self.assertEqual(pins.regress_frac, 0.5)
        self.assertEqual(pins.a_q2, SEALED_A_Q2)
        self.assertEqual(pins.b_q2, SEALED_B_Q2)

    def test_wrong_fit_sha_refuses_batch(self) -> None:
        cfg = dict(load_frozen_config(FROZEN))
        cfg["fit_object_sha256"] = "deadbeef" + cfg["fit_object_sha256"][8:]
        with self.assertRaises(SidecarRefuse):
            verify_pins(GAMES, OUTCOMES, cfg, FROZEN_MD)


class TestLeakageGreenOnEmitted(unittest.TestCase):
    def test_assert_asof_leakage_green_on_2013_w2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = emit_sidecar(
                games_path=GAMES,
                outcomes_path=OUTCOMES,
                frozen_path=FROZEN,
                frozen_md_path=FROZEN_MD,
                seasons=(2013,),
                weeks=(2,),
                outdir=Path(tmp),
                write_files=True,
            )
        self.assertGreaterEqual(len(result.rows), 1)
        self.assertEqual(result.refused, [])
        for row in result.rows:
            validate_row(row)
            self.assertEqual(row["season"], 2013)
            self.assertEqual(row["week"], 2)
            self.assertEqual(row["q2_asof_rule"], "cf514078")
            self.assertLess(row["q2_n_asof_games"], 32)  # W1 only, not same-kickoff W2
            self.assertGreaterEqual(row["q2_n_asof_games"], 1)
        # Re-run the keep-packet leakage symbol on a reconstructed feat list.
        feats = []
        for row in result.rows:
            game = Game(
                season=row["season"],
                week=row["week"],
                game_id=row["game_id"],
                home=row["home"],
                away=row["away"],
                kickoff_utc=datetime.fromisoformat(row["kickoff_utc"]),
                home_score=0.0,
                away_score=0.0,
                record_entering_home="0-0",
                record_entering_away="0-0",
                market_spread_home=None,
            )
            feats.append(
                AsOfFeatures(
                    game=game,
                    home_s=row["q2_home_s"],
                    away_s=row["q2_away_s"],
                    rating_diff=row["q2_rating_diff"],
                    n_asof_games=row["q2_n_asof_games"],
                    hfa=row["q2_hfa"],
                )
            )
        # History for the recount is the real 2013 scored set used during emit.
        from q2pb.data import load_games, load_outcomes_score_only

        outcomes = load_outcomes_score_only(OUTCOMES, (2013,))
        history = load_games(GAMES, outcomes, (2013,), phase="sidecar_offline_asof")
        assert_asof_leakage(history, feats)


class TestFailClosedMissingField(unittest.TestCase):
    def test_missing_required_field_refuses_row(self) -> None:
        row = _valid_row()
        del row["q2_home_s"]
        with self.assertRaises(SidecarRefuse) as ctx:
            validate_row(row)
        self.assertIn("q2_home_s", str(ctx.exception))

    def test_nan_numeric_refuses_row(self) -> None:
        row = _valid_row(q2_away_s=float("nan"))
        with self.assertRaises(SidecarRefuse) as ctx:
            validate_row(row)
        self.assertIn("q2_away_s", str(ctx.exception))

    def test_wrong_pin_on_row_refuses(self) -> None:
        row = _valid_row(q2_fit_sha="0" * 64)
        with self.assertRaises(SidecarRefuse):
            validate_row(row)

    def test_empty_identity_refuses(self) -> None:
        row = _valid_row(home="")
        with self.assertRaises(SidecarRefuse):
            validate_row(row)

    def test_2024_row_refuses(self) -> None:
        row = _valid_row(season=2024)
        with self.assertRaises(SidecarRefuse):
            validate_row(row)

    def test_emit_refuses_2024_season_arg(self) -> None:
        with self.assertRaises(SidecarRefuse):
            emit_sidecar(
                games_path=GAMES,
                outcomes_path=OUTCOMES,
                frozen_path=FROZEN,
                seasons=(2024,),
                weeks=(2,),
                write_files=False,
            )


class TestIsolation(unittest.TestCase):
    def test_writer_source_has_no_forecast_imports_or_writes(self) -> None:
        source = WRITER.read_text()
        tree = ast.parse(source)
        imported: list[str] = []
        stored_attrs: list[str] = []
        called: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                stored_attrs.append(node.attr)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    called.append(func.id)
                elif isinstance(func, ast.Attribute):
                    called.append(func.attr)
        blob = " ".join(imported)
        for needle in FORBIDDEN_IMPORT_NEEDLES:
            self.assertNotIn(needle, blob)
        for attr in (
            "offense_index_home",
            "offense_index_away",
            "defense_index_home",
            "defense_index_away",
            "off_eff_h",
            "off_eff_a",
            "def_eff_h",
            "def_eff_a",
            "margin_mu",
            "market_blend",
        ):
            self.assertNotIn(attr, stored_attrs)
        for name in (
            "simulate_nfl_game",
            "simulate_nfl_game_independent_fair",
            "run_nfl_market_simulations",
        ):
            self.assertNotIn(name, called)

    def test_emitted_rows_only_contract_fields(self) -> None:
        result = emit_sidecar(
            games_path=GAMES,
            outcomes_path=OUTCOMES,
            frozen_path=FROZEN,
            frozen_md_path=FROZEN_MD,
            seasons=(2013,),
            weeks=(2,),
            write_files=False,
        )
        allow = set(ROW_FIELDS)
        for row in result.rows:
            self.assertTrue(allow.issuperset(row.keys()), set(row) - allow)
            self.assertFalse(set(row) & set(FORBIDDEN_OUTPUT_KEYS))

    def test_import_does_not_load_forecast_modules(self) -> None:
        # Do not reload the writer: a new SidecarRefuse class would break
        # later assertRaises. Forecast modules must already be absent.
        self.assertIn("emit_q2_asof_sidecar", sys.modules)
        loaded = " ".join(sys.modules)
        self.assertNotIn("nfl_simulator", loaded)
        self.assertNotIn("nfl_handicap_ledger", loaded)
        self.assertNotIn("simulate_nfl_game", loaded)

    def test_writer_does_not_open_hist_index(self) -> None:
        source = WRITER.read_text()
        self.assertNotIn("historical_oos_games.csv", source)
        from emit_q2_asof_sidecar import ALLOWED_OPEN_NAMES

        self.assertNotIn("historical_oos_games.csv", ALLOWED_OPEN_NAMES)
        self.assertEqual(
            ALLOWED_OPEN_NAMES,
            {
                "games_4fe1cdd7.csv",
                "outcomes_2013_2022_score_only.csv",
                "FROZEN_CONFIG_Q2PB_t5009u.json",
                "FROZEN_CONFIG_Q2PB_t5009u.md",
            },
        )
        self.assertNotIn("1ee90fac", "".join(ALLOWED_OPEN_NAMES))

    def test_artifacts_stay_under_outdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "sidecar_out"
            result = emit_sidecar(
                games_path=GAMES,
                outcomes_path=OUTCOMES,
                frozen_path=FROZEN,
                frozen_md_path=FROZEN_MD,
                seasons=(2013,),
                weeks=(2,),
                outdir=dest,
                write_files=True,
            )
            self.assertTrue(dest.exists())
            for path in dest.iterdir():
                self.assertTrue(str(path).startswith(str(dest)))
                self.assertIn(path.suffix, {".json", ".csv", ".md"})
            # Isolation claim is stamped on the JSON payload.
            import json

            payload = json.loads((dest / "q2_asof_sidecar_t5018u.json").read_text())
            self.assertFalse(payload["isolation"]["writes_offense_index"])
            self.assertFalse(payload["isolation"]["writes_l0_market_blend"])
            self.assertFalse(payload["isolation"]["calls_simulate_nfl_game"])
            self.assertFalse(payload["isolation"]["joins_forecast_path"])
            self.assertEqual(payload["cert"], 0)
            self.assertEqual(len(payload["rows"]), len(result.rows))

    def test_forecast_path_files_not_modified_in_this_tree(self) -> None:
        """Diff-level isolation: writer PR must not touch Layer 3 / ledger."""
        import subprocess

        changed: set[str] = set()
        for args in (
            ["git", "diff", "--name-only", "origin/deploy-vercel"],
            ["git", "diff", "--name-only", "--cached", "origin/deploy-vercel"],
        ):
            diff = subprocess.check_output(args, cwd=REPO_ROOT, text=True)
            changed.update(line.strip() for line in diff.splitlines() if line.strip())
        for rel in FORECAST_PATH_FILES:
            self.assertNotIn(str(rel), changed)
        for path in changed:
            self.assertFalse(path.startswith("services/model-service/src/"), path)
            self.assertNotIn("nfl_simulator", path)
            self.assertNotIn("celery", path)


class TestSealedMapNoRefit(unittest.TestCase):
    def test_pm_new_uses_frozen_ols_only(self) -> None:
        T0 = datetime(2013, 9, 8, 17, 0, tzinfo=timezone.utc)
        game = Game(
            season=2013,
            week=2,
            game_id="2013_02_FAKE_FAKE",
            home="AAA",
            away="BBB",
            kickoff_utc=T0 + timedelta(days=7),
            home_score=20,
            away_score=10,
            record_entering_home="1-0",
            record_entering_away="0-1",
            market_spread_home=None,
        )
        feat = AsOfFeatures(
            game=game,
            home_s=2.0,
            away_s=-1.0,
            rating_diff=3.0,
            n_asof_games=1,
            hfa=2.5,
        )
        cfg = load_frozen_config(FROZEN)
        pins = verify_pins(GAMES, OUTCOMES, cfg, FROZEN_MD)
        hist = [
            Game(
                season=2013,
                week=1,
                game_id="2013_01_BBB_AAA",
                home="AAA",
                away="BBB",
                kickoff_utc=T0,
                home_score=27,
                away_score=13,
                record_entering_home="0-0",
                record_entering_away="0-0",
                market_spread_home=None,
            ),
            game,
        ]
        row = row_from_feat(feat, hist, pins)
        self.assertAlmostEqual(row["q2_pm_new"], SEALED_A_Q2 + SEALED_B_Q2 * 3.0)
        self.assertAlmostEqual(row["q2_asof_wl_diff"], 1.0 - 0.0)


if __name__ == "__main__":
    unittest.main()
