"""P2 preseason prior — official FBS, QB SoT, leakage, research-only."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine import (
    DEFAULT_SEASON_ENGINE_VERSION,
    engine_status_payload,
    project_game_preview,
    project_game_to_dict,
    build_packaged_universe,
)
from src.services.cfb_season_engine.fbs_universe import (
    is_official_fbs,
    official_fbs_codes,
)
from src.services.cfb_warehouse.leakage import assert_available_before_kickoff
from src.services.cfb_warehouse.preseason_prior import (
    PRIOR_VERSION,
    USED_IN_SPREAD,
    combine_prior,
    lookup_prior,
    rebuild_p2_from_packaged,
    research_prior_block,
    season_weight,
)


CAMP = ("UGA", "MICH", "FSU", "LSU")


def test_official_fbs_lock() -> None:
    codes = official_fbs_codes()
    assert len(codes) == 136
    assert "MIZZ" in codes
    assert "ND" in codes
    assert "CONN" in codes
    assert "ARMY" in codes
    for junk in ("ACU", "CHAT", "IDHO", "FAY", "SOUTH"):
        assert junk not in codes
        assert not is_official_fbs(junk)
    # Aliases resolve to official members; they are not themselves in the lock.
    assert "TXAM" not in codes
    assert is_official_fbs("TXAM")  # canonical TAMU
    assert is_official_fbs("UGA")
    trans = official_fbs_codes(include_transition=True)
    assert "NDSU" in trans and "NDSU" not in codes


def test_engine_version_and_status_never_blank() -> None:
    assert DEFAULT_SEASON_ENGINE_VERSION == "cfb-season-engine-v0.10-preseason-prior"
    status = engine_status_payload(season=2026, demo=True)
    assert status["engine_version"] == DEFAULT_SEASON_ENGINE_VERSION
    assert status.get("used_in_spread") is False
    assert status["preseason_prior"]["used_in_spread"] is False
    assert status["fbs_universe"]["n_fbs_full"] == 136


def test_every_official_team_has_mean_sigma_drivers() -> None:
    rows = rebuild_p2_from_packaged(as_of="2026-08-13")
    assert len(rows) == 136
    for row in rows:
        assert row["used_in_spread"] is False
        assert row["official_fbs"] is True
        assert isinstance(row["rating_mean"], float)
        assert isinstance(row["rating_sigma"], float)
        assert 3.2 <= row["rating_sigma"] <= 9.5
        comps = row["components"]
        assert "program_points" in comps
        assert "program_off_points" in comps
        assert "program_def_points" in comps
        assert "returning_by_unit" in comps
        assert set(comps["returning_by_unit"]) == {"ol", "skill", "front_seven", "secondary"}
        assert comps["qb_class"]
        assert "qb_sigma" in comps


def test_camp_qb_sot_not_false_incumbent() -> None:
    rows = {r["team_id"]: r for r in rebuild_p2_from_packaged(as_of="2026-08-13")}
    osu = rows["OSU"]
    for team in CAMP:
        row = rows[team]
        assert row["components"]["qb_class"] != "incumbent", team
        assert row["components"]["qb_class"] == "open_competition", team
        assert row["rating_sigma"] > osu["rating_sigma"], team
        assert row["components"]["qb_sigma"] > 5.5, team
    assert rows["FSU"]["components"]["qb_name"] == "Ashton Daniels"
    assert rows["LSU"]["components"]["qb_name"] == "Sam Leavitt"
    assert "Stockton" not in (rows["UGA"]["components"]["qb_name"] or "")
    assert "Underwood" not in (rows["MICH"]["components"]["qb_name"] or "")


def test_smell_blue_blood_vs_rebuild() -> None:
    rows = {r["team_id"]: r for r in rebuild_p2_from_packaged(as_of="2026-08-13")}
    assert rows["OSU"]["rating_mean"] > rows["BALL"]["rating_mean"] + 8
    assert rows["UGA"]["rating_mean"] > rows["MASS"]["rating_mean"]
    assert rows["BALL"]["rating_sigma"] > rows["OSU"]["rating_sigma"]


def test_used_in_spread_false_on_project_game() -> None:
    universe = build_packaged_universe(2026)
    proj = project_game_preview(
        universe, home_team="UGA", away_team="BALL", week=1, neutral_site=True
    )
    payload = project_game_to_dict(proj)
    assert payload["research_prior"]["used_in_spread"] is False
    assert payload["research_prior"]["kei"] is False
    assert payload["research_prior"]["home"]["qb_class"] != "incumbent"
    block = research_prior_block("UGA", "OSU")
    assert block["used_in_spread"] is False
    assert USED_IN_SPREAD is False
    assert PRIOR_VERSION.startswith("cfb-preseason-prior-v2")


def test_leakage_season_boundary_still_holds() -> None:
    assert season_weight(2026, 2026) == 0.0
    assert season_weight(2025, 2026) > 0.0
    try:
        assert_available_before_kickoff(
            available_at="2024-09-07T20:00:00+00:00",
            kickoff="2024-09-07T19:00:00+00:00",
        )
        raise AssertionError("same-timestamp must fail")
    except ValueError:
        pass


def test_missing_roster_is_labeled_not_silent_zero() -> None:
    row = combine_prior(
        team_id="MIZZ",
        prior_year=2026,
        program={"points": 8.4, "sigma": 4.8, "seasons": [2023, 2024, 2025]},
        roster_strength=50.0,
        returning_production=50.0,
        portal_out=50.0,
        qb_class="unknown",
        new_hc=False,
        as_of="2026-08-13",
        roster_present=False,
    )
    assert "roster_pack_missing_neutral" in row["components"]["missing_data"]
    assert row["components"]["roster_points"] == 0.0
    assert row["used_in_spread"] is False


def test_packaged_lookup_after_rebuild_contract() -> None:
    uga = lookup_prior("UGA")
    assert uga is not None
    assert uga.get("used_in_spread") in (False, None) or uga.get("used_in_spread") is False
