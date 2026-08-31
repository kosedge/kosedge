"""CFB grading harness — seed contract (no KEI rewrite)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "cfb" / "grade_harness.py"
STORE = ROOT / "data" / "cfb_grades_2026.jsonl"
SCHEMA = ROOT / "docs" / "CFB_GRADE_SCHEMA.md"
CARD = ROOT / "data" / "ops" / "cfb-w1-handicap-card-20260831.json"
KEI = ROOT / "apps" / "web" / "data" / "processed" / "kei_lines_cfb.json"


def test_schema_and_card_exist() -> None:
    assert SCHEMA.exists()
    text = SCHEMA.read_text(encoding="utf-8")
    assert "cfb_grades_2026.jsonl" in text
    assert "fat-dog" in text
    assert CARD.exists()
    card = json.loads(CARD.read_text(encoding="utf-8"))
    assert card.get("sheet_ts") == "2026-08-31T21:38Z"


def test_store_w0_and_w1_first_fill() -> None:
    assert STORE.exists(), "run: python3 scripts/cfb/grade_harness.py seed"
    rows = [
        json.loads(line)
        for line in STORE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    w0 = [r for r in rows if r.get("week") == 0]
    assert len(w0) == 12
    assert all(r.get("tag") == "n/a" for r in w0)
    unc = next(
        r
        for r in w0
        if r.get("away") == "UNC"
        and r.get("home") == "TCU"
        and r.get("market") == "spread"
    )
    assert unc.get("final_away") == 15
    assert unc.get("final_home") == 10

    w1_spreads = [
        r for r in rows if r.get("week") == 1 and r.get("market") == "spread"
    ]
    assert len(w1_spreads) == 83
    assert sum(1 for r in w1_spreads if r.get("tag") == "PLAY") == 25
    ball = next(
        r for r in w1_spreads if r.get("away") == "BALL" and r.get("home") == "OSU"
    )
    assert ball.get("tag") == "PLAY"
    assert abs(float(ball["kei"]) - (-40.51)) < 1e-6
    assert ball.get("best_kick") == -50.5
    assert ball.get("size_note") == "fat-dog"


def test_status_does_not_rewrite_kei() -> None:
    before = KEI.read_bytes()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "status"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert before == KEI.read_bytes()
