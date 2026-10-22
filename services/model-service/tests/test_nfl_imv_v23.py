"""ccecea74 — IMV v2.3 contracts. Synthetic only. Does not run Mac builder/W7."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMV = ROOT / "scripts" / "nfl" / "imv"
sys.path.insert(0, str(IMV))

import nfl_imv_v23 as v23  # noqa: E402


def test_p3_v21_pin_matches_05027146() -> None:
    rec = v23.stamp_helper_shas(IMV)
    assert rec["ok"] is True
    assert rec["v21"] == v23.V21_PIN
    assert rec["v21"].startswith("05027146")
    assert rec["v22"]
    assert rec["flag"] is None


def test_p3_stamp_writes_both_helper_files(tmp_path: Path) -> None:
    rec = v23.write_helper_stamps(tmp_path, IMV)
    assert rec["ok"] is True
    assert (tmp_path / "HELPER_V21.sha256").read_text(encoding="utf-8").strip() == v23.V21_PIN
    assert (tmp_path / "HELPER_V22.sha256").read_text(encoding="utf-8").strip() == rec["v22"]
    helpers = json.loads((tmp_path / "HELPERS.json").read_text(encoding="utf-8"))
    assert helpers["v21_pin"] == v23.V21_PIN


def test_x3_no_export_is_not_run() -> None:
    doc = v23.parity_local_w_vs_prod_w_minus_1(
        [{"game_id_product": "2026-W06-SEA@DEN", "week": 6, "home_team": "DEN", "away_team": "SEA"}],
        v23.load_prod_export(None),
        week_cap=6,
    )
    assert doc["status"] == "NOT_RUN_NO_PROD_EXPORT"
    assert doc["authored_samples_refused"] is True


def test_x3_authored_v22_fixture_is_not_a_prod_export() -> None:
    # The v2.2 committed prod sample has no EXPORT.meta.json — refused.
    fake = IMV / "fixtures"
    doc = v23.load_prod_export(fake)
    assert doc["status"] == "NOT_RUN_NO_PROD_EXPORT"


def test_x3_local_w_vs_prod_w_minus_1_tolerances(tmp_path: Path) -> None:
    prod_rows = [
        {
            "game_id": "2026_05_GB_CHI",
            "week": 5,
            "home_team": "GB",
            "away_team": "CHI",
            "home_off_epa_5g": 0.030,
            "away_off_epa_5g": 0.028,
            "home_def_epa_allowed_5g": -0.01,
            "away_def_epa_allowed_5g": -0.015,
            "home_pass_rate_5g": 0.57,
            "away_pass_rate_5g": 0.56,
            "home_success_offense_5g": 0.45,
            "away_success_offense_5g": 0.44,
            "home_pressure_allowed_5g": 0.20,
            "away_pressure_allowed_5g": 0.18,
        }
    ]
    jsonl = tmp_path / "features.jsonl"
    payload = "".join(json.dumps(r) + "\n" for r in prod_rows)
    jsonl.write_text(payload, encoding="utf-8")
    sha = hashlib.sha256(jsonl.read_bytes()).hexdigest()
    meta = {
        "kind": v23.PROD_EXPORT_KIND,
        "source": "test-constructed-not-prod",
        "query": "SELECT 1 -- in-test only",
        "sha256": sha,
        "weeks": [5],
        "columns": ["week", "home_team", "away_team", "home_off_epa_5g"],
        "captured_utc": "2026-10-22T00:00:00Z",
    }
    (tmp_path / "EXPORT.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    export = v23.load_prod_export(tmp_path)
    assert export["status"] == "OK"
    local = [
        {
            "game_id_product": "2026-W06-CHI@GB",
            "week": 6,
            "home_team": "GB",
            "away_team": "CHI",
            "home_off_epa_5g": 0.031,
            "away_off_epa_5g": 0.029,
            "home_def_epa_allowed_5g": -0.01,
            "away_def_epa_allowed_5g": -0.015,
            "home_pass_rate_5g": 0.57,
            "away_pass_rate_5g": 0.56,
            "home_success_offense_5g": 0.45,
            "away_success_offense_5g": 0.44,
            "home_pressure_allowed_5g": 0.20,
            "away_pressure_allowed_5g": 0.18,
        }
    ]
    ok = v23.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6)
    assert ok["status"] == "PASS"
    assert ok["join"].startswith("local.week W")
    assert ok["n_keys"] >= 5
    # Blow EPA past 0.02 tol
    local[0]["home_off_epa_5g"] = 0.10
    bad = v23.parity_local_w_vs_prod_w_minus_1(local, export, week_cap=6)
    assert bad["status"] == "FAIL_VALUE_MISMATCH"
    assert bad["diffs"]


def test_p1_runner_reads_out_store(tmp_path: Path) -> None:
    parent = tmp_path / "out"
    store = parent / "store"
    store.mkdir(parents=True)
    (store / "features.jsonl").write_text("{}\n", encoding="utf-8")
    assert v23.resolve_feature_store(parent) == store
    lone = tmp_path / "flat"
    lone.mkdir()
    (lone / "features.jsonl").write_text("{}\n", encoding="utf-8")
    assert v23.resolve_feature_store(lone) == lone


def test_p2_w8_deadline_and_exclude_kickoff() -> None:
    early = v23.w8_seal_window(datetime(2026, 10, 29, 23, 0, tzinfo=timezone.utc))
    assert early["ok"] is True
    late = v23.w8_seal_window(datetime(2026, 10, 30, 0, 15, tzinfo=timezone.utc))
    assert late["ok"] is False
    assert late["flag"] == "W8_SEAL_AFTER_DEADLINE"
    assert late["deadline_et"] == "2026-10-29 20:15 ET"
    assert v23.game_excluded_at_or_before_seal("2026-10-30T00:15:00Z", "2026-10-30T00:15:00Z") is True
    assert v23.game_excluded_at_or_before_seal("2026-10-30T00:16:00Z", "2026-10-30T00:15:00Z") is False


def test_p5_blocked_build_and_missing_finals() -> None:
    assert v23.refuse_blocked_build(None)["flag"] == "BLOCKED_BUILD_REPORT_MISSING"
    assert v23.refuse_blocked_build({"status": "BLOCKED", "blocked": ["x"]})["allow_sealed_run"] is False
    assert v23.refuse_blocked_build({"status": "BUILT"})["ok"] is True
    miss = v23.missing_finals_blocked(["2026-W06-SEA@DEN"], [])
    assert miss["ok"] is False
    assert miss["rerun_is_new_snapshot"] is True
    assert v23.missing_finals_blocked([], [])["ok"] is True


def test_weekly_avg_rule_is_unweighted() -> None:
    assert "unweighted mean of weekly rates" in v23.WEEKLY_AVG_RULE
    assert "not used as rate weights" in v23.WEEKLY_AVG_RULE


def test_source_gating_p1_p3_p5() -> None:
    runner = (IMV / "nfl-imv-sealed-v2.3.sh").read_text(encoding="utf-8")
    assert "HELPER_V21" in runner or "write_helper_stamps" in runner
    assert "BLOCKED_BUILD_NO_SEALED_RUN" in runner or "refuse_blocked_build" in runner
    assert 'IMV_FEATURE_STORE}/store' in runner or "resolve_feature_store" in runner
    assert "2026-10-30T00:15:00Z" in runner
    builder = (IMV / "nfl-imv-feature-build-v2.3.sh").read_text(encoding="utf-8")
    assert "HELPER_V21.sha256" in builder
    assert "050271467cd38f5a174043c67f2df9622d7f0b8125f137b822f888846f4c561f" in builder
    assert "BUILD_BLOCKED" in builder
    assert "OUT}/store" in builder
