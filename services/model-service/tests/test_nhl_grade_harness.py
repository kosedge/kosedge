"""NHL grading harness — schema + example seed (no pack rewrite)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "nhl" / "grade_harness.py"
STORE = ROOT / "data" / "nhl_grades_2026.jsonl"
SCHEMA = ROOT / "docs" / "NHL_GRADE_SCHEMA.md"
KEI = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "nhl_season_engine"
    / "data"
    / "nhl_kei_lines_ch4.json"
)
PROJ = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "nhl_season_engine"
    / "data"
    / "nhl_player_projection_2026.json"
)
PROPS = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "nhl_season_engine"
    / "nhl_props.py"
)
FANTASY = (
    ROOT
    / "services"
    / "model-service"
    / "src"
    / "services"
    / "nhl_season_engine"
    / "nhl_fantasy.py"
)


def test_schema_exists() -> None:
    assert SCHEMA.exists()
    text = SCHEMA.read_text(encoding="utf-8")
    assert "nhl_grades_2026.jsonl" in text
    assert "v0.1" in text
    assert "at tip" in text.lower() or "Freeze **at tip**" in text
    assert "n/a" in text
    assert "NHL_FANTASY_GAMES = 84" in text or "NHL_FANTASY_GAMES=84" in text
    assert "84" in text


def test_store_schema_example_first_fill() -> None:
    assert STORE.exists(), "run: python3 scripts/nhl/grade_harness.py seed"
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
    assert "goals" in markets and "sog" in markets

    teams = [r for r in rows if r.get("player_id") is None]
    props = [r for r in rows if r.get("player_id")]
    assert teams and props
    assert all(r.get("kei") is not None and r.get("proj") is None for r in teams)
    assert all(r.get("proj") is not None and r.get("kei") is None for r in props)
    assert all(r.get("tag") == "n/a" for r in props)

    # Example team rows are Ch4-shaped (FLA@CAR continuity) without pack rewrite.
    puck = next(r for r in teams if r.get("market") == "spread")
    total = next(r for r in teams if r.get("market") == "total")
    assert abs(float(puck["kei"]) - (-0.94)) < 1e-9
    assert abs(float(total["kei"]) - 6.71) < 1e-9


def test_fla_car_kei_pack_untouched() -> None:
    kei = json.loads(KEI.read_text(encoding="utf-8"))
    game = next(
        g for g in kei["games"] if g.get("away") == "FLA" and g.get("home") == "CAR"
    )
    assert abs(float(game["kei_puck_home"]) - (-0.94)) < 1e-9
    assert abs(float(game["kei_total"]) - 6.71) < 1e-9


def test_ch7_season_games_not_patched_in_this_pr() -> None:
    """Flag NHL_FANTASY_GAMES=84 in Ch9 docs; Ch7 code stays ×82 until follow-up."""
    text = FANTASY.read_text(encoding="utf-8")
    assert "SEASON_GAMES = 82" in text
    assert "SEASON_GAMES = 84" not in text


def test_status_and_summary_do_not_rewrite_packs() -> None:
    before = {
        "kei": KEI.read_bytes(),
        "proj": PROJ.read_bytes(),
        "props": PROPS.read_bytes(),
        "fantasy": FANTASY.read_bytes(),
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
    assert before["fantasy"] == FANTASY.read_bytes()


def test_props_module_still_dark() -> None:
    from src.services.nhl_season_engine.nhl_props import build_dark_props_board

    board = build_dark_props_board(limit=10)
    assert board.get("play_n", 0) == 0
    assert board.get("lean_n", 0) == 0
    for row in board.get("lines") or []:
        assert row.get("tag") == "PASS"
