"""Research-only helpers for the 2026 roster-inflation diagnostic.

Does not open 2025. Does not change production compose.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "cfb"))

from cfb_2026_roster_inflation_diagnostic import (  # noqa: E402
    blend_roster_metrics,
    invert_espn_experience,
    invert_espn_portal_in,
    invert_espn_portal_out,
    invert_espn_returning,
    resolve_qb_talent,
)


def test_blend_invert_roundtrip_recruiting_50() -> None:
    rec = 50.0
    blended = blend_roster_metrics(
        recruiting=rec,
        espn_returning=48.0,
        espn_portal_in=52.0,
        espn_portal_out=47.0,
        espn_experience=51.0,
    )
    assert abs(invert_espn_returning(blended["returning_production"], rec) - 48.0) < 0.05
    assert abs(invert_espn_portal_in(blended["portal_in_value"], rec) - 52.0) < 0.05
    assert abs(invert_espn_portal_out(blended["portal_out_value"], rec) - 47.0) < 0.05
    assert abs(invert_espn_experience(blended["experience_index"], rec) - 51.0) < 0.05


def test_blend_invert_roundtrip_recruiting_90() -> None:
    rec = 90.0
    blended = blend_roster_metrics(
        recruiting=rec,
        espn_returning=40.0,
        espn_portal_in=60.0,
        espn_portal_out=42.0,
        espn_experience=55.0,
    )
    assert abs(invert_espn_returning(blended["returning_production"], rec) - 40.0) < 0.05
    assert abs(invert_espn_portal_in(blended["portal_in_value"], rec) - 60.0) < 0.05


def test_qb_talent_high_attempts_ignores_recruiting() -> None:
    hi = resolve_qb_talent(400, 3200, 24, is_portal=False, recruiting_class_score=95.0)
    lo = resolve_qb_talent(400, 3200, 24, is_portal=False, recruiting_class_score=50.0)
    assert abs(hi - lo) < 1e-9


def test_qb_talent_zero_attempts_uses_recruiting() -> None:
    assert resolve_qb_talent(0, 0, 0, is_portal=False, recruiting_class_score=90.0) == 90.0
    assert resolve_qb_talent(0, 0, 0, is_portal=False, recruiting_class_score=50.0) == 50.0


def test_script_does_not_open_2025() -> None:
    src = (ROOT / "scripts/cfb/cfb_2026_roster_inflation_diagnostic.py").read_text()
    assert "open_2025" not in src
    assert '"2025_opened": False' in src or "2025_opened" in src
    assert "lambda_fitted" in src
