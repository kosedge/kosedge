"""NFL Current-line hygiene: reject non-book shapes, never invent a nearby line."""

from __future__ import annotations

from src.services.nfl_market_line_hygiene import (
    apply_nfl_current_hygiene,
    consensus_nfl_spread,
    consensus_nfl_total,
    sanitize_nfl_ml,
    sanitize_nfl_spread,
    sanitize_nfl_total,
)


def test_keeps_posted_half_points() -> None:
    assert sanitize_nfl_spread(-3.5) == (-3.5, None)
    assert sanitize_nfl_spread(-3.0) == (-3.0, None)
    assert sanitize_nfl_spread(0.5) == (0.5, None)
    assert sanitize_nfl_spread(-0.5) == (-0.5, None)
    assert sanitize_nfl_spread(1.5) == (1.5, None)
    assert sanitize_nfl_spread(-20.5) == (-20.5, None)
    assert sanitize_nfl_total(44.5) == (44.5, None)
    assert sanitize_nfl_total(40.5) == (40.5, None)
    assert sanitize_nfl_total(48.0) == (48.0, None)
    assert sanitize_nfl_ml(-150) == (-150.0, None)
    assert sanitize_nfl_ml(130) == (130.0, None)
    assert sanitize_nfl_ml(1.91) == (1.91, None)


def test_rejects_avg_garbage_and_does_not_round() -> None:
    assert sanitize_nfl_spread(-3.58) == (None, "not_half_point")
    assert sanitize_nfl_spread(-3.08) == (None, "not_half_point")
    assert sanitize_nfl_spread(-4.75) == (None, "not_half_point")
    assert sanitize_nfl_spread(0.17) == (None, "looks_like_probability")
    assert sanitize_nfl_spread(3.8) == (None, "not_half_point")
    assert sanitize_nfl_spread(2.4) == (None, "not_half_point")
    assert sanitize_nfl_total(44.42) == (None, "not_half_point")
    assert sanitize_nfl_total(42.25) == (None, "not_half_point")
    assert sanitize_nfl_total(46.75) == (None, "not_half_point")
    assert sanitize_nfl_total(2.4) == (None, "looks_like_spread")
    assert sanitize_nfl_total(3.8) == (None, "looks_like_spread")


def test_rejects_null_zero_outliers_swapped_and_probs() -> None:
    assert sanitize_nfl_spread(None)[0] is None
    assert sanitize_nfl_spread(0) == (None, "zero")
    assert sanitize_nfl_spread(0.42) == (None, "looks_like_probability")
    assert sanitize_nfl_spread(-110) == (None, "looks_like_ml")
    assert sanitize_nfl_spread(44.5) == (None, "looks_like_total")
    assert sanitize_nfl_spread(25) == (None, "out_of_range")
    assert sanitize_nfl_total(0) == (None, "zero")
    assert sanitize_nfl_total(7.5) == (None, "looks_like_spread")
    assert sanitize_nfl_total(80) == (None, "out_of_range")
    assert sanitize_nfl_ml(0) == (None, "zero")
    assert sanitize_nfl_ml(-66) == (None, "out_of_range")
    assert sanitize_nfl_ml(3.5) == (None, "looks_like_spread")
    assert sanitize_nfl_ml(3.8) == (None, "looks_like_spread")


def test_mode_of_valid_samples_not_average() -> None:
    value, reason = consensus_nfl_spread([-3.5, -4.0, -3.5])
    assert reason is None
    assert value == -3.5
    value, reason = consensus_nfl_spread([-3.5, -3.0])
    assert value == -3.0  # tie → smaller abs, not −3.25
    value, reason = consensus_nfl_spread([1.5, 0.5, -1.5])
    assert value == 0.5
    value, reason = consensus_nfl_total([44.5, 44.0, 44.5])
    assert value == 44.5
    # Scalar AVG garbage is not repaired into a nearby line.
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
        "open_spread_home": -3.0,  # Open is not a Current field; leave it
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


# Documented post-#287 live AVG currents (Week 1). Do not round these into nearby lines.
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
        cleaned_s, reason_s = sanitize_nfl_spread(spread)
        cleaned_t, reason_t = sanitize_nfl_total(total)
        if game in {"SF@LAR", "TB@CIN"}:
            assert cleaned_s == -3.5
            assert cleaned_t == total
            continue
        if game == "CLE@JAX":
            assert cleaned_s is None and reason_s == "not_half_point"
            assert cleaned_t == 40.5  # total already posted-shaped
            continue
        if game == "BUF@HOU":
            assert cleaned_s is None
            assert cleaned_t == 44.5
            continue
        assert cleaned_s is None, game
        assert cleaned_t is None, f"{game} total {total} reason={reason_t}"
        # Never invent −3.58 → −3.5.
        if spread == -3.58:
            assert cleaned_s is None


def test_week1_slate_every_painted_current_is_book_shaped_or_blank() -> None:
    """16 Week 1 games from live post-#287 AVG currents. Open unchanged."""
    # (game, open_s, avg_s, open_t, avg_t) — Railway 2026-08-23
    slate = [
        ("ARI@LAC", -10.5, -10.42, 46.5, 46.5),
        ("ATL@PIT", -3.0, -3.08, 41.5, 42.25),
        ("BAL@IND", 3.5, 3.42, 48.5, 48.33),
        ("BUF@HOU", 1.5, 0.17, 44.5, 44.5),
        ("CHI@CAR", 2.5, 2.58, 45.5, 47.5),
        ("CLE@JAX", -7.5, -7.42, 40.5, 40.5),
        ("DAL@NYG", 2.5, 2.58, 48.5, 48.42),
        ("DEN@KC", -3.0, -2.83, 42.5, 42.83),
        ("GB@MIN", -1.5, -0.92, 45.5, 45.08),
        ("MIA@LV", -3.5, -3.58, 40.5, 40.42),
        ("NE@SEA", -3.5, -3.58, 44.5, 44.42),
        ("NO@DET", -7.0, -7.08, 49.5, 49.0),
        ("NYJ@TEN", -2.5, -2.58, 38.5, 39.08),
        ("SF@LAR", -3.5, -3.5, 48.5, 48.5),
        ("TB@CIN", -3.5, -3.5, 52.5, 51.5),
        ("WAS@PHI", -4.5, -4.75, 47.5, 46.75),
    ]
    assert len(slate) == 16
    kept_spread = blank_spread = kept_total = blank_total = 0
    for game, open_s, cur_s, open_t, cur_t in slate:
        assert sanitize_nfl_spread(open_s)[0] == open_s, game
        assert sanitize_nfl_total(open_t)[0] == open_t, game
        painted_s, _ = sanitize_nfl_spread(cur_s)
        painted_t, _ = sanitize_nfl_total(cur_t)
        if painted_s is None:
            blank_spread += 1
        else:
            kept_spread += 1
            assert painted_s == cur_s
        if painted_t is None:
            blank_total += 1
        else:
            kept_total += 1
            assert painted_t == cur_t
        if game in {"NE@SEA", "CLE@JAX"}:
            assert painted_s is None, game
        if painted_s is None:
            assert cur_s != open_s
    assert kept_spread + blank_spread == 16
    assert kept_total + blank_total == 16
    assert kept_spread == 2  # SF@LAR, TB@CIN only
    assert blank_spread == 14
    assert kept_total == 7
    assert blank_total == 9
