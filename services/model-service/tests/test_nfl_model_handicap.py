"""Unit tests for NFL model_* vs handicap_* (KEI) helpers."""

from __future__ import annotations

from src.services.nfl_model_handicap import (
    annotate_projection_model_handicap,
    fair_lines_model_handicap_fields,
    pre_blend_model_markets_from_diagnostics,
    resolve_model_and_handicap,
    resolve_model_markets,
    snapshot_markets,
)


def _markets(*, spread: float = -3.5, total: float = 44.0, win: float = 0.58) -> dict:
    return {
        "home_win_prob": win,
        "away_win_prob": round(1.0 - win, 4),
        "total_mean": total,
        "spread_home": spread,
        "fair_home_ml": -140,
        "fair_away_ml": 120,
    }


def test_identity_when_no_blend() -> None:
    markets = _markets()
    projection = {"markets": markets, "diagnostics": {"market_blend": {"spread_applied": False, "total_applied": False}}}
    model = resolve_model_markets(markets, projection=projection)
    assert model["spread_home"] == -3.5
    assert model["total_mean"] == 44.0


def test_pre_blend_derives_model_spread_and_total() -> None:
    markets = _markets(spread=-2.0, total=46.5)
    projection = {
        "markets": markets,
        "diagnostics": {
            "market_blend": {
                "spread_applied": True,
                "total_applied": True,
                "pre_blend_margin_mean": 4.2,  # home favored by 4.2 → spread -4.2
                "pre_blend_total_mean": 43.1,
                "post_blend_margin_mean": 2.0,
                "post_blend_total_mean": 46.5,
            }
        },
    }
    derived = pre_blend_model_markets_from_diagnostics(projection)
    assert derived is not None
    assert derived["spread_home"] == -4.2
    assert derived["total_mean"] == 43.1
    # ML stays from published markets (no pre-blend ML).
    assert derived["fair_home_ml"] == -140


def test_annotate_model_role_stamps_split() -> None:
    projection = {
        "markets": _markets(spread=-2.0, total=46.5),
        "diagnostics": {
            "market_blend": {
                "spread_applied": True,
                "total_applied": True,
                "pre_blend_margin_mean": 3.5,
                "pre_blend_total_mean": 42.0,
            }
        },
    }
    annotate_projection_model_handicap(projection, line_role="model")
    assert projection["model_markets"]["spread_home"] == -3.5
    assert projection["handicap_markets"]["spread_home"] == -2.0
    assert projection["model_total_mean"] == 42.0
    assert projection["handicap_total_mean"] == 46.5
    assert projection["line_role"] == "model"


def test_handicap_role_preserves_prior_model() -> None:
    prior = snapshot_markets(_markets(spread=-7.0, total=40.0))
    projection = {
        "markets": _markets(spread=-3.0, total=45.0),
        "diagnostics": {
            "market_blend": {
                "spread_applied": True,
                "total_applied": True,
                "pre_blend_margin_mean": 5.0,
                "pre_blend_total_mean": 41.0,
            }
        },
    }
    annotate_projection_model_handicap(
        projection,
        prior_model_markets=prior,
        line_role="handicap",
    )
    assert projection["model_markets"]["spread_home"] == -7.0
    assert projection["model_markets"]["total_mean"] == 40.0
    assert projection["handicap_markets"]["spread_home"] == -3.0


def test_fair_lines_resolve_identity_fallback() -> None:
    model, handicap = resolve_model_and_handicap(
        projection=None,
        spread_home=-3.5,
        total_mean=41.3,
        home_win_prob=0.6,
        away_win_prob=0.4,
        fair_home_ml=-160,
        fair_away_ml=140,
    )
    assert model["spread_home"] == handicap["spread_home"] == -3.5
    fields = fair_lines_model_handicap_fields(model=model, handicap=handicap)
    assert fields["model_equals_kei"] is True
    assert fields["model_spread_home"] == -3.5


def test_fair_lines_resolve_from_legacy_diagnostics() -> None:
    projection = {
        "markets": _markets(spread=-1.5, total=47.0),
        "diagnostics": {
            "market_blend": {
                "spread_applied": True,
                "total_applied": False,
                "pre_blend_margin_mean": 3.0,
            }
        },
    }
    model, handicap = resolve_model_and_handicap(
        projection=projection,
        spread_home=-1.5,
        total_mean=47.0,
    )
    assert handicap["spread_home"] == -1.5
    assert model["spread_home"] == -3.0
    assert model["total_mean"] == 47.0  # no total blend → identity total
    fields = fair_lines_model_handicap_fields(model=model, handicap=handicap)
    assert fields["model_equals_kei"] is False
