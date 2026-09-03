"""CFB totals PLAY sit — mirrors apps/web/lib/cfb-trusted-market.ts."""

from __future__ import annotations

from src.services.book_ledger.cfb_trusted_market import (
    ABSURD_VS_KEI_PTS,
    LEAN_EDGE_PTS,
    PLAY_EDGE_PTS,
    TOTALS_PLAY_ELIGIBLE,
    cfb_edge_tag,
    cfb_publish_tag_from_edge,
    trust_cfb_market,
)

W1_PLAY_OVERS = [
    ("UNLV@HAW", 11.5),
    ("TOL@MSU", 11.3),
    ("MASS@RUT", 11.2),
    ("MIA@STAN", 11.1),
    ("LOU@MISS", 10.4),
    ("WSU@WASH", 10.1),
    ("WIS@ND", 9.7),
    ("NIU@IOWA", 9.6),
    ("UAB@ILL", 8.3),
    ("WKU@NEV", 8.2),
    ("KENT@SC", 8.1),
    ("LIB@JMU", 7.8),
    ("ARST@MEM", 7.7),
    ("FRES@USC", 7.4),
    ("UNT@IU", 7.3),
    ("ECU@ALA", 7.1),
    ("SMU@FSU", 7.0),
    ("BAY@AUB", 5.9),
    ("COLO@GT", 5.5),
    ("SHSU@TROY", 5.2),
    ("BALL@OSU", 5.1),
    ("WYO@CSU", 4.7),
    ("ULM@MSST", 4.5),
    ("ORST@HOU", 4.3),
]

W1_LEANS = [
    ("UCLA@Cal", 3.8),
    ("OKST@Tulsa", -2.8),
]


def test_totals_play_flag_and_cuts():
    assert TOTALS_PLAY_ELIGIBLE is False
    assert PLAY_EDGE_PTS == 4.0
    assert LEAN_EDGE_PTS == 2.5
    assert ABSURD_VS_KEI_PTS == 12.0


def test_named_w1_play_overs_become_pass():
    assert len(W1_PLAY_OVERS) == 24
    for pair, edge in W1_PLAY_OVERS:
        assert abs(edge) >= PLAY_EDGE_PTS
        assert cfb_edge_tag(abs(edge), "total") == "PASS", pair
        assert cfb_publish_tag_from_edge(abs(edge), "total") == "PASS", pair
        assert cfb_edge_tag(abs(edge), "spread") == "PASS", pair


def test_leans_preserved():
    for pair, edge in W1_LEANS:
        abs_e = abs(edge)
        assert LEAN_EDGE_PTS <= abs_e < PLAY_EDGE_PTS
        assert cfb_edge_tag(abs_e, "total") == "LEAN", pair


def test_absurd_12_untrusted_no_play():
    gaps = [20.0, 18.5, 16.2, 15.0, 14.1, 13.8, 13.2, 12.9, 12.4, 12.1, 12.0]
    assert len(gaps) == 11
    for gap in gaps:
        v = trust_cfb_market(kei=50 + gap, best=50.0, open_line=50.0, book_count=2)
        assert v["trusted"] is False
        assert v["reason"] == "absurd_vs_kei"
        assert cfb_edge_tag(gap, "total") == "PASS"


def test_publish_equals_display():
    for edge in (11.5, 4.0, 3.8, 2.8, 2.0, None):
        for market in ("total", "spread"):
            assert cfb_publish_tag_from_edge(edge, market) == cfb_edge_tag(edge, market)


def test_spread_also_sat():
    assert cfb_edge_tag(4.0, "spread") == "PASS"
    assert cfb_edge_tag(3.0, "spread") == "LEAN"
    assert cfb_edge_tag(2.0, "spread") == "PASS"
