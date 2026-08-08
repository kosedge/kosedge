"""True PR foundation — gradual prior→current blend on the live load path."""

from __future__ import annotations

from collections import namedtuple
from typing import Any, Dict, List, Optional

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks
from src.services.nfl_season_engine import build_demo_universe, build_packaged_real_universe
from src.services.nfl_season_engine.efficiency_backbone import (
    UnitEfficiency,
    TeamEfficiencyPackage,
    blend_packages,
    prior_current_blend_weight,
    strength_payload_from_package,
    uncertainty_from_games,
)
from src.services.nfl_season_engine.injury_paths import apply_strength_shock
from src.services.nfl_season_engine.loaders import STRENGTH_SOURCE_DEMO
from src.services.nfl_season_engine.team_strength import initialize_strengths
from src.services.nfl_season_engine.types import TeamStrengthState


class _Result:
    def __init__(self, rows=None, row=None):
        self._rows = rows or []
        self._row = row

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row

    def scalar(self):
        if self._row is not None and hasattr(self._row, "n"):
            return self._row.n
        return 0


Row = namedtuple(
    "Row",
    "season week team off_epa_per_play_5g def_epa_allowed_per_play_5g "
    "pressure_rate_generated_5g pressure_rate_allowed_5g "
    "pass_rate_5g success_rate_offense_5g success_rate_defense_allowed_5g "
    "red_zone_td_rate_5g games_in_window_5",
)
TeamCount = namedtuple("TeamCount", "team n")


def _prior_row(team: str, off: float, deff: float) -> Any:
    return Row(
        2025, 18, team, off, deff, 0.18, 0.15, 0.58, 0.46, 0.42, 0.58, 5
    )


def _current_row(team: str, off: float, deff: float, games: int) -> Any:
    return Row(
        2026, 1, team, off, deff, 0.18, 0.15, 0.58, 0.50, 0.40, 0.60, games
    )


class _BlendSession:
    """Fake DB for true-PR blend smell tests."""

    def __init__(
        self,
        *,
        league_completed: int,
        team_games: Dict[str, int],
        prior_rows: List[Any],
        current_rows: Optional[List[Any]] = None,
    ):
        self.league_completed = league_completed
        self.team_games = team_games
        self.prior_rows = prior_rows
        self.current_rows = current_rows or []

    def execute(self, sql, params=None):
        query = str(sql)
        params = dict(params or {})
        if "COUNT(*)" in query and "nfl_dp_schedules" in query and "UNION ALL" not in query:
            return _Result(row=namedtuple("C", "n")(n=self.league_completed))
        if "UNION ALL" in query and "nfl_dp_schedules" in query:
            return _Result(
                rows=[TeamCount(team=t, n=n) for t, n in self.team_games.items()]
            )
        if "nfl_dp_team_st_kav_weekly" in query:
            return _Result(rows=[])
        if "nfl_dp_team_rolling_features_weekly" in query:
            seasons = list(params.get("seasons") or [])
            if seasons == [2025]:
                return _Result(rows=self.prior_rows)
            if seasons == [2026]:
                return _Result(rows=self.current_rows)
            raise AssertionError(f"Unexpected seasons={seasons}")
        raise AssertionError(f"Unexpected SQL: {query}")


def test_blend_weight_schedule_0_1_4_8() -> None:
    assert prior_current_blend_weight(current_games=0) == 0.0
    assert prior_current_blend_weight(current_games=1) == 0.125
    assert prior_current_blend_weight(current_games=4) == 0.5
    assert prior_current_blend_weight(current_games=8) == 1.0
    assert prior_current_blend_weight(current_games=17) == 1.0


def _patch_continuity_off(monkeypatch) -> None:
    """Isolate games/8 blend curve tests from continuity travel."""
    monkeypatch.setattr(
        "src.services.nfl_season_engine.continuity_score.build_continuity_book",
        lambda *args, **kwargs: {},
    )


def _patch_qb_premium_off(monkeypatch) -> None:
    """Isolate foundation blend tests from QB premium deltas."""
    monkeypatch.setattr(
        "src.services.nfl_season_engine.qb_premium.build_qb_premium_book",
        lambda *args, **kwargs: {},
    )


def test_live_loader_preseason_100_percent_prior(monkeypatch) -> None:
    """Smell 1: 0 REG → prior only; SEA-type ≫ ARI-type from real prior."""
    session = _BlendSession(
        league_completed=0,
        team_games={},
        prior_rows=[
            _prior_row("SEA", 0.05, -0.12),
            _prior_row("ARI", -0.04, 0.06),
        ],
    )
    monkeypatch.setattr(
        "src.services.nfl_season_engine.loaders.load_packaged_epa_priors",
        lambda season: ({}, {}),
    )
    _patch_continuity_off(monkeypatch)
    _patch_qb_premium_off(monkeypatch)
    out = tasks._load_team_strength_priors(session, season_year=2026, as_of_week=1)
    assert out["SEA"]["blend_current_weight"] == 0.0
    assert out["SEA"]["blend_prior_weight"] == 1.0
    assert out["SEA"]["offense_index"] > out["ARI"]["offense_index"]
    assert out["SEA"]["defense_index"] > out["ARI"]["defense_index"]
    sea_c = out["SEA"]["offense_index"] + out["SEA"]["defense_index"]
    ari_c = out["ARI"]["offense_index"] + out["ARI"]["defense_index"]
    assert sea_c > ari_c + 0.10
    assert out["SEA"]["variance"] >= uncertainty_from_games(0) - 0.01
    assert "demo" not in str(out["SEA"].get("_source", "")).lower()
    assert out["SEA"]["qb_premium"] == 0.0
    drivers = out["SEA"]["drivers"]
    assert drivers["stubs"]["qb_premium"] == "stub_not_applied"
    assert drivers["stubs"]["continuity"] == "stub_not_applied"
    assert drivers["uncertainty"]["sample_note"] == "wide_early"


def test_live_loader_one_game_small_move_not_recalibration(monkeypatch) -> None:
    """Smell 2: after 1 REG → w_current ≈ 1/8; not a hard switch to pure 5g."""
    monkeypatch.setattr(
        "src.services.nfl_season_engine.loaders.load_packaged_epa_priors",
        lambda season: ({}, {}),
    )
    _patch_continuity_off(monkeypatch)
    _patch_qb_premium_off(monkeypatch)
    session0 = _BlendSession(
        league_completed=0,
        team_games={},
        prior_rows=[_prior_row("SEA", 0.04, -0.10)],
    )
    prior_only = tasks._load_team_strength_priors(session0, season_year=2026, as_of_week=1)

    # Prior: moderate. Current: absurd one-game spike.
    session = _BlendSession(
        league_completed=16,
        team_games={"SEA": 1, "ARI": 1},
        prior_rows=[
            _prior_row("SEA", 0.04, -0.10),
            _prior_row("ARI", -0.03, 0.05),
        ],
        current_rows=[
            _current_row("SEA", 0.55, -0.50, 1),
            _current_row("ARI", 0.40, -0.35, 1),
        ],
    )
    out = tasks._load_team_strength_priors(session, season_year=2026, as_of_week=1)
    assert abs(out["SEA"]["blend_current_weight"] - 0.125) < 1e-9
    assert abs(out["SEA"]["blend_prior_weight"] - 0.875) < 1e-9
    assert out["SEA"]["_source"] == "efficiency_backbone_blend"
    # Blended offense moves toward spike but stays far from pure current.
    assert out["SEA"]["offense_index"] > prior_only["SEA"]["offense_index"]
    assert out["SEA"]["offense_index"] < 1.18  # not near clamp from 0.55 EPA
    assert out["SEA"]["variance"] >= 1.20  # still wide after 1 game


def test_live_loader_four_games_half_blend(monkeypatch) -> None:
    """Smell 3: ~4 games → ~50/50."""
    session = _BlendSession(
        league_completed=64,
        team_games={"NE": 4},
        prior_rows=[_prior_row("NE", 0.06, -0.05)],
        current_rows=[_current_row("NE", -0.02, 0.04, 4)],
    )
    monkeypatch.setattr(
        "src.services.nfl_season_engine.loaders.load_packaged_epa_priors",
        lambda season: ({}, {}),
    )
    _patch_continuity_off(monkeypatch)
    _patch_qb_premium_off(monkeypatch)
    out = tasks._load_team_strength_priors(session, season_year=2026, as_of_week=4)
    assert abs(out["NE"]["blend_current_weight"] - 0.5) < 1e-9
    assert abs(out["NE"]["blend_prior_weight"] - 0.5) < 1e-9


def test_live_loader_eight_plus_current_dominated(monkeypatch) -> None:
    """Smell 4: 8+ games → current-dominated."""
    session = _BlendSession(
        league_completed=128,
        team_games={"KC": 8},
        prior_rows=[_prior_row("KC", -0.05, 0.08)],
        current_rows=[_current_row("KC", 0.10, -0.12, 8)],
    )
    monkeypatch.setattr(
        "src.services.nfl_season_engine.loaders.load_packaged_epa_priors",
        lambda season: ({}, {}),
    )
    _patch_continuity_off(monkeypatch)
    _patch_qb_premium_off(monkeypatch)
    out = tasks._load_team_strength_priors(session, season_year=2026, as_of_week=9)
    assert out["KC"]["blend_current_weight"] == 1.0
    assert out["KC"]["blend_prior_weight"] == 0.0


def test_missing_current_keeps_prior(monkeypatch) -> None:
    session = _BlendSession(
        league_completed=16,
        team_games={"SEA": 1},  # ARI not yet played
        prior_rows=[
            _prior_row("SEA", 0.04, -0.10),
            _prior_row("ARI", -0.03, 0.05),
        ],
        current_rows=[_current_row("SEA", 0.20, -0.15, 1)],
    )
    monkeypatch.setattr(
        "src.services.nfl_season_engine.loaders.load_packaged_epa_priors",
        lambda season: ({}, {}),
    )
    _patch_continuity_off(monkeypatch)
    _patch_qb_premium_off(monkeypatch)
    out = tasks._load_team_strength_priors(session, season_year=2026, as_of_week=1)
    assert "ARI" in out
    assert out["ARI"]["blend_current_weight"] == 0.0
    assert out["SEA"]["blend_current_weight"] == 0.125


def test_full_strength_differs_when_injury_applied() -> None:
    """Smell 5: full-strength ≠ current after injury shock."""
    state = TeamStrengthState(
        team="PHI",
        offense_index=1.10,
        defense_index=1.05,
        full_strength_offense_index=1.10,
        full_strength_defense_index=1.05,
        source="efficiency_backbone_blend",
    )
    shocked = apply_strength_shock(state, offense_delta=-0.08)
    assert shocked.full_strength_offense_index == 1.10
    assert shocked.offense_index < shocked.full_strength_offense_index
    assert shocked.injury_delta_offense < 0
    assert "injury_shock" in shocked.source
    assert shocked.drivers["injury_availability_delta"]["status"] == "applied"


def test_strength_payload_exposes_full_vs_current_and_stubs() -> None:
    prior = TeamEfficiencyPackage(
        team="BUF",
        offense=UnitEfficiency(epa_per_play=0.08, success_rate=0.47, plays=1000),
        defense=UnitEfficiency(epa_per_play=-0.06, success_rate=0.41, plays=1000),
        games_played=17,
        variance=0.55,
        source="prior",
        prior_season=2025,
    )
    current = TeamEfficiencyPackage(
        team="BUF",
        offense=UnitEfficiency(epa_per_play=0.02, success_rate=0.44, plays=240),
        defense=UnitEfficiency(epa_per_play=0.01, success_rate=0.45, plays=240),
        games_played=4,
        variance=uncertainty_from_games(4),
        source="current",
    )
    blended = blend_packages(prior, current, current_games=4)
    payload = strength_payload_from_package(blended)
    assert abs(payload["blend_current_weight"] - 0.5) < 1e-9
    assert payload["full_strength_offense_index"] == payload["current_offense_index"]
    assert payload["injury_delta_offense"] == 0.0
    assert payload["qb_premium"] == 0.0
    # Past SOS status is exposed when applied; absent → thin_unavailable (not a fake stub).
    assert payload["drivers"]["stubs"]["true_time_of_game_sos"] in (
        "thin_unavailable",
        "applied_time_of_game",
        "applied_approximate",
        "mixed",
    )
    assert payload["drivers"]["stubs"]["injury_at_time_depth"] == "stub_not_applied"
    assert "st_index" in payload["drivers"]
    book = initialize_strengths({"BUF": payload})
    assert book["BUF"].full_strength_offense_index == book["BUF"].offense_index
    assert book["BUF"].blend_current_weight == 0.5


def test_packaged_real_has_no_demo_strength_labels() -> None:
    """Smell 7: production packaged path never carries demo strength labels."""
    packaged = build_packaged_real_universe(2026)
    for team, state in packaged.strengths.items():
        assert "demo" not in state.source.lower()
        assert state.source != STRENGTH_SOURCE_DEMO
    demo = build_demo_universe(2026)
    assert demo.strengths["NE"].source == STRENGTH_SOURCE_DEMO


def test_packaged_hierarchy_smell_sea_ari() -> None:
    packaged = build_packaged_real_universe(2026)
    sea = packaged.strengths["SEA"]
    ari = packaged.strengths["ARI"]
    assert (sea.offense_index + sea.defense_index) > (
        ari.offense_index + ari.defense_index + 0.15
    )
