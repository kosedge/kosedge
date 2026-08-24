"""NFL Current-line hygiene: simple book-line gate, never invent a nearby line."""

from __future__ import annotations

from src.services.nfl_market_line_hygiene import (
    apply_nfl_current_hygiene,
    consensus_nfl_spread,
    consensus_nfl_total,
    sanitize_nfl_ml,
    sanitize_nfl_spread,
    sanitize_nfl_total,
    to_float,
)


def test_keeps_posted_book_lines() -> None:
    assert sanitize_nfl_spread(-3.5) == (-3.5, None)
    assert sanitize_nfl_spread(-3.0) == (-3.0, None)
    assert sanitize_nfl_spread(0) == (0.0, None)  # PK
    assert sanitize_nfl_spread(0.5) == (0.5, None)
    assert sanitize_nfl_spread(7) == (7.0, None)
    assert sanitize_nfl_spread(-20) == (-20.0, None)
    assert sanitize_nfl_total(44.5) == (44.5, None)
    assert sanitize_nfl_total(30) == (30.0, None)
    assert sanitize_nfl_total(65) == (65.0, None)
    assert sanitize_nfl_ml(-150) == (-150.0, None)
    assert sanitize_nfl_ml(130) == (130.0, None)


def test_parses_unicode_minus() -> None:
    assert to_float("−3.5") == -3.5
    assert sanitize_nfl_spread("−3.5") == (-3.5, None)
    assert sanitize_nfl_spread("\u22127") == (-7.0, None)
    assert sanitize_nfl_total("44.5") == (44.5, None)


def test_does_not_reject_current_equal_open() -> None:
    open_s, cur_s = -3.5, -3.5
    assert sanitize_nfl_spread(open_s)[0] == open_s
    assert sanitize_nfl_spread(cur_s)[0] == cur_s
    assert cur_s == open_s


def test_rejects_avg_garbage_and_does_not_round() -> None:
    assert sanitize_nfl_spread(-3.58) == (None, "not_half_point")
    assert sanitize_nfl_spread(3.8) == (None, "not_half_point")
    assert sanitize_nfl_spread(2.4) == (None, "not_half_point")
    assert sanitize_nfl_spread(0.17) == (None, "not_half_point")
    assert sanitize_nfl_total(44.42) == (None, "not_half_point")
    assert sanitize_nfl_spread(-110) == (None, "out_of_range")
    assert sanitize_nfl_spread(44.5) == (None, "out_of_range")
    assert sanitize_nfl_spread(25) == (None, "out_of_range")
    assert sanitize_nfl_total(2.4) == (None, "out_of_range")
    assert sanitize_nfl_total(80) == (None, "out_of_range")
    assert sanitize_nfl_ml(3.8) == (None, "not_american_ml")
    assert sanitize_nfl_ml(0) == (None, "out_of_range")


def test_mode_of_valid_samples_not_average() -> None:
    value, reason = consensus_nfl_spread([-3.5, -4.0, -3.5])
    assert reason is None
    assert value == -3.5
    value, reason = consensus_nfl_spread([-3.5, -3.0])
    assert value == -3.0
    value, reason = consensus_nfl_spread(["−3.5", -4.0, "−3.5"])
    assert value == -3.5
    value, reason = consensus_nfl_total([44.5, 44.0, 44.5])
    assert value == 44.5
    value, reason = consensus_nfl_spread([-3.58])
    assert value is None
    assert reason == "not_half_point"


def test_mode_ignores_invalid_books() -> None:
    value, reason = consensus_nfl_spread([-3.5, 3.8, 2.4, -3.5])
    assert value == -3.5
    assert reason is None
    value, reason = consensus_nfl_spread([3.8, 2.4, -3.58])
    assert value is None
    assert reason == "not_half_point"


def test_apply_hygiene_nulls_invalid_independently() -> None:
    market = {
        "market_spread_home": -3.58,
        "best_spread_home": -3.58,
        "market_total": 44.5,
        "best_total": 44.42,
        "market_home_ml": -150,
        "market_away_ml": 3.8,
        "dk_spread_home": -3.5,
        "open_spread_home": -3.0,
    }
    apply_nfl_current_hygiene(market)
    assert market["market_spread_home"] is None
    assert market["best_spread_home"] is None
    assert market["dk_spread_home"] == -3.5
    assert market["market_total"] == 44.5
    assert market["best_total"] is None
    assert market["market_home_ml"] == -150.0
    assert market["market_away_ml"] is None
    assert market["open_spread_home"] == -3.0


_WEEK1_DOCUMENTED_AVG = {
    "NE@SEA": (-3.58, 44.42),
    "CLE@JAX": (-7.42, 40.5),
    "BUF@HOU": (0.17, 44.5),
    "ATL@PIT": (-3.08, 42.25),
    "WAS@PHI": (-4.75, 46.75),
    "SF@LAR": (-3.5, 48.5),
    "TB@CIN": (-3.5, 51.5),
}


def test_week1_documented_avg_garbage_is_blank_not_repaired() -> None:
    for game, (spread, total) in _WEEK1_DOCUMENTED_AVG.items():
        cleaned_s, _reason_s = sanitize_nfl_spread(spread)
        cleaned_t, _reason_t = sanitize_nfl_total(total)
        if game in {"SF@LAR", "TB@CIN"}:
            assert cleaned_s == -3.5
            assert cleaned_t == total
            continue
        if game == "CLE@JAX":
            assert cleaned_s is None
            assert cleaned_t == 40.5
            continue
        if game == "BUF@HOU":
            assert cleaned_s is None
            assert cleaned_t == 44.5
            continue
        assert cleaned_s is None, game
        assert cleaned_t is None, game


def test_week1_posted_snapshot_lines_pass() -> None:
    """Live post-#288 snapshot consensus (mode of books) — all 16 should pass."""
    slate = [
        ("ARI@LAC", -10.5, 46.5),
        ("ATL@PIT", -3.0, 42.5),
        ("BAL@IND", 3.5, 48.5),
        ("BUF@HOU", 1.5, 44.5),
        ("CHI@CAR", 2.5, 47.5),
        ("CLE@JAX", -7.5, 40.5),
        ("DAL@NYG", 2.5, 48.5),
        ("DEN@KC", -3.0, 42.5),
        ("GB@MIN", -1.5, 45.0),
        ("MIA@LV", -3.5, 40.5),
        ("NE@SEA", -3.5, 44.5),
        ("NO@DET", -7.0, 48.5),
        ("NYJ@TEN", -2.5, 39.5),
        ("SF@LAR", -3.5, 48.5),
        ("TB@CIN", -3.5, 51.5),
        ("WAS@PHI", -4.5, 46.5),
    ]
    assert len(slate) == 16
    kept = 0
    for game, spread, total in slate:
        ps, rs = sanitize_nfl_spread(spread)
        pt, rt = sanitize_nfl_total(total)
        assert ps == spread, f"{game} spread {spread} {rs}"
        assert pt == total, f"{game} total {total} {rt}"
        kept += 1
    assert kept == 16
