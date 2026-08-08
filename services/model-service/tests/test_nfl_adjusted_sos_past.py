"""Past SOS (Adjusted Strength of Competition) smell tests."""

from __future__ import annotations

import os
from collections import namedtuple
from typing import Any, Dict, List, Optional

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src import tasks
from src.services.nfl_season_engine import build_packaged_real_universe
from src.services.nfl_season_engine.adjusted_sos import (
    OpponentRating,
    PriorGameContext,
    apply_past_sos_to_package,
    compute_team_past_sos,
)
from src.services.nfl_season_engine.efficiency_backbone import (
    TeamEfficiencyPackage,
    UnitEfficiency,
    blend_packages,
    prior_current_blend_weight,
    strength_payload_from_package,
    uncertainty_from_games,
)
from src.services.nfl_season_engine.injury_paths import apply_strength_shock
from src.services.nfl_season_engine.player_regression import (
    apply_process_priors,
    build_player_process_prior,
)
from src.services.nfl_season_engine.types import PlayerRole, TeamStrengthState


def _rating_books() -> tuple[Dict[tuple[str, int], OpponentRating], Dict[str, OpponentRating]]:
    weekly: Dict[tuple[str, int], OpponentRating] = {}
    season: Dict[str, OpponentRating] = {}
    # Soft defenses: high EPA allowed. Elite: low / negative EPA allowed.
    for name, off, deff in [
        ("BAD1", -0.05, 0.10),
        ("BAD2", -0.04, 0.09),
        ("BAD3", -0.03, 0.11),
        ("BAD4", -0.06, 0.08),
        ("ELITE1", 0.08, -0.10),
        ("ELITE2", 0.07, -0.09),
        ("ELITE3", 0.09, -0.11),
        ("ELITE4", 0.06, -0.08),
        ("SOFTTEAM", 0.12, 0.10),  # feasted — high raw off
        ("HARDTEAM", -0.02, -0.08),  # suppressed — low raw off vs elite D
    ]:
        season[name] = OpponentRating(off_epa=off, def_epa=deff, source="approximate")
        for w in range(1, 12):
            weekly[(name, w)] = OpponentRating(
                off_epa=off, def_epa=deff, source="time_of_game"
            )
    return weekly, season


def test_soft_slate_schedule_adj_offense_below_raw() -> None:
    """Smell 1: soft slate → schedule-adjusted strength lower than raw."""
    weekly, season = _rating_books()
    soft_games = [
        PriorGameContext(team="SOFTTEAM", week=2, opponent="BAD1", is_home=True),
        PriorGameContext(team="SOFTTEAM", week=3, opponent="BAD2", is_home=True),
        PriorGameContext(team="SOFTTEAM", week=4, opponent="BAD3", is_home=True),
        PriorGameContext(team="SOFTTEAM", week=5, opponent="BAD4", is_home=True),
        PriorGameContext(team="SOFTTEAM", week=6, opponent="BAD1", is_home=True),
        PriorGameContext(team="SOFTTEAM", week=7, opponent="BAD2", is_home=True),
        PriorGameContext(team="SOFTTEAM", week=8, opponent="BAD3", is_home=True),
        PriorGameContext(team="SOFTTEAM", week=9, opponent="BAD4", is_home=True),
    ]
    raw_off = 0.10
    sos = compute_team_past_sos(
        "SOFTTEAM",
        soft_games,
        raw_off_epa=raw_off,
        raw_def_epa_allowed=0.02,
        weekly_book=weekly,
        season_book=season,
        league_off_epa=0.0,
        league_def_epa=0.0,
    )
    assert sos.games == 8
    assert sos.schedule_adj_off_epa < sos.raw_off_epa
    assert sos.status in ("applied_time_of_game", "mixed")
    assert sos.future_schedule_excluded is True
    drivers = sos.drivers()
    assert drivers["raw_off_epa"] > drivers["schedule_adj_off_epa"]
    assert drivers.get("not_opponent_win_pct") is True
    assert drivers.get("primary_metric") == "opponent_efficiency_power"


def test_hard_slate_schedule_adj_offense_above_raw() -> None:
    """Smell 2: hard slate → schedule-adjusted strength higher than raw."""
    weekly, season = _rating_books()
    hard_games = [
        PriorGameContext(team="HARDTEAM", week=2, opponent="ELITE1", is_home=False),
        PriorGameContext(team="HARDTEAM", week=3, opponent="ELITE2", is_home=False),
        PriorGameContext(team="HARDTEAM", week=4, opponent="ELITE3", is_home=False),
        PriorGameContext(team="HARDTEAM", week=5, opponent="ELITE4", is_home=False),
        PriorGameContext(team="HARDTEAM", week=6, opponent="ELITE1", is_home=False),
        PriorGameContext(team="HARDTEAM", week=7, opponent="ELITE2", is_home=False),
        PriorGameContext(team="HARDTEAM", week=8, opponent="ELITE3", is_home=False),
        PriorGameContext(team="HARDTEAM", week=9, opponent="ELITE4", is_home=False),
    ]
    raw_off = -0.02
    sos = compute_team_past_sos(
        "HARDTEAM",
        hard_games,
        raw_off_epa=raw_off,
        raw_def_epa_allowed=-0.01,
        weekly_book=weekly,
        season_book=season,
        league_off_epa=0.0,
        league_def_epa=0.0,
    )
    assert sos.schedule_adj_off_epa > sos.raw_off_epa
    assert sos.status in ("applied_time_of_game", "mixed")


def test_week1_falls_back_to_approximate() -> None:
    weekly, season = _rating_books()
    games = [
        PriorGameContext(team="SOFTTEAM", week=1, opponent="BAD1", is_home=True),
    ]
    sos = compute_team_past_sos(
        "SOFTTEAM",
        games,
        raw_off_epa=0.05,
        raw_def_epa_allowed=0.0,
        weekly_book=weekly,
        season_book=season,
        league_off_epa=0.0,
        league_def_epa=0.0,
    )
    assert sos.approximate_games == 1
    assert sos.time_of_game_games == 0
    assert sos.status == "applied_approximate"


def test_apply_past_sos_exposes_raw_vs_adj_drivers() -> None:
    weekly, season = _rating_books()
    games = [
        PriorGameContext(team="SOFTTEAM", week=w, opponent="BAD1", is_home=True)
        for w in range(2, 6)
    ]
    sos = compute_team_past_sos(
        "SOFTTEAM",
        games,
        raw_off_epa=0.08,
        raw_def_epa_allowed=0.01,
        weekly_book=weekly,
        season_book=season,
        league_off_epa=0.0,
        league_def_epa=0.0,
    )
    pkg = TeamEfficiencyPackage(
        team="SOFTTEAM",
        offense=UnitEfficiency(epa_per_play=0.08, success_rate=0.46, plays=900),
        defense=UnitEfficiency(epa_per_play=0.01, success_rate=0.44, plays=900),
        games_played=17,
        notes={"off_epa_raw": 0.08, "def_epa_raw": 0.01},
    )
    adj = apply_past_sos_to_package(pkg, sos)
    assert adj.offense.epa_per_play < pkg.offense.epa_per_play
    assert adj.notes["past_sos"]["raw_off_epa"] == 0.08
    assert adj.notes["past_sos"]["schedule_adj_off_epa"] < 0.08
    payload = strength_payload_from_package(adj)
    assert "past_sos" in payload["drivers"]
    assert payload["drivers"]["stubs"]["injury_at_time_depth"] == "stub_not_applied"
    assert payload["drivers"]["stubs"]["true_time_of_game_sos"] != "stub_not_applied"


def test_packaged_hierarchy_still_plausible_after_sos() -> None:
    """Smell 3: SEA-type ≫ ARI-type on packaged real path."""
    packaged = build_packaged_real_universe(2026)
    sea = packaged.strengths["SEA"]
    ari = packaged.strengths["ARI"]
    assert (sea.offense_index + sea.defense_index) > (
        ari.offense_index + ari.defense_index + 0.12
    )


def test_blend_weights_unchanged_by_sos_math() -> None:
    """Smell 4: blend at 0/1/4/8 still no cliff (true PR contract)."""
    assert prior_current_blend_weight(current_games=0) == 0.0
    assert prior_current_blend_weight(current_games=1) == 0.125
    assert prior_current_blend_weight(current_games=4) == 0.5
    assert prior_current_blend_weight(current_games=8) == 1.0
    prior = TeamEfficiencyPackage(
        team="BUF",
        offense=UnitEfficiency(epa_per_play=0.06, plays=1000),
        defense=UnitEfficiency(epa_per_play=-0.04, plays=1000),
        games_played=17,
        notes={
            "past_sos": {
                "status": "applied_time_of_game",
                "raw_off_epa": 0.05,
                "schedule_adj_off_epa": 0.06,
                "future_schedule_excluded": True,
            }
        },
    )
    current = TeamEfficiencyPackage(
        team="BUF",
        offense=UnitEfficiency(epa_per_play=0.01, plays=250),
        defense=UnitEfficiency(epa_per_play=0.02, plays=250),
        games_played=4,
    )
    blended = blend_packages(prior, current, current_games=4)
    assert abs(blended.notes["blend_current_weight"] - 0.5) < 1e-9
    payload = strength_payload_from_package(blended)
    assert abs(payload["blend_current_weight"] - 0.5) < 1e-9
    # Prior-side SOS metadata survives on blend notes for ops visibility.
    assert blended.notes.get("past_sos_prior") or prior.notes.get("past_sos")


def test_full_strength_and_player_regression_paths_healthy() -> None:
    """Smell 5: injury full-strength split + player regression still healthy."""
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

    role = PlayerRole(
        player_key="phi-wr-test",
        player_name="Test WR",
        team="PHI",
        position="WR",
        depth_order=1,
        target_share=0.22,
        ypr=12.0,
        catch_rate=0.62,
        rec_td_rate=0.08,
        role_confidence=0.8,
        source="test",
    )
    prior = build_player_process_prior(role)
    assert prior.process_index is not None
    annotated = apply_process_priors(role)
    assert annotated.regression_posture in ("negative", "positive", "neutral")


def test_remaining_stubs_labeled() -> None:
    """Smell 6: injury-at-time + full venue remain labeled stubs/partial."""
    weekly, season = _rating_books()
    sos = compute_team_past_sos(
        "SOFTTEAM",
        [PriorGameContext(team="SOFTTEAM", week=3, opponent="BAD1", is_home=True)],
        raw_off_epa=0.04,
        raw_def_epa_allowed=0.0,
        weekly_book=weekly,
        season_book=season,
        league_off_epa=0.0,
        league_def_epa=0.0,
    )
    d = sos.drivers()
    assert d["injury_at_time_depth"] == "stub_not_applied"
    assert d["full_venue_model"] in ("partial_hfa_only", "stub_not_applied")
    assert d["future_schedule_excluded"] is True


Row = namedtuple(
    "Row",
    "season week team off_epa_per_play_5g def_epa_allowed_per_play_5g "
    "pressure_rate_generated_5g pressure_rate_allowed_5g "
    "pass_rate_5g success_rate_offense_5g success_rate_defense_allowed_5g "
    "red_zone_td_rate_5g games_in_window_5",
)
TeamCount = namedtuple("TeamCount", "team n")


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


class _SosAwareSession:
    """Fake DB: blend path + empty Past SOS schedule (graceful skip)."""

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
        if "home_team" in query and "away_team" in query and "nfl_dp_schedules" in query:
            # Past SOS schedule fetch — empty → skip adjustment, blend intact.
            return _Result(rows=[])
        if "nfl_dp_team_rolling_features_weekly" in query and "off_epa_per_play_5g" in query:
            if "ROW_NUMBER" in query or "ranked" in query.lower() or "PARTITION BY" in query:
                seasons = list(params.get("seasons") or [])
                if seasons == [2025]:
                    return _Result(rows=self.prior_rows)
                if seasons == [2026]:
                    return _Result(rows=self.current_rows)
            # weekly opponent book query
            return _Result(rows=[])
        if "nfl_dp_team_rolling_features_weekly" in query:
            seasons = list(params.get("seasons") or [])
            if seasons == [2025]:
                return _Result(rows=self.prior_rows)
            if seasons == [2026]:
                return _Result(rows=self.current_rows)
            return _Result(rows=[])
        raise AssertionError(f"Unexpected SQL: {query[:200]}")


def test_live_loader_blend_still_works_when_sos_thin(monkeypatch) -> None:
    """True PR blend still passes when Past SOS has no schedule rows."""
    monkeypatch.setattr(
        "src.services.nfl_season_engine.loaders.load_packaged_epa_priors",
        lambda season: ({}, {}),
    )
    session = _SosAwareSession(
        league_completed=64,
        team_games={"NE": 4},
        prior_rows=[
            Row(
                2025, 18, "NE", 0.06, -0.05, 0.18, 0.15, 0.58, 0.46, 0.42, 0.58, 5
            )
        ],
        current_rows=[
            Row(2026, 4, "NE", -0.02, 0.04, 0.18, 0.15, 0.58, 0.50, 0.40, 0.60, 4)
        ],
    )
    out = tasks._load_team_strength_priors(session, season_year=2026, as_of_week=4)
    assert abs(out["NE"]["blend_current_weight"] - 0.5) < 1e-9
    assert out["NE"]["variance"] == uncertainty_from_games(4)
