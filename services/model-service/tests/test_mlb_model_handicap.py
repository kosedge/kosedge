"""Unit tests for MLB model_* vs handicap_* (KEI) helpers."""

from __future__ import annotations

from src.services.mlb_model_handicap import (
    annotate_projection_model_handicap,
    extract_prior_model_markets,
    fair_lines_payload_from_row,
    resolve_model_markets,
    snapshot_markets,
)


def _markets(*, ml: int = -110, win: float = 0.55, total: float = 8.5) -> dict:
    return {
        "f5_home_win_prob": win - 0.01,
        "fg_home_win_prob": win,
        "f5_total_mean": total - 4.0,
        "fg_total_mean": total,
        "fair_f5_home_ml": ml + 5,
        "fair_fg_home_ml": ml,
        "fair_f5_total": total - 4.0,
        "fair_fg_total": total,
        "fair_fg_spread_home": -1.5,
    }


def test_identity_when_no_prior_model() -> None:
    markets = _markets(ml=-120, win=0.58)
    model = resolve_model_markets(markets)
    assert model["fair_fg_home_ml"] == -120
    assert model["fg_home_win_prob"] == 0.58


def test_preserve_prior_model_on_handicap_annotate() -> None:
    prior = snapshot_markets(_markets(ml=-105, win=0.52, total=8.0))
    projection = {
        "game_id": "g1",
        "markets": _markets(ml=-130, win=0.60, total=9.0),
    }
    annotate_projection_model_handicap(
        projection,
        prior_model_markets=prior,
        line_role="handicap",
    )
    assert projection["model_markets"]["fair_fg_home_ml"] == -105
    assert projection["handicap_markets"]["fair_fg_home_ml"] == -130
    assert projection["model_fair_fg_home_ml"] == -105
    assert projection["handicap_fair_fg_home_ml"] == -130


def test_model_role_sets_identity() -> None:
    projection = {"markets": _markets(ml=-115, win=0.54)}
    annotate_projection_model_handicap(projection, line_role="model")
    assert (
        projection["model_markets"]["fair_fg_home_ml"]
        == projection["handicap_markets"]["fair_fg_home_ml"]
        == -115
    )


def test_fair_lines_payload_aliases_fair_fg_to_handicap() -> None:
    model = snapshot_markets(_markets(ml=-100, win=0.50, total=7.5))
    handicap = snapshot_markets(_markets(ml=-140, win=0.62, total=9.5))
    row = fair_lines_payload_from_row(
        game_id="g1",
        game_date="2026-08-02",
        start_time=None,
        home_team="Home",
        away_team="Away",
        fg_home_win_prob=0.62,
        fair_fg_home_ml=-140,
        fg_total_mean=9.5,
        fair_fg_total=9.5,
        fair_fg_spread_home=-1.5,
        fg_home_cover_prob_run_line=0.48,
        fg_margin_mean=0.4,
        projected_at=None,
        model_markets=model,
        handicap_markets=handicap,
    )
    assert row["fair_fg_home_ml"] == -140
    assert row["handicap_fair_fg_home_ml"] == -140
    assert row["model_fair_fg_home_ml"] == -100
    assert row["model_fg_home_win_prob"] == 0.50


def test_extract_prior_from_projection_json() -> None:
    row = {
        "projection": {
            "model_markets": _markets(ml=-108, win=0.53),
            "markets": _markets(ml=-125, win=0.59),
        }
    }
    prior = extract_prior_model_markets(row)
    assert prior is not None
    assert prior["fair_fg_home_ml"] == -108
