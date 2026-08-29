"""Market info_overlap MVP — classify only; no KEI juice / accepts."""

from __future__ import annotations

from src.services.nfl_kei_week1_reprice import apply_week1_kei_reprice, load_week1_pack
from src.services.nfl_market_info_overlap import (
    INFO_OVERLAP_VERSION,
    MARKET_MOVE_THRESHOLD,
    attach_info_overlap_to_kei_log,
    classify_info_overlap,
    extract_kei_situation_flags,
)


def test_classify_kei_ahead_when_market_flat() -> None:
    assert (
        classify_info_overlap(
            kei_spread_delta=0.55,
            market_line=-3.0,
            market_line_at_pack=-3.0,
            pack_as_of="2026-08-29",
        )
        == "kei_ahead"
    )


def test_classify_market_ahead_same_side_move() -> None:
    # KEI home weaker (+0.55); market also home weaker (-3 → -1.0) beyond aligned band
    assert (
        classify_info_overlap(
            kei_spread_delta=0.55,
            market_line=-1.0,
            market_line_at_pack=-3.0,
            pack_as_of="2026-08-29",
            market_as_of="2026-08-29T18:00:00Z",
        )
        == "market_ahead"
    )


def test_classify_aligned_near_kei_delta() -> None:
    assert (
        classify_info_overlap(
            kei_spread_delta=1.0,
            market_line=-2.0,
            market_line_at_pack=-3.0,
            pack_as_of="2026-08-29",
        )
        == "aligned"
    )


def test_classify_unknown_missing_market() -> None:
    assert (
        classify_info_overlap(
            kei_spread_delta=0.5,
            market_line=None,
            market_line_at_pack=-3.0,
            pack_as_of="2026-08-29",
        )
        == "unknown"
    )
    assert (
        classify_info_overlap(
            kei_spread_delta=0.5,
            market_line=-2.5,
            market_line_at_pack=-3.0,
            pack_as_of="",
        )
        == "unknown"
    )


def test_opposite_side_is_unknown() -> None:
    # KEI home weaker; market home stronger
    assert (
        classify_info_overlap(
            kei_spread_delta=0.8,
            market_line=-4.0,
            market_line_at_pack=-3.0,
            pack_as_of="2026-08-29",
        )
        == "unknown"
    )


def test_attach_does_not_claim_juice() -> None:
    log = {
        "spread_delta": 0.55,
        "pack_as_of": "2026-08-29",
        "applied_factors": [
            {"factor": "injury", "applied": True, "reason": "S1 out"},
            {"factor": "injury_net", "applied": True, "reason": "net"},
        ],
    }
    out = attach_info_overlap_to_kei_log(
        log,
        market_line=-1.0,
        market_line_at_pack=-3.0,
        market_as_of="2026-08-29T18:00:00Z",
    )
    assert out["info_overlap"] == "market_ahead"
    assert out["kei_situation_flags"] == ["injury"]
    assert out["market_line"] == -1.0
    assert out["market_as_of"] == "2026-08-29T18:00:00Z"
    assert out["info_overlap_card"]["market_ahead_adds_kei_juice"] is False
    assert out["spread_delta"] == 0.55  # unchanged
    assert INFO_OVERLAP_VERSION == "info_overlap_v1"
    assert MARKET_MOVE_THRESHOLD == 0.5


def test_kei_reprice_attaches_overlap_without_changing_spread() -> None:
    pack = load_week1_pack(2026)
    handicap = {"spread_home": -3.0, "total_mean": 44.0}
    new_h, log = apply_week1_kei_reprice(
        handicap=handicap,
        home_abbr="MIN",
        away_abbr="GB",
        week=1,
        season=2026,
        pack=pack,
        market_line=-3.0,
        market_line_at_pack=-3.0,
        market_as_of="2026-08-29T12:00:00Z",
    )
    # Handicap path unchanged by overlap attachment.
    assert "spread_home" in new_h
    assert "info_overlap" in log
    assert log["info_overlap"] in {"unknown", "kei_ahead", "market_ahead", "aligned"}
    assert isinstance(log.get("kei_situation_flags"), list)
    assert extract_kei_situation_flags(log) == log["kei_situation_flags"]
