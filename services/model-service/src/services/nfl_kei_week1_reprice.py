"""Week 1 REG KEI reprice — desk factors on top of frozen Model.

Doctrine
--------
- Model = research fair (stable). This module never mutates Model markets.
- KEI = Model + Gate B adjustments (injury / QB confirmation / rest-travel).
- Edge / Tag = KEI vs market only.
- Identity fallback when Model/spread is missing.
- Week 1 REG 2026 only. Other weeks/slates pass through unchanged.

SoT
---
QB1 / injury names come from the packaged depth chart (#220), not a second map.
OL injuries live in pack ``ol_roles``; defense in ``defense_roles``;
skill injuries on pack rows.

Honesty
-------
- Weather: indoor → not applied; outdoor uses a real forecast (Open-Meteo / desk
  obs) when in horizon. Never climatology. Never invent stadium weather.
- Refs: apply only from a Week 1 crew pack. Empty pack → "ref not applied".
- Open QB competition: wider uncertainty / lower confidence — not a fake spread lock.
- Do not restack a factor already inside the frozen model snapshot.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

from src.services.nfl_injury_kei_cadence import DEFAULT_IMPACT_POINTS
from src.services.nfl_unit_shock_table import (
    collect_shock_table_v1,
    row_covered_by_shock_table,
)

# ---------------------------------------------------------------------------
# Caps / scope
# ---------------------------------------------------------------------------

SCOPE_SEASON = 2026
SCOPE_WEEK = 1
SPREAD_CAP = 4.0
TOTAL_CAP = 2.0
TEAM_INJURY_SPREAD_CAP = 1.5
WEATHER_TOTAL_CAP = 1.5
REF_TOTAL_CAP = 0.5
# Wind/cold/precip bands — totals first; weather does not move the spread.
WIND_BAND_MPH = 20.0
WIND_EXTREME_MPH = 25.0
COLD_BAND_F = 20.0
PRECIP_BAND_MM = 2.0

# Timezone hours west of ET. Cross-country = |delta| >= 3.
_PACIFIC = frozenset({"SEA", "SF", "LA", "LAR", "LAC", "ARI", "LV"})
_MOUNTAIN = frozenset({"DEN"})
_CENTRAL = frozenset({"CHI", "DAL", "HOU", "MIN", "GB", "TEN", "NO", "KC"})
# Remaining 32-team set is Eastern.

# Indoor / dome / typically-closed retractable. SoFi (LA/LAC) is outdoor.
INDOOR_TEAMS = frozenset(
    {"ATL", "DET", "NO", "MIN", "DAL", "HOU", "ARI", "LV", "IND"}
)

OUT_STATUSES = frozenset({"out", "ir", "pup", "suspended", "inactive"})
UNRESOLVED_STATUSES = frozenset({"limited", "questionable", "doubtful"})
SKILL_POSITIONS = frozenset({"RB", "WR", "TE", "HB", "FB"})
QB_POSITIONS = frozenset({"QB"})
DEFENSE_POSITIONS = frozenset({"EDGE", "DL", "LB", "CB", "S", "NB", "DE", "DT", "DB", "NT"})

TZ_EASTERN = ZoneInfo("America/New_York")


def _norm_team(abbr: Any) -> str:
    token = str(abbr or "").strip().upper()
    if token in {"LAR", "LA"}:
        return "LA"
    if token == "AZ":
        return "ARI"
    return token


def _tz_hours_west_of_et(team: str) -> int:
    code = _norm_team(team)
    if code in _PACIFIC:
        return 3
    if code in _MOUNTAIN:
        return 2
    if code in _CENTRAL:
        return 1
    return 0


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def _clamp(value: float, cap: float) -> Tuple[float, bool]:
    if value > cap:
        return cap, True
    if value < -cap:
        return -cap, True
    return value, False


def _status(raw: Any) -> str:
    return str(raw or "").strip().lower()


# ---------------------------------------------------------------------------
# Pack (single SoT)
# ---------------------------------------------------------------------------


@dataclass
class Week1Pack:
    """Skill rows + OL + defense roles from the #220 depth pack."""

    skill_by_team: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    ol_by_team: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    defense_by_team: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    snapshot_id: str = ""
    as_of: str = ""
    loaded: bool = False

    @classmethod
    def empty(cls) -> "Week1Pack":
        return cls()

    def skill(self, team: str) -> List[Dict[str, Any]]:
        return list(self.skill_by_team.get(_norm_team(team), []))

    def ol(self, team: str) -> List[Dict[str, Any]]:
        return list(self.ol_by_team.get(_norm_team(team), []))

    def defense(self, team: str) -> List[Dict[str, Any]]:
        return list(self.defense_by_team.get(_norm_team(team), []))

    def qb_rows(self, team: str) -> List[Dict[str, Any]]:
        rows = [r for r in self.skill(team) if str(r.get("position") or "").upper() == "QB"]
        rows.sort(key=lambda r: int(r.get("depth_order") or 99))
        return rows

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Week1Pack":
        """Index a raw depth-pack JSON (same SoT file, no second map)."""
        skill: Dict[str, List[Dict[str, Any]]] = {}
        for raw in payload.get("rows") or []:
            if not isinstance(raw, Mapping):
                continue
            team = _norm_team(raw.get("team"))
            if not team:
                continue
            skill.setdefault(team, []).append(dict(raw))
        ol: Dict[str, List[Dict[str, Any]]] = {}
        for raw in payload.get("ol_roles") or []:
            if not isinstance(raw, Mapping):
                continue
            team = _norm_team(raw.get("team"))
            if not team:
                continue
            ol.setdefault(team, []).append(dict(raw))
        defense: Dict[str, List[Dict[str, Any]]] = {}
        for raw in payload.get("defense_roles") or []:
            if not isinstance(raw, Mapping):
                continue
            team = _norm_team(raw.get("team"))
            if not team:
                continue
            defense.setdefault(team, []).append(dict(raw))
        return cls(
            skill_by_team=skill,
            ol_by_team=ol,
            defense_by_team=defense,
            snapshot_id=str(payload.get("snapshot_id") or ""),
            as_of=str(payload.get("as_of") or payload.get("as_of_timestamp") or ""),
            loaded=bool(skill),
        )


@lru_cache(maxsize=4)
def load_week1_pack(season: int = SCOPE_SEASON) -> Week1Pack:
    """Load packaged depth once per process. Missing pack → empty (honest skip)."""
    try:
        from src.services.nfl_season_engine.loaders import load_packaged_depth_chart

        rows, meta = load_packaged_depth_chart(int(season))
    except Exception:
        return Week1Pack.empty()

    skill: Dict[str, List[Dict[str, Any]]] = {}
    for raw in rows or []:
        if not isinstance(raw, Mapping):
            continue
        team = _norm_team(raw.get("team"))
        if not team:
            continue
        skill.setdefault(team, []).append(dict(raw))

    ol: Dict[str, List[Dict[str, Any]]] = {}
    for raw in meta.get("ol_roles") or []:
        if not isinstance(raw, Mapping):
            continue
        team = _norm_team(raw.get("team"))
        if not team:
            continue
        ol.setdefault(team, []).append(dict(raw))

    defense: Dict[str, List[Dict[str, Any]]] = {}
    for raw in meta.get("defense_roles") or []:
        if not isinstance(raw, Mapping):
            continue
        team = _norm_team(raw.get("team"))
        if not team:
            continue
        defense.setdefault(team, []).append(dict(raw))

    return Week1Pack(
        skill_by_team=skill,
        ol_by_team=ol,
        defense_by_team=defense,
        snapshot_id=str(meta.get("snapshot_id") or ""),
        as_of=str(meta.get("roster_as_of") or meta.get("as_of") or ""),
        loaded=True,
    )


# ---------------------------------------------------------------------------
# Factor log
# ---------------------------------------------------------------------------


@dataclass
class FactorEntry:
    factor: str
    applied: bool
    team: Optional[str]
    direction: str
    spread_pts: float
    total_pts: float
    confidence_delta: float
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _entry(
    *,
    factor: str,
    applied: bool,
    reason: str,
    team: Optional[str] = None,
    direction: str = "none",
    spread_pts: float = 0.0,
    total_pts: float = 0.0,
    confidence_delta: float = 0.0,
) -> FactorEntry:
    return FactorEntry(
        factor=factor,
        applied=applied,
        team=team,
        direction=direction,
        spread_pts=round(float(spread_pts), 4),
        total_pts=round(float(total_pts), 4),
        confidence_delta=round(float(confidence_delta), 4),
        reason=reason,
    )


def _home_signed(team: str, home: str, away: str, team_spread: float) -> Tuple[float, str]:
    """Convert 'this team is weaker by team_spread' into home-spread convention.

    Home weaker → positive home spread. Away weaker → negative home spread.
    """
    code = _norm_team(team)
    if code == _norm_team(home):
        return float(team_spread), "home_weaker" if team_spread > 0 else (
            "home_stronger" if team_spread < 0 else "none"
        )
    if code == _norm_team(away):
        return -float(team_spread), "away_weaker" if team_spread > 0 else (
            "away_stronger" if team_spread < 0 else "none"
        )
    return 0.0, "none"


# ---------------------------------------------------------------------------
# Double-count guards (frozen model snapshot)
# ---------------------------------------------------------------------------


def _projection_dict(projection: Any) -> Dict[str, Any]:
    if isinstance(projection, str):
        try:
            import json

            projection = json.loads(projection)
        except Exception:
            return {}
    return projection if isinstance(projection, dict) else {}


def _factor_contrib(projection: Any, key: str) -> Dict[str, Any]:
    proj = _projection_dict(projection)
    decomp = proj.get("decomposition")
    if not isinstance(decomp, dict):
        decomp = proj.get("diagnostics") if isinstance(proj.get("diagnostics"), dict) else {}
    contribs = decomp.get("factor_contributions") if isinstance(decomp, dict) else None
    if not isinstance(contribs, dict):
        diag = proj.get("diagnostics")
        if isinstance(diag, dict):
            contribs = diag.get("factor_contributions")
    if not isinstance(contribs, dict):
        return {}
    row = contribs.get(key)
    return row if isinstance(row, dict) else {}


def model_already_has_injury(projection: Any) -> bool:
    """True when the frozen snapshot already stacked injury into the published line."""
    proj = _projection_dict(projection)
    diag = proj.get("diagnostics")
    if isinstance(diag, dict) and diag.get("injury_kei_reprice"):
        return True
    inj = _factor_contrib(proj, "injuries_depth")
    margin = abs(_to_float(inj.get("margin_points")) or 0.0)
    total = abs(_to_float(inj.get("total_points")) or 0.0)
    return margin > 0.05 or total > 0.05


def model_already_has_travel(projection: Any) -> bool:
    for key in ("travel_schedule", "rest_travel"):
        row = _factor_contrib(projection, key)
        if abs(_to_float(row.get("margin_points")) or 0.0) > 0.05:
            return True
        if abs(_to_float(row.get("total_points")) or 0.0) > 0.05:
            return True
    return False


def model_already_has_weather(projection: Any) -> bool:
    proj = _projection_dict(projection)
    diag = proj.get("diagnostics")
    if isinstance(diag, dict):
        weather = diag.get("weather")
        if isinstance(weather, dict) and weather.get("available"):
            return True
    row = _factor_contrib(proj, "weather_environment")
    if row.get("available") is True:
        return True
    return abs(_to_float(row.get("total_points")) or 0.0) > 0.05 or abs(
        _to_float(row.get("margin_points")) or 0.0
    ) > 0.05


# ---------------------------------------------------------------------------
# Factors
# ---------------------------------------------------------------------------


def _qb_factor(team: str, pack: Week1Pack) -> Tuple[List[FactorEntry], bool]:
    """QB confirmation. Open competition → confidence only, not a spread lock."""
    rows = pack.qb_rows(team)
    if not rows:
        return [
            _entry(
                factor="qb_confirmation",
                applied=False,
                team=team,
                reason="QB SoT missing for team — not applied",
            )
        ], True

    qb1 = rows[0]
    name = str(qb1.get("player_name") or "QB1")
    status = str(qb1.get("competition_status") or qb1.get("depth_slot") or "").strip().lower()
    names = ", ".join(
        str(r.get("player_name") or "") for r in rows[:2] if r.get("player_name")
    )
    inj = _status(qb1.get("injury_status"))

    if inj in OUT_STATUSES:
        pts = float(DEFAULT_IMPACT_POINTS["qb1_out_spread"])
        tot = float(DEFAULT_IMPACT_POINTS["qb1_out_total"])
        # Team-weaker magnitude; apply_week1_kei_reprice signs into home-spread.
        return [
            _entry(
                factor="qb_backup_dropoff",
                applied=True,
                team=team,
                direction="team_weaker",
                spread_pts=pts,
                total_pts=tot,
                confidence_delta=-0.08,
                reason=f"QB1 {name} {inj} — backup drop-off",
            )
        ], False

    if status == "open_competition":
        return [
            _entry(
                factor="qb_confirmation",
                applied=True,
                team=team,
                direction="none",
                spread_pts=0.0,
                total_pts=0.0,
                confidence_delta=-0.12,
                reason=f"open_competition {names} — no crown; wider uncertainty",
            )
        ], False

    return [
        _entry(
            factor="qb_confirmation",
            applied=True,
            team=team,
            direction="none",
            spread_pts=0.0,
            total_pts=0.0,
            reason=f"QB1 confirmed {name} ({status or 'named_starter'})",
        )
    ], True


def _injury_factors(team: str, pack: Week1Pack) -> Tuple[List[FactorEntry], bool]:
    """Known key injuries from SoT. No invented IR. TE3/depth skips.

    Keystone outs (C / LT / EDGE1 / CB1 / S1) use ``shock_table_v1`` once —
    never stacked with a full unit wipe for the same event.
    """
    applied: List[FactorEntry] = []
    considered: List[FactorEntry] = []
    injury_clear = True
    team_spread = 0.0
    team_total = 0.0

    shocks = collect_shock_table_v1(
        team=team,
        ol_rows=pack.ol(team),
        defense_rows=pack.defense(team),
    )
    for shock in shocks.role_shocks:
        team_spread += shock.spread_pts
        team_total += shock.total_pts
        factor = "injury_ol" if shock.unit == "ol" else "injury_defense"
        applied.append(
            _entry(
                factor=factor,
                applied=True,
                team=team,
                direction="team_weaker",
                spread_pts=shock.spread_pts,
                total_pts=shock.total_pts,
                reason=shock.reason(),
            )
        )
    for skip in shocks.unit_wipe_skips:
        considered.append(
            _entry(
                factor="unit_wipe",
                applied=False,
                team=team,
                direction="none",
                spread_pts=0.0,
                total_pts=0.0,
                reason=skip.reason(),
            )
        )

    for row in pack.ol(team):
        if row_covered_by_shock_table(row, shocks):
            continue  # shock_table_v1 already applied — no flat ol_out double-count
        inj = _status(row.get("injury_status"))
        slot = str(row.get("depth_slot") or "").strip().lower()
        order = int(row.get("depth_order") or 0)
        name = str(row.get("player_name") or "OL")
        pos = str(row.get("position") or "OL")
        is_out_slot = slot == "out" or order >= 90
        is_starter = order == 1 or slot in {"starter", "starter_competition"}
        if inj in OUT_STATUSES or is_out_slot:
            pts = float(DEFAULT_IMPACT_POINTS["ol_out_spread"])
            tot = float(DEFAULT_IMPACT_POINTS["ol_out_total"])
            team_spread += pts
            team_total += tot
            if "unknown" in str(row.get("injury_window") or "").lower() or not is_out_slot:
                # Allegretti-class: listed out but W1 window not invented.
                if "unknown" in str(row.get("injury_window") or "").lower():
                    injury_clear = False
            applied.append(
                _entry(
                    factor="injury_ol",
                    applied=True,
                    team=team,
                    direction="team_weaker",
                    spread_pts=pts,
                    total_pts=tot,
                    confidence_delta=-0.04 if not injury_clear else 0.0,
                    reason=f"{name} {pos} {inj or slot} (SoT ol_roles)",
                )
            )
        elif inj in UNRESOLVED_STATUSES and is_starter:
            injury_clear = False
            pts = 0.25
            tot = 0.10
            team_spread += pts
            team_total += tot
            applied.append(
                _entry(
                    factor="injury_ol",
                    applied=True,
                    team=team,
                    direction="team_weaker",
                    spread_pts=pts,
                    total_pts=tot,
                    confidence_delta=-0.06,
                    reason=f"{name} {pos} {inj} starter — unresolved",
                )
            )

    for row in pack.defense(team):
        if row_covered_by_shock_table(row, shocks):
            continue  # shock_table_v1 already applied — no flat defense_out double-count
        pos = str(row.get("position") or "").upper() or "DEF"
        if pos not in DEFENSE_POSITIONS and pos != "DEF":
            continue
        inj = _status(row.get("injury_status"))
        slot = str(row.get("depth_slot") or "").strip().lower()
        order = int(row.get("depth_order") or 0)
        name = str(row.get("player_name") or pos)
        is_out_slot = slot == "out" or order >= 90
        is_starter = order == 1 or slot in {"starter", "starter_competition"}
        if inj in OUT_STATUSES or is_out_slot:
            if not is_starter and not is_out_slot and order >= 3:
                considered.append(
                    _entry(
                        factor="injury_defense",
                        applied=False,
                        team=team,
                        reason=f"{name} {pos}{order} {inj} — not a key role, not applied",
                    )
                )
                continue
            pts = float(DEFAULT_IMPACT_POINTS["defense_out_spread"])
            tot = float(DEFAULT_IMPACT_POINTS["defense_out_total"])
            if is_starter or is_out_slot or order <= 1:
                pass  # full starter impact
            elif order == 2:
                pts = 0.35
                tot = 0.10
            else:
                considered.append(
                    _entry(
                        factor="injury_defense",
                        applied=False,
                        team=team,
                        reason=f"{name} {pos}{order} {inj} — not a key role, not applied",
                    )
                )
                continue
            team_spread += pts
            team_total += tot
            applied.append(
                _entry(
                    factor="injury_defense",
                    applied=True,
                    team=team,
                    direction="team_weaker",
                    spread_pts=pts,
                    total_pts=tot,
                    reason=f"{name} {pos}{order or 1} {inj or slot} (SoT defense_roles)",
                )
            )
        elif inj in UNRESOLVED_STATUSES and is_starter:
            injury_clear = False
            pts = 0.25
            tot = 0.10
            team_spread += pts
            team_total += tot
            applied.append(
                _entry(
                    factor="injury_defense",
                    applied=True,
                    team=team,
                    direction="team_weaker",
                    spread_pts=pts,
                    total_pts=tot,
                    confidence_delta=-0.05,
                    reason=f"{name} {pos} {inj} starter — unresolved",
                )
            )

    for row in pack.skill(team):
        pos = str(row.get("position") or "").upper()
        if pos in QB_POSITIONS:
            continue  # QB handled in _qb_factor
        if pos not in SKILL_POSITIONS:
            continue
        inj = _status(row.get("injury_status"))
        order = int(row.get("depth_order") or 99)
        name = str(row.get("player_name") or pos)
        if inj not in OUT_STATUSES | UNRESOLVED_STATUSES:
            continue
        if order >= 3:
            considered.append(
                _entry(
                    factor="injury_skill",
                    applied=False,
                    team=team,
                    reason=f"{name} {pos}{order} {inj} — not a key role, not applied",
                )
            )
            continue
        if inj in OUT_STATUSES:
            if order == 1:
                pts = float(DEFAULT_IMPACT_POINTS["skill_out_spread"])
                tot = float(DEFAULT_IMPACT_POINTS["skill_out_total"])
            else:
                pts = 0.40
                tot = 0.20
            team_spread += pts
            team_total += tot
            applied.append(
                _entry(
                    factor="injury_skill",
                    applied=True,
                    team=team,
                    direction="team_weaker",
                    spread_pts=pts,
                    total_pts=tot,
                    reason=f"{name} {pos}{order} {inj} (SoT)",
                )
            )
        else:
            injury_clear = False
            if order == 1:
                pts, tot = 0.25, 0.10
                team_spread += pts
                team_total += tot
                applied.append(
                    _entry(
                        factor="injury_skill",
                        applied=True,
                        team=team,
                        direction="team_weaker",
                        spread_pts=pts,
                        total_pts=tot,
                        confidence_delta=-0.05,
                        reason=f"{name} {pos}1 {inj} — unresolved",
                    )
                )
            else:
                considered.append(
                    _entry(
                        factor="injury_skill",
                        applied=False,
                        team=team,
                        reason=f"{name} {pos}{order} {inj} — not a starter, not applied",
                    )
                )

    if team_spread > TEAM_INJURY_SPREAD_CAP:
        scale = TEAM_INJURY_SPREAD_CAP / team_spread
        team_spread = TEAM_INJURY_SPREAD_CAP
        team_total *= scale
        applied.append(
            _entry(
                factor="injury_cap",
                applied=True,
                team=team,
                direction="team_weaker",
                spread_pts=0.0,
                total_pts=0.0,
                reason=f"team injury spread capped at {TEAM_INJURY_SPREAD_CAP}",
            )
        )

    # Attach net on a summary only when something applied; individual rows keep unit pts.
    if not applied and not considered:
        considered.append(
            _entry(
                factor="injury",
                applied=False,
                team=team,
                reason="no key SoT injury flags",
            )
        )

    # Stash net on first applied row via a synthetic net marker for the assembler.
    net_marker: List[FactorEntry] = []
    if applied:
        net_marker.append(
            _entry(
                factor="injury_net",
                applied=True,
                team=team,
                direction="team_weaker",
                spread_pts=round(team_spread, 4),
                total_pts=round(team_total, 4),
                reason=f"{team} injury net (key SoT only)",
            )
        )
    return applied + considered + net_marker, injury_clear


def _rest_travel_factors(
    *,
    home: str,
    away: str,
    start_time: Any,
    skip_travel_points: bool,
) -> List[FactorEntry]:
    out: List[FactorEntry] = []
    out.append(
        _entry(
            factor="short_week",
            applied=False,
            reason="short_week not applied (Week 1, no prior REG rest gap)",
        )
    )

    weekday = _kickoff_weekday_et(start_time)
    if weekday == 3:  # Thursday
        out.append(
            _entry(
                factor="thu_night",
                applied=False,
                reason="Thu on slate; W1 opener is not a short week from prior REG — not applied",
            )
        )
    elif weekday == 0:  # Monday
        out.append(
            _entry(
                factor="mon_night",
                applied=False,
                reason="Mon on slate; W1 MNF is not a short-week rest tax — not applied",
            )
        )

    home_tz = _tz_hours_west_of_et(home)
    away_tz = _tz_hours_west_of_et(away)
    delta = abs(home_tz - away_tz)
    if skip_travel_points:
        out.append(
            _entry(
                factor="travel",
                applied=False,
                team=away,
                reason="travel already in frozen model snapshot — not restacked",
            )
        )
        return out

    if delta >= 3:
        pts, tot = 1.00, -0.50
    elif delta >= 2:
        pts, tot = 0.75, -0.30
    elif delta >= 1:
        pts, tot = 0.35, -0.15
    else:
        out.append(
            _entry(
                factor="travel",
                applied=False,
                reason=f"same-coast ({_norm_team(away)} → {_norm_team(home)}) — travel not applied",
            )
        )
        return out

    signed, direction = _home_signed(away, home, away, pts)
    out.append(
        _entry(
            factor="travel",
            applied=True,
            team=away,
            direction=direction,
            spread_pts=signed,
            total_pts=tot,
            reason=(
                f"{_norm_team(away)} travels {delta} TZ band(s) to {_norm_team(home)} "
                f"— visitor weaker"
            ),
        )
    )
    return out


def _kickoff_weekday_et(start_time: Any) -> Optional[int]:
    if start_time is None:
        return None
    dt: Optional[datetime] = None
    if isinstance(start_time, datetime):
        dt = start_time
    elif isinstance(start_time, str):
        raw = start_time.strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_EASTERN).weekday()


def _geo_team(home: str) -> str:
    code = _norm_team(home)
    return "LAR" if code in {"LA", "LAR"} else code


def _weather_total_from_obs(obs: Mapping[str, Any]) -> Tuple[float, List[str]]:
    """Totals-first bands. Never invent values — missing readings are skipped."""
    notes: List[str] = []
    total = 0.0
    wind = _to_float(obs.get("wind_mph"))
    temp = _to_float(obs.get("temp_f"))
    precip = _to_float(obs.get("precip_mm"))
    if wind is not None:
        if wind >= WIND_EXTREME_MPH:
            total -= 1.5
            notes.append(f"wind {wind:.0f} mph")
        elif wind >= WIND_BAND_MPH:
            total -= 1.0
            notes.append(f"wind {wind:.0f} mph")
    if temp is not None and temp <= COLD_BAND_F:
        total -= 0.5
        notes.append(f"temp {temp:.0f}F")
    if precip is not None and precip >= PRECIP_BAND_MM:
        total -= 0.5
        notes.append(f"precip {precip:.1f} mm")
    clamped, _ = _clamp(total, WEATHER_TOTAL_CAP)
    return round(clamped, 4), notes


def _fetch_real_forecast(*, home: str, start_time: Any) -> Optional[Dict[str, Any]]:
    """Open-Meteo / VC only. Never climatology. Swallows network errors."""
    if start_time is None:
        return None
    if isinstance(start_time, datetime):
        kickoff = start_time
    elif isinstance(start_time, str) and start_time.strip():
        try:
            kickoff = datetime.fromisoformat(start_time.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    try:
        from src.services.nfl_environment import TEAM_HOME_GEO, fetch_game_weather_context
    except Exception:
        return None
    geo = TEAM_HOME_GEO.get(_geo_team(home))
    if not geo:
        return None
    try:
        payload = fetch_game_weather_context(
            game_time_iso=kickoff.isoformat(),
            lat=float(geo["lat"]),
            lon=float(geo["lon"]),
        )
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    if "climatology" in str(payload.get("source") or ""):
        return None
    return payload


def _weather_factors(
    *,
    home: str,
    projection: Any,
    start_time: Any = None,
    weather_obs: Optional[Mapping[str, Any]] = None,
) -> Tuple[List[FactorEntry], bool]:
    """Indoor / restack / real forecast. Never fabricate stadium weather."""
    home_n = _norm_team(home)
    if home_n in INDOOR_TEAMS:
        return [
            _entry(
                factor="weather",
                applied=False,
                team=home_n,
                reason="weather not applied (indoor)",
            )
        ], True
    if model_already_has_weather(projection):
        return [
            _entry(
                factor="weather",
                applied=False,
                team=home_n,
                reason="weather already in frozen model snapshot — not restacked",
            )
        ], True

    obs: Optional[Mapping[str, Any]] = weather_obs
    if obs is None:
        obs = _fetch_real_forecast(home=home_n, start_time=start_time)

    if not obs:
        reason = (
            "weather not applied (no kickoff for forecast)"
            if start_time is None
            else "weather not applied (no forecast on this read path)"
        )
        return [
            _entry(factor="weather", applied=False, team=home_n, reason=reason)
        ], True

    if obs.get("available") is False:
        status = str(obs.get("status") or "")
        if status == "outside_forecast_window":
            reason = "weather not applied (beyond forecast horizon)"
        else:
            reason = f"weather not applied ({status or 'forecast unavailable'})"
        return [
            _entry(factor="weather", applied=False, team=home_n, reason=reason)
        ], True

    delta, notes = _weather_total_from_obs(obs)
    source = str(obs.get("source") or "forecast")
    if not notes:
        wind = _to_float(obs.get("wind_mph"))
        temp = _to_float(obs.get("temp_f"))
        detail = []
        if wind is not None:
            detail.append(f"wind {wind:.0f} mph")
        if temp is not None:
            detail.append(f"temp {temp:.0f}F")
        tail = ", ".join(detail) if detail else "bands quiet"
        return [
            _entry(
                factor="weather",
                applied=False,
                team=home_n,
                reason=f"weather not applied ({source}; {tail} — below KEI bands)",
            )
        ], True

    return [
        _entry(
            factor="weather",
            applied=True,
            team=home_n,
            direction="under",
            total_pts=delta,
            reason=f"weather {source}: {', '.join(notes)} (totals first, cap ±{WEATHER_TOTAL_CAP})",
        )
    ], True


@lru_cache(maxsize=4)
def load_week1_officials(season: int = SCOPE_SEASON) -> Dict[str, Any]:
    path = (
        Path(__file__).resolve().parent
        / "nfl_season_engine"
        / "data"
        / f"nfl_week1_officials_{season}.json"
    )
    if not path.is_file():
        return {"crews": [], "loaded": False, "snapshot_id": ""}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"crews": [], "loaded": False, "snapshot_id": ""}
    if not isinstance(payload, dict):
        return {"crews": [], "loaded": False, "snapshot_id": ""}
    payload = dict(payload)
    payload["loaded"] = True
    return payload


def _ref_factor(
    *,
    home: str,
    away: str,
    officials: Optional[Mapping[str, Any]] = None,
) -> FactorEntry:
    """Tiny total tendency only when a real Week 1 crew row exists. Never invent."""
    pack = officials if officials is not None else load_week1_officials(SCOPE_SEASON)
    crews = list(pack.get("crews") or []) if isinstance(pack, Mapping) else []
    home_n = _norm_team(home)
    away_n = _norm_team(away)
    match: Optional[Mapping[str, Any]] = None
    for raw in crews:
        if not isinstance(raw, Mapping):
            continue
        if _norm_team(raw.get("home")) == home_n and _norm_team(raw.get("away")) == away_n:
            match = raw
            break
    if match is None:
        return _entry(
            factor="ref",
            applied=False,
            reason="ref not applied (no Week 1 crew assignment)",
        )
    crew_name = str(match.get("crew") or match.get("referee") or "crew").strip() or "crew"
    raw_total = _to_float(match.get("total_tendency"))
    if raw_total is None or abs(raw_total) < 1e-9:
        return _entry(
            factor="ref",
            applied=False,
            reason=f"ref not applied ({crew_name} — no / neutral total tendency)",
        )
    clamped, _ = _clamp(raw_total, REF_TOTAL_CAP)
    direction = "over" if clamped > 0 else "under"
    return _entry(
        factor="ref",
        applied=True,
        direction=direction,
        total_pts=round(clamped, 4),
        reason=f"ref {crew_name} total tendency {clamped:+.2f} (cap ±{REF_TOTAL_CAP})",
    )


# ---------------------------------------------------------------------------
# Public apply
# ---------------------------------------------------------------------------


def in_week1_scope(
    *,
    week: Optional[int],
    season: int,
    season_type: str = "REG",
) -> bool:
    st = str(season_type or "REG").strip().upper()
    if st and st != "REG":
        return False
    return int(season or 0) == SCOPE_SEASON and week is not None and int(week) == SCOPE_WEEK


def apply_week1_kei_reprice(
    *,
    handicap: Mapping[str, Any],
    home_abbr: str,
    away_abbr: str,
    week: Optional[int],
    season: int,
    season_type: str = "REG",
    projection: Any = None,
    start_time: Any = None,
    pack: Optional[Week1Pack] = None,
    weather_obs: Optional[Mapping[str, Any]] = None,
    officials: Optional[Mapping[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (new_handicap, log). Model markets are not touched.

    ``spread_pts`` on the log net is home-spread convention (positive = home weaker).
    """
    handicap_out = dict(handicap)
    skipped = {
        "scope": "week1_reg_2026",
        "applied": False,
        "skipped": True,
        "reason": "",
        "spread_delta": 0.0,
        "total_delta": 0.0,
        "confidence_delta": 0.0,
        "qb_clear": True,
        "injury_clear": True,
        "weather_clear": True,
        "capped": False,
        "applied_factors": [],
        "considered_not_applied": [],
        "pack_snapshot_id": "",
        "pack_as_of": "",
    }
    if not in_week1_scope(week=week, season=season, season_type=season_type):
        skipped["reason"] = "not Week 1 REG 2026 — reprice skipped"
        return handicap_out, skipped

    spread = _to_float(handicap_out.get("spread_home"))
    total = _to_float(handicap_out.get("total_mean"))
    if spread is None:
        skipped["reason"] = "model/handicap spread missing — identity fallback, reprice skipped"
        return handicap_out, skipped

    pack = pack if pack is not None else load_week1_pack(int(season))
    home = _norm_team(home_abbr)
    away = _norm_team(away_abbr)

    applied: List[FactorEntry] = []
    considered: List[FactorEntry] = []
    net_spread = 0.0
    net_total = 0.0
    net_conf = 0.0
    qb_clear = True
    injury_clear = True

    # --- QB (always log; 0-pt confirmation still listed as applied) ---
    for team in (home, away):
        qb_entries, team_qb_clear = _qb_factor(team, pack)
        qb_clear = qb_clear and team_qb_clear
        for e in qb_entries:
            if e.factor == "qb_backup_dropoff" and e.applied:
                signed, direction = _home_signed(team, home, away, e.spread_pts)
                e.spread_pts = round(signed, 4)
                e.direction = direction
                net_spread += signed
                net_total += e.total_pts
            net_conf += e.confidence_delta
            (applied if e.applied else considered).append(e)

    # --- Injury ---
    skip_injury = model_already_has_injury(projection)
    if skip_injury:
        considered.append(
            _entry(
                factor="injury",
                applied=False,
                reason="injury already in frozen model snapshot — not restacked",
            )
        )
    elif not pack.loaded:
        considered.append(
            _entry(
                factor="injury",
                applied=False,
                reason="depth SoT pack missing — injury not applied",
            )
        )
    else:
        for team in (home, away):
            entries, team_clear = _injury_factors(team, pack)
            injury_clear = injury_clear and team_clear
            for e in entries:
                if e.factor == "injury_net" and e.applied:
                    signed, direction = _home_signed(team, home, away, e.spread_pts)
                    e.spread_pts = round(signed, 4)
                    e.direction = direction
                    net_spread += signed
                    net_total += e.total_pts
                    applied.append(e)
                elif e.applied:
                    applied.append(e)
                else:
                    considered.append(e)

    # --- Rest / travel ---
    skip_travel = model_already_has_travel(projection)
    for e in _rest_travel_factors(
        home=home,
        away=away,
        start_time=start_time,
        skip_travel_points=skip_travel,
    ):
        if e.applied:
            net_spread += e.spread_pts
            net_total += e.total_pts
            applied.append(e)
        else:
            considered.append(e)

    # --- Weather (real forecast when present; never climatology) ---
    weather_entries, weather_clear = _weather_factors(
        home=home,
        projection=projection,
        start_time=start_time,
        weather_obs=weather_obs,
    )
    for e in weather_entries:
        if e.applied:
            net_total += e.total_pts
            applied.append(e)
        else:
            considered.append(e)

    # --- Refs (crew pack only; empty pack → not applied) ---
    ref_entry = _ref_factor(home=home, away=away, officials=officials)
    if ref_entry.applied:
        net_total += ref_entry.total_pts
        applied.append(ref_entry)
    else:
        considered.append(ref_entry)

    capped = False
    clamped_spread, cap_s = _clamp(net_spread, SPREAD_CAP)
    clamped_total, cap_t = _clamp(net_total, TOTAL_CAP)
    if cap_s or cap_t:
        capped = True
        applied.append(
            _entry(
                factor="reprice_cap",
                applied=True,
                direction="capped",
                spread_pts=round(clamped_spread - net_spread, 4),
                total_pts=round(clamped_total - net_total, 4),
                reason=f"net reprice capped at spread ±{SPREAD_CAP} / total ±{TOTAL_CAP}",
            )
        )
        net_spread = clamped_spread
        net_total = clamped_total

    net_spread = round(net_spread, 2)
    net_total = round(net_total, 2)
    if total is not None:
        handicap_out["total_mean"] = round(total + net_total, 2)
    handicap_out["spread_home"] = round(spread + net_spread, 2)

    fires = abs(net_spread) > 1e-9 or abs(net_total) > 1e-9
    log = {
        "scope": "week1_reg_2026",
        "applied": fires,
        "skipped": False,
        "reason": "week1_desk_factors" if fires else "logged_only_no_point_delta",
        "spread_delta": net_spread,
        "total_delta": net_total,
        "confidence_delta": round(net_conf, 4),
        "qb_clear": qb_clear,
        "injury_clear": injury_clear,
        "weather_clear": weather_clear,
        "capped": capped,
        "applied_factors": [e.as_dict() for e in applied],
        "considered_not_applied": [e.as_dict() for e in considered],
        "pack_snapshot_id": pack.snapshot_id,
        "pack_as_of": pack.as_of,
        "caps": {
            "spread": SPREAD_CAP,
            "total": TOTAL_CAP,
            "team_injury_spread": TEAM_INJURY_SPREAD_CAP,
            "weather_total": WEATHER_TOTAL_CAP,
            "ref_total": REF_TOTAL_CAP,
        },
    }
    return handicap_out, log


def week1_slate_reprice_table(
    games: Sequence[Mapping[str, Any]],
    *,
    model_spread: float = -3.0,
    model_total: float = 44.0,
    pack: Optional[Week1Pack] = None,
) -> List[Dict[str, Any]]:
    """Factor-only sample table (synthetic model) for ops / smoke."""
    pack = pack if pack is not None else load_week1_pack(SCOPE_SEASON)
    rows: List[Dict[str, Any]] = []
    for g in games:
        home = str(g.get("home_team") or g.get("home_abbr") or "")
        away = str(g.get("away_team") or g.get("away_abbr") or "")
        handicap = {"spread_home": model_spread, "total_mean": model_total}
        new_h, log = apply_week1_kei_reprice(
            handicap=handicap,
            home_abbr=home,
            away_abbr=away,
            week=int(g.get("week") or SCOPE_WEEK),
            season=int(g.get("season") or SCOPE_SEASON),
            season_type=str(g.get("game_type") or g.get("season_type") or "REG"),
            pack=pack,
        )
        rows.append(
            {
                "game": f"{_norm_team(away)} @{_norm_team(home)}",
                "home": _norm_team(home),
                "away": _norm_team(away),
                "model_spread": model_spread,
                "kei_spread": new_h.get("spread_home"),
                "model_total": model_total,
                "kei_total": new_h.get("total_mean"),
                "spread_delta": log.get("spread_delta"),
                "total_delta": log.get("total_delta"),
                "qb_clear": log.get("qb_clear"),
                "factors": [
                    e.get("reason")
                    for e in (log.get("applied_factors") or [])
                    if e.get("factor") != "injury_net"
                ],
                "not_applied": [
                    e.get("reason") for e in (log.get("considered_not_applied") or [])
                ],
            }
        )
    return rows
