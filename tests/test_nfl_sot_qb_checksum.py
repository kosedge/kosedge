"""SoT QB checksum — dual-map must not publish."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "nfl"))
sys.path.insert(0, str(ROOT / "services" / "model-service" / "src"))

from check_nfl_sot_qb_checksum import checksum, _depth_qb1  # noqa: E402


def test_depth_pack_qb1_is_post_swap_sot() -> None:
    depth = _depth_qb1(2026)
    assert "Tua" in depth["ATL"]
    assert "Willis" in depth["MIA"]
    assert "Kyler" in depth["MIN"] or "Murray" in depth["MIN"]
    assert "Kyler" not in depth.get("ARI", "")


def test_published_bundle_checksum_when_present() -> None:
    bundle = ROOT / "data/ops/nfl-preseason-sim-2026-20260813T132801Z"
    if not (bundle / "player_regular_season_totals.csv").is_file():
        return
    result = checksum(bundle)
    assert result["ok"], result.get("failed")
