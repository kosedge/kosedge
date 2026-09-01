"""WNBA grading harness — schema + example seed (no pack rewrite)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "wnba" / "grade_harness.py"
STORE = ROOT / "data" / "wnba_grades_2026.jsonl"
SCHEMA = ROOT / "docs" / "WNBA_GRADE_SCHEMA.md"
KEI = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "wnba_season_engine"
    / "data"
    / "wnba_kei_lines_ch4.json"
)
PROJ = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "wnba_season_engine"
    / "data"
    / "wnba_player_projection_2026.json"
)
PROPS = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "wnba_season_engine"
    / "wnba_props.py"
)
NBA_FANTASY = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "nba_season_engine"
    / "nba_fantasy.py"
)
CFB_KEI = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "cfb_season_engine"
    / "data"
    / "cfb_kei_w0_w1_2026.json"
)


def test_schema_exists() -> None:
    assert SCHEMA.exists()
    text = SCHEMA.read_text(encoding="utf-8")
    assert "wnba_grades_2026.jsonl" in text
    assert "Stamp frozen:** `v0.1` · Ch2–Ch7" in text or "v0.1" in text
    assert "Freeze **at tip**" in text or "at tip" in text.lower()
    assert "n/a" in text
    assert "Not a tag PR" in text or "not a tag PR" in text.lower()
    assert "pts" in text and "threes" in text


def test_store_schema_example_first_fill() -> None:
    assert STORE.exists(), "run: python3 scripts/wnba/grade_harness.py seed"
    rows = [
        json.loads(line)
        for line in STORE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) >= 4
    assert all(r.get("source") == "schema_example" for r in rows)
    assert all(r.get("close") is None for r in rows)
    assert all(r.get("final") is None for r in rows)
    assert all(r.get("signed_error") is None for r in rows)

    markets = {r.get("market") for r in rows}
    assert "spread" in markets and "total" in markets
    assert "pts" in markets and "threes" in markets

    teams = [r for r in rows if r.get("player_id") is None]
    props = [r for r in rows if r.get("player_id")]
    assert teams and props
    assert all(r.get("kei") is not None and r.get("proj") is None for r in teams)
    assert all(r.get("proj") is not None and r.get("kei") is None for r in props)
    assert all(r.get("tag") == "n/a" for r in props)


def test_status_and_summary_do_not_rewrite_packs() -> None:
    before = {
        "kei": KEI.read_bytes(),
        "proj": PROJ.read_bytes(),
        "props": PROPS.read_bytes(),
    }
    for cmd in ("status", "summary"):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), cmd],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
    assert before["kei"] == KEI.read_bytes()
    assert before["proj"] == PROJ.read_bytes()
    assert before["props"] == PROPS.read_bytes()


def test_nba_fantasy_module_untouched() -> None:
    text = NBA_FANTASY.read_text(encoding="utf-8")
    assert 'FANTASY_VERSION = "nba-fantasy-ch7-v1"' in text
    assert "SEASON_GAMES = 82" in text


def test_cfb_ball_osu_untouched() -> None:
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    game = next(
        g
        for g in kei["games"]
        if g.get("away") == "BALL" and g.get("home") == "OSU" and g.get("week") == 1
    )
    assert abs(float(game["kei"]["kei_spread_home"]) - (-40.51)) < 1e-9
