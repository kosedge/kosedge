"""P0 CFB structural restore — NAME_TO_CODE + fail-closed power/conference."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine.cfb_kei import (
    DOCUMENTED_W2_KEI_VERSION,
    W0_CLOSE_AS_OF,
    kei_version_for_weeks,
    resolve_kei_as_of,
)
from src.services.cfb_season_engine.conferences import conference_for, load_conference_map
from src.services.cfb_season_engine.efficiency import build_efficiency_profile
from src.services.cfb_season_engine.name_to_code import (
    NAME_TO_CODE,
    P0_REQUIRED_CODES,
    assert_p0_codes_mapped,
    require_mapped_code,
)
from src.services.cfb_season_engine.power_sot import sit_missing_power_from_sot_rows
from src.services.cfb_season_engine.team_features import (
    CFB_EDGE_BOARD_PUBLIC_ENABLED,
    MissingRequiredTeamFeature,
    require_finite_power_for_codes,
    require_finite_power_index,
)
from src.services.cfb_season_engine.types import EngineUniverse, TeamProjectionState


P0_SHORT_NAMES = {
    "MIZZ": "Missouri",
    "ARST": "Arkansas State",
    "CSU": "Colorado State",
    "ECU": "East Carolina",
    "JVST": "Jacksonville State",
    "NEV": "Nevada",
    "ODU": "Old Dominion",
    "TOL": "Toledo",
    "UAB": "UAB",
    "UNM": "New Mexico",
    "UNT": "North Texas",
}

P0_CONFERENCES = {
    "MIZZ": "SEC",
    "ARST": "Sun Belt",
    "CSU": "Pac-12",
    "ECU": "AAC",
    "JVST": "CUSA",
    "NEV": "Mountain West",
    "ODU": "Sun Belt",
    "TOL": "MAC",
    "UAB": "AAC",
    "UNM": "Mountain West",
    "UNT": "AAC",
}


def test_missouri_stays_distinct_from_missouri_state() -> None:
    assert NAME_TO_CODE["Missouri"] == "MIZZ"
    assert NAME_TO_CODE["Missouri State"] == "MOST"
    assert NAME_TO_CODE["Missouri"] != NAME_TO_CODE["Missouri State"]
    assert require_mapped_code("Missouri") == "MIZZ"
    assert require_mapped_code("Missouri State") == "MOST"


def test_all_11_p0_codes_present_in_name_to_code() -> None:
    assert_p0_codes_mapped()
    assert len(P0_REQUIRED_CODES) == 11
    for code in P0_REQUIRED_CODES:
        assert code in set(NAME_TO_CODE.values()), code
        assert P0_SHORT_NAMES[code] in NAME_TO_CODE
        assert NAME_TO_CODE[P0_SHORT_NAMES[code]] == code


def test_missing_mapping_fail_closed() -> None:
    with pytest.raises(MissingRequiredTeamFeature, match="Unmapped CFB name"):
        require_mapped_code("Not A Real FBS Team")
    broken = dict(NAME_TO_CODE)
    del broken["Missouri"]
    with pytest.raises(MissingRequiredTeamFeature, match="Missouri"):
        require_mapped_code("Missouri", broken)
    with pytest.raises(MissingRequiredTeamFeature, match="missing required P0"):
        assert_p0_codes_mapped({"Indiana": "IU"})


def test_p0_codes_are_not_independent() -> None:
    load_conference_map.cache_clear()
    packaged = load_conference_map()
    for code, conf in P0_CONFERENCES.items():
        assert conference_for(code) == conf, code
        assert packaged[code] == conf, code
        # Leftover Independent in a stale map must not win.
        assert conference_for(code, {code: "Independent"}) == conf, code


def test_true_independents_stay_independent() -> None:
    assert conference_for("ND") == "Independent"
    assert conference_for("CONN") == "Independent"


def test_official_fbs_missing_conference_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.cfb_season_engine.conferences.is_official_fbs",
        lambda team, include_transition=False: str(team).upper() == "ZZZX",
    )
    monkeypatch.setattr(
        "src.services.cfb_season_engine.conferences._universe_conference",
        lambda code: None,
    )
    with pytest.raises(MissingRequiredTeamFeature, match="missing conference"):
        conference_for("ZZZX", mapping={})


def test_missing_efficiency_for_official_fbs_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.services.cfb_season_engine.efficiency.is_official_fbs",
        lambda team, include_transition=False: str(team).upper() == "ZZZX",
    )
    monkeypatch.setattr(
        "src.services.cfb_season_engine.efficiency.load_efficiency_snapshot",
        lambda: {"teams": {}},
    )
    with pytest.raises(MissingRequiredTeamFeature, match="missing packaged efficiency"):
        build_efficiency_profile("ZZZX")


def test_null_power_does_not_default_to_1() -> None:
    with pytest.raises(MissingRequiredTeamFeature, match="do not default 1.0"):
        require_finite_power_index(None, field="offense_index", team="MIZZ")
    with pytest.raises(MissingRequiredTeamFeature, match="do not default 1.0"):
        require_finite_power_index("", field="defense_index", team="ARST")
    assert require_finite_power_index(1.12, field="offense_index", team="UGA") == 1.12


def test_required_slate_missing_power_hard_fails_rebuild() -> None:
    universe = EngineUniverse(
        season=2026,
        schedule=[],
        teams={
            "UGA": TeamProjectionState(
                team="UGA", offense_index=1.4, defense_index=1.3
            )
        },
        conferences={},
    )
    with pytest.raises(MissingRequiredTeamFeature, match="do not hydrate 1.0"):
        require_finite_power_for_codes(universe, ["MIZZ", "UGA"], context="rebuild")
    with pytest.raises(MissingRequiredTeamFeature, match="do not hydrate 1.0"):
        sit_missing_power_from_sot_rows(
            universe,
            [{"team": "MIZZ", "offense_index": None, "defense_index": None}],
            required=("MIZZ",),
            context="rebuild/pack",
        )
    assert "MIZZ" not in universe.teams


def test_hydrate_sits_null_power_instead_of_1_0() -> None:
    universe = EngineUniverse(
        season=2026,
        schedule=[],
        teams={
            "UGA": TeamProjectionState(
                team="UGA", offense_index=1.4, defense_index=1.3
            )
        },
        conferences={},
    )
    sat = sit_missing_power_from_sot_rows(
        universe,
        [
            {"team": "MIZZ", "offense_index": None, "defense_index": None},
            {"team": "ARST", "offense_index": 1.0, "defense_index": None},
            {"team": "UGA", "offense_index": 1.4, "defense_index": 1.3},
        ],
    )
    assert sat == 2
    assert "MIZZ" not in universe.teams
    assert "ARST" not in universe.teams
    assert universe.teams["UGA"].offense_index == 1.4
    # Historic silent coerce must stay gone from the hydrate / builder path.
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    power_src = open(
        os.path.join(
            root,
            "services",
            "model-service",
            "src",
            "services",
            "cfb_season_engine",
            "power_sot.py",
        ),
        encoding="utf-8",
    ).read()
    builder = open(
        os.path.join(root, "scripts", "cfb", "build_cfb_kei_futures_2026.py"),
        encoding="utf-8",
    ).read()
    assert "or 1.0)" not in power_src
    assert "or 1.0)" not in builder


def test_w2_mint_cannot_silently_keep_w0_stamps(monkeypatch) -> None:
    monkeypatch.delenv("CFB_CLOSE_AS_OF", raising=False)
    assert kei_version_for_weeks((0, 1, 2)) == DOCUMENTED_W2_KEI_VERSION
    assert kei_version_for_weeks((0,)) == "cfb-kei-v1.0-2026w0"
    as_of = resolve_kei_as_of(weeks=(0, 1, 2), explicit="2026-09-10")
    assert as_of == "2026-09-10"
    assert as_of != W0_CLOSE_AS_OF
    with pytest.raises(MissingRequiredTeamFeature, match="CFB_CLOSE_AS_OF"):
        resolve_kei_as_of(weeks=(0, 1, 2), explicit=None)
    with pytest.raises(MissingRequiredTeamFeature, match="2026-08-31"):
        resolve_kei_as_of(weeks=(0, 1, 2), explicit=W0_CLOSE_AS_OF)
    monkeypatch.setenv("CFB_CLOSE_AS_OF", "2026-09-10")
    assert resolve_kei_as_of(weeks=(0, 1, 2)) == "2026-09-10"
    monkeypatch.delenv("CFB_CLOSE_AS_OF", raising=False)
    assert resolve_kei_as_of(weeks=(0, 1), explicit=None) == W0_CLOSE_AS_OF


def test_public_kill_switch_stays_off() -> None:
    assert CFB_EDGE_BOARD_PUBLIC_ENABLED is False


def test_twin_maps_keep_p0_names_and_most_distinct() -> None:
    from src.services.cfb_warehouse.identity import ESPN_ABBR_TO_CODE, ESPN_NAME_TO_CODE

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    slate = open(
        os.path.join(root, "scripts", "cfb", "publish_official_slate_2026.py"),
        encoding="utf-8",
    ).read()
    roster = open(
        os.path.join(root, "scripts", "cfb", "package_real_roster_2026.py"),
        encoding="utf-8",
    ).read()
    assert '"missouri": "MIZZ"' in slate
    assert '"missouri state": "MOST"' in slate
    assert '"MIZZ": "MIZ"' in roster
    assert ESPN_ABBR_TO_CODE["MIZ"] == "MIZZ"
    assert ESPN_ABBR_TO_CODE["MIZZ"] == "MIZZ"
    assert ESPN_ABBR_TO_CODE["MOST"] == "MOST"
    assert ESPN_NAME_TO_CODE["Missouri"] == "MIZZ"
    assert ESPN_NAME_TO_CODE["Missouri State"] == "MOST"
    for code, name in P0_SHORT_NAMES.items():
        assert ESPN_NAME_TO_CODE[name] == code, name
