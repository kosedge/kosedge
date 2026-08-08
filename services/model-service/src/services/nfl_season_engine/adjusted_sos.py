"""Adjusted Strength of Competition (Past SOS) for prior-season performance.

Past SOS corrects how we read 2025 (and prior) efficiency before it enters the
true-PR prior→current blend. Future / projected 2026 schedule difficulty is
**never** applied here — that product is a separate pass and must not move
Week 1 intrinsic PR.

Formula (per historical REG game used in the prior):
  1. Opponent intrinsic rating at time of game (rolling week W−1 preferred)
  2. Optional venue (modest HFA) + rest when dates exist
  3. Active-roster / injury-at-time depth: stub until wired

Season aggregates:
  - Actual SOS (offense) = mean effective opponent defense EPA faced
  - Actual SOS (defense) = mean effective opponent offense EPA faced
  - Schedule-adjusted off EPA = raw_off + (league_def − mean_opp_def)
  - Schedule-adjusted def EPA allowed = raw_def + (league_off − mean_opp_off)

Soft slate (high opp.def EPA allowed) → schedule-adjusted offense **lower**
than raw. Hard slate → schedule-adjusted offense **higher** than raw.

North star: ``data/ops/nfl-model-vision.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.efficiency_backbone import (
    TeamEfficiencyPackage,
    UnitEfficiency,
    package_to_strength_indices,
)

# Modest home-field ease on the EPA scale (positive on opp.def = softer faced).
_HFA_OPP_DEF_EPA = 0.018
# Tiny rest context when dates exist (short rest for us → slightly harder).
_REST_SHORT_DAYS = 6
_REST_TEAM_SHORT_EPA = 0.008  # added to opp.def difficulty polarity via lowering ease
_REST_OPP_SHORT_EPA = 0.006  # opponent on short rest → slightly softer
# One-pass SOS uses lagged rolling (noisy early). Partial dampen keeps soft/hard
# polarity without inventing a full iterative KAV re-rank as false precision.
_SOS_DAMPEN = 0.70


@dataclass(frozen=True)
class OpponentRating:
    """Opponent power/efficiency used for SOS (offense EPA, defense EPA allowed)."""

    off_epa: float
    def_epa: float
    source: str  # time_of_game | approximate


@dataclass(frozen=True)
class PriorGameContext:
    """One completed REG game from the prior season slate."""

    team: str
    week: int
    opponent: str
    is_home: bool
    team_rest_days: Optional[int] = None
    opp_rest_days: Optional[int] = None
    game_id: str = ""


@dataclass
class TeamPastSos:
    """Season-level Past SOS + schedule-adjusted prior performance."""

    team: str
    games: int
    actual_sos_offense: float  # mean effective opp.def_epa faced (higher = softer)
    actual_sos_defense: float  # mean effective opp.off_epa faced (higher = harder)
    raw_off_epa: float
    raw_def_epa_allowed: float
    schedule_adj_off_epa: float
    schedule_adj_def_epa_allowed: float
    time_of_game_games: int = 0
    approximate_games: int = 0
    status: str = "thin_unavailable"
    venue_applied: bool = False
    rest_applied: bool = False
    future_schedule_excluded: bool = True
    notes: Dict[str, Any] = field(default_factory=dict)

    @property
    def time_of_game_share(self) -> float:
        if self.games <= 0:
            return 0.0
        return float(self.time_of_game_games) / float(self.games)

    def drivers(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "games_used": int(self.games),
            "time_of_game_games": int(self.time_of_game_games),
            "approximate_games": int(self.approximate_games),
            "time_of_game_share": round(self.time_of_game_share, 4),
            "actual_sos_offense": round(float(self.actual_sos_offense), 6),
            "actual_sos_defense": round(float(self.actual_sos_defense), 6),
            "raw_off_epa": round(float(self.raw_off_epa), 6),
            "schedule_adj_off_epa": round(float(self.schedule_adj_off_epa), 6),
            "raw_def_epa_allowed": round(float(self.raw_def_epa_allowed), 6),
            "schedule_adj_def_epa_allowed": round(
                float(self.schedule_adj_def_epa_allowed), 6
            ),
            "off_delta": round(
                float(self.schedule_adj_off_epa) - float(self.raw_off_epa), 6
            ),
            "def_delta": round(
                float(self.schedule_adj_def_epa_allowed)
                - float(self.raw_def_epa_allowed),
                6,
            ),
            "venue_applied": bool(self.venue_applied),
            "rest_applied": bool(self.rest_applied),
            "future_schedule_excluded": True,
            "injury_at_time_depth": "stub_not_applied",
            "full_venue_model": (
                "partial_hfa_only" if self.venue_applied else "stub_not_applied"
            ),
            **dict(self.notes or {}),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "games": self.games,
            "actual_sos_offense": self.actual_sos_offense,
            "actual_sos_defense": self.actual_sos_defense,
            "raw_off_epa": self.raw_off_epa,
            "raw_def_epa_allowed": self.raw_def_epa_allowed,
            "schedule_adj_off_epa": self.schedule_adj_off_epa,
            "schedule_adj_def_epa_allowed": self.schedule_adj_def_epa_allowed,
            "time_of_game_games": self.time_of_game_games,
            "approximate_games": self.approximate_games,
            "status": self.status,
            "venue_applied": self.venue_applied,
            "rest_applied": self.rest_applied,
            "future_schedule_excluded": True,
            "notes": dict(self.notes or {}),
        }


def normalize_team(team: str) -> str:
    t = str(team or "").strip().upper()
    if t == "LAR":
        return "LA"
    return t


def resolve_opponent_rating(
    opponent: str,
    *,
    game_week: int,
    weekly_book: Mapping[Tuple[str, int], OpponentRating],
    season_book: Mapping[str, OpponentRating],
    league_fallback: Optional[OpponentRating] = None,
) -> OpponentRating:
    """Prefer lag week W−1 rolling; else season package (approximate)."""
    opp = normalize_team(opponent)
    lag_week = int(game_week) - 1
    if lag_week >= 1:
        hit = weekly_book.get((opp, lag_week))
        if hit is not None:
            return OpponentRating(
                off_epa=float(hit.off_epa),
                def_epa=float(hit.def_epa),
                source="time_of_game",
            )
    season_hit = season_book.get(opp)
    if season_hit is not None:
        return OpponentRating(
            off_epa=float(season_hit.off_epa),
            def_epa=float(season_hit.def_epa),
            source="approximate",
        )
    if league_fallback is not None:
        return OpponentRating(
            off_epa=float(league_fallback.off_epa),
            def_epa=float(league_fallback.def_epa),
            source="approximate",
        )
    return OpponentRating(off_epa=0.0, def_epa=0.0, source="approximate")


def effective_opponent_units(
    rating: OpponentRating,
    *,
    is_home: bool,
    team_rest_days: Optional[int] = None,
    opp_rest_days: Optional[int] = None,
) -> Tuple[float, float, Dict[str, Any]]:
    """Return (eff_opp_def_epa, eff_opp_off_epa, meta) for SOS aggregation.

    Higher ``eff_opp_def_epa`` = softer defense faced by our offense.
    Higher ``eff_opp_off_epa`` = harder offense faced by our defense.
    """
    opp_def = float(rating.def_epa)
    opp_off = float(rating.off_epa)
    meta: Dict[str, Any] = {
        "venue_hfa": False,
        "rest": False,
        "rating_source": rating.source,
    }
    if is_home:
        # Home: opponent defense slightly easier to face.
        opp_def = opp_def + _HFA_OPP_DEF_EPA
        meta["venue_hfa"] = True
    else:
        opp_def = opp_def - _HFA_OPP_DEF_EPA
        meta["venue_hfa"] = True
    if team_rest_days is not None and int(team_rest_days) < _REST_SHORT_DAYS:
        # Short rest for us → slightly tougher environment (lower opp.def ease).
        opp_def = opp_def - _REST_TEAM_SHORT_EPA
        meta["rest"] = True
    if opp_rest_days is not None and int(opp_rest_days) < _REST_SHORT_DAYS:
        opp_def = opp_def + _REST_OPP_SHORT_EPA
        opp_off = opp_off - _REST_OPP_SHORT_EPA
        meta["rest"] = True
    return opp_def, opp_off, meta


def compute_team_past_sos(
    team: str,
    games: Sequence[PriorGameContext],
    *,
    raw_off_epa: float,
    raw_def_epa_allowed: float,
    weekly_book: Mapping[Tuple[str, int], OpponentRating],
    season_book: Mapping[str, OpponentRating],
    league_off_epa: float,
    league_def_epa: float,
) -> TeamPastSos:
    """Build Actual SOS + schedule-adjusted performance for one prior team."""
    t = normalize_team(team)
    team_games = [g for g in games if normalize_team(g.team) == t]
    if not team_games:
        return TeamPastSos(
            team=t,
            games=0,
            actual_sos_offense=float(league_def_epa),
            actual_sos_defense=float(league_off_epa),
            raw_off_epa=float(raw_off_epa),
            raw_def_epa_allowed=float(raw_def_epa_allowed),
            schedule_adj_off_epa=float(raw_off_epa),
            schedule_adj_def_epa_allowed=float(raw_def_epa_allowed),
            status="thin_unavailable",
            notes={"reason": "no_prior_games"},
        )

    league_fb = OpponentRating(
        off_epa=float(league_off_epa),
        def_epa=float(league_def_epa),
        source="approximate",
    )
    opp_defs: List[float] = []
    opp_offs: List[float] = []
    tog = 0
    approx = 0
    venue = False
    rest = False
    for g in team_games:
        rating = resolve_opponent_rating(
            g.opponent,
            game_week=int(g.week),
            weekly_book=weekly_book,
            season_book=season_book,
            league_fallback=league_fb,
        )
        if rating.source == "time_of_game":
            tog += 1
        else:
            approx += 1
        eff_def, eff_off, meta = effective_opponent_units(
            rating,
            is_home=bool(g.is_home),
            team_rest_days=g.team_rest_days,
            opp_rest_days=g.opp_rest_days,
        )
        opp_defs.append(float(eff_def))
        opp_offs.append(float(eff_off))
        venue = venue or bool(meta.get("venue_hfa"))
        rest = rest or bool(meta.get("rest"))

    mean_opp_def = sum(opp_defs) / len(opp_defs)
    mean_opp_off = sum(opp_offs) / len(opp_offs)
    dampen = float(_SOS_DAMPEN)
    adj_off = float(raw_off_epa) + dampen * (float(league_def_epa) - mean_opp_def)
    adj_def = float(raw_def_epa_allowed) + dampen * (
        float(league_off_epa) - mean_opp_off
    )

    if tog > 0 and approx == 0:
        status = "applied_time_of_game"
    elif tog > 0 and approx > 0:
        status = "mixed"
    elif approx > 0:
        status = "applied_approximate"
    else:
        status = "thin_unavailable"

    return TeamPastSos(
        team=t,
        games=len(team_games),
        actual_sos_offense=round(mean_opp_def, 6),
        actual_sos_defense=round(mean_opp_off, 6),
        raw_off_epa=round(float(raw_off_epa), 6),
        raw_def_epa_allowed=round(float(raw_def_epa_allowed), 6),
        schedule_adj_off_epa=round(adj_off, 6),
        schedule_adj_def_epa_allowed=round(adj_def, 6),
        time_of_game_games=tog,
        approximate_games=approx,
        status=status,
        venue_applied=venue,
        rest_applied=rest,
        notes={
            "league_off_epa": round(float(league_off_epa), 6),
            "league_def_epa": round(float(league_def_epa), 6),
            "sos_dampen": dampen,
            "primary_metric": "opponent_efficiency_power",
            "not_opponent_win_pct": True,
        },
    )


def compute_league_past_sos(
    games: Sequence[PriorGameContext],
    *,
    raw_by_team: Mapping[str, Mapping[str, float]],
    weekly_book: Mapping[Tuple[str, int], OpponentRating],
    season_book: Mapping[str, OpponentRating],
) -> Dict[str, TeamPastSos]:
    """Compute Past SOS for every team present in ``raw_by_team``."""
    off_vals = [
        float(v.get("off_epa_per_play", v.get("raw_off_epa", 0.0)) or 0.0)
        for v in raw_by_team.values()
    ]
    def_vals = [
        float(
            v.get("def_epa_allowed_per_play", v.get("raw_def_epa_allowed", 0.0)) or 0.0
        )
        for v in raw_by_team.values()
    ]
    league_off = sum(off_vals) / max(1, len(off_vals))
    league_def = sum(def_vals) / max(1, len(def_vals))
    out: Dict[str, TeamPastSos] = {}
    for team, raw in raw_by_team.items():
        t = normalize_team(team)
        out[t] = compute_team_past_sos(
            t,
            games,
            raw_off_epa=float(raw.get("off_epa_per_play", raw.get("raw_off_epa", 0.0)) or 0.0),
            raw_def_epa_allowed=float(
                raw.get(
                    "def_epa_allowed_per_play",
                    raw.get("raw_def_epa_allowed", 0.0),
                )
                or 0.0
            ),
            weekly_book=weekly_book,
            season_book=season_book,
            league_off_epa=league_off,
            league_def_epa=league_def,
        )
    return out


def _shift_unit(unit: UnitEfficiency, delta: float) -> UnitEfficiency:
    """Shift EPA fields by ``delta``; rates unchanged (honest, no invented rates)."""
    d = float(delta)
    return UnitEfficiency(
        epa_per_play=float(unit.epa_per_play) + d,
        success_rate=unit.success_rate,
        explosive_rate=unit.explosive_rate,
        negative_rate=unit.negative_rate,
        pass_epa=float(unit.pass_epa) + d,
        run_epa=float(unit.run_epa) + d,
        early_down_epa=float(unit.early_down_epa) + d,
        late_down_conversion_rate=unit.late_down_conversion_rate,
        red_zone_td_rate=unit.red_zone_td_rate,
        pressure_rate=unit.pressure_rate,
        plays=unit.plays,
        pass_plays=unit.pass_plays,
        run_plays=unit.run_plays,
        early_down_plays=unit.early_down_plays,
    )


def apply_past_sos_to_package(
    pkg: TeamEfficiencyPackage,
    sos: TeamPastSos,
) -> TeamEfficiencyPackage:
    """Return a prior package with schedule-adjusted EPA (prior side only)."""
    if sos.games <= 0 or sos.status == "thin_unavailable":
        notes = dict(pkg.notes or {})
        notes["past_sos"] = sos.drivers()
        return replace(pkg, notes=notes)

    off_delta = float(sos.schedule_adj_off_epa) - float(sos.raw_off_epa)
    def_delta = float(sos.schedule_adj_def_epa_allowed) - float(sos.raw_def_epa_allowed)
    # Prefer shifting from package raw notes when present (pre-centering).
    raw_off = float(pkg.notes.get("off_epa_raw", pkg.offense.epa_per_play))
    raw_def = float(pkg.notes.get("def_epa_raw", pkg.defense.epa_per_play))
    # If package EPA already equals sos.raw, use sos deltas; else re-base to sos adj.
    if abs(raw_off - float(sos.raw_off_epa)) < 1e-9:
        new_off = _shift_unit(pkg.offense, off_delta)
    else:
        # Align to schedule-adjusted absolute level from sos.
        new_off = _shift_unit(
            pkg.offense, float(sos.schedule_adj_off_epa) - float(pkg.offense.epa_per_play)
        )
    if abs(raw_def - float(sos.raw_def_epa_allowed)) < 1e-9:
        new_def = _shift_unit(pkg.defense, def_delta)
    else:
        new_def = _shift_unit(
            pkg.defense,
            float(sos.schedule_adj_def_epa_allowed) - float(pkg.defense.epa_per_play),
        )

    notes = dict(pkg.notes or {})
    notes["past_sos"] = sos.drivers()
    notes["off_epa_raw"] = round(float(sos.raw_off_epa), 6)
    notes["def_epa_raw"] = round(float(sos.raw_def_epa_allowed), 6)
    notes["off_epa_schedule_adj"] = round(float(sos.schedule_adj_off_epa), 6)
    notes["def_epa_schedule_adj"] = round(float(sos.schedule_adj_def_epa_allowed), 6)
    notes["past_sos_applied"] = True

    adj = TeamEfficiencyPackage(
        team=pkg.team,
        offense=new_off,
        defense=new_def,
        st_index=pkg.st_index,
        st_epa_per_play=pkg.st_epa_per_play,
        st_plays=pkg.st_plays,
        pace=pkg.pace,
        pass_rate=pkg.pass_rate,
        explosiveness=pkg.explosiveness,
        variance=pkg.variance,
        qb_premium=0.0,
        games_played=pkg.games_played,
        as_of=pkg.as_of,
        version=pkg.version,
        source=pkg.source,
        prior_season=pkg.prior_season,
        notes=notes,
    )
    # Refresh packaged index notes when present so cold-start hierarchy moves with SOS.
    idx = package_to_strength_indices(adj)
    if "packaged_offense_index" in notes:
        adj.notes["packaged_offense_index"] = float(idx["offense_index"])
        adj.notes["packaged_defense_index"] = float(idx["defense_index"])
    return adj


def season_book_from_packages(
    packages: Mapping[str, TeamEfficiencyPackage],
) -> Dict[str, OpponentRating]:
    """Approximate season opponent book from prior packages (fallback)."""
    out: Dict[str, OpponentRating] = {}
    for team, pkg in packages.items():
        t = normalize_team(team)
        out[t] = OpponentRating(
            off_epa=float(pkg.offense.epa_per_play),
            def_epa=float(pkg.defense.epa_per_play),
            source="approximate",
        )
    return out


def season_book_from_raw(
    raw_by_team: Mapping[str, Mapping[str, float]],
) -> Dict[str, OpponentRating]:
    out: Dict[str, OpponentRating] = {}
    for team, raw in raw_by_team.items():
        t = normalize_team(team)
        out[t] = OpponentRating(
            off_epa=float(raw.get("off_epa_per_play", raw.get("raw_off_epa", 0.0)) or 0.0),
            def_epa=float(
                raw.get(
                    "def_epa_allowed_per_play",
                    raw.get("raw_def_epa_allowed", 0.0),
                )
                or 0.0
            ),
            source="approximate",
        )
    return out


def attach_past_sos_drivers(
    drivers: Dict[str, Any],
    sos: Optional[TeamPastSos],
) -> Dict[str, Any]:
    """Merge Past SOS into true-PR drivers; label remaining stubs honestly."""
    out = dict(drivers or {})
    stubs = dict(out.get("stubs") or {})
    stubs.setdefault("qb_premium", "stub_not_applied")
    stubs.setdefault("continuity", "stub_not_applied")
    stubs["injury_at_time_depth"] = "stub_not_applied"
    if sos is None or sos.games <= 0:
        stubs["full_venue_model"] = "stub_not_applied"
        stubs["true_time_of_game_sos"] = "thin_unavailable"
        out["stubs"] = stubs
        out["past_sos"] = {
            "status": "thin_unavailable",
            "future_schedule_excluded": True,
        }
        return out

    sos_drivers = sos.drivers()
    stubs["full_venue_model"] = sos_drivers.get("full_venue_model", "stub_not_applied")
    stubs["true_time_of_game_sos"] = str(sos.status)
    out["stubs"] = stubs
    out["past_sos"] = sos_drivers
    return out


def rest_days_from_dates(
    team_dates: Mapping[str, Sequence[Any]],
) -> Dict[Tuple[str, Any], int]:
    """Map (team, game_date) → rest days since previous game for that team."""
    out: Dict[Tuple[str, Any], int] = {}
    for team, dates in team_dates.items():
        ordered = sorted([d for d in dates if d is not None])
        prev = None
        for d in ordered:
            if prev is not None:
                try:
                    out[(normalize_team(team), d)] = int((d - prev).days)
                except Exception:
                    pass
            prev = d
    return out


def expand_schedule_games(
    schedule_rows: Iterable[Mapping[str, Any]],
    *,
    rest_lookup: Optional[Mapping[Tuple[str, Any], int]] = None,
) -> List[PriorGameContext]:
    """Expand home/away schedule rows into per-team prior game contexts."""
    games: List[PriorGameContext] = []
    rest_lookup = rest_lookup or {}
    for row in schedule_rows:
        week = int(row.get("week") or 0)
        if week < 1 or week > 18:
            continue
        home = normalize_team(str(row.get("home_team") or ""))
        away = normalize_team(str(row.get("away_team") or ""))
        if not home or not away:
            continue
        game_id = str(row.get("game_id") or "")
        gdate = row.get("game_date")
        home_rest = rest_lookup.get((home, gdate)) if gdate is not None else None
        away_rest = rest_lookup.get((away, gdate)) if gdate is not None else None
        games.append(
            PriorGameContext(
                team=home,
                week=week,
                opponent=away,
                is_home=True,
                team_rest_days=home_rest,
                opp_rest_days=away_rest,
                game_id=game_id,
            )
        )
        games.append(
            PriorGameContext(
                team=away,
                week=week,
                opponent=home,
                is_home=False,
                team_rest_days=away_rest,
                opp_rest_days=home_rest,
                game_id=game_id,
            )
        )
    return games
