from datetime import date

from src.services.wnba_data import (
    WNBA_TEAM_ABBREV,
    normalize_team_key,
    rolling_average_features,
    wnba_abbr_match_keys,
    wnba_full_names_for_abbr,
    wnba_season_year_from_date,
    default_league_average_inputs,
)


def test_fifteen_team_directory() -> None:
    assert len(WNBA_TEAM_ABBREV) == 15
    assert "Golden State Valkyries" in WNBA_TEAM_ABBREV
    assert WNBA_TEAM_ABBREV["Las Vegas Aces"] == "LAS"
    assert WNBA_TEAM_ABBREV["New York Liberty"] == "NY"
    assert WNBA_TEAM_ABBREV["Washington Mystics"] == "WSH"
    assert WNBA_TEAM_ABBREV["Portland Fire"] == "POR"
    assert WNBA_TEAM_ABBREV["Toronto Tempo"] == "TOR"
    assert normalize_team_key("GS") == "GSV"
    assert normalize_team_key("POR") == "POR"
    assert normalize_team_key("Toronto Tempo") == "TOR"


def test_abbr_aliases_avoid_nba_collision_confusion() -> None:
    # CDN uses LVA/NYL/WAS — canonicalize to desk keys.
    assert normalize_team_key("LVA") == "LAS"
    assert normalize_team_key("NYL") == "NY"
    assert normalize_team_key("WAS") == "WSH"
    assert normalize_team_key("Chicago Sky") == "CHI"
    # Sport-scoped: CHI is valid WNBA (Sky), not Bulls.
    assert "CHI" in {v for v in WNBA_TEAM_ABBREV.values()}


def test_season_year_may_start_rule() -> None:
    assert wnba_season_year_from_date(date(2025, 5, 16)) == 2025
    assert wnba_season_year_from_date(date(2025, 10, 10)) == 2025
    assert wnba_season_year_from_date(date(2025, 3, 1)) == 2024
    assert wnba_season_year_from_date(date(2026, 1, 15)) == 2025


def test_full_name_and_abbr_match_keys() -> None:
    names = wnba_full_names_for_abbr("LAS")
    assert "Las Vegas Aces" in names
    keys = wnba_abbr_match_keys("LAS")
    assert "LAS" in keys
    assert "LVA" in keys


def test_league_avg_inputs_are_wnba_not_nba() -> None:
    d = default_league_average_inputs("g1", "Home", "Away")
    assert d["pace_home"] == 81.0
    assert d["ortg_home"] == 103.0
    assert d["feature_pack_version"] == "wnba-league-avg-v0"
    # Explicitly not NBA defaults.
    assert d["pace_home"] != 100.0
    assert d["ortg_home"] != 114.0


def test_rolling_average_defaults_wnba() -> None:
    avg = rolling_average_features([])
    assert avg["pace"] == 81.0
    assert avg["ortg"] == 103.0
