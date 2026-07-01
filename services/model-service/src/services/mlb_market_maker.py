from __future__ import annotations

from typing import Iterable, Optional, Tuple

from src.services.mlb_market_consensus import book_weight, weighted_consensus


def american_implied_prob(price: Optional[int]) -> Optional[float]:
    if price is None:
        return None
    if price > 0:
        return 100.0 / (price + 100.0)
    return abs(price) / (abs(price) + 100.0)


def no_vig_two_way_prob(price_a: Optional[int], price_b: Optional[int]) -> Optional[float]:
    pa = american_implied_prob(price_a)
    pb = american_implied_prob(price_b)
    if pa is None or pb is None:
        return None
    total = pa + pb
    if total <= 0:
        return None
    return pa / total


def american_from_prob(probability: Optional[float]) -> Optional[int]:
    if probability is None:
        return None
    prob = min(0.9999, max(0.0001, probability))
    if prob >= 0.5:
        return int(round(-(100.0 * prob / (1.0 - prob))))
    return int(round((100.0 * (1.0 - prob) / prob)))


def synthetic_no_vig_from_books(
    home_prices: Iterable[Tuple[str, int]],
    away_prices: Iterable[Tuple[str, int]],
) -> Optional[float]:
    home_map = {str(book): int(price) for book, price in home_prices}
    away_map = {str(book): int(price) for book, price in away_prices}

    paired_probs: list[tuple[str, float]] = []
    for book in sorted(set(home_map) & set(away_map)):
        prob = no_vig_two_way_prob(home_map[book], away_map[book])
        if prob is not None:
            paired_probs.append((book, prob))

    if paired_probs:
        total_weight = 0.0
        weighted_sum = 0.0
        for book, probability in paired_probs:
            weight = book_weight(book)
            total_weight += weight
            weighted_sum += weight * probability
        if total_weight > 0:
            return weighted_sum / total_weight

    home_implied = weighted_consensus(
        (book, american_implied_prob(price))
        for book, price in home_map.items()
        if american_implied_prob(price) is not None
    )
    away_implied = weighted_consensus(
        (book, american_implied_prob(price))
        for book, price in away_map.items()
        if american_implied_prob(price) is not None
    )
    if home_implied is None or away_implied is None:
        return None
    total = home_implied + away_implied
    if total <= 0:
        return None
    return home_implied / total

