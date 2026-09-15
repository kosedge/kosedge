"""Research opponent-adjusted EPA — unit tests (no production promote)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_warehouse.current_season_2026 import classify_completion
from src.services.cfb_warehouse.delayed_game_verify import (
    DELAYED_GAME_ID,
    OFFICIAL_HOME_SCORE,
    audit_pbp_vs_official_final,
    should_exclude_snapshot_game,
    verify_delayed_game,
)
from src.services.cfb_warehouse.owned_metrics import audit_epa_success
from src.services.cfb_warehouse.paths import HD_RAW_PBP, hd_pbp_hist_research_target, pbp_hist_research_dir
from src.services.cfb_warehouse.research_hist_features import (
    INVENTORY_2021_2024_GAMES,
    INVENTORY_2021_2024_PLAYS,
    HIST_SEASONS,
    historical_path_convention,
)
from src.services.cfb_warehouse.research_opp_adj import (
    EPA_SOURCE_NAME,
    NOT_KE_RATINGS,
    PRODUCT_LABEL,
    RESEARCH_ONLY,
    AdjParams,
    TeamGameEpa,
    eligible_plays,
    fit_joint,
    games_before_cutoff,
    is_overtime,
    predict_game,
)
from src.services.cfb_warehouse.research_opp_adj_validate import (
    HOLDOUT_SEASON,
    apply_to_season,
    recommend,
    select_params,
)


def _play(**kwargs):
    base = {
        "season": 2024,
        "week": 1,
        "game_id": "g1",
        "id": 1,
        "pos_team": "Georgia Bulldogs",
        "def_pos_team": "Clemson Tigers",
        "homeTeamName": "Georgia Bulldogs",
        "awayTeamName": "Clemson Tigers",
        "down": 1,
        "distance": 10,
        "statYardage": 5,
        "EPA": 0.2,
        "EPA_success": True,
        "scrimmage_play": True,
        "pass": False,
        "rush": True,
        "pos_score_diff": 0,
        "period": 1,
        "half": 1,
        "start.TimeSecsRem": 1800,
        "under_2": False,
    }
    base.update(kwargs)
    return base


def _g(**kwargs) -> TeamGameEpa:
    base = dict(
        season=2023,
        week=1,
        game_id="g",
        offense="AAA",
        defense="BBB",
        y=0.0,
        n_plays=20,
        n_weighted=20.0,
        home=1.0,
        fcs_offense=False,
        fcs_defense=False,
        available_week=1,
    )
    base.update(kwargs)
    return TeamGameEpa(**base)


def test_product_is_not_ke_or_spreads() -> None:
    assert RESEARCH_ONLY is True
    assert NOT_KE_RATINGS is True
    assert "KE" not in PRODUCT_LABEL
    assert "SportsDataverse" in EPA_SOURCE_NAME
    assert "expected-points" not in EPA_SOURCE_NAME.lower()


def test_delayed_game_snapshot_excluded() -> None:
    delayed = classify_completion("STATUS_DELAYED", home_score=21, away_score=0)
    assert delayed["actually_completed"] is False
    assert should_exclude_snapshot_game(
        DELAYED_GAME_ID, status="STATUS_DELAYED", home_score=21, away_score=0
    )
    # STATUS_FINAL 49-7 without complete PBP is still exclude (fail-closed).
    assert should_exclude_snapshot_game(
        DELAYED_GAME_ID,
        status="STATUS_FINAL",
        home_score=OFFICIAL_HOME_SCORE,
        away_score=7,
        pbp_complete=False,
    )
    assert not should_exclude_snapshot_game(
        DELAYED_GAME_ID,
        status="STATUS_FINAL",
        home_score=OFFICIAL_HOME_SCORE,
        away_score=7,
        pbp_complete=True,
    )
    verdict = verify_delayed_game(fetch=False)
    assert verdict["decision_on_559_snapshot"] == "exclude"
    assert verdict["include_in_regenerated_559_outputs"] is False
    assert verdict["cfbd_used"] is False
    assert verdict["old_status"] == "STATUS_DELAYED"
    assert verdict["official_status"] == "STATUS_FINAL"
    assert verdict["official_score"] == {"home": 49, "away": 7}
    assert "DELAYED + score is not a standing include" in verdict["standing_eligibility_rule"]


def test_pbp_audit_partial_q2_cut_excludes() -> None:
    """#559 SHA cut: 3 JSU pass TDs + Nix INT to 28-0, no Q3/Q4, no EKU score."""
    plays = [
        {
            "game_id": DELAYED_GAME_ID,
            "id": 1,
            "period": 1,
            "end.homeScore": 7,
            "end.awayScore": 0,
            "type.text": "Passing Touchdown",
            "drive.id": "d1",
            "clock.displayValue": "6:27",
        },
        {
            "game_id": DELAYED_GAME_ID,
            "id": 2,
            "period": 1,
            "end.homeScore": 14,
            "end.awayScore": 0,
            "type.text": "Passing Touchdown",
            "drive.id": "d2",
            "clock.displayValue": "4:25",
        },
        {
            "game_id": DELAYED_GAME_ID,
            "id": 3,
            "period": 2,
            "end.homeScore": 21,
            "end.awayScore": 0,
            "type.text": "Passing Touchdown",
            "drive.id": "d3",
            "clock.displayValue": "12:24",
        },
        {
            "game_id": DELAYED_GAME_ID,
            "id": 4,
            "period": 2,
            "end.homeScore": 28,
            "end.awayScore": 0,
            "type.text": "Interception Return",
            "drive.id": "d4",
            "clock.displayValue": "10:27",
        },
    ]
    audit = audit_pbp_vs_official_final(plays)
    assert audit["complete_through_final"] is False
    assert audit["decision"] == "exclude"
    assert audit["max_period"] == 2
    assert audit["max_home_score"] == 28
    assert audit["max_away_score"] == 0
    assert any(m["home"] == 49 for m in audit["missing_official_markers"])
    assert any(m["away"] == 7 for m in audit["missing_official_markers"])
    # Full 49-7 through Q4 would include.
    full = list(plays) + [
        {
            "game_id": DELAYED_GAME_ID,
            "id": n,
            "period": m["period"],
            "end.homeScore": m["home"],
            "end.awayScore": m["away"],
            "type.text": "Rush",
            "drive.id": f"d{n}",
            "clock.displayValue": m["clock"],
        }
        for n, m in enumerate(
            [
                {"period": 2, "home": 28, "away": 7, "clock": "9:45"},
                {"period": 2, "home": 35, "away": 7, "clock": "5:28"},
                {"period": 3, "home": 42, "away": 7, "clock": "6:03"},
                {"period": 4, "home": 49, "away": 7, "clock": "7:09"},
            ],
            start=5,
        )
    ]
    ok = audit_pbp_vs_official_final(full)
    assert ok["complete_through_final"] is True
    assert ok["decision"] == "include"


def test_overtime_and_garbage_eligible_rules() -> None:
    ot = _play(period=5, EPA=2.0)
    assert is_overtime(ot) is True
    reg = _play(period=4, EPA=0.1)
    assert is_overtime(reg) is False
    kept = eligible_plays(
        [ot, reg, _play(**{"scrimmage_play": False, "pass": False, "rush": False, "EPA": 0.5})]
    )
    assert len(kept) == 1
    assert kept[0]["period"] == 4
    assert kept[0]["_w"] > 0


def test_epa_success_gt_zero_not_standard_sr() -> None:
    plays = [
        _play(id=1, EPA=0.4, EPA_success=True, statYardage=1),
        _play(id=2, EPA=-0.2, EPA_success=False, statYardage=8),
    ]
    audit = audit_epa_success(plays)
    assert audit["verdict"] == "EPA_success_matches_EPA_gt_0"


def test_pregame_cutoff_excludes_same_and_future_week() -> None:
    games = [
        _g(season=2023, week=1, game_id="a"),
        _g(season=2023, week=2, game_id="b"),
        _g(season=2024, week=1, game_id="c"),
    ]
    prior = games_before_cutoff(games, season=2023, week=2)
    assert {g.game_id for g in prior} == {"a"}
    prior2 = games_before_cutoff(games, season=2024, week=1)
    assert {g.game_id for g in prior2} == {"a", "b"}


def test_joint_ridge_recovers_offense_and_defense() -> None:
    # GOOD offense vs BAD defense should not be credited entirely to GOOD.
    # BAD offense vs GOOD defense should not be blamed entirely on BAD.
    games = []
    gid = 0
    for week in range(1, 7):
        for home, away, y_home, y_away in (
            ("GOOD", "BAD", 0.25, -0.20),
            ("AVG", "BAD", 0.10, -0.05),
            ("GOOD", "AVG", 0.12, -0.08),
            ("BAD", "GOOD", -0.18, 0.22),
        ):
            gid += 1
            games.append(
                _g(
                    week=week,
                    game_id=str(gid),
                    offense=home,
                    defense=away,
                    y=y_home,
                    home=1.0,
                )
            )
            gid += 1
            games.append(
                _g(
                    week=week,
                    game_id=str(gid),
                    offense=away,
                    defense=home,
                    y=y_away,
                    home=0.0,
                )
            )
    fit = fit_joint(games, params=AdjParams(lam=20.0, iters=8))
    assert fit.ratings["GOOD"].off > fit.ratings["AVG"].off > fit.ratings["BAD"].off
    # Defense: lower allowed EPA is better.
    assert fit.ratings["GOOD"].defn < fit.ratings["AVG"].defn < fit.ratings["BAD"].defn
    pred = predict_game(fit, offense="GOOD", defense="BAD", home=1.0)
    assert pred["pred_off_epa"] > 0
    assert abs(sum(r.off for t, r in fit.ratings.items() if not r.fcs)) < 1e-6


def test_fcs_kept_and_stronger_ridge() -> None:
    games = [
        _g(offense="ALA", defense="fcs:Citadel", y=0.40, fcs_defense=True, week=1),
        _g(offense="ALA", defense="UGA", y=0.02, week=2, game_id="g2"),
        _g(offense="UGA", defense="ALA", y=0.01, home=0.0, week=2, game_id="g3"),
    ]
    fit = fit_joint(games, params=AdjParams(lam=40.0, lam_fcs_mult=4.0, iters=6))
    assert "fcs:Citadel" in fit.ratings
    assert fit.ratings["fcs:Citadel"].fcs is True
    assert fit.ratings["ALA"].fcs is False


def test_holdout_not_in_selection_contract() -> None:
    assert HOLDOUT_SEASON == 2025
    games = []
    for season in (2022, 2023, 2024, 2025):
        for week in (1, 2, 3):
            games.append(
                _g(
                    season=season,
                    week=week,
                    game_id=f"{season}{week}a",
                    offense="AAA",
                    defense="BBB",
                    y=0.05 if season < 2025 else 0.20,
                )
            )
            games.append(
                _g(
                    season=season,
                    week=week,
                    game_id=f"{season}{week}b",
                    offense="BBB",
                    defense="AAA",
                    y=-0.04,
                    home=0.0,
                )
            )
    sel = select_params(
        games,
        grid=(AdjParams(lam=40.0), AdjParams(lam=160.0)),
        val_seasons=(2023, 2024),
    )
    assert sel["holdout_used_for_selection"] is False
    assert sel["holdout_season"] == 2025
    assert 2025 not in sel["selection_seasons"]


def test_recommend_advance_revise_reject() -> None:
    adv = recommend(
        {"mean_mae": 0.10, "mean_mae_unadj": 0.14, "mean_mae_blend": 0.13, "n_team_games": 800},
        {"selected": {"lam": 80.0}},
    )
    assert adv["recommendation"] == "advance"
    assert adv["production_promote"] is False
    rev = recommend(
        {"mean_mae": 0.119, "mean_mae_unadj": 0.12, "mean_mae_blend": 0.11, "n_team_games": 800},
        {"selected": {}},
    )
    assert rev["recommendation"] in {"revise", "reject"}
    rej = recommend(
        {"mean_mae": 0.20, "mean_mae_unadj": 0.12, "mean_mae_blend": 0.11, "n_team_games": 800},
        {"selected": {}},
    )
    assert rej["recommendation"] == "reject"


def test_apply_merges_prior_only_teams() -> None:
    prior_games = [
        _g(season=2025, week=1, offense="AAA", defense="BBB", y=0.1),
        _g(season=2025, week=1, offense="BBB", defense="AAA", y=-0.05, home=0.0, game_id="g2"),
        _g(season=2025, week=2, offense="CCC", defense="AAA", y=-0.02, home=0.0, game_id="g3"),
    ]
    from src.services.cfb_warehouse.research_opp_adj_validate import build_season_finals

    finals = build_season_finals(prior_games, [2025], AdjParams(lam=40.0, iters=4))
    current = [_g(season=2026, week=1, offense="AAA", defense="BBB", y=0.08)]
    out = apply_to_season(
        current, season=2026, as_of_week=2, params=AdjParams(lam=40.0, iters=4), prior_fit=finals[2025]
    )
    teams = {r["team"] for r in out["ratings"]}
    assert {"AAA", "BBB", "CCC"} <= teams
    ccc = next(r for r in out["ratings"] if r["team"] == "CCC")
    assert ccc["n_games"] == 0
    assert ccc["prior_weight"] == 1.0
    assert ccc["insufficient_history"] is True


def test_hist_paths_never_the_aug13_lake() -> None:
    dest = pbp_hist_research_dir("20260915")
    assert "pbp_hist" in str(dest)
    assert dest.resolve() != HD_RAW_PBP.resolve()
    conv = historical_path_convention("20260915")
    assert conv["historical_lake_write"] is False
    assert str(HD_RAW_PBP) == conv["canonical_hd_lake"]
    assert "pbp_research" in str(hd_pbp_hist_research_target("20260915"))
    assert HIST_SEASONS[0] == 2014 and HIST_SEASONS[-1] == 2025
    assert INVENTORY_2021_2024_PLAYS == 612597
    assert INVENTORY_2021_2024_GAMES == 3552
