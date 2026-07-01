from src.services.mlb_market_maker import (
    american_from_prob,
    american_implied_prob,
    no_vig_two_way_prob,
    synthetic_no_vig_from_books,
)


def test_american_implied_prob() -> None:
    assert round(american_implied_prob(-120) or 0.0, 4) > 0.5
    assert round(american_implied_prob(110) or 0.0, 4) < 0.5


def test_no_vig_two_way_prob_normalizes() -> None:
    p = no_vig_two_way_prob(-120, 110)
    assert p is not None
    assert 0.0 < p < 1.0


def test_american_from_prob_round_trips_reasonably() -> None:
    line = american_from_prob(0.57)
    assert line is not None
    implied = american_implied_prob(line)
    assert implied is not None
    assert abs(implied - 0.57) < 0.02


def test_synthetic_no_vig_from_books() -> None:
    p = synthetic_no_vig_from_books(
        [("pinnacle", -130), ("draftkings", -125), ("fanduel", -122)],
        [("pinnacle", 118), ("draftkings", 112), ("fanduel", 110)],
    )
    assert p is not None
    assert 0.5 < p < 0.65


def test_synthetic_no_vig_from_books_ignores_unpaired_outlier_books() -> None:
    p = synthetic_no_vig_from_books(
        [
            ("pinnacle", -130),
            ("draftkings", -125),
            ("rogue_unpaired", -350),
        ],
        [("pinnacle", 118), ("draftkings", 112)],
    )
    assert p is not None
    assert 0.52 < p < 0.58
