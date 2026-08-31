"""CFB enterprise gates — Week 0 close pass (CFB-only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.cfb_futures import select_cfp_field
from src.services.cfb_season_engine.cfb_kei import assert_kei_not_tail, apply_cfb_kei
from src.services.cfb_season_engine.team_projection import win_prob_from_expected_scores

DATA = Path(__file__).resolve().parents[1] / "src/services/cfb_season_engine/data"


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_unique_as_of_across_cfb_surfaces() -> None:
    power = _load("cfb_power_sot_2026.json")
    proj = _load("cfb_season_projections_2026.json")
    futures = _load("cfb_futures_2026.json")
    kei = _load("cfb_kei_w0_w1_2026.json")
    values = {
        power.get("power_as_of"),
        proj.get("as_of"),
        futures.get("as_of"),
        kei.get("as_of"),
    }
    assert None not in values
    assert len(values) == 1


def test_cupcake_wp_saturation_reaches_nineties() -> None:
    # Large favorite margins must print real 90s after SD saturation.
    for margin, sd in ((26.22, 22.38), (28.56, 22.88), (32.41, 22.70)):
        home, away = 35.0, 35.0 - margin
        wp = win_prob_from_expected_scores(home, away, margin_sd=sd)
        assert wp >= 0.90 - 1e-9, (margin, sd, wp)
    assert P.WP_POWER_GAP_T > 0
    assert P.WIN_PROB_MARGIN_SD == 15.2  # named scale not stretched for Vegas


def test_usf_std_tighter_than_osu() -> None:
    proj = _load("cfb_season_projections_2026.json")
    by = {r["team"]: r for r in proj["teams"]}
    assert by["USF"]["std"] < by["OSU"]["std"]


def test_top7_power_order_stable() -> None:
    power = _load("cfb_power_sot_2026.json")
    top = sorted(power["teams"], key=lambda r: -(r.get("power_index") or 0))[:7]
    # Ch2 Phase 2B s=0.85: membership may change only ORE↔MISS order and ND↔TEX.
    assert [r["team"] for r in top] == ["OSU", "MISS", "ORE", "MIA", "TAMU", "IU", "TEX"]
    assert abs(float(top[0]["power_index"]) - 1.5785) <= 0.01


def test_kei_not_tail_metrics() -> None:
    out = apply_cfb_kei(
        {
            "week": 1,
            "spread_home": -14.0,
            "expected_total": 52.0,
            "home_win_prob": 0.82,
            "margin_sd": 16.0,
        }
    )
    assert "kei_spread_home" in out
    assert_kei_not_tail(out)
    with pytest.raises(AssertionError, match="KEI_EQUALS_TAIL"):
        assert_kei_not_tail({**out, "natty_pct": 6.0})


def test_field_is_power_aware_p4_plus_g6() -> None:
    teams = [f"T{i:02d}" for i in range(20)]
    wins = {t: float(8 + (i % 5)) for i, t in enumerate(teams)}
    conf_wins = {t: float(5) for t in teams}
    conferences = {
        t: ["SEC", "Big Ten", "ACC", "Big 12", "AAC"][i % 5] for i, t in enumerate(teams)
    }
    power = {t: 1.6 - i * 0.03 for i, t in enumerate(teams)}
    field = select_cfp_field(
        teams=teams,
        wins=wins,
        conf_wins=conf_wins,
        conferences=conferences,
        power=power,
    )
    assert len(field) == 12
    assert len(set(field)) == 12


def test_live_engine_stamp_matches_frozen_artifacts() -> None:
    expected = "cfb-season-engine-v0.15-power-sot"
    assert P.ENGINE_VERSION == expected
    assert "v0.9-inseason" not in P.ENGINE_VERSION
    for name in (
        "cfb_power_sot_2026.json",
        "cfb_season_projections_2026.json",
        "cfb_futures_2026.json",
        "cfb_kei_w0_w1_2026.json",
    ):
        blob = _load(name)
        assert blob.get("engine_version") == expected, name


def test_live_default_universe_is_official_closed_slate() -> None:
    from src.services.cfb_season_engine.loaders import (
        build_packaged_universe,
        documentation,
    )

    uni = build_packaged_universe(2026)
    assert str(uni.notes.get("official_schedule")).lower() == "true"
    assert "densify" not in documentation()["schedule_policy"] or "fallback" in documentation()[
        "schedule_policy"
    ]
    policy = documentation()["schedule_policy"]
    assert "official" in policy.lower()
    # Week 0 finals remain locked on the live schedule objects.
    scored = [
        g
        for g in uni.schedule
        if getattr(g, "week", None) == 0
        and getattr(g, "home_score", None) is not None
        and getattr(g, "away_score", None) is not None
    ]
    assert len(scored) >= 6


def test_live_cupcake_project_game_matches_closed_nineties() -> None:
    from src.services.cfb_season_engine import project_game_preview, project_game_to_dict
    from src.services.cfb_season_engine.loaders import resolve_season_universe

    uni, _ = resolve_season_universe(season=2026, as_of_week=0, demo=True)
    cases = [
        ("OSU", "BALL", 0.98),
        ("USC", "FRES", 0.9278),
        ("RUT", "MASS", 0.9147),
    ]
    for home, away, expected in cases:
        proj = project_game_preview(
            uni, home_team=home, away_team=away, week=1, season=2026
        )
        payload = project_game_to_dict(proj)
        assert payload.get("engine_version") == P.ENGINE_VERSION
        wp = float(payload.get("home_win_prob") or 0.0)
        assert wp >= 0.90 - 1e-9, (home, away, wp)
        assert abs(wp - expected) <= 0.02, (home, away, wp, expected)


def test_week0_canary_ewins_unchanged_within_epsilon() -> None:
    proj = _load("cfb_season_projections_2026.json")
    by = {r["team"]: r for r in proj["teams"]}
    # Tag cfb-week0-close-2026-08-31 dump (no new board).
    assert abs(float(by["OSU"]["mean"]) - 9.537) <= 0.05
    assert abs(float(by["USF"]["mean"]) - 8.382) <= 0.05
    assert abs(float(by["UTAH"]["mean"]) - 9.634) <= 0.05
    assert abs(float(by["OSU"]["power_index"]) - 1.6168) <= 0.01
    assert abs(float(by["USF"]["power_index"]) - 1.2601) <= 0.01
    assert abs(float(by["UTAH"]["power_index"]) - 1.4841) <= 0.01
