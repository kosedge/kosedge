"""t5146u R4 last-played T2 — identity proofs, not status-only."""

from __future__ import annotations

import math
from datetime import timedelta
from pathlib import Path

import pytest

from src.services.nfl_t5107u.last_played_t2 import (
    KO_MINUS,
    LABELS,
    PATH_ID,
    LastPlayedRefuse,
    exact_week_t2_row,
    ko_minus_60,
    last_five_source_game_ids,
    parse_utc,
    select_last_played_sides,
    select_last_played_t2,
    t4_from_last_played,
)
from src.services.nfl_t5107u.recon_driver import (
    HELPER_SHA256,
    apply_2020_23_identity,
    freeze_completeness,
    load_verified_helper,
    reconstruct_slate,
    sha256_file,
    t4_from_t2_sides,
    verify_helper_pin,
)

T2_METRICS = {
    "epa_per_play_offense_5g": 0.10,
    "epa_per_play_defense_allowed_5g": -0.04,
    "pass_rate_5g": 0.58,
    "success_rate_offense_5g": 0.46,
    "success_rate_defense_allowed_5g": 0.41,
    "pressure_rate_generated_5g": 0.22,
    "pressure_rate_allowed_5g": 0.18,
    "red_zone_td_rate_5g": 0.55,
}


def _pd():
    return pytest.importorskip("pandas")


def _helper():
    pytest.importorskip("pandas")
    return load_verified_helper()


def _t2_row(
    team: str,
    week: int,
    game_id: str,
    *,
    season: int = 2021,
    **metrics: object,
) -> dict:
    row = {
        "team": team,
        "season": season,
        "week": week,
        "source_game_ids": game_id,
        **T2_METRICS,
    }
    row.update(metrics)
    return row


def _game(
    gid: str,
    week: int,
    home: str,
    away: str,
    kick: str,
    *,
    season: int = 2021,
) -> dict:
    return {
        "game_id": gid,
        "season": season,
        "week": week,
        "home": home,
        "away": away,
        "kickoff_utc": kick,
    }


def _play(gid: str, week: int, off: str, deff: str, **kw: object) -> dict:
    row = {
        "season": 2021,
        "week": week,
        "game_id": gid,
        "posteam": off,
        "defteam": deff,
        "play_type": "pass",
        "sack": 0.0,
        "qb_hit": 0.0,
        "yardline_100": 40.0,
        "touchdown": 0.0,
        "down": 1.0,
        "first_down": 0.0,
        "success": 1.0,
        "epa": 0.1,
    }
    row.update(kw)
    return row


def _pair_plays(gid: str, week: int, home: str, away: str, epa_home: float = 0.1) -> list[dict]:
    return [
        _play(gid, week, home, away, epa=epa_home),
        _play(
            gid,
            week,
            home,
            away,
            play_type="run",
            yardline_100=5.0,
            touchdown=1.0,
            success=1.0,
            epa=2.0,
        ),
        _play(gid, week, away, home, epa=-0.1),
        _play(
            gid,
            week,
            away,
            home,
            play_type="run",
            yardline_100=5.0,
            touchdown=0.0,
            success=0.0,
            epa=-0.2,
        ),
    ]


def test_helper_and_recon_driver_pins_unchanged():
    helper = verify_helper_pin()
    assert sha256_file(helper) == HELPER_SHA256
    driver = Path(__file__).resolve().parents[1] / "src/services/nfl_t5107u/recon_driver.py"
    assert sha256_file(driver) == (
        "be5aa097f99c47c075d474e199f13fca2980fd282a59a69425549a9ed12e2aa5"
    )


def test_ordinary_no_bye_matches_exact_week_path():
    games = [
        _game("2021_01_AAA_BBB", 1, "AAA", "BBB", "2021-09-12T17:00:00Z"),
        _game("2021_02_AAA_CCC", 2, "AAA", "CCC", "2021-09-19T17:00:00Z"),
    ]
    t2 = [
        _t2_row("AAA", 1, "2021_01_AAA_BBB", epa_per_play_offense_5g=0.33),
        _t2_row("CCC", 1, "2021_01_CCC_DDD", epa_per_play_offense_5g=0.11),
        _t2_row("AAA", 2, "2021_02_AAA_CCC", epa_per_play_offense_5g=9.99),
        _t2_row("CCC", 2, "2021_02_AAA_CCC", epa_per_play_offense_5g=8.88),
    ]
    games.append(_game("2021_01_CCC_DDD", 1, "CCC", "DDD", "2021-09-12T20:00:00Z"))
    home, away = select_last_played_sides(
        t2,
        home="AAA",
        away="CCC",
        season=2021,
        target_week=2,
        target_game_id="2021_02_AAA_CCC",
        target_kickoff_utc="2021-09-19T17:00:00Z",
        games=games,
    )
    assert home.selected_rating_week == 1
    assert away.selected_rating_week == 1
    exact_h = exact_week_t2_row(t2, "AAA", 1)
    exact_a = exact_week_t2_row(t2, "CCC", 1)
    assert exact_h is not None and exact_a is not None
    assert home.t2_row["epa_per_play_offense_5g"] == exact_h["epa_per_play_offense_5g"]
    assert away.t2_row["epa_per_play_offense_5g"] == exact_a["epa_per_play_offense_5g"]
    assert t4_from_last_played(home, away) == t4_from_t2_sides(exact_h, exact_a)
    assert home.last_five_source_game_ids == ("2021_01_AAA_BBB",)
    assert away.last_five_source_game_ids == ("2021_01_CCC_DDD",)
    assert 9.99 not in (
        home.t2_row["epa_per_play_offense_5g"],
        away.t2_row["epa_per_play_offense_5g"],
    )


def test_ordinary_no_bye_matches_frozen_reconstruct_slate_t4():
    mod = _helper()
    apply_2020_23_identity(mod)
    games = [
        _game("2021_01_DEN_LV", 1, "LV", "DEN", "2021-09-12T20:00:00Z"),
        _game("2021_01_BUF_NYJ", 1, "NYJ", "BUF", "2021-09-12T17:00:00Z"),
        _game("2021_02_BUF_LV", 2, "LV", "BUF", "2021-09-19T20:00:00Z"),
    ]
    completed = [
        {
            **g,
            "home_score": 21.0,
            "away_score": 17.0,
        }
        for g in games
        if g["week"] == 1
    ]
    plays = _pd().DataFrame(
        _pair_plays("2021_01_DEN_LV", 1, "LV", "DEN")
        + _pair_plays("2021_01_BUF_NYJ", 1, "NYJ", "BUF")
    )
    seal = freeze_completeness(games, completed, mod)
    result = reconstruct_slate(
        targets=games,
        games=games,
        completed=completed,
        helper=mod,
        plays=plays,
        completeness_seal=seal,
    )
    t1 = mod.t1_from_plays(plays)
    t2 = mod.rolling_5g(t1)
    home, away = select_last_played_sides(
        t2,
        home="LV",
        away="BUF",
        season=2021,
        target_week=2,
        target_game_id="2021_02_BUF_LV",
        target_kickoff_utc="2021-09-19T20:00:00Z",
        games=games,
        t1=t1,
    )
    assert home.selected_rating_week == 1
    assert away.selected_rating_week == 1
    values = t4_from_last_played(home, away)
    for field, value in values.items():
        cell = next(row for row in result["matrix"] if row["field"] == field)
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            assert cell["status"] == "MISSING_RECORD"
        else:
            assert cell["status"] == "DERIVED_PREGAME"
            assert float(cell["reconstructed_value"]) == pytest.approx(float(value), abs=1e-12)
    exact_h = mod.lookup_t2(t2, "LV", 1)
    exact_a = mod.lookup_t2(t2, "BUF", 1)
    assert t4_from_t2_sides(exact_h, exact_a) == values


def test_one_and_multiple_bye_weeks_select_last_played():
    games = [
        _game("2021_01_AAA_BBB", 1, "AAA", "BBB", "2021-09-12T17:00:00Z"),
        _game("2021_02_AAA_CCC", 2, "AAA", "CCC", "2021-09-19T17:00:00Z"),
        _game("2021_04_AAA_DDD", 4, "AAA", "DDD", "2021-10-03T17:00:00Z"),
        _game("2021_06_AAA_EEE", 6, "AAA", "EEE", "2021-10-17T17:00:00Z"),
    ]
    t2 = [
        _t2_row("AAA", 1, "2021_01_AAA_BBB", epa_per_play_offense_5g=0.01),
        _t2_row("AAA", 2, "2021_02_AAA_CCC", epa_per_play_offense_5g=0.02),
        _t2_row("AAA", 4, "2021_04_AAA_DDD", epa_per_play_offense_5g=0.04),
        _t2_row("EEE", 5, "2021_05_EEE_FFF", epa_per_play_offense_5g=0.50),
    ]
    games.append(_game("2021_05_EEE_FFF", 5, "EEE", "FFF", "2021-10-10T17:00:00Z"))
    one_bye = select_last_played_t2(
        t2,
        team="AAA",
        season=2021,
        target_week=4,
        target_game_id="2021_04_AAA_DDD",
        target_kickoff_utc="2021-10-03T17:00:00Z",
        games=games,
    )
    assert one_bye.selected_rating_week == 2
    assert one_bye.t2_row["epa_per_play_offense_5g"] == 0.02
    assert exact_week_t2_row(t2, "AAA", 3) is None
    multi = select_last_played_t2(
        t2,
        team="AAA",
        season=2021,
        target_week=6,
        target_game_id="2021_06_AAA_EEE",
        target_kickoff_utc="2021-10-17T17:00:00Z",
        games=games,
    )
    assert multi.selected_rating_week == 4
    assert multi.last_five_source_game_ids == (
        "2021_01_AAA_BBB",
        "2021_02_AAA_CCC",
        "2021_04_AAA_DDD",
    )


def test_distinct_home_and_away_rating_weeks():
    games = [
        _game("2021_03_HHH_XXX", 3, "HHH", "XXX", "2021-09-26T17:00:00Z"),
        _game("2021_05_AAA_YYY", 5, "AAA", "YYY", "2021-10-10T17:00:00Z"),
        _game("2021_06_HHH_AAA", 6, "HHH", "AAA", "2021-10-17T17:00:00Z"),
    ]
    t2 = [
        _t2_row("HHH", 3, "2021_03_HHH_XXX", epa_per_play_offense_5g=0.30),
        _t2_row("AAA", 5, "2021_05_AAA_YYY", epa_per_play_offense_5g=0.50),
    ]
    home, away = select_last_played_sides(
        t2,
        home="HHH",
        away="AAA",
        season=2021,
        target_week=6,
        target_game_id="2021_06_HHH_AAA",
        target_kickoff_utc="2021-10-17T17:00:00Z",
        games=games,
    )
    assert home.selected_rating_week == 3
    assert away.selected_rating_week == 5
    assert home.t2_row["source_game_ids"] == "2021_03_HHH_XXX"
    assert away.t2_row["source_game_ids"] == "2021_05_AAA_YYY"
    values = t4_from_last_played(home, away)
    assert values["home_off_epa_5g"] == 0.30
    assert values["away_off_epa_5g"] == 0.50


def test_week1_and_no_history_refuse():
    games = [_game("2021_01_AAA_BBB", 1, "AAA", "BBB", "2021-09-12T17:00:00Z")]
    with pytest.raises(LastPlayedRefuse, match="W1_NO_PRIOR"):
        select_last_played_t2(
            [],
            team="AAA",
            season=2021,
            target_week=1,
            target_game_id="2021_01_AAA_BBB",
            target_kickoff_utc="2021-09-12T17:00:00Z",
            games=games,
        )
    with pytest.raises(LastPlayedRefuse, match="no history"):
        select_last_played_t2(
            [_t2_row("CCC", 1, "2021_01_CCC_DDD")],
            team="AAA",
            season=2021,
            target_week=2,
            target_game_id="2021_02_AAA_EEE",
            target_kickoff_utc="2021-09-19T17:00:00Z",
            games=games + [_game("2021_02_AAA_EEE", 2, "AAA", "EEE", "2021-09-19T17:00:00Z")],
        )


def test_cross_season_leakage_refuse():
    games = [
        _game("2020_18_AAA_BBB", 18, "AAA", "BBB", "2021-01-03T18:00:00Z", season=2020),
        _game("2021_02_AAA_CCC", 2, "AAA", "CCC", "2021-09-19T17:00:00Z"),
    ]
    t2 = [_t2_row("AAA", 18, "2020_18_AAA_BBB", season=2020)]
    with pytest.raises(LastPlayedRefuse, match="cross-season leakage"):
        select_last_played_t2(
            t2,
            team="AAA",
            season=2021,
            target_week=2,
            target_game_id="2021_02_AAA_CCC",
            target_kickoff_utc="2021-09-19T17:00:00Z",
            games=games,
        )
    mixed = [
        _t2_row("AAA", 18, "2020_18_AAA_BBB", season=2020, epa_per_play_offense_5g=9.9),
        _t2_row("AAA", 1, "2021_01_AAA_BBB", epa_per_play_offense_5g=0.12),
    ]
    games.append(_game("2021_01_AAA_BBB", 1, "AAA", "BBB", "2021-09-12T17:00:00Z"))
    kept = select_last_played_t2(
        mixed,
        team="AAA",
        season=2021,
        target_week=2,
        target_game_id="2021_02_AAA_CCC",
        target_kickoff_utc="2021-09-19T17:00:00Z",
        games=games,
    )
    assert kept.selected_rating_week == 1
    assert kept.t2_row["epa_per_play_offense_5g"] == 0.12
    assert "2020_18_AAA_BBB" not in kept.consumed_game_ids


def test_duplicate_conflict_and_ambiguous_duplicate_refuse():
    games = [
        _game("2021_01_AAA_BBB", 1, "AAA", "BBB", "2021-09-12T17:00:00Z"),
        _game("2021_02_AAA_CCC", 2, "AAA", "CCC", "2021-09-19T17:00:00Z"),
    ]
    conflict = [
        _t2_row("AAA", 1, "2021_01_AAA_BBB", epa_per_play_offense_5g=0.10),
        _t2_row("AAA", 1, "2021_01_AAA_BBB", epa_per_play_offense_5g=0.99),
    ]
    with pytest.raises(LastPlayedRefuse, match="DUPLICATE_CONFLICT"):
        select_last_played_t2(
            conflict,
            team="AAA",
            season=2021,
            target_week=2,
            target_game_id="2021_02_AAA_CCC",
            target_kickoff_utc="2021-09-19T17:00:00Z",
            games=games,
        )
    identical = [
        _t2_row("AAA", 1, "2021_01_AAA_BBB"),
        _t2_row("AAA", 1, "2021_01_AAA_BBB"),
    ]
    with pytest.raises(LastPlayedRefuse, match="AMBIGUOUS_DUPLICATE"):
        select_last_played_t2(
            identical,
            team="AAA",
            season=2021,
            target_week=2,
            target_game_id="2021_02_AAA_CCC",
            target_kickoff_utc="2021-09-19T17:00:00Z",
            games=games,
        )


def test_nonfinite_newest_row_is_not_skipped():
    games = [
        _game("2021_01_AAA_BBB", 1, "AAA", "BBB", "2021-09-12T17:00:00Z"),
        _game("2021_02_AAA_CCC", 2, "AAA", "CCC", "2021-09-19T17:00:00Z"),
        _game("2021_04_AAA_DDD", 4, "AAA", "DDD", "2021-10-03T17:00:00Z"),
    ]
    t2 = [
        _t2_row("AAA", 1, "2021_01_AAA_BBB", red_zone_td_rate_5g=0.60),
        _t2_row("AAA", 2, "2021_02_AAA_CCC", red_zone_td_rate_5g=float("nan")),
    ]
    selected = select_last_played_t2(
        t2,
        team="AAA",
        season=2021,
        target_week=4,
        target_game_id="2021_04_AAA_DDD",
        target_kickoff_utc="2021-10-03T17:00:00Z",
        games=games,
    )
    assert selected.selected_rating_week == 2
    assert selected.newest_nonfinite is True
    assert math.isnan(float(selected.t2_row["red_zone_td_rate_5g"]))
    assert selected.t2_row["source_game_ids"] == "2021_02_AAA_CCC"
    dummy_away = select_last_played_t2(
        [_t2_row("DDD", 3, "2021_03_DDD_EEE")],
        team="DDD",
        season=2021,
        target_week=4,
        target_game_id="2021_04_AAA_DDD",
        target_kickoff_utc="2021-10-03T17:00:00Z",
        games=games + [_game("2021_03_DDD_EEE", 3, "DDD", "EEE", "2021-09-26T17:00:00Z")],
    )
    values = t4_from_last_played(selected, dummy_away)
    assert values["matchup_diff_red_zone_td_rate_5g"] is None or (
        isinstance(values["matchup_diff_red_zone_td_rate_5g"], float)
        and not math.isfinite(values["matchup_diff_red_zone_td_rate_5g"])
    )


def test_target_and_future_game_exclusion_and_ko60_boundary():
    target_kick = "2021-10-03T18:00:00Z"
    cutoff = ko_minus_60(target_kick)
    assert cutoff == parse_utc(target_kick) - KO_MINUS
    on_boundary = (cutoff).strftime("%Y-%m-%dT%H:%M:%SZ")
    just_before = (cutoff - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    games = [
        _game("2021_01_AAA_BBB", 1, "AAA", "BBB", just_before),
        _game("2021_03_AAA_CCC", 3, "AAA", "CCC", on_boundary),
        _game("2021_04_AAA_DDD", 4, "AAA", "DDD", target_kick),
        _game("2021_05_AAA_EEE", 5, "AAA", "EEE", "2021-10-10T18:00:00Z"),
    ]
    t2 = [
        _t2_row("AAA", 1, "2021_01_AAA_BBB"),
        _t2_row("AAA", 3, "2021_03_AAA_CCC"),
        _t2_row("AAA", 4, "2021_04_AAA_DDD"),
        _t2_row("AAA", 5, "2021_05_AAA_EEE"),
    ]
    with pytest.raises(LastPlayedRefuse, match="KO-60"):
        select_last_played_t2(
            t2,
            team="AAA",
            season=2021,
            target_week=4,
            target_game_id="2021_04_AAA_DDD",
            target_kickoff_utc=target_kick,
            games=games,
        )
    ok = select_last_played_t2(
        [_t2_row("AAA", 1, "2021_01_AAA_BBB"), _t2_row("AAA", 4, "2021_04_AAA_DDD")],
        team="AAA",
        season=2021,
        target_week=4,
        target_game_id="2021_04_AAA_DDD",
        target_kickoff_utc=target_kick,
        games=games,
    )
    assert ok.selected_rating_week == 1
    assert ok.last_five_source_game_ids == ("2021_01_AAA_BBB",)
    assert "2021_04_AAA_DDD" not in ok.consumed_game_ids
    assert "2021_05_AAA_EEE" not in ok.consumed_game_ids


def test_target_outcome_change_does_not_change_allowed_features():
    mod = _helper()
    apply_2020_23_identity(mod)
    games = [
        _game("2021_01_DEN_LV", 1, "LV", "DEN", "2021-09-12T20:00:00Z"),
        _game("2021_01_BUF_NYJ", 1, "NYJ", "BUF", "2021-09-12T17:00:00Z"),
        _game("2021_02_BUF_LV", 2, "LV", "BUF", "2021-09-19T20:00:00Z"),
    ]
    base = _pair_plays("2021_01_DEN_LV", 1, "LV", "DEN", epa_home=0.25) + _pair_plays(
        "2021_01_BUF_NYJ", 1, "NYJ", "BUF", epa_home=0.40
    )
    target_plays = _pair_plays("2021_02_BUF_LV", 2, "LV", "BUF", epa_home=1.75)
    mutated = _pair_plays("2021_02_BUF_LV", 2, "LV", "BUF", epa_home=-9.0)

    def _select(plays: list[dict]):
        frame = _pd().DataFrame(plays)
        t1 = mod.t1_from_plays(frame)
        t2 = mod.rolling_5g(t1)
        return select_last_played_sides(
            t2,
            home="LV",
            away="BUF",
            season=2021,
            target_week=2,
            target_game_id="2021_02_BUF_LV",
            target_kickoff_utc="2021-09-19T20:00:00Z",
            games=games,
            t1=t1,
        )

    home_a, away_a = _select(base + target_plays)
    home_b, away_b = _select(base + mutated)
    assert home_a.selected_rating_week == home_b.selected_rating_week == 1
    assert away_a.selected_rating_week == away_b.selected_rating_week == 1
    assert home_a.last_five_source_game_ids == home_b.last_five_source_game_ids
    assert away_a.last_five_source_game_ids == away_b.last_five_source_game_ids
    assert "2021_02_BUF_LV" not in home_a.consumed_game_ids
    assert t4_from_last_played(home_a, away_a) == t4_from_last_played(home_b, away_b)
    assert home_a.t2_row["epa_per_play_offense_5g"] == home_b.t2_row["epa_per_play_offense_5g"]


def test_proves_selected_last_five_source_game_identities():
    games = [
        _game(f"2021_0{week}_AAA_T{week}", week, "AAA", f"T{week}", f"2021-09-{5+week:02d}T17:00:00Z")
        for week in range(1, 7)
    ]
    t2 = [
        _t2_row("AAA", week, f"2021_0{week}_AAA_T{week}", epa_per_play_offense_5g=week / 100.0)
        for week in range(1, 6)
    ]
    selected = select_last_played_t2(
        t2,
        team="AAA",
        season=2021,
        target_week=6,
        target_game_id="2021_06_AAA_T6",
        target_kickoff_utc="2021-09-11T17:00:00Z",
        games=games,
    )
    assert selected.selected_rating_week == 5
    assert selected.last_five_source_game_ids == (
        "2021_01_AAA_T1",
        "2021_02_AAA_T2",
        "2021_03_AAA_T3",
        "2021_04_AAA_T4",
        "2021_05_AAA_T5",
    )
    assert selected.consumed_game_ids == selected.last_five_source_game_ids
    window = last_five_source_game_ids(
        t2, team="AAA", season=2021, rating_week=5
    )
    assert window == selected.last_five_source_game_ids
    assert "2021_06_AAA_T6" not in window


def test_labels_and_unverified_timestamps():
    games = [
        _game("2021_01_AAA_BBB", 1, "AAA", "BBB", "2021-09-12T17:00:00Z"),
        _game("2021_02_AAA_CCC", 2, "AAA", "CCC", "2021-09-19T17:00:00Z"),
    ]
    selected = select_last_played_t2(
        [_t2_row("AAA", 1, "2021_01_AAA_BBB")],
        team="AAA",
        season=2021,
        target_week=2,
        target_game_id="2021_02_AAA_CCC",
        target_kickoff_utc="2021-09-19T17:00:00Z",
        games=games,
    )
    assert selected.labels == LABELS
    assert selected.publication_timestamp_status == "unverified"
    assert selected.observation_timestamp_status == "unverified"
    assert selected.production_causal_claim is False
    assert selected.realtime_source_availability_claim is False
    assert selected.path_id == PATH_ID
    assert "not a production-causal" in selected.notes[0]


def test_does_not_fill_from_another_team_or_zero_default():
    games = [
        _game("2021_01_ZZZ_YYY", 1, "ZZZ", "YYY", "2021-09-12T17:00:00Z"),
        _game("2021_02_AAA_CCC", 2, "AAA", "CCC", "2021-09-19T17:00:00Z"),
    ]
    t2 = [_t2_row("ZZZ", 1, "2021_01_ZZZ_YYY", epa_per_play_offense_5g=0.0)]
    with pytest.raises(LastPlayedRefuse, match="no history"):
        select_last_played_t2(
            t2,
            team="AAA",
            season=2021,
            target_week=2,
            target_game_id="2021_02_AAA_CCC",
            target_kickoff_utc="2021-09-19T17:00:00Z",
            games=games,
        )
