"""CFB research desk payloads — 136 DNA + official W0/W1 board."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.routes.cfb import ProjectGameBody
from src.services.cfb_season_engine import (
    build_packaged_universe,
    engine_status_payload,
    project_game_preview,
    project_game_to_dict,
    simulate_full_season,
)
from src.services.cfb_season_engine.product_desk import (
    official_week_board,
    product_desk_payload,
    team_dna_table,
)
from src.services.cfb_season_engine.season_sim import season_sim_to_dict


def test_week_board_has_week0_and_week1() -> None:
    board = official_week_board((0, 1))
    weeks = {int(g["week"]) for g in board["games"]}
    assert 0 in weeks
    assert 1 in weeks
    assert board["n_games"] >= 20
    assert board["used_in_spread"] is False
    assert board["kei"] is False
    assert any(
        g["home"] == "TCU" and g["away"] == "UNC" and g["week"] == 0
        for g in board["games"]
    )


def test_team_dna_is_official_136() -> None:
    universe = build_packaged_universe(2026)
    dna = team_dna_table(universe)
    assert dna["n"] == 136
    assert dna["official_fbs"] == 136
    assert dna["used_in_spread"] is False
    codes = {row["team"] for row in dna["teams"]}
    assert "UGA" in codes
    assert "MIZZ" in codes
    assert "ND" in codes
    warehouse = [r for r in dna["teams"] if r["efficiency_fill"] == "warehouse"]
    assert warehouse  # fills are visible, not silent
    assert all(r.get("offense_index") is not None for r in dna["teams"])


def test_status_attaches_desk_and_used_in_spread_false() -> None:
    status = engine_status_payload(season=2026, demo=True)
    assert status["used_in_spread"] is False
    desk = status["desk"]
    assert desk["used_in_spread"] is False
    assert desk["kei"] is False
    assert desk["team_dna"]["n"] == 136
    assert desk["week_board"]["n_games"] >= 20


def test_project_game_accepts_week_zero() -> None:
    body = ProjectGameBody(home_team="TCU", away_team="UNC", week=0)
    assert body.week == 0
    universe = build_packaged_universe(2026)
    proj = project_game_preview(
        universe, home_team="TCU", away_team="UNC", week=0, n_sims=200, seed=2026
    )
    payload = project_game_to_dict(proj)
    spread = payload.get("spread_home")
    total = payload.get("expected_total") or payload.get("fair_total")
    sigma = payload.get("margin_sd") or (payload.get("uncertainty") or {}).get(
        "effective_margin_sd"
    )
    assert spread is not None
    assert total is not None and float(total) > 20
    assert sigma is not None
    assert payload.get("used_in_spread") is False


def test_simulate_keeps_cfp_stub() -> None:
    universe = build_packaged_universe(2026)
    result = simulate_full_season(universe, n_sims=2, seed=7)
    payload = season_sim_to_dict(result)
    assert payload["used_in_spread"] is False
    assert payload["cfp_make"] is None
    assert payload["natty"] is None
    assert payload["win_tables_final"] is False
    assert len(payload["ranking"]) >= 100


def test_product_desk_payload_contract() -> None:
    universe = build_packaged_universe(2026)
    desk = product_desk_payload(universe)
    assert desk["research_only"] is True
    assert desk["kei"] is False
    assert desk["used_in_spread"] is False
