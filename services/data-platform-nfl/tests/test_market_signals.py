from __future__ import annotations

from data_platform_nfl.market_signals import (
    _american_to_implied_prob,
    market_probabilities_to_percentile_ranks,
)


def test_american_to_implied_prob_favorite_and_underdog() -> None:
    favorite = _american_to_implied_prob(-200)
    underdog = _american_to_implied_prob(150)
    assert favorite > 0.5
    assert underdog < 0.5


def test_percentile_ranks_are_bounded_and_ordered() -> None:
    probs = {"KC": 0.20, "DET": 0.02, "NE": 0.001, "JAX": 0.08}
    ranks = market_probabilities_to_percentile_ranks(probs)
    assert ranks["KC"] == 1.0
    assert ranks["NE"] == 0.0
    assert ranks["NE"] < ranks["DET"] < ranks["JAX"] < ranks["KC"]
    assert all(0.0 <= v <= 1.0 for v in ranks.values())
