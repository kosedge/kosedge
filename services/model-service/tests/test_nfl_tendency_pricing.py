from __future__ import annotations

from src.services.nfl_tendency_pricing import (
    apply_tendency_to_player_pass_rate,
    tendency_game_signals,
    tendency_pass_rate_factor,
)


def test_tendency_pass_rate_factor_is_bounded() -> None:
    assert 0.94 <= tendency_pass_rate_factor(0.10) <= 1.06
    assert 0.94 <= tendency_pass_rate_factor(-0.10) <= 1.06


def test_tendency_game_signals_mild() -> None:
    signals = tendency_game_signals(0.05, -0.02)
    assert abs(signals["spread_signal"]) <= 0.6
    assert abs(signals["total_signal"]) <= 1.2


def test_apply_tendency_multiplies_base() -> None:
    proe = {"KC": 0.06, "BAL": -0.02}
    out = apply_tendency_to_player_pass_rate(1.0, team="KC", opponent="BAL", proe_by_team=proe)
    assert out > 1.0
    assert out <= 1.35
