"""Release gates for the ESPN-only 2025 efficiency chain. Measure / fail-closed only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

ROOT = Path(__file__).resolve().parents[3]
MS_DATA = (
    Path(__file__).resolve().parents[1] / "src/services/cfb_season_engine/data"
)
CANARY = ROOT / "data/ops/cfb-w0-canary-20260831"
PACKAGER = ROOT / "scripts/cfb/package_efficiency_2025_carry.py"


def _load_packager():
    spec = importlib.util.spec_from_file_location("cfb_eff_packager", PACKAGER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cfb_eff_packager"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_live_2026_board_guard_fail_closes() -> None:
    mod = _load_packager()
    rows = [{"team": f"T{i}", "record": "1-0"} for i in range(30)]
    try:
        mod._assert_not_live_2026_board(rows)
    except mod.LivePublicIsNotFinal2025 as exc:
        assert "2026 in-season" in str(exc)
    else:
        raise AssertionError("live 2026-shaped records must fail closed")
    finals = [{"team": f"T{i}", "record": "11-2"} for i in range(30)]
    mod._assert_not_live_2026_board(finals)


def test_packager_cli_refuses_live_public_and_splice() -> None:
    splice = subprocess.run(
        [sys.executable, str(PACKAGER), "--splice-p0-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert splice.returncode == 1
    assert "mixes ESPN rows onto a frozen cfbupdate" in splice.stderr
    live = subprocess.run(
        [sys.executable, str(PACKAGER), "--allow-live-public"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert live.returncode == 1
    assert "2026 in-season" in live.stderr or "live public SP+" in live.stderr


def test_working_efficiency_is_not_live_2026() -> None:
    snap = json.loads(
        (MS_DATA / "cfb_efficiency_snapshot_2025_carry_2026.json").read_text(
            encoding="utf-8"
        )
    )
    teams = snap["teams"]
    assert snap["source"]["vintage"] == "espn_story_2025_final"
    assert snap["source"]["live_public"] == "rejected_2026_inseason_cfbupdate"
    assert teams["TCU"]["sp_plus"] == 8.3
    assert teams["UNC"]["sp_plus"] == -6.6
    assert teams["UNT"]["sp_plus"] == 13.8
    assert teams["IU"]["sp_plus"] == 32.4
    # Live 2026 board values that must not appear.
    assert teams["TCU"]["sp_plus"] != 3.9
    assert teams["UNC"]["sp_plus"] != 5.8
    assert teams["UNT"]["sp_plus"] != -13.2


def test_totals_identity_kei_equals_model() -> None:
    kei = json.loads((MS_DATA / "cfb_kei_w0_w1_2026.json").read_text(encoding="utf-8"))
    n = 0
    for g in kei.get("games") or []:
        if not g.get("fbs_vs_fbs"):
            continue
        blob = g.get("kei") or {}
        mt = g.get("model_total")
        kt = blob.get("kei_total")
        if mt is None:
            continue
        n += 1
        assert kt is not None
        assert abs(float(kt) - float(mt)) < 1e-9
    assert n >= 90


def test_as_of_chain_compatible() -> None:
    sched = json.loads((MS_DATA / "cfb_official_schedule_2026.json").read_text())
    power = json.loads((MS_DATA / "cfb_power_sot_2026.json").read_text())
    proj = json.loads((MS_DATA / "cfb_season_projections_2026.json").read_text())
    futures = json.loads((MS_DATA / "cfb_futures_2026.json").read_text())
    kei = json.loads((MS_DATA / "cfb_kei_w0_w1_2026.json").read_text())
    eff = json.loads((MS_DATA / "cfb_efficiency_snapshot_2025_carry_2026.json").read_text())
    assert sched.get("as_of") == "2026-08-31"
    assert power.get("power_as_of") == "2026-08-31"
    assert power.get("power_version") == "cfb-power-sot-v0.15-week0-close-20260831"
    assert proj.get("as_of") == "2026-08-31"
    assert proj.get("artifact_id") == (
        "cfb-season-projections-v0.15-n10000-week0-close-20260831"
    )
    assert futures.get("as_of") == "2026-08-31"
    assert eff.get("as_of") == "2026-08-31"
    assert (eff.get("source") or {}).get("published") == "2026-01-20"
    assert kei.get("as_of") == "2026-09-10"
    assert kei.get("kei_version") == "cfb-kei-v1.0-2026w2"


def test_w0_canary_hashes_locked() -> None:
    man = json.loads((CANARY / "MANIFEST.json").read_text(encoding="utf-8"))
    assert man["do_not_overwrite"] is True
    for name, exp in man["sha256"].items():
        got = hashlib.sha256((CANARY / name).read_bytes()).hexdigest()
        assert got == exp, name


def test_public_kill_switch_stays_off() -> None:
    from src.services.cfb_season_engine.team_features import (
        CFB_EDGE_BOARD_PUBLIC_ENABLED,
    )

    assert CFB_EDGE_BOARD_PUBLIC_ENABLED is False
