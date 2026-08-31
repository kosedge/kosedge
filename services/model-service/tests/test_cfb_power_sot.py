"""Single Power SoT + frozen season-projection artifact (CFB-only)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.cfb_season_engine import build_packaged_universe, loaders
from src.services.cfb_season_engine.power_sot import (
    USED_IN_SPREAD,
    build_power_sot,
    build_season_projection_artifact,
    frozen_home_wp,
)


def setup_function() -> None:
    loaders._PACKAGED_UNIVERSE_CACHE.clear()


def test_power_sot_is_official_136() -> None:
    universe = build_packaged_universe(2026)
    sot = build_power_sot(universe)
    assert sot["n_teams"] == 136
    assert sot["used_in_spread"] is False
    assert sot["kei"] is False
    assert USED_IN_SPREAD is False
    with_idx = [r for r in sot["teams"] if r.get("offense_index") is not None]
    assert len(with_idx) >= 120
    uga = sot["by_team"]["UGA"]
    live = universe.teams["UGA"]
    assert uga["offense_index"] == round(live.offense_index, 4)
    assert uga["defense_index"] == round(live.defense_index, 4)


def test_frozen_projection_locks_week0_finals() -> None:
    universe = build_packaged_universe(2026)
    art = build_season_projection_artifact(universe, n_sims=50, seed=7)
    assert art["n_sims"] == 50
    assert art["used_in_spread"] is False
    assert art.get("n_games_locked", 0) >= 6
    assert art["kei"] is False
    assert "lineage" in art


def test_frozen_home_wp_cupcake_nineties() -> None:
    # Margin 28 with fat early SD still clears 0.90 via saturation.
    wp = frozen_home_wp(49.0, 21.0, sd=16.5)
    assert wp >= 0.90 - 1e-9
