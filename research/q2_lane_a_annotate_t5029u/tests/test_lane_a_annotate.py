#!/usr/bin/env python3
"""t5029u Lane A CLEAR_ANNOTATE guards.

Join identity · refuse-on-miss · pin mismatch refuse · no strength mutation ·
determinism (two runs same sha). CERT=0 · DEV_RESEARCH · research-consumed only.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from emit_lane_a_annotations import (  # noqa: E402
    ALLOWED_OPEN_NAMES,
    FROZEN_GAME_IDS,
    FROZEN_N_IDENTITIES,
    SCORED_1EE90FAC_COLUMNS,
    SEALED_ASOF_RULE,
    SEALED_CONFIG_SHA,
    SEALED_FIT_SHA,
    SEALED_GAMES_PIN,
    SEALED_GAMES_SHA,
    SEALED_MANIFEST_SHA,
    SEALED_OUTCOMES_SHA,
    SEALED_SIDECAR_SHA,
    STRENGTH_FIELDS,
    AnnotateRefuse,
    emit_annotations,
    identity_tuple,
    join_frozen_identities,
    join_identity,
    load_frozen_manifest,
    load_json_object,
    snapshot_strength,
    verify_pins,
)

GAMES = ROOT / "data" / "games_4fe1cdd7.csv"
OUTCOMES = ROOT / "data" / "outcomes_2013_2022_score_only.csv"
FROZEN = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.json"
FROZEN_MD = ROOT / "frozen" / "FROZEN_CONFIG_Q2PB_t5009u.md"
MANIFEST = ROOT / "frozen" / "FROZEN_MANIFEST_2013_REG_W2.json"
SIDECAR = ROOT / "inputs" / "q2_asof_sidecar_t5018u.json"
IF_DEMO = ROOT / "inputs" / "if_demo_inputs_2013_reg_w2.json"
ADAPTER = ROOT / "emit_lane_a_annotations.py"

FORECAST_PATH_FILES = (
    Path("services/model-service/src/services/nfl_simulator.py"),
    Path("services/model-service/src/routes/nfl.py"),  # N3 caller-of-record
    Path("services/model-service/src/tasks.py"),
    Path("services/model-service/src/services/nfl_handicap_ledger/schema.py"),
    Path("data/ops/nfl-hist-diag-score-70-t4910u/score_t4910u.py"),
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
)

FORBIDDEN_CALLS = (
    "simulate_nfl_game",
    "simulate_nfl_game_independent_fair",
    "run_nfl_market_simulations",
    "asof_for_targets",
    "asof_wl_diff",
)

REPO_ROOT = ROOT.parents[1]


def _emit(**kwargs):
    defaults = dict(
        games_path=GAMES,
        outcomes_path=OUTCOMES,
        frozen_path=FROZEN,
        frozen_md_path=FROZEN_MD,
        manifest_path=MANIFEST,
        sidecar_path=SIDECAR,
        if_demo_path=IF_DEMO,
        write_files=False,
    )
    defaults.update(kwargs)
    return emit_annotations(**defaults)


class TestJoinIdentity(unittest.TestCase):
    def test_game_id_join_when_both_sides_have_it(self) -> None:
        sidecar = {
            "game_id": "2013_02_NYJ_NE",
            "season": 2013,
            "week": 2,
            "home": "NE",
            "away": "NYJ",
        }
        demo = dict(sidecar)
        self.assertEqual(join_identity(sidecar, demo), "game_id")

    def test_game_key_join_when_one_side_lacks_game_id(self) -> None:
        sidecar = {
            "game_id": "2013_02_NYJ_NE",
            "season": 2013,
            "week": 2,
            "home": "NE",
            "away": "NYJ",
        }
        demo = {"game_id": "", "season": 2013, "week": 2, "home": "NE", "away": "NYJ"}
        self.assertEqual(join_identity(sidecar, demo), "Game.key")
        self.assertEqual(identity_tuple(sidecar), (2013, 2, "NE", "NYJ"))

    def test_game_id_mismatch_refuses_even_if_key_matches(self) -> None:
        sidecar = {
            "game_id": "2013_02_NYJ_NE",
            "season": 2013,
            "week": 2,
            "home": "NE",
            "away": "NYJ",
        }
        demo = dict(sidecar, game_id="2013_02_OTHER")
        with self.assertRaises(AnnotateRefuse) as ctx:
            join_identity(sidecar, demo)
        self.assertIn("game_id mismatch", str(ctx.exception))

    def test_key_mismatch_under_same_game_id_refuses(self) -> None:
        sidecar = {
            "game_id": "2013_02_NYJ_NE",
            "season": 2013,
            "week": 2,
            "home": "NE",
            "away": "NYJ",
        }
        demo = dict(sidecar, home="BUF")
        with self.assertRaises(AnnotateRefuse) as ctx:
            join_identity(sidecar, demo)
        self.assertIn("Game.key mismatch", str(ctx.exception))

    def test_incomplete_key_refuses(self) -> None:
        sidecar = {
            "game_id": "",
            "season": 2013,
            "week": 2,
            "home": "NE",
            "away": "NYJ",
        }
        demo = {"game_id": "", "season": 2013, "week": 2, "home": "NE", "away": ""}
        with self.assertRaises(AnnotateRefuse):
            join_identity(sidecar, demo)

    def test_emit_uses_game_id_on_frozen_2013_w2(self) -> None:
        result = _emit()
        self.assertEqual(len(result.rows), FROZEN_N_IDENTITIES)
        self.assertEqual([row["game_id"] for row in result.rows], list(FROZEN_GAME_IDS))
        for row in result.rows:
            self.assertEqual(row["join_key"], "game_id")
            self.assertEqual(row["season"], 2013)
            self.assertEqual(row["week"], 2)
            self.assertEqual(row["dev_research_label"], "DEV_RESEARCH")
            self.assertEqual(row["cert"], 0)
            self.assertTrue(row["not_a_forecast_quality_claim"])


class TestRefuseOnMiss(unittest.TestCase):
    def test_missing_sidecar_identity_refuses(self) -> None:
        identities = load_frozen_manifest(MANIFEST)
        sidecar_rows = [
            row
            for row in json.loads(SIDECAR.read_text())["rows"]
            if row["game_id"] != "2013_02_NYJ_NE"
        ]
        demo_rows = json.loads(IF_DEMO.read_text())["rows"]
        with self.assertRaises(AnnotateRefuse) as ctx:
            join_frozen_identities(identities, sidecar_rows, demo_rows)
        self.assertIn("missing sidecar identity 2013_02_NYJ_NE", str(ctx.exception))

    def test_missing_demo_identity_refuses(self) -> None:
        identities = load_frozen_manifest(MANIFEST)
        sidecar_rows = json.loads(SIDECAR.read_text())["rows"]
        demo_rows = [
            row
            for row in json.loads(IF_DEMO.read_text())["rows"]
            if row["game_id"] != "2013_02_PIT_CIN"
        ]
        with self.assertRaises(AnnotateRefuse) as ctx:
            join_frozen_identities(identities, sidecar_rows, demo_rows)
        self.assertIn("missing IF/demo identity 2013_02_PIT_CIN", str(ctx.exception))

    def test_extra_sidecar_identity_refuses_expansion(self) -> None:
        identities = load_frozen_manifest(MANIFEST)
        sidecar_rows = list(json.loads(SIDECAR.read_text())["rows"])
        extra = dict(sidecar_rows[0], game_id="2013_03_NYJ_NE", week=3)
        sidecar_rows.append(extra)
        demo_rows = json.loads(IF_DEMO.read_text())["rows"]
        with self.assertRaises(AnnotateRefuse) as ctx:
            join_frozen_identities(identities, sidecar_rows, demo_rows)
        self.assertIn("silent sample expansion refused", str(ctx.exception))

    def test_tampered_sidecar_sha_also_refuses_at_emit(self) -> None:
        payload = json.loads(SIDECAR.read_text())
        payload["rows"] = [row for row in payload["rows"] if row["game_id"] != "2013_02_NYJ_NE"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "q2_asof_sidecar_t5018u.json"
            path.write_text(json.dumps(payload))
            with self.assertRaises(AnnotateRefuse) as ctx:
                _emit(sidecar_path=path)
            self.assertIn("sidecar", str(ctx.exception).lower())

    def test_manifest_must_be_frozen_2013_reg_w2(self) -> None:
        identities = load_frozen_manifest(MANIFEST)
        self.assertEqual(len(identities), 16)
        self.assertEqual([row["game_id"] for row in identities], list(FROZEN_GAME_IDS))


class TestPinMismatchRefuse(unittest.TestCase):
    def test_sealed_pins_match(self) -> None:
        cfg = load_json_object(FROZEN)
        pins = verify_pins(GAMES, OUTCOMES, cfg, FROZEN_MD, SIDECAR, MANIFEST, IF_DEMO)
        self.assertEqual(pins.games_sha256, SEALED_GAMES_SHA)
        self.assertTrue(pins.games_sha256.startswith(SEALED_GAMES_PIN))
        self.assertEqual(pins.outcomes_sha256, SEALED_OUTCOMES_SHA)
        self.assertTrue(pins.outcomes_sha256.startswith("50bda875"))
        self.assertEqual(pins.fit_sha, SEALED_FIT_SHA)
        self.assertTrue(pins.fit_sha.startswith("70db070d"))
        self.assertEqual(pins.config_sha, SEALED_CONFIG_SHA)
        self.assertTrue(pins.config_sha.startswith("aa2b47b3"))
        self.assertEqual(pins.asof_rule, SEALED_ASOF_RULE)
        self.assertTrue(pins.frozen_md_sha256.startswith("28c582a1"))
        self.assertEqual(pins.sidecar_sha256, SEALED_SIDECAR_SHA)
        self.assertEqual(pins.manifest_sha256, SEALED_MANIFEST_SHA)

    def test_wrong_fit_sha_refuses(self) -> None:
        cfg = dict(load_json_object(FROZEN))
        cfg["fit_object_sha256"] = "deadbeef" + cfg["fit_object_sha256"][8:]
        with self.assertRaises(AnnotateRefuse) as ctx:
            verify_pins(GAMES, OUTCOMES, cfg, FROZEN_MD, SIDECAR, MANIFEST, IF_DEMO)
        self.assertIn("70db070d", str(ctx.exception))

    def test_wrong_asof_rule_refuses(self) -> None:
        cfg = dict(load_json_object(FROZEN))
        cfg["tip_asof"] = "week-cap"
        with self.assertRaises(AnnotateRefuse) as ctx:
            verify_pins(GAMES, OUTCOMES, cfg, FROZEN_MD, SIDECAR, MANIFEST, IF_DEMO)
        self.assertIn("cf514078", str(ctx.exception))

    def test_tampered_games_file_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "games_4fe1cdd7.csv"
            path.write_bytes(GAMES.read_bytes() + b"\n")
            with self.assertRaises(AnnotateRefuse):
                _emit(games_path=path)

    def test_tampered_sidecar_file_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "q2_asof_sidecar_t5018u.json"
            path.write_bytes(SIDECAR.read_bytes() + b"\n")
            with self.assertRaises(AnnotateRefuse) as ctx:
                _emit(sidecar_path=path)
            self.assertIn("sidecar", str(ctx.exception).lower())


class TestNoStrengthMutation(unittest.TestCase):
    def test_emit_copies_if_demo_strength_fields_unchanged(self) -> None:
        demo_rows = {row["game_id"]: row for row in json.loads(IF_DEMO.read_text())["rows"]}
        result = _emit()
        self.assertEqual(len(result.rows), 16)
        for row in result.rows:
            before = snapshot_strength(demo_rows[row["game_id"]])
            after = snapshot_strength(row)
            self.assertEqual(after, before)
            self.assertNotEqual(row["margin_mu"], row["q2_pm_new"])
            self.assertEqual(row["market_blend"], 0.0)

    def test_q2_fields_sit_beside_and_do_not_overwrite_strength_names(self) -> None:
        result = _emit()
        for row in result.rows:
            for name in STRENGTH_FIELDS:
                self.assertIn(name, row)
            self.assertIn("q2_home_s", row)
            self.assertIn("q2_pm_new", row)
            self.assertIn("dev_research_label", row)


class TestDeterminism(unittest.TestCase):
    def test_two_runs_same_payload_sha(self) -> None:
        first = _emit()
        second = _emit()
        self.assertEqual(first.payload_sha256, second.payload_sha256)
        self.assertEqual(len(first.payload_sha256), 64)
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a"
            b = Path(tmp) / "b"
            ra = _emit(outdir=a, write_files=True)
            rb = _emit(outdir=b, write_files=True)
            self.assertEqual(ra.payload_sha256, rb.payload_sha256)
            self.assertEqual(ra.payload_sha256, first.payload_sha256)
            self.assertEqual(
                (a / "lane_a_annotations_t5029u.json").read_bytes(),
                (b / "lane_a_annotations_t5029u.json").read_bytes(),
            )


class TestLeakageReuse(unittest.TestCase):
    def test_assert_asof_leakage_green_on_joined_2013_w2(self) -> None:
        result = _emit()
        self.assertEqual(len(result.rows), 16)
        for row in result.rows:
            self.assertEqual(row["q2_asof_rule"], "cf514078")
            self.assertLess(row["q2_n_asof_games"], 32)
            self.assertGreaterEqual(row["q2_n_asof_games"], 1)


class TestIsolation(unittest.TestCase):
    def test_adapter_source_has_no_forecast_imports_or_sim_calls(self) -> None:
        source = ADAPTER.read_text()
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
        for name in FORBIDDEN_CALLS:
            self.assertNotIn(name, called)
        for attr in STRENGTH_FIELDS:
            self.assertNotIn(attr, stored_attrs)
        self.assertIn("assert_asof_leakage", called)
        self.assertNotIn("emit_q2_asof_sidecar", blob)
        self.assertNotIn("emit_sidecar", called)

    def test_does_not_open_hist_index_or_scored_1ee90fac(self) -> None:
        self.assertNotIn("1ee90fac", "".join(ALLOWED_OPEN_NAMES))
        self.assertNotIn("historical_oos_games.csv", ALLOWED_OPEN_NAMES)
        result = _emit()
        for row in result.rows:
            for col in SCORED_1EE90FAC_COLUMNS:
                self.assertNotIn(col, row)
            self.assertNotIn("pit_schedule_sha256", row)
            self.assertNotIn("pit_schedule_path", row)

    def test_n3_diff_proof_names_routes_nfl_py(self) -> None:
        # N3: blended caller-of-record at this tip is routes/nfl.py, not tasks.py.
        self.assertEqual(
            str(FORECAST_PATH_FILES[1]),
            "services/model-service/src/routes/nfl.py",
        )
        source = ADAPTER.read_text()
        self.assertIn("routes/nfl.py", source)
        self.assertIn("edits_routes_nfl_py", source)

    def test_forecast_path_files_not_modified_in_this_tree(self) -> None:
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
            self.assertNotIn("score_t4910u", path)
            self.assertNotIn("routes/nfl.py", path)

    def test_artifacts_stay_under_outdir_and_stamp_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ann_out"
            result = _emit(outdir=dest, write_files=True)
            payload = json.loads((dest / "lane_a_annotations_t5029u.json").read_text())
            self.assertFalse(payload["isolation"]["mutates_offense_index"])
            self.assertFalse(payload["isolation"]["mutates_margin_mu"])
            self.assertFalse(payload["isolation"]["mutates_market_blend"])
            self.assertFalse(payload["isolation"]["calls_simulate_nfl_game"])
            self.assertFalse(payload["isolation"]["rewrites_q2_writer"])
            self.assertFalse(payload["isolation"]["edits_routes_nfl_py"])
            self.assertEqual(payload["cert"], 0)
            self.assertEqual(payload["label"], "DEV_RESEARCH")
            self.assertTrue(payload["not_a_forecast_quality_claim"])
            self.assertEqual(len(payload["rows"]), len(result.rows))


class TestWriterNotRewritten(unittest.TestCase):
    def test_tree_does_not_carry_the_q2_writer(self) -> None:
        self.assertFalse((ROOT / "emit_q2_asof_sidecar.py").exists())
        self.assertTrue(SIDECAR.is_file())
        self.assertEqual(SIDECAR.name, "q2_asof_sidecar_t5018u.json")


if __name__ == "__main__":
    unittest.main()
