"""Preseason release gate — constants + Walker volume band."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/nfl/preseason_release_gate.py"


def _load():
    spec = importlib.util.spec_from_file_location("preseason_release_gate", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_lock_tag_and_walker_band() -> None:
    mod = _load()
    assert mod.LOCK_TAG == "nfl-season-engine-2026-preseason-lock"
    assert mod.WALKER_RUSH_MIN == 1050.0
    assert mod.WALKER_RUSH_MAX == 1650.0
    assert 904 < mod.WALKER_RUSH_MIN  # old starved 904 fails
    assert 1172 >= mod.WALKER_RUSH_MIN  # post-floor Walker passes
    assert 1800 > mod.WALKER_RUSH_MAX  # no invented Henry-class


def test_render_markdown_fail_table() -> None:
    mod = _load()
    md = mod.render_markdown(
        {
            "ok": False,
            "bundle": "data/ops/example",
            "generated_at_utc": "2026-08-13T00:00Z",
            "lock_tag": mod.LOCK_TAG,
            "identity": "test",
            "checks": [
                {"id": "walker_kc", "ok": True, "detail": "Walker team=KC"},
                {
                    "id": "walker_feature_volume",
                    "ok": False,
                    "detail": "Walker rush=904",
                },
            ],
            "walker": {
                "team": "KC",
                "rush": 904,
                "pos_rank": 29,
                "overall": 98,
                "pts": 169.6,
            },
            "charbonnet": {"team": "SEA", "rush": 1188, "pos_rank": 5},
            "top5_rb_spread": 80.0,
            "qb_ge_4000": 4,
        }
    )
    assert "**FAIL**" in md
    assert "`walker_feature_volume`" in md
    assert "904" in md
