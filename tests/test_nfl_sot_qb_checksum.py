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
    # 2026-09-02: Kyler restored to ARI; McCarthy is MIN (GB@MIN attribution).
    assert "Kyler" in depth["ARI"] or "Murray" in depth["ARI"]
    assert "Kyler" not in depth.get("MIN", "")
    assert "McCarthy" in depth["MIN"] or "J.J" in depth["MIN"]

def test_published_bundle_checksum_when_present() -> None:
    bundle = ROOT / "data/ops/nfl-preseason-sim-2026-20260813T132801Z"
    if not (bundle / "player_regular_season_totals.csv").is_file():
        return
    result = checksum(bundle)
    assert result["ok"], result.get("failed")
