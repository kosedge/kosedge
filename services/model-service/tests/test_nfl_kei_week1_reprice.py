"""Week 1 KEI reprice — Gate B desk factors (Model frozen)."""

from __future__ import annotations

import json
from pathlib import Path

from src.services.nfl_kei_week1_reprice import (
    Week1Pack,
    apply_week1_kei_reprice,
    load_week1_pack,
    week1_slate_reprice_table,
)
from src.services.nfl_decision_engine import assess_confidence


def _handicap(spread: float = -3.0, total: float = 44.0) -> dict:
    return {"spread_home": spread, "total_mean": total, "home_win_prob": 0.58}


def _apply(**kwargs):
    defaults = dict(
        handicap=_handicap(),
        home_abbr="PHI",
        away_abbr="WAS",
        week=1,
        season=2026,
        season_type="REG",
        pack=Week1Pack.empty(),
    )
    defaults.update(kwargs)
    return apply_week1_kei_reprice(**defaults)


def test_qb_named_starter_logs_zero_spread() -> None:
    pack = Week1Pack(
        loaded=True,
        skill_by_team={
            "MIN": [
                {
                    "team": "MIN",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Kyler Murray",
                    "competition_status": "named_starter",
                }
            ],
            "GB": [
                {
                    "team": "GB",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Jordan Love",
                    "competition_status": "named_starter",
                }
            ],
        },
    )
    new_h, log = _apply(home_abbr="MIN", away_abbr="GB", pack=pack)
    assert new_h["spread_home"] == -3.0
    assert log["qb_clear"] is True
    reasons = " ".join(e["reason"] for e in log["applied_factors"])
    assert "Kyler Murray" in reasons
    assert "Jordan Love" in reasons


def test_open_competition_widens_uncertainty_not_fake_spread() -> None:
    pack = Week1Pack(
        loaded=True,
        skill_by_team={
            "ATL": [
                {
                    "team": "ATL",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Tua Tagovailoa",
                    "competition_status": "open_competition",
                },
                {
                    "team": "ATL",
                    "position": "QB",
                    "depth_order": 2,
                    "player_name": "Michael Penix Jr.",
                    "competition_status": "open_competition",
                },
            ],
            "PIT": [
                {
                    "team": "PIT",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Aaron Rodgers",
                    "competition_status": "named_starter",
                }
            ],
        },
    )
    new_h, log = _apply(home_abbr="PIT", away_abbr="ATL", pack=pack)
    assert new_h["spread_home"] == -3.0
    assert log["spread_delta"] == 0.0
    assert log["qb_clear"] is False
    assert log["confidence_delta"] < 0
    reasons = " ".join(e["reason"] for e in log["applied_factors"])
    assert "open_competition" in reasons
    assert "Tua" in reasons
    conf = assess_confidence(qb_clear=log["qb_clear"])
    assert "qb_unresolved" in conf.unresolved_flags
    assert conf.score < assess_confidence(qb_clear=True).score


def test_qb_backup_dropoff_home_weaker() -> None:
    pack = Week1Pack(
        loaded=True,
        skill_by_team={
            "PIT": [
                {
                    "team": "PIT",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Starter",
                    "competition_status": "named_starter",
                    "injury_status": "out",
                }
            ],
            "CLE": [
                {
                    "team": "CLE",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Watson",
                    "competition_status": "named_starter",
                }
            ],
        },
    )
    new_h, log = _apply(home_abbr="PIT", away_abbr="CLE", pack=pack, handicap=_handicap(-7.0))
    # Home QB out → home weaker → spread more positive (-7 → -3.5). Same-coast: no travel.
    assert new_h["spread_home"] == -3.5
    assert log["spread_delta"] == 3.5
    assert log["qb_clear"] is False


def test_injury_ol_away_weaker() -> None:
    pack = Week1Pack(
        loaded=True,
        ol_by_team={
            "WAS": [
                {
                    "team": "WAS",
                    "position": "LT",
                    "depth_order": 99,
                    "depth_slot": "out",
                    "player_name": "Laremy Tunsil",
                    "injury_status": "out",
                }
            ]
        },
        skill_by_team={
            "WAS": [
                {
                    "team": "WAS",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Jayden Daniels",
                    "competition_status": "named_starter",
                }
            ],
            "PHI": [
                {
                    "team": "PHI",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Jalen Hurts",
                    "competition_status": "named_starter",
                }
            ],
        },
    )
    new_h, log = _apply(pack=pack)
    # Away LT out → shock_table_v1 LT (0.80) → away weaker → home more favored
    assert new_h["spread_home"] == -3.8
    assert log["spread_delta"] == -0.8
    reasons = " ".join(e["reason"] for e in log["applied_factors"])
    assert "Tunsil" in reasons
    assert "shock_table_v1" in reasons
    skipped = " ".join(e["reason"] for e in log["considered_not_applied"])
    assert "unit wipe skipped" in skipped
    assert "no double-count" in skipped


def test_injury_not_restacked_when_already_in_model() -> None:
    pack = Week1Pack(
        loaded=True,
        ol_by_team={
            "WAS": [
                {
                    "team": "WAS",
                    "position": "LT",
                    "depth_order": 99,
                    "depth_slot": "out",
                    "player_name": "Laremy Tunsil",
                    "injury_status": "out",
                }
            ]
        },
    )
    projection = {
        "diagnostics": {
            "injury_kei_reprice": {"net_spread_pts": 0.5},
        }
    }
    new_h, log = _apply(pack=pack, projection=projection)
    assert new_h["spread_home"] == -3.0
    skipped = " ".join(e["reason"] for e in log["considered_not_applied"])
    assert "not restacked" in skipped


def test_te3_out_not_applied() -> None:
    pack = Week1Pack(
        loaded=True,
        skill_by_team={
            "WAS": [
                {
                    "team": "WAS",
                    "position": "TE",
                    "depth_order": 3,
                    "player_name": "John Bates",
                    "injury_status": "out",
                },
                {
                    "team": "WAS",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Jayden Daniels",
                    "competition_status": "named_starter",
                },
            ],
            "PHI": [
                {
                    "team": "PHI",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Jalen Hurts",
                    "competition_status": "named_starter",
                }
            ],
        },
    )
    new_h, log = _apply(pack=pack)
    assert new_h["spread_home"] == -3.0
    skipped = " ".join(e["reason"] for e in log["considered_not_applied"])
    assert "Bates" in skipped
    assert "not a key role" in skipped


def test_cross_country_travel_away_weaker() -> None:
    new_h, log = _apply(home_abbr="SEA", away_abbr="NE")
    # NE travels 3 TZ bands west → visitor weaker → home spread more negative
    assert log["spread_delta"] == -1.0
    assert new_h["spread_home"] == -4.0
    assert new_h["total_mean"] == 43.5
    reasons = " ".join(e["reason"] for e in log["applied_factors"])
    assert "travels 3 TZ" in reasons


def test_same_coast_travel_not_applied() -> None:
    new_h, log = _apply(home_abbr="LAC", away_abbr="ARI")
    assert log["spread_delta"] == 0.0
    skipped = " ".join(e["reason"] for e in log["considered_not_applied"])
    assert "same-coast" in skipped


def test_weather_stub_outdoor_and_indoor() -> None:
    _, outdoor = _apply(home_abbr="SEA", away_abbr="NE")
    weather = [e["reason"] for e in outdoor["considered_not_applied"] if e["factor"] == "weather"]
    assert weather
    assert "not applied" in weather[0]
    assert "indoor" not in weather[0]

    _, indoor = _apply(home_abbr="DET", away_abbr="NO")
    weather_i = [e["reason"] for e in indoor["considered_not_applied"] if e["factor"] == "weather"]
    assert weather_i
    assert "indoor" in weather_i[0]


def test_outdoor_extreme_wind_moves_total_kei() -> None:
    new_h, log = _apply(
        home_abbr="PHI",
        away_abbr="WAS",
        weather_obs={"available": True, "source": "test", "wind_mph": 28, "temp_f": 55, "precip_mm": 0},
    )
    assert log["total_delta"] == -1.5
    assert new_h["total_mean"] == 42.5
    assert new_h["spread_home"] == -3.0  # weather is totals-only
    reasons = " ".join(e["reason"] for e in log["applied_factors"])
    assert "wind 28" in reasons


def test_dome_stays_flat_even_with_extreme_wind_obs() -> None:
    new_h, log = _apply(
        home_abbr="MIN",
        away_abbr="GB",
        weather_obs={"available": True, "source": "test", "wind_mph": 30, "temp_f": 5, "precip_mm": 4},
    )
    weather = [e for e in log["considered_not_applied"] if e["factor"] == "weather"]
    assert weather and "indoor" in weather[0]["reason"]
    assert log["total_delta"] == 0.0
    assert new_h["total_mean"] == 44.0


def test_ref_stub_always_logged() -> None:
    _, log = _apply()
    refs = [e for e in log["considered_not_applied"] if e["factor"] == "ref"]
    assert refs
    assert "ref not applied" in refs[0]["reason"]


def test_ref_crew_tiny_total_does_not_dominate() -> None:
    officials = {
        "loaded": True,
        "crews": [
            {"home": "PHI", "away": "WAS", "crew": "Kemp", "total_tendency": 1.5},
        ],
    }
    new_h, log = _apply(officials=officials)
    refs = [e for e in log["applied_factors"] if e["factor"] == "ref"]
    assert refs
    assert refs[0]["total_pts"] == 0.5  # cap
    assert new_h["total_mean"] == 44.5
    assert new_h["spread_home"] == -3.0


def test_short_week_not_applied_week1() -> None:
    _, log = _apply()
    reasons = " ".join(e["reason"] for e in log["considered_not_applied"])
    assert "short_week not applied" in reasons


def test_pre_slate_skipped() -> None:
    new_h, log = _apply(season_type="PRE")
    assert new_h["spread_home"] == -3.0
    assert log["skipped"] is True


def test_identity_when_spread_missing() -> None:
    new_h, log = _apply(handicap={"total_mean": 44.0})
    assert "spread_home" not in new_h or new_h.get("spread_home") is None
    assert log["skipped"] is True
    assert "identity fallback" in log["reason"]


def test_caps_bind_runaway_stack() -> None:
    pack = Week1Pack(
        loaded=True,
        skill_by_team={
            "KC": [
                {
                    "team": "KC",
                    "position": "QB",
                    "depth_order": 1,
                    "player_name": "Starter",
                    "competition_status": "named_starter",
                    "injury_status": "out",
                }
            ]
        },
        ol_by_team={
            "KC": [
                {
                    "team": "KC",
                    "position": "LT",
                    "depth_order": 99,
                    "depth_slot": "out",
                    "player_name": "LT",
                    "injury_status": "out",
                },
                {
                    "team": "KC",
                    "position": "C",
                    "depth_order": 1,
                    "player_name": "C",
                    "injury_status": "out",
                },
            ]
        },
    )
    # Home weaker from QB out 3.5 + shock_table LT+C (0.80+0.65) > spread cap 4.0
    new_h, log = _apply(home_abbr="KC", away_abbr="DEN", pack=pack, handicap=_handicap(-7.0))
    assert log["capped"] is True
    assert log["spread_delta"] == 4.0
    assert new_h["spread_home"] == -3.0


def test_week1_sot_smoke_model_neq_kei() -> None:
    pack = load_week1_pack(2026)
    assert pack.loaded
    schedule_path = (
        Path(__file__).resolve().parents[1]
        / "src/services/nfl_season_engine/data/nfl_regular_schedule_2026.json"
    )
    payload = json.loads(schedule_path.read_text(encoding="utf-8"))
    games = [g for g in payload["games"] if int(g["week"]) == 1]
    assert len(games) == 16
    rows = week1_slate_reprice_table(games, pack=pack)
    diverged = [r for r in rows if r["spread_delta"] or r["total_delta"]]
    assert len(diverged) >= 1

    by_game = {r["game"]: r for r in rows}

    atl = by_game["ATL @PIT"]
    atl_text = " ".join(atl["factors"] + atl["not_applied"])
    assert "open_competition" in atl_text

    mia = by_game["MIA @LV"]
    mia_text = " ".join(mia["factors"] + mia["not_applied"])
    assert "Willis" in mia_text or "named_starter" in mia_text

    minn = by_game["GB @MIN"]
    min_text = " ".join(minn["factors"] + minn["not_applied"])
    assert "Kyler" in min_text or "Murray" in min_text

    cle = by_game["CLE @JAX"]
    cle_text = " ".join(cle["factors"] + cle["not_applied"])
    # Desk accept (#296) closed Watson as named_starter; depth_slot may still
    # say open_competition historically — either label is honest SoT.
    assert (
        "Watson" in cle_text
        or "named_starter" in cle_text
        or "open_competition" in cle_text
    )

    was = by_game["WAS @PHI"]
    was_text = " ".join(was["factors"])
    assert "Tunsil" in was_text or was["spread_delta"] != 0

    # Several games move on travel/injury
    assert len(diverged) >= 4
    # Indoor home: weather stub is honest even when TZ travel still fires
    det = by_game["NO @DET"]
    indoor_weather = " ".join(det["not_applied"])
    assert "indoor" in indoor_weather
