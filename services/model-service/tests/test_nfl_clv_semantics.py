from datetime import date

from src.services.nfl_clv_semantics import (
    NFL_CLV_DEFINITION,
    assess_live_clv_trust,
    classify_clv,
    market_summary_from_counts,
    moneyline_clv,
    spread_clv,
    summarize_clv_values,
    total_clv,
)


def test_definition_says_beat_the_close() -> None:
    assert "beat the close" in NFL_CLV_DEFINITION.lower()
    assert "recommended side" in NFL_CLV_DEFINITION.lower()


def test_moneyline_shortening_plus_price_is_beat() -> None:
    # Bet +150 (imp 40%). Close +120 (imp ~45.45%). Market moved toward us.
    clv = moneyline_clv(open_price=150, close_price=120)
    assert clv > 0
    assert classify_clv(clv) == "beat"
    assert abs(clv - (100.0 / 220.0 - 100.0 / 250.0)) < 1e-12


def test_moneyline_identical_line_is_push() -> None:
    clv = moneyline_clv(open_price=150, close_price=150)
    assert clv == 0.0
    assert classify_clv(clv) == "push"


def test_moneyline_lengthening_plus_price_is_lose() -> None:
    clv = moneyline_clv(open_price=150, close_price=180)
    assert clv < 0
    assert classify_clv(clv) == "lose"


def test_moneyline_favorite_getting_shorter_is_beat() -> None:
    # Bet -110 (imp ~52.38%). Close -130 (imp ~56.52%).
    clv = moneyline_clv(open_price=-110, close_price=-130)
    assert clv > 0
    assert classify_clv(clv) == "beat"


def test_total_over_line_rising_is_beat() -> None:
    clv = total_clv(side="over", open_total=44.5, close_total=46.0)
    assert clv == 1.5
    assert classify_clv(clv) == "beat"


def test_total_over_line_falling_is_lose() -> None:
    clv = total_clv(side="over", open_total=44.5, close_total=43.0)
    assert clv == -1.5
    assert classify_clv(clv) == "lose"


def test_total_under_line_falling_is_beat() -> None:
    clv = total_clv(side="under", open_total=44.5, close_total=43.0)
    assert clv == 1.5
    assert classify_clv(clv) == "beat"


def test_spread_home_getting_heavier_is_beat() -> None:
    clv = spread_clv(side="home", open_spread_home=-3.0, close_spread_home=-6.5)
    assert clv == 3.5
    assert classify_clv(clv) == "beat"


def test_total_unchanged_is_push() -> None:
    clv = total_clv(side="over", open_total=44.5, close_total=44.5)
    assert clv == 0.0
    assert classify_clv(clv) == "push"


def test_zeros_are_pushes_not_losses_in_beat_close_rate() -> None:
    summary = summarize_clv_values([0.05, 0.0, 0.0, 0.0, -0.02, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert summary["n"] == 11
    assert summary["beat_close"] == 1
    assert summary["push"] == 9
    assert summary["lose_close"] == 1
    # Old Tracking math: 1/11 ≈ 9.1% — zeros counted as non-positive.
    assert abs(summary["positive_clv_rate"] - (1 / 11)) < 1e-12
    # Honest beat-close among moved lines: 1/2 = 50%.
    assert summary["beat_close_rate"] == 0.5
    assert summary["decided_n"] == 2


def test_all_pushes_have_no_beat_close_rate() -> None:
    summary = market_summary_from_counts(
        n=20, beat=0, push=20, lose=0, avg_clv=0.0
    )
    assert summary["beat_close_rate"] is None
    assert summary["positive_clv_rate"] == 0.0


def test_august_2026_live_clv_is_not_trustworthy() -> None:
    trust = assess_live_clv_trust(
        as_of=date(2026, 8, 12),
        n=90,
        beat=8,
        push=80,
        lose=2,
    )
    assert trust["trustworthy"] is False
    assert "preseason_no_reg_closes" in trust["reasons"]
    assert "majority_identical_open_close" in trust["reasons"]


def test_in_season_moved_sample_is_trustworthy() -> None:
    trust = assess_live_clv_trust(
        as_of=date(2026, 10, 15),
        n=80,
        beat=42,
        push=6,
        lose=32,
    )
    assert trust["trustworthy"] is True
    assert trust["reasons"] == []
