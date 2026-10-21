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
from cfb_2026_qb_talent_contract_diagnostic import (  # noqa: E402
    decompose_talent,
    hist_qb_index,
    location_shift,
    talent_from_terms,
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
    src2 = (ROOT / "scripts/cfb/cfb_2026_qb_talent_contract_diagnostic.py").read_text()
    assert "open_2025" not in src2
    assert "matchup_response_changed" in src2


def test_typical_starter_talent_is_near_67_not_50() -> None:
    parts = decompose_talent(280, 2100, 18, is_portal=False)
    assert parts["completion_term"] is None
    talent = talent_from_terms(parts)
    assert 63.0 <= talent <= 72.0


def test_location_shift_preserves_rank_and_sd() -> None:
    xs = [55.0, 62.0, 67.0, 74.0, 81.0]
    med = 67.0
    ys = location_shift(xs, median=med, target=50.0)
    assert ys[2] == 50.0
    assert [a < b for a, b in zip(ys, ys[1:])] == [True, True, True, True]
    mean = sum(xs) / len(xs)
    sd0 = (sum((x - mean) ** 2 for x in xs) / len(xs)) ** 0.5
    my = sum(ys) / len(ys)
    sd1 = (sum((y - my) ** 2 for y in ys) / len(ys)) ** 0.5
    assert abs(sd0 - sd1) < 1e-9


def test_hist_cal_qb_index_is_unknown_at_50() -> None:
    row = hist_qb_index()
    assert row["qb_class"] == "unknown"
    assert row["qb_talent"] == 50.0
    assert row["qb_situation_index"] < 1.0
    assert abs(row["class_mult"] - 0.92) < 1e-9
