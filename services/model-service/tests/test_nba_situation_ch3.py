"""NBA Chapter 3 — situation class gates (on-read modifiers)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nba_season_engine import priors as P
from src.services.nba_season_engine.roster_minutes import get_rebased_team
from src.services.nba_season_engine.situation import (
    apply_situation_for_game,
    apply_situation_to_player_projections,
    apply_situation_to_team,
    coefficients,
    load_situation_pack,
    load_venues_pack,
    situation_net_delta,
    venue_altitude_class,
)
from src.services.nba_season_engine.team_prior import load_team_prior_pack

CFB_KEI = (
    Path(__file__).resolve().parents[1]
    / "src/services/cfb_season_engine/data/cfb_kei_w0_w1_2026.json"
)


def test_ch3_constants_and_ch1_ch2_untouched() -> None:
    assert P.ENGINE_VERSION == "nba-season-engine-v0.1"
    assert P.TEAM_CARRY_SHRINK == 0.85
    assert P.TEAM_REBASE_RESIDUAL_CAP == 3.0
    assert P.SITUATION_HOME_NET == 1.5
    assert P.SITUATION_B2B_NET == -2.0
    assert P.SITUATION_TRAVEL_NET == -1.0
    assert P.SITUATION_ALTITUDE_NET == -1.5
    assert P.SITUATION_NET_CAP == 4.0
    assert P.TRAVEL_TZ_BAND_MIN_HOURS == 2
    ch1 = load_team_prior_pack(force=True)
    assert ch1["TEAM_CARRY_SHRINK"] == 0.85
    coefs = coefficients()
    assert coefs["SITUATION_HOME_NET"] == 1.5
    assert coefs["SITUATION_NET_CAP"] == 4.0


def test_venues_altitude_class_not_team_if() -> None:
    venues = load_venues_pack()
    assert venues["present"] is True
    assert len(venues["venues"]) == 30
    assert venue_altitude_class("DEN") is True
    assert venue_altitude_class("UTA") is True
    assert venue_altitude_class("LAL") is False
    # Application path uses venue flag helper — never scan team names in source.
    src = (
        Path(__file__).resolve().parents[1]
        / "src/services/nba_season_engine/situation.py"
    ).read_text(encoding="utf-8")
    # Executable branches only — docstring prose may mention the forbid.
    body = src.split('"""', 2)[-1] if src.count('"""') >= 2 else src
    assert 'if team ==' not in body
    assert '== "DEN"' not in body
    assert "== 'DEN'" not in body
    assert '== "Nuggets"' not in body


def test_situation_cap_and_class_math() -> None:
    # All four classes: 1.5 - 2.0 - 1.0 - 1.5 = -3.0 inside cap 4
    sit = situation_net_delta(
        {
            "home": True,
            "rest_class": True,
            "travel": True,
            "altitude_visitor": True,
        }
    )
    assert sit["raw_net"] == -3.0
    assert sit["delta_net"] == -3.0
    assert sit["capped"] is False

    # Force a cap: pretend huge home by using raw parts via large travel stack —
    # with locked coefs max |raw| is 1.5+2+1+1.5=6 → cap to 4 when all adverse away
    sit_away = situation_net_delta(
        {
            "home": False,
            "rest_class": True,
            "travel": True,
            "altitude_visitor": True,
        }
    )
    assert sit_away["raw_net"] == -4.5
    assert sit_away["delta_net"] == -4.0
    assert sit_away["capped"] is True


def test_apply_on_read_keeps_ratings_sane() -> None:
    base = get_rebased_team("BOS")
    assert base is not None
    home = apply_situation_to_team("BOS", home=True)
    assert home is not None
    assert home["net_rating"] == round(float(base["net_rating"]) + 1.5, 4)
    assert abs(home["ortg"] - home["drtg"] - home["net_rating"]) < 1e-6
    # League-sane band (not lottery 90s / not 140)
    assert 105.0 <= home["ortg"] <= 125.0
    assert 105.0 <= home["drtg"] <= 125.0

    away_b2b = apply_situation_to_team("BOS", home=False, b2b=True)
    assert away_b2b is not None
    assert away_b2b["net_rating"] == round(float(base["net_rating"]) - 2.0, 4)


def test_altitude_visitor_uses_venue_flag() -> None:
    # Visitor at DEN venue — altitude_class on venue, not team==DEN
    line = apply_situation_to_team(
        "LAL",
        home=False,
        venue_team="DEN",
    )
    assert line is not None
    assert line["situation_flags"]["altitude_visitor"] is True
    assert line["situation"]["delta_net"] == -1.5


def test_player_copy_through_respects_residual_cap() -> None:
    line = apply_situation_to_team("OKC", home=True)
    assert line is not None
    rows = apply_situation_to_player_projections("OKC", line)
    assert len(rows) == 9
    sum_pts = sum(float(r["PTS"]) for r in rows)
    assert abs(sum_pts - float(line["implied_ppg"])) <= P.TEAM_REBASE_RESIDUAL_CAP + 1e-6


def test_schedule_pack_and_game_apply() -> None:
    pack = load_situation_pack()
    assert pack["present"] is True
    assert pack["n_games"] >= 1000
    # Find an away altitude visitor game
    hit = None
    for g in pack["games"]:
        if g.get("away_altitude_visitor"):
            hit = g
            break
    assert hit is not None
    out = apply_situation_for_game(hit["game_id"], hit["away"])
    assert out is not None
    assert out["situation_flags"]["altitude_visitor"] is True
    assert abs(out["player_pts_drift"]) <= P.TEAM_REBASE_RESIDUAL_CAP + 1e-6


def test_no_prop_tag_fields_and_cfb_untouched() -> None:
    pack = load_situation_pack()
    # No stake-tag product fields on games / coefficients.
    assert "publish_tag" not in pack
    assert "edge_tag" not in pack
    assert "PROP_PLAY" not in json.dumps(pack.get("coefficients") or {})
    for g in (pack.get("games") or [])[:20]:
        assert "tag" not in g
        assert "PLAY" not in g
    kei = json.loads(CFB_KEI.read_text(encoding="utf-8"))
    ball = next(
        g
        for g in kei["games"]
        if g.get("week") == 1 and g.get("home") == "OSU" and g.get("away") == "BALL"
    )
    assert ball["kei"]["kei_spread_home"] == -40.51
