"""NFL depth + coaching one source of truth."""

from __future__ import annotations

from src.services.nfl_season_engine.coaching_staff import (
    COACHING_SOURCE_PACKAGED,
    coaching_intel_rows,
    continuity_staff_from_packaged,
    load_packaged_coaching_staff,
    packaged_depth_intel_rows,
    packaged_roster_pulse_rows,
)
from src.services.nfl_season_engine.loaders import (
    ROSTER_SOURCE_PACKAGED,
    build_packaged_real_universe,
    load_packaged_depth_chart,
    resolve_season_universe,
)
from src.services.nfl_season_engine import project_game_player_boxes


def test_packaged_coaching_covers_32_named_hc() -> None:
    book, meta = load_packaged_coaching_staff(2026)
    assert meta["coaching_source"] == COACHING_SOURCE_PACKAGED
    assert meta["coaching_team_count"] == 32
    assert meta["coaching_named_hc_count"] == 32
    assert meta["coaching_full_staff_count"] >= 31  # TB DC thin
    assert not meta["coaching_holes"]
    assert "TB" in meta["coaching_thin_dc"]

    ari = book["ARI"]
    assert ari["hc_name"] == "Mike LaFleur"
    assert ari["oc_name"] == "Nathaniel Hackett"
    assert ari["dc_name"] == "Nick Rallis"
    assert ari["new_hc"] is True
    assert ari["new_oc"] is True

    kc = book["KC"]
    assert kc["hc_name"] == "Andy Reid"
    assert kc["new_hc"] is False

    sf = book["SF"]
    assert sf["hc_name"] == "Kyle Shanahan"
    assert sf["oc_name"] == "Klay Kubiak"


def test_continuity_staff_does_not_invent_new_defaults() -> None:
    staff = continuity_staff_from_packaged(2026)
    assert staff["ARI"]["new_hc"] is True
    assert staff["KC"]["new_hc"] is False
    # Unknown flags omitted (not coerced to False/new)
    hou = staff.get("HOU", {})
    assert hou.get("new_hc") is False
    assert "new_oc" not in hou or hou.get("new_oc") is None or isinstance(
        hou.get("new_oc"), bool
    )


def test_coaching_intel_rows_ari_live() -> None:
    rows, meta = coaching_intel_rows(season=2026, team="ARI")
    assert len(rows) == 1
    assert rows[0]["hc_name"] == "Mike LaFleur"
    assert rows[0]["status"] in ("live", "thin_dc")
    assert rows[0]["continuity_label"] == "new_staff"
    assert meta["coaching_team_count"] == 32


def test_packaged_depth_intel_matches_engine_qb1() -> None:
    depth_rows, depth_meta = packaged_depth_intel_rows(
        season=2026, week=1, team="ARI"
    )
    assert depth_meta["roster_source"] == ROSTER_SOURCE_PACKAGED
    qb1 = next(
        r
        for r in depth_rows
        if r["position"] == "QB" and int(r["depth_order"]) == 1
    )
    assert "Brissett" in qb1["player_name"]
    assert qb1["depth_slot"] == "starter"

    roster_rows, _ = packaged_roster_pulse_rows(season=2026, week=1, team="ARI")
    assert len(roster_rows) > 0
    assert any(r["player_name"] == qb1["player_name"] for r in roster_rows)

    universe, meta = resolve_season_universe(season=2026, demo=False, session=None)
    assert meta["roster_source"] == ROSTER_SOURCE_PACKAGED
    ari_qb1 = next(
        r for r in universe.rosters["ARI"] if r.position == "QB" and r.depth_order == 1
    )
    assert ari_qb1.player_name == qb1["player_name"]


def test_smoke_depth_coverage_sample_teams() -> None:
    rows, _ = load_packaged_depth_chart(2026)
    by_team = {}
    for r in rows:
        by_team.setdefault(r["team"], []).append(r)
    assert len(by_team) == 32
    for team in ("ARI", "KC", "SF", "MIA", "LV"):
        qbs = sorted(
            [r for r in by_team[team] if r["position"] == "QB"],
            key=lambda x: x["depth_order"],
        )
        assert qbs, f"{team} missing QB depth"
        assert qbs[0]["player_name"]


def test_game_box_ari_uses_packaged_qb1() -> None:
    """ARI@LAC box path should surface the same QB1 as depth pack."""
    universe = build_packaged_real_universe(2026)
    assert universe.notes.get("roster_source") == ROSTER_SOURCE_PACKAGED
    ari_qb = next(
        r for r in universe.rosters["ARI"] if r.position == "QB" and r.depth_order == 1
    )
    week = 1
    home, away = "LAC", "ARI"
    for g in universe.schedule:
        if {g.home_team, g.away_team} == {"ARI", "LAC"}:
            week = int(g.week)
            home, away = g.home_team, g.away_team
            break
    proj = project_game_player_boxes(
        universe,
        home_team=home,
        away_team=away,
        week=week,
        n_replicates=40,
        seed=7,
    )
    ari_players = [p for p in proj.players if p.get("team") == "ARI"]
    assert ari_players
    qb = next(
        (
            p
            for p in ari_players
            if p.get("usage_role") == "QB1" or p.get("position") == "QB"
        ),
        None,
    )
    assert qb is not None
    assert qb["player_name"] == ari_qb.player_name
    assert "Brissett" in qb["player_name"]
