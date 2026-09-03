"""CFB spread PLAY sit — mirrors apps/web/lib/cfb-trusted-market.ts."""

from __future__ import annotations

from src.services.book_ledger.cfb_trusted_market import (
    ABSURD_VS_KEI_PTS,
    LEAN_EDGE_PTS,
    PLAY_EDGE_PTS,
    SPREAD_PLAY_ELIGIBLE,
    TOTALS_PLAY_ELIGIBLE,
    cfb_edge_tag,
    cfb_publish_tag_from_edge,
    trust_cfb_market,
)

W1_SPREAD_PLAYS = [
    ("OKST@TLSA", 11.7),
    ("MOST@TAMU", 11.0),
    ("KENT@SCAR", 10.7),
    ("UTEP@OU", 10.4),
    ("BC@CIN", 10.3),
    ("BALL@OSU", 10.0),
    ("CLEM@LSU", 9.0),
    ("UNT@IU", 8.9),
    ("NIU@IOWA", 8.7),
    ("TXST@TEX", 7.1),
    ("WIS@ND", 6.2),
    ("WYO@CSU", 6.1),
    ("TOL@MSU", 6.1),
    ("WKU@NEV", 5.9),
    ("WSU@WASH", 5.9),
    ("CCU@WVU", 5.7),
    ("UNLV@HAW", 5.5),
    ("SMU@FSU", 5.4),
    ("MRSH@PSU", 5.3),
    ("CMU@UNM", 5.2),
    ("UAB@ILL", 4.9),
    ("FRES@USC", 4.8),
    ("LOU@MISS", 4.6),
    ("TULN@DUKE", 4.4),
    ("ARST@MEM", 4.1),
]

W1_SPREAD_LEANS = [
    ("MASS@RUT", 3.9),
    ("FIU@USF", 3.9),
    ("LIB@JMU", 2.9),
    ("BOISE@ORE", 2.5),
]


def test_spread_play_flag_and_cuts():
    assert SPREAD_PLAY_ELIGIBLE is False
    assert TOTALS_PLAY_ELIGIBLE is False
    assert PLAY_EDGE_PTS == 4.0
    assert LEAN_EDGE_PTS == 2.5
    assert ABSURD_VS_KEI_PTS == 12.0


def test_named_w1_spread_plays_become_pass():
    assert len(W1_SPREAD_PLAYS) >= 24
    for pair, edge in W1_SPREAD_PLAYS:
        assert abs(edge) >= PLAY_EDGE_PTS
        assert cfb_edge_tag(abs(edge), "spread") == "PASS", pair
        assert cfb_publish_tag_from_edge(abs(edge), "spread") == "PASS", pair
        assert cfb_edge_tag(abs(edge), "total") == "PASS", pair


def test_spread_leans_preserved():
    for pair, edge in W1_SPREAD_LEANS:
        abs_e = abs(edge)
        assert LEAN_EDGE_PTS <= abs_e < PLAY_EDGE_PTS
        assert cfb_edge_tag(abs_e, "spread") == "LEAN", pair


def test_play_band_pass_lean_band_lean():
    assert cfb_edge_tag(4.0, "spread") == "PASS"
    assert cfb_edge_tag(11.5, "spread") == "PASS"
    assert cfb_edge_tag(3.0, "spread") == "LEAN"
    assert cfb_edge_tag(2.5, "spread") == "LEAN"
    assert cfb_edge_tag(2.0, "spread") == "PASS"


def test_absurd_12_untrusted_no_play():
    gaps = [20.0, 18.5, 16.2, 15.0, 14.1, 13.8, 13.2, 12.9, 12.4, 12.1, 12.0]
    assert len(gaps) == 11
    for gap in gaps:
        v = trust_cfb_market(kei=50 + gap, best=50.0, open_line=50.0, book_count=2)
        assert v["trusted"] is False
        assert v["reason"] == "absurd_vs_kei"
        assert cfb_edge_tag(gap, "spread") == "PASS"


def test_publish_equals_display():
    for edge in (11.5, 4.0, 3.8, 2.8, 2.0, None):
        for market in ("total", "spread"):
            assert cfb_publish_tag_from_edge(edge, market) == cfb_edge_tag(edge, market)


def test_totals_still_never_play():
    assert cfb_edge_tag(4.1, "total") == "PASS"
    assert cfb_edge_tag(11.5, "total") == "PASS"
    assert cfb_edge_tag(3.0, "total") == "LEAN"
