"""Research efficiency → scoring — unit tests (no lake, no production promote)."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.research_opp_adj import AdjParams, TeamGameEpa, fit_joint
from src.services.cfb_warehouse.research_opp_adj_validate import (
    HOLDOUT_SEASON,
    IBF_FALLBACK_SEASONS,
    IBF_RULE_ID,
    evaluate_seasons,
    independent_league_raw_mean,
)
from src.services.cfb_warehouse.research_scoring import (
    PRODUCTION_PROMOTE,
    RESEARCH_ONLY,
    ScoringKnobs,
    extract_official_scores,
    forbidden_thin_window_spread,
    margin_total,
    overlay_epa_identity,
    predict_epa_no_hfa,
    shrink_hfa,
    _side_id,
)
from src.services.cfb_warehouse.identity import known_engine_codes
from src.services.cfb_warehouse.research_scoring_validate import (
    SCORING_CONFIRM_MIN_WEEK,
    SCORING_CONFIRM_SEASON,
    SCORING_DEV_EVIDENCE_SEASON,
    SCORING_TRAIN_SEASONS,
    SCORING_VAL_SEASONS,
    recommend_scoring,
    scoring_set_label,
    select_scoring_params,
)

REPO = Path(__file__).resolve().parents[3]
PROTOCOL = REPO / "docs" / "cfb" / "EVAL_PROTOCOL.md"


def _g(**kwargs) -> TeamGameEpa:
    base = dict(
        season=2022,
        week=1,
        game_id="g",
        offense="AAA",
        defense="BBB",
        y=0.05,
        n_plays=20,
        n_weighted=20.0,
        home=1.0,
        fcs_offense=False,
        fcs_defense=False,
        available_week=1,
    )
    base.update(kwargs)
    return TeamGameEpa(**base)


def test_protocol_file_locked_in_repo() -> None:
    assert PROTOCOL.is_file()
    text = PROTOCOL.read_text()
    assert "Locked:" in text
    assert "2025 is not a fresh scoring test" in text or "Do not present 2025" in text
    assert "SCORING" in text or "2024 weeks" in text
    assert "production_promote=false" in text
    assert "IBF-v1" in text
    assert "Do **not** multiply" in text or "Do not multiply" in text


def test_scoring_splits_match_protocol() -> None:
    assert SCORING_TRAIN_SEASONS == tuple(range(2016, 2023))
    assert SCORING_VAL_SEASONS == (2023,)
    assert SCORING_CONFIRM_SEASON == 2024
    assert SCORING_CONFIRM_MIN_WEEK == 10
    assert SCORING_DEV_EVIDENCE_SEASON == 2025
    assert HOLDOUT_SEASON == 2025
    assert scoring_set_label(2023, 12) == "validation"
    assert scoring_set_label(2024, 9) == "other"
    assert scoring_set_label(2024, 10) == "confirmation"
    assert scoring_set_label(2025, 1) == "development_evidence"
    assert scoring_set_label(2019, 3) == "train"


def test_ibf_mean_ignores_val_and_holdout() -> None:
    games = [
        _g(season=2018, y=0.10, offense="AAA", defense="BBB"),
        _g(season=2018, y=0.10, offense="BBB", defense="AAA", home=0.0, game_id="g2"),
        _g(season=2023, y=9.0, offense="AAA", defense="BBB"),
        _g(season=2025, y=-9.0, offense="AAA", defense="BBB"),
    ]
    mu = independent_league_raw_mean(games)
    assert abs(mu - 0.10) < 1e-12
    assert 2023 not in IBF_FALLBACK_SEASONS
    assert 2025 not in IBF_FALLBACK_SEASONS


def test_unadj_blend_independent_of_candidate_mu() -> None:
    """Changing adj-model μ must not move unadj/blend once IBF-v1 is on."""
    games = []
    for week in (1, 2, 3):
        games.append(_g(season=2022, week=week, game_id=f"22{week}a", y=0.04))
        games.append(
            _g(
                season=2022,
                week=week,
                game_id=f"22{week}b",
                offense="BBB",
                defense="AAA",
                y=0.04,
                home=0.0,
            )
        )
    # 2025 week 1: brand-new defender with no STD and no prior-season raw.
    games.append(
        _g(
            season=2025,
            week=1,
            game_id="25w1",
            offense="AAA",
            defense="NEW",
            y=0.20,
        )
    )
    games.append(
        _g(
            season=2025,
            week=1,
            game_id="25w1b",
            offense="BBB",
            defense="NEW",
            y=-0.10,
            home=0.0,
        )
    )
    lo = evaluate_seasons(games, (2025,), AdjParams(lam=40.0, prior_n0=4.0, iters=4))
    hi = evaluate_seasons(games, (2025,), AdjParams(lam=160.0, prior_n0=6.0, iters=4))
    assert lo["unadjusted_std"]["off"] == hi["unadjusted_std"]["off"]
    assert lo["unadjusted_std"]["def"] == hi["unadjusted_std"]["def"]
    assert lo["prior_blend"]["off"] == hi["prior_blend"]["off"]
    assert lo["prior_blend"]["def"] == hi["prior_blend"]["def"]
    assert lo["baseline_fallback"]["uses_candidate_mu"] is False
    assert lo["baseline_fallback"]["rule_id"] == IBF_RULE_ID
    assert lo["baseline_fallback"]["defense_rows_using_ibf"] >= 1
    # Candidate μ differs across λ; IBF fallback stays the train mean (0.04).
    assert abs(lo["baseline_fallback"]["fallback_value"] - 0.04) < 1e-12


def test_select_scoring_params_rejects_wrong_val_seasons() -> None:
    try:
        select_scoring_params(
            val_games=[],
            train_team_rows_by_pace={"competitive_pace_plays": [], "pace_plays": []},
            train_games=[],
            val_games_by_pace={"competitive_pace_plays": [], "pace_plays": []},
            ppp=6.5,
            league_pace_by_source={"competitive_pace_plays": 65.0, "pace_plays": 70.0},
            train_pts=27.0,
            val_seasons=(2023, 2024),
        )
    except ValueError as exc:
        assert "2023" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_select_scoring_params_contract_flags() -> None:
    train_rows = []
    train_games = []
    val_games = []
    for i in range(12):
        train_games.append(
            {
                "game_id": f"t{i}",
                "season": 2018,
                "week": 1 + (i % 8),
                "home": "AAA",
                "away": "BBB",
                "home_points": 28 + i,
                "away_points": 21,
                "neutral": False,
                "margin": 7 + i,
                "total": 49 + i,
                "epa_home": 0.05,
                "epa_away": -0.02,
                "exp_plays": 65.0,
                "set": "train",
                "band": "early",
                "fbs_vs_fbs": True,
            }
        )
        train_rows.append(
            {
                "points": 28 + i,
                "epa_plays": 0.05 * 65.0,
                "home": 1.0,
            }
        )
        train_rows.append(
            {
                "points": 21,
                "epa_plays": -0.02 * 65.0,
                "home": 0.0,
            }
        )
        val_games.append(
            {
                "game_id": f"v{i}",
                "season": 2023,
                "week": 1 + i,
                "home": "AAA",
                "away": "BBB",
                "home_points": 31,
                "away_points": 24,
                "neutral": False,
                "margin": 7,
                "total": 55,
                "epa_home": 0.04,
                "epa_away": -0.01,
                "exp_plays": 66.0,
                "set": "validation",
                "band": "early" if i < 4 else "mid",
                "fbs_vs_fbs": True,
            }
        )
    by_pace = {
        "competitive_pace_plays": val_games,
        "pace_plays": val_games,
    }
    sel = select_scoring_params(
        val_games=val_games,
        train_team_rows_by_pace={
            "competitive_pace_plays": train_rows,
            "pace_plays": train_rows,
        },
        train_games=train_games,
        val_games_by_pace=by_pace,
        ppp=6.5,
        league_pace_by_source={"competitive_pace_plays": 65.0, "pace_plays": 70.0},
        train_pts=27.0,
    )
    assert sel["selection_seasons"] == [2023]
    assert 2024 not in sel["selection_seasons"]
    assert 2025 not in sel["selection_seasons"]
    assert sel["confirmation_used_for_selection"] is False
    assert sel["dev_evidence_used_for_selection"] is False
    assert sel["holdout_used_for_selection"] is False
    assert sel["selected"]["hfa_k"] in {10.0, 20.0, 40.0, 80.0, 160.0}


def test_recommend_always_false_promote() -> None:
    confirm = {
        "all": {
            "n_games": 200,
            "margin": {"mae": 12.0, "bias": 0.1},
            "total": {"mae": 14.0, "bias": 0.2},
        }
    }
    bases = {
        "std_points": {
            "all": {
                "n_games": 200,
                "margin": {"mae": 16.0, "bias": 0.0},
                "total": {"mae": 18.0, "bias": 0.0},
            }
        },
        "prior_blend_points": {
            "all": {
                "n_games": 200,
                "margin": {"mae": 15.5, "bias": 0.2},
                "total": {"mae": 17.0, "bias": 0.1},
            }
        },
        "league_mean_points": {
            "all": {
                "n_games": 200,
                "margin": {"mae": 20.0, "bias": 0.0},
                "total": {"mae": 22.0, "bias": 0.0},
            }
        },
    }
    rec = recommend_scoring(confirm, bases)
    assert rec["recommendation"] == "advance"
    assert rec["production_promote"] is False
    assert rec["dev_evidence_2025_not_used_for_call"] is True

    thin = recommend_scoring({"all": {"n_games": 20, "margin": {"mae": 1}, "total": {"mae": 1}}}, bases)
    assert thin["recommendation"] == "reject"
    assert thin["production_promote"] is False


def test_hfa_shrink_formula() -> None:
    # Equal mix when N = k.
    assert abs(shrink_hfa(h_window=4.0, h_prior=2.0, n=40, k=40) - 3.0) < 1e-12
    # Large N stays near window.
    assert shrink_hfa(h_window=3.0, h_prior=2.0, n=10_000, k=40) > 2.99
    # Thin N (the thing we refuse to treat as a spread) shrinks hard to prior.
    thin = shrink_hfa(h_window=20.0, h_prior=2.5, n=84, k=160)
    assert thin < 10.0
    banned = forbidden_thin_window_spread(0.244, 70.0)
    assert banned["used"] is False
    assert abs(banned["forbidden_spread"] - 0.244 * 70.0) < 1e-12


def test_margin_sign_and_product_flags() -> None:
    margin, total = margin_total(31, 24)
    assert margin == 7
    assert total == 55
    assert RESEARCH_ONLY is True
    assert PRODUCTION_PROMOTE is False


def test_predict_epa_drops_hfa_term() -> None:
    games = [
        _g(offense="AAA", defense="BBB", y=0.20, home=1.0, n_weighted=40.0),
        _g(offense="BBB", defense="AAA", y=-0.05, home=0.0, game_id="g2", n_weighted=40.0),
        _g(offense="CCC", defense="AAA", y=0.00, home=0.0, game_id="g3", n_weighted=40.0),
        _g(offense="AAA", defense="CCC", y=0.10, home=1.0, game_id="g4", n_weighted=40.0),
    ]
    fit = fit_joint(games, params=AdjParams(lam=1.0, prior_n0=0.0, iters=8))
    no_h = predict_epa_no_hfa(fit, offense="AAA", defense="BBB")
    with_h = fit.mu + fit.hfa * 1.0 + fit.ratings["AAA"].off + fit.ratings["BBB"].defn
    assert abs(no_h - (fit.mu + fit.ratings["AAA"].off + fit.ratings["BBB"].defn)) < 1e-12
    if abs(fit.hfa) > 1e-6:
        assert abs(no_h - with_h) > 1e-9


def test_extract_scores_no_synthetic_fill() -> None:
    plays = [
        {
            "game_id": "1",
            "season": 2024,
            "week": 10,
            "homeTeamName": "Georgia Bulldogs",
            "awayTeamName": "Alabama Crimson Tide",
            "end.homeScore": 14,
            "end.awayScore": 7,
            "period": 2,
        },
        {
            "game_id": "1",
            "season": 2024,
            "week": 10,
            "homeTeamName": "Georgia Bulldogs",
            "awayTeamName": "Alabama Crimson Tide",
            "end.homeScore": 31,
            "end.awayScore": 24,
            "period": 4,
        },
        {
            "game_id": "2",
            "season": 2024,
            "week": 10,
            "homeTeamName": "Unused",
            "awayTeamName": "Also Unused",
            "period": 1,
        },
    ]
    scores = extract_official_scores(plays)
    assert scores["1"]["home_points"] == 31
    assert scores["1"]["away_points"] == 24
    assert scores["2"]["home_points"] is None
    assert scores["2"]["away_points"] is None


def test_side_id_uses_espn_abbr_when_name_is_short() -> None:
    known = known_engine_codes()
    code, fcs = _side_id("Georgia", "UGA", known)
    assert code == "UGA"
    assert fcs is False
    code2, fcs2 = _side_id("Alabama", "ALA", known)
    assert code2 == "ALA"
    assert fcs2 is False


def test_overlay_epa_identity_wins() -> None:
    scores = {
        "g1": {
            "game_id": "g1",
            "home": "fcs:Georgia",
            "away": "fcs:Alabama",
            "home_fcs": True,
            "away_fcs": True,
            "home_points": 31,
            "away_points": 24,
        }
    }
    epa = [
        _g(game_id="g1", offense="UGA", defense="ALA", home=1.0, fcs_offense=False),
        _g(game_id="g1", offense="ALA", defense="UGA", home=0.0, fcs_offense=False),
    ]
    out = overlay_epa_identity(scores, epa)
    assert out["g1"]["home"] == "UGA"
    assert out["g1"]["away"] == "ALA"
    assert out["g1"]["home_fcs"] is False
    assert out["g1"]["away_fcs"] is False


def test_scoring_knobs_grid_is_protocol_grid() -> None:
    knobs = ScoringKnobs()
    assert knobs.pace_source in {"competitive_pace_plays", "pace_plays"}
    assert knobs.hfa_k in {10.0, 20.0, 40.0, 80.0, 160.0}
