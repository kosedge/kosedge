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
    assert [r["team"] for r in top] == ["OSU", "ORE", "MISS", "MIA", "IU", "TAMU", "ND"]
    assert abs(float(top[0]["power_index"]) - 1.6168) <= 0.01


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
