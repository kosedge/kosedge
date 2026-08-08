"""NFL Real QB Premium — measured starter-quality adjustment on true PR.

North star: ``data/ops/nfl-model-vision.md``.

Continuity (#143) already answers “same QB vs new QB?” as **prior travel**.
This module answers “how good is the projected starter?” as a capped
offense-index delta on top of the reconstructed team.

Anti-double-count posture
-------------------------
Team EPA packages already embed some QB contribution. Therefore:

* Same-QB / high-continuity → **dampened** residual premium (identity tilt)
* New starter → **fuller** premium (prior EPA embeds the old passer; continuity
  already discounted travel — premium restores current-starter quality)

Never invent precision: thin samples → smaller delta + wider uncertainty +
honest labels. Caps prevent one QB from dominating team reconstruction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_season_engine.continuity_score import (
    fetch_current_qb1,
    fetch_prior_primary_qbs,
    normalize_team,
)

QB_PREMIUM_VERSION = "v1.0"

# Map quality → offense_index units (1.0 = league avg).
PREMIUM_SCALE = 0.058  # |tanh|→1 maps near this before caps / shrinks
PREMIUM_CAP = 0.070  # hard cap — QB cannot dominate reconstruction
# Residual weight when same starter already lives inside team EPA.
SAME_QB_IDENTITY_WEIGHT = 0.40
NEW_QB_IDENTITY_WEIGHT = 0.90
UNCERTAIN_IDENTITY_WEIGHT = 0.55

# Sample floors (dropbacks).
DROPBACKS_FULL = 280
DROPBACKS_MIN = 80
DROPBACKS_THIN = 40

# League anchors for process metrics (recent NFL starter-ish).
_LEAGUE_QB_EPA = 0.02
_LEAGUE_QB_EPA_SD = 0.10
_LEAGUE_SUCCESS = 0.46
_LEAGUE_SUCCESS_SD = 0.045
_LEAGUE_CPOE = 0.0
_LEAGUE_CPOE_SD = 2.8
_LEAGUE_YPA = 7.0
_LEAGUE_YPA_SD = 0.85

# Uncertainty wideners (added to package variance).
ROOKIE_VARIANCE_BOOST = 0.14
FIRST_YEAR_VARIANCE_BOOST = 0.10
NEW_TEAM_VARIANCE_BOOST = 0.07
OPEN_COMP_VARIANCE_BOOST = 0.12
THIN_SAMPLE_VARIANCE_BOOST = 0.08


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _z(value: Optional[float], mean: float, sd: float) -> Optional[float]:
    if value is None or sd <= 1e-9:
        return None
    return (float(value) - float(mean)) / float(sd)


@dataclass(frozen=True)
class QbQualitySignal:
    """Process-over-counting QB quality inputs for one player-season."""

    player_id: str
    player_name: str = ""
    team: str = ""
    season: int = 0
    dropbacks: int = 0
    epa_per_play: Optional[float] = None
    success_rate: Optional[float] = None
    cpoe: Optional[float] = None
    yards_per_attempt: Optional[float] = None
    completion_rate: Optional[float] = None
    pressure_epa: Optional[float] = None  # when pressure bucket exists
    source: str = "missing"  # epa_process | counting_fallback | missing
    fidelity: str = "missing"  # real | approximate | missing
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team": self.team,
            "season": int(self.season),
            "dropbacks": int(self.dropbacks),
            "epa_per_play": self.epa_per_play,
            "success_rate": self.success_rate,
            "cpoe": self.cpoe,
            "yards_per_attempt": self.yards_per_attempt,
            "completion_rate": self.completion_rate,
            "pressure_epa": self.pressure_epa,
            "source": self.source,
            "fidelity": self.fidelity,
            "notes": self.notes,
        }


@dataclass
class TeamQbPremium:
    """Inspectable QB premium for one team (full-strength + current)."""

    team: str
    starter_id: str = ""
    starter_name: str = ""
    backup_id: str = ""
    backup_name: str = ""
    quality_z: float = 0.0
    premium_full: float = 0.0  # applied to full-strength offense
    premium_current: float = 0.0  # applied to current offense
    identity_weight: float = 0.0
    sample_shrink: float = 0.0
    variance_boost: float = 0.0
    tenure: str = "unknown"  # incumbent | new_team | first_year | rookie | open_comp | unknown
    same_as_prior: Optional[bool] = None
    starter_available: bool = True
    signal_source: str = "missing"
    fidelity: str = "missing"
    drivers: Dict[str, Any] = field(default_factory=dict)

    def to_drivers(self) -> Dict[str, Any]:
        return {
            "version": QB_PREMIUM_VERSION,
            "team": self.team,
            "starter_id": self.starter_id,
            "starter_name": self.starter_name,
            "backup_id": self.backup_id or None,
            "backup_name": self.backup_name or None,
            "quality_z": round(float(self.quality_z), 4),
            "premium_full": round(float(self.premium_full), 6),
            "premium_current": round(float(self.premium_current), 6),
            "availability_delta": round(
                float(self.premium_current) - float(self.premium_full), 6
            ),
            "identity_weight": round(float(self.identity_weight), 4),
            "sample_shrink": round(float(self.sample_shrink), 4),
            "variance_boost": round(float(self.variance_boost), 4),
            "tenure": self.tenure,
            "same_as_prior": self.same_as_prior,
            "starter_available": bool(self.starter_available),
            "signal_source": self.signal_source,
            "fidelity": self.fidelity,
            "caps": {"premium_cap": PREMIUM_CAP, "premium_scale": PREMIUM_SCALE},
            "detail": dict(self.drivers or {}),
        }


def sample_shrink_from_dropbacks(dropbacks: int) -> float:
    """0–1 confidence from dropback sample (never invent finished identity)."""
    n = max(0, int(dropbacks))
    if n <= 0:
        return 0.0
    if n < DROPBACKS_THIN:
        return _clamp(n / float(DROPBACKS_THIN) * 0.20, 0.05, 0.20)
    if n < DROPBACKS_MIN:
        return _clamp(0.20 + 0.25 * (n - DROPBACKS_THIN) / (DROPBACKS_MIN - DROPBACKS_THIN), 0.20, 0.45)
    return _clamp(n / float(DROPBACKS_FULL), 0.45, 1.0)


def compose_quality_z(signal: QbQualitySignal) -> Tuple[float, str, List[str]]:
    """Build process-first quality z. Returns (z, source_label, component notes)."""
    notes: List[str] = []
    parts: List[Tuple[float, float]] = []  # (z, weight)

    epa_z = _z(signal.epa_per_play, _LEAGUE_QB_EPA, _LEAGUE_QB_EPA_SD)
    if epa_z is not None:
        parts.append((_clamp(epa_z, -3.5, 3.5), 0.55))
        notes.append(f"epa_z={epa_z:.3f}")

    sr_z = _z(signal.success_rate, _LEAGUE_SUCCESS, _LEAGUE_SUCCESS_SD)
    if sr_z is not None:
        parts.append((_clamp(sr_z, -3.5, 3.5), 0.25))
        notes.append(f"success_z={sr_z:.3f}")

    cpoe_z = _z(signal.cpoe, _LEAGUE_CPOE, _LEAGUE_CPOE_SD)
    if cpoe_z is not None:
        parts.append((_clamp(cpoe_z, -3.5, 3.5), 0.20))
        notes.append(f"cpoe_z={cpoe_z:.3f}")

    # Pressure-adjusted soft tilt when present (does not replace overall EPA).
    press_z = _z(signal.pressure_epa, _LEAGUE_QB_EPA - 0.15, _LEAGUE_QB_EPA_SD)
    if press_z is not None and epa_z is not None:
        parts.append((_clamp(press_z, -3.5, 3.5), 0.08))
        notes.append(f"pressure_epa_z={press_z:.3f}")

    if parts:
        wsum = sum(w for _, w in parts) or 1.0
        z = sum(v * w for v, w in parts) / wsum
        return round(z, 4), "epa_process", notes

    # Weak counting fallback — labeled approximate.
    ypa_z = _z(signal.yards_per_attempt, _LEAGUE_YPA, _LEAGUE_YPA_SD)
    cmp_z = _z(signal.completion_rate, 0.64, 0.04)
    if ypa_z is None and cmp_z is None:
        return 0.0, "missing", ["no process or counting metrics"]
    fallback_parts: List[Tuple[float, float]] = []
    if ypa_z is not None:
        fallback_parts.append((_clamp(ypa_z, -3.0, 3.0), 0.65))
        notes.append(f"ypa_z={ypa_z:.3f}")
    if cmp_z is not None:
        fallback_parts.append((_clamp(cmp_z, -3.0, 3.0), 0.35))
        notes.append(f"comp_z={cmp_z:.3f}")
    wsum = sum(w for _, w in fallback_parts) or 1.0
    z = sum(v * w for v, w in fallback_parts) / wsum
    notes.append("counting_stats_fallback")
    return round(z, 4), "counting_fallback", notes


def identity_weight_for_context(
    *,
    same_as_prior: Optional[bool],
    tenure: str,
) -> float:
    """How hard premium pulls given continuity already handled travel."""
    if tenure in ("rookie", "first_year", "open_comp"):
        return UNCERTAIN_IDENTITY_WEIGHT
    if same_as_prior is True:
        return SAME_QB_IDENTITY_WEIGHT
    if same_as_prior is False:
        return NEW_QB_IDENTITY_WEIGHT
    return UNCERTAIN_IDENTITY_WEIGHT


def map_quality_to_premium(
    quality_z: float,
    *,
    sample_shrink: float,
    identity_weight: float,
    fidelity: str = "real",
) -> float:
    """Smooth, capped quality → offense-index delta."""
    # Soft saturating map so extremes do not explode.
    shaped = math.tanh(float(quality_z) / 1.75)
    raw = shaped * PREMIUM_SCALE * _clamp(sample_shrink, 0.0, 1.0) * _clamp(
        identity_weight, 0.0, 1.0
    )
    if fidelity == "approximate":
        raw *= 0.75
    elif fidelity == "missing":
        return 0.0
    return round(_clamp(raw, -PREMIUM_CAP, PREMIUM_CAP), 6)


def variance_boost_for_tenure(
    tenure: str,
    *,
    sample_shrink: float,
) -> float:
    """Widen uncertainty for rookies / open competitions / thin samples."""
    base = {
        "rookie": ROOKIE_VARIANCE_BOOST,
        "first_year": FIRST_YEAR_VARIANCE_BOOST,
        "new_team": NEW_TEAM_VARIANCE_BOOST,
        "open_comp": OPEN_COMP_VARIANCE_BOOST,
        "incumbent": 0.0,
        "unknown": 0.04,
    }.get(tenure, 0.04)
    thin = THIN_SAMPLE_VARIANCE_BOOST * (1.0 - _clamp(sample_shrink, 0.0, 1.0))
    return round(base + thin, 4)


def infer_tenure(
    *,
    starter_id: str,
    prior_qb_id: Optional[str],
    signal_dropbacks: int,
    prior_season_dropbacks: int,
    open_competition: bool = False,
) -> Tuple[str, Optional[bool]]:
    """Classify starter tenure + same-as-prior flag."""
    if open_competition:
        return "open_comp", None
    sid = str(starter_id or "").strip()
    pid = str(prior_qb_id or "").strip() or None
    same: Optional[bool] = None
    if sid and pid:
        same = sid == pid
    if not sid:
        return "unknown", same
    if prior_season_dropbacks < DROPBACKS_THIN and signal_dropbacks < DROPBACKS_MIN:
        return "rookie", same if same is not None else False
    if prior_season_dropbacks < DROPBACKS_MIN:
        return "first_year", same if same is not None else False
    if same is False:
        return "new_team", False
    if same is True:
        return "incumbent", True
    return "unknown", same


def build_team_qb_premium_from_inputs(
    team: str,
    *,
    starter: Optional[Tuple[str, str]] = None,
    backup: Optional[Tuple[str, str]] = None,
    prior_qb: Optional[Tuple[str, str]] = None,
    starter_signal: Optional[QbQualitySignal] = None,
    backup_signal: Optional[QbQualitySignal] = None,
    prior_signal_dropbacks: int = 0,
    starter_available: bool = True,
    open_competition: bool = False,
) -> TeamQbPremium:
    """Pure compose path for tests + loaders."""
    team_n = normalize_team(team)
    starter_id = starter[0] if starter else ""
    starter_name = starter[1] if starter else ""
    backup_id = backup[0] if backup else ""
    backup_name = backup[1] if backup else ""
    prior_id = prior_qb[0] if prior_qb else None

    signal = starter_signal or QbQualitySignal(player_id=starter_id or "missing")
    quality_z, source, component_notes = compose_quality_z(signal)
    shrink = sample_shrink_from_dropbacks(int(signal.dropbacks))
    tenure, same = infer_tenure(
        starter_id=starter_id,
        prior_qb_id=prior_id,
        signal_dropbacks=int(signal.dropbacks),
        prior_season_dropbacks=int(prior_signal_dropbacks),
        open_competition=open_competition,
    )
    id_w = identity_weight_for_context(same_as_prior=same, tenure=tenure)

    fidelity = str(signal.fidelity or "missing")
    if source == "missing" or not starter_id:
        fidelity = "missing"
    elif source == "counting_fallback":
        fidelity = "approximate"

    premium_full = map_quality_to_premium(
        quality_z,
        sample_shrink=shrink,
        identity_weight=id_w,
        fidelity=fidelity,
    )

    # Current path: healthy starter vs backup / replacement when unavailable.
    premium_current = premium_full
    current_detail: Dict[str, Any] = {"mode": "starter"}
    if not starter_available:
        if backup_signal is not None and str(backup_signal.player_id or ""):
            b_z, b_src, b_notes = compose_quality_z(backup_signal)
            b_shrink = sample_shrink_from_dropbacks(int(backup_signal.dropbacks))
            b_fid = backup_signal.fidelity
            if b_src == "counting_fallback":
                b_fid = "approximate"
            elif b_src == "missing":
                b_fid = "missing"
            premium_current = map_quality_to_premium(
                b_z,
                sample_shrink=b_shrink,
                identity_weight=NEW_QB_IDENTITY_WEIGHT,
                fidelity=b_fid,
            )
            current_detail = {
                "mode": "backup",
                "backup_quality_z": b_z,
                "backup_source": b_src,
                "backup_notes": b_notes,
                "backup_fidelity": b_fid,
            }
        else:
            # Replacement-level drag when backup quality unknown.
            premium_current = map_quality_to_premium(
                -1.10,
                sample_shrink=0.55,
                identity_weight=NEW_QB_IDENTITY_WEIGHT,
                fidelity="approximate",
            )
            current_detail = {
                "mode": "replacement_approx",
                "note": "starter out; backup signal missing → approx replacement",
            }

    var_boost = variance_boost_for_tenure(tenure, sample_shrink=shrink)
    if not starter_available:
        var_boost = round(var_boost + 0.06, 4)

    drivers = {
        "quality_components": component_notes,
        "signal": signal.to_dict(),
        "current": current_detail,
        "prior_qb_id": prior_id,
        "prior_qb_name": prior_qb[1] if prior_qb else "",
        "anti_double_count": (
            "same_qb_dampened_residual"
            if same is True
            else ("new_qb_fuller_identity" if same is False else "uncertain_identity")
        ),
    }

    return TeamQbPremium(
        team=team_n,
        starter_id=starter_id,
        starter_name=starter_name,
        backup_id=backup_id,
        backup_name=backup_name,
        quality_z=quality_z,
        premium_full=premium_full,
        premium_current=premium_current,
        identity_weight=id_w,
        sample_shrink=shrink,
        variance_boost=var_boost,
        tenure=tenure,
        same_as_prior=same,
        starter_available=bool(starter_available),
        signal_source=source if starter_id else "missing",
        fidelity=fidelity if starter_id else "missing",
        drivers=drivers,
    )


def attach_qb_premium_drivers(
    drivers: Dict[str, Any],
    premium: Optional[TeamQbPremium],
) -> Dict[str, Any]:
    """Merge QB premium into true-PR drivers; preserve continuity block."""
    out = dict(drivers or {})
    stubs = dict(out.get("stubs") or {})
    if premium is None or premium.fidelity == "missing":
        stubs["qb_premium"] = "stub_not_applied"
        out["stubs"] = stubs
        out["qb_premium"] = {
            "status": "stub_not_applied",
            "note": "qb premium not applied",
        }
        return out

    stubs["qb_premium"] = (
        "applied_approximate" if premium.fidelity == "approximate" else "applied"
    )
    out["stubs"] = stubs
    out["qb_premium"] = premium.to_drivers()
    unc = dict(out.get("uncertainty") or {})
    unc["qb_premium_boost"] = round(float(premium.variance_boost), 4)
    out["uncertainty"] = unc
    return out


def apply_qb_premium_to_payload(
    payload: Dict[str, Any],
    premium: Optional[TeamQbPremium],
) -> Dict[str, Any]:
    """Apply full/current premiums onto a strength payload (offense only)."""
    out = dict(payload or {})
    if premium is None or premium.fidelity == "missing":
        out["qb_premium"] = 0.0
        out["drivers"] = attach_qb_premium_drivers(out.get("drivers") or {}, None)
        return out

    full_d = float(premium.premium_full)
    cur_d = float(premium.premium_current)

    def _bump(key: str, delta: float) -> None:
        if key in out:
            out[key] = round(float(out[key]) + delta, 6)

    # Full-strength assumes healthy projected starter.
    _bump("full_strength_offense_index", full_d)
    # Current reflects starter availability (backup / replacement when out).
    _bump("offense_index", cur_d)
    _bump("current_offense_index", cur_d)

    # Keep injury_delta coherent with full vs current split.
    full_off = float(out.get("full_strength_offense_index", out.get("offense_index", 1.0)))
    cur_off = float(out.get("offense_index", full_off))
    out["injury_delta_offense"] = round(cur_off - full_off, 6)
    out["qb_premium"] = round(full_d, 6)

    var = float(out.get("variance", 1.0) or 1.0)
    out["variance"] = round(min(1.70, var + float(premium.variance_boost)), 4)

    drivers = attach_qb_premium_drivers(out.get("drivers") or {}, premium)
    # Surface availability delta status when starter out.
    if not premium.starter_available:
        iad = dict(drivers.get("injury_availability_delta") or {})
        iad["offense"] = float(out["injury_delta_offense"])
        iad["status"] = "qb_starter_unavailable"
        iad["qb_premium_availability_delta"] = round(cur_d - full_d, 6)
        drivers["injury_availability_delta"] = iad
    out["drivers"] = drivers
    return out


# ---------------------------------------------------------------------------
# DB loaders
# ---------------------------------------------------------------------------


def fetch_qb_overall_signals(
    session: Any,
    *,
    season: int,
    min_dropbacks: int = 1,
) -> Dict[str, QbQualitySignal]:
    """Load overall QB process signals from situational splits → {player_id: signal}."""
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            SELECT player_id, player_name, team, dropbacks, epa_per_play,
                   success_rate, cpoe, yards_per_attempt, completion_rate
            FROM nfl_dp_qb_situational_splits
            WHERE season = :season
              AND situation_type = 'overall'
              AND situation_bucket = 'overall'
              AND dropbacks >= :min_dropbacks
            """
        ),
        {"season": int(season), "min_dropbacks": int(min_dropbacks)},
    ).fetchall()

    # Optional pressure bucket for soft process tilt.
    pressure: Dict[str, float] = {}
    try:
        prow = session.execute(
            text(
                """
                SELECT player_id, epa_per_play, dropbacks
                FROM nfl_dp_qb_situational_splits
                WHERE season = :season
                  AND situation_type = 'pressure'
                  AND situation_bucket = 'pressure'
                  AND dropbacks >= 40
                """
            ),
            {"season": int(season)},
        ).fetchall()
        for r in prow:
            pid = str(getattr(r, "player_id", None) or r[0] or "").strip()
            epa = _safe_float(getattr(r, "epa_per_play", None) if hasattr(r, "epa_per_play") else r[1])
            if pid and epa is not None:
                pressure[pid] = epa
    except Exception:
        pressure = {}

    out: Dict[str, QbQualitySignal] = {}
    for row in rows:
        pid = str(getattr(row, "player_id", None) or row[0] or "").strip()
        if not pid:
            continue
        dropbacks = int(getattr(row, "dropbacks", None) or row[3] or 0)
        epa = _safe_float(getattr(row, "epa_per_play", None) if hasattr(row, "epa_per_play") else row[4])
        sr = _safe_float(getattr(row, "success_rate", None) if hasattr(row, "success_rate") else row[5])
        cpoe = _safe_float(getattr(row, "cpoe", None) if hasattr(row, "cpoe") else row[6])
        ypa = _safe_float(
            getattr(row, "yards_per_attempt", None) if hasattr(row, "yards_per_attempt") else row[7]
        )
        cmp_r = _safe_float(
            getattr(row, "completion_rate", None) if hasattr(row, "completion_rate") else row[8]
        )
        has_process = epa is not None or sr is not None or cpoe is not None
        out[pid] = QbQualitySignal(
            player_id=pid,
            player_name=str(getattr(row, "player_name", None) or row[1] or ""),
            team=normalize_team(str(getattr(row, "team", None) or row[2] or "")),
            season=int(season),
            dropbacks=dropbacks,
            epa_per_play=epa,
            success_rate=sr,
            cpoe=cpoe,
            yards_per_attempt=ypa,
            completion_rate=cmp_r,
            pressure_epa=pressure.get(pid),
            source="epa_process" if has_process else "counting_fallback",
            fidelity="real" if has_process else "approximate",
            notes="nfl_dp_qb_situational_splits.overall",
        )
    return out


def fetch_qb_depth(
    session: Any,
    *,
    season: int,
    as_of_week: Optional[int] = None,
) -> Dict[str, Dict[int, Tuple[str, str]]]:
    """{team: {depth_team: (player_id, name)}} for QBs."""
    from sqlalchemy import text

    week = int(as_of_week or 1)
    out: Dict[str, Dict[int, Tuple[str, str]]] = {}
    try:
        rows = session.execute(
            text(
                """
                SELECT team, player_id, player_name, depth_team
                FROM nfl_dp_official_depth_charts
                WHERE season = :season AND week = :week AND position = 'QB'
                  AND depth_team IN (1, 2)
                """
            ),
            {"season": int(season), "week": week},
        ).fetchall()
        for row in rows:
            team = normalize_team(str(getattr(row, "team", None) or row[0] or ""))
            pid = str(getattr(row, "player_id", None) or row[1] or "").strip()
            name = str(getattr(row, "player_name", None) or row[2] or "")
            depth = int(getattr(row, "depth_team", None) or row[3] or 99)
            if team and pid and depth in (1, 2):
                out.setdefault(team, {})[depth] = (pid, name)
    except Exception:
        out = {}
    return out


def fetch_inactive_qb_ids(
    session: Any,
    *,
    season: int,
    as_of_week: Optional[int] = None,
) -> set:
    """Best-effort set of QB player_ids marked out/inactive for the week.

    Thin feed → empty set (do not invent outs). Callers keep starter_available=True.
    """
    from sqlalchemy import text

    week = int(as_of_week or 0)
    if week <= 0:
        return set()
    out: set = set()
    # Prefer injury report style tables when present; tolerate absence.
    for sql in (
        """
        SELECT player_id FROM nfl_dp_injuries
        WHERE season = :season AND week = :week
          AND UPPER(COALESCE(position, '')) = 'QB'
          AND UPPER(COALESCE(status, report_status, '')) IN
              ('OUT', 'INACTIVE', 'IR', 'PUP', 'SUSPENDED')
        """,
        """
        SELECT player_id FROM nfl_dp_inactives
        WHERE season = :season AND week = :week
          AND UPPER(COALESCE(position, '')) = 'QB'
        """,
    ):
        try:
            rows = session.execute(
                text(sql), {"season": int(season), "week": week}
            ).fetchall()
            for row in rows:
                pid = str(getattr(row, "player_id", None) or row[0] or "").strip()
                if pid:
                    out.add(pid)
            if out:
                return out
        except Exception:
            continue
    return out


def _blend_signals(
    prior: Optional[QbQualitySignal],
    current: Optional[QbQualitySignal],
    *,
    current_games: int,
) -> Optional[QbQualitySignal]:
    """Blend prior/current QB signals with the same games/8 spirit (player-level)."""
    if current is None and prior is None:
        return None
    if current is None:
        return prior
    if prior is None:
        return current
    w_cur = _clamp(int(current_games) / 8.0, 0.0, 1.0)
    w_prior = 1.0 - w_cur

    def _mix(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None and b is None:
            return None
        if a is None:
            return b
        if b is None:
            return a
        return w_prior * float(a) + w_cur * float(b)

    dropbacks = int(round(w_prior * prior.dropbacks + w_cur * current.dropbacks))
    has_process = (
        _mix(prior.epa_per_play, current.epa_per_play) is not None
        or _mix(prior.success_rate, current.success_rate) is not None
        or _mix(prior.cpoe, current.cpoe) is not None
    )
    return QbQualitySignal(
        player_id=current.player_id or prior.player_id,
        player_name=current.player_name or prior.player_name,
        team=current.team or prior.team,
        season=current.season or prior.season,
        dropbacks=dropbacks,
        epa_per_play=_mix(prior.epa_per_play, current.epa_per_play),
        success_rate=_mix(prior.success_rate, current.success_rate),
        cpoe=_mix(prior.cpoe, current.cpoe),
        yards_per_attempt=_mix(prior.yards_per_attempt, current.yards_per_attempt),
        completion_rate=_mix(prior.completion_rate, current.completion_rate),
        pressure_epa=_mix(prior.pressure_epa, current.pressure_epa),
        source="epa_process" if has_process else "counting_fallback",
        fidelity="real" if has_process else "approximate",
        notes=f"blend prior/current w_cur={w_cur:.3f}",
    )


def build_qb_premium_book(
    session: Any,
    *,
    season: int,
    as_of_week: Optional[int] = None,
    teams: Optional[Iterable[str]] = None,
    team_games: Optional[Mapping[str, int]] = None,
    starter_out_ids: Optional[Iterable[str]] = None,
) -> Dict[str, TeamQbPremium]:
    """Build per-team QB premium from depth chart + situational process splits."""
    prior_season = int(season) - 1
    team_list = [normalize_team(t) for t in (teams or [])]
    games_map = {normalize_team(k): int(v) for k, v in (team_games or {}).items()}

    try:
        prior_signals = fetch_qb_overall_signals(session, season=prior_season)
    except Exception:
        prior_signals = {}
    try:
        current_signals = fetch_qb_overall_signals(session, season=int(season))
    except Exception:
        current_signals = {}

    try:
        current_qbs = fetch_current_qb1(
            session, season=int(season), as_of_week=as_of_week
        )
    except Exception:
        current_qbs = {}
    try:
        prior_qbs = fetch_prior_primary_qbs(session, prior_season=prior_season)
    except Exception:
        prior_qbs = {}
    try:
        depth = fetch_qb_depth(session, season=int(season), as_of_week=as_of_week)
    except Exception:
        depth = {}

    inactive = set(str(x) for x in (starter_out_ids or []))
    if not inactive:
        try:
            inactive = fetch_inactive_qb_ids(
                session, season=int(season), as_of_week=as_of_week
            )
        except Exception:
            inactive = set()

    if not team_list:
        team_list = sorted(set(current_qbs) | set(prior_qbs) | set(depth))

    out: Dict[str, TeamQbPremium] = {}
    for team in team_list:
        starter = current_qbs.get(team) or (depth.get(team) or {}).get(1)
        backup = (depth.get(team) or {}).get(2)
        prior_qb = prior_qbs.get(team)
        if starter is None:
            out[team] = build_team_qb_premium_from_inputs(team)
            continue

        sid = starter[0]
        starter_sig = _blend_signals(
            prior_signals.get(sid),
            current_signals.get(sid),
            current_games=int(games_map.get(team, 0) or 0),
        )
        # If starter has no player-level history (true rookie / sparse), keep missing
        # signal so premium shrinks + uncertainty widens rather than inventing elite.
        if starter_sig is None:
            starter_sig = QbQualitySignal(
                player_id=sid,
                player_name=starter[1],
                team=team,
                season=int(season),
                dropbacks=0,
                source="missing",
                fidelity="missing",
                notes="no situational splits for starter",
            )

        backup_sig = None
        if backup:
            backup_sig = _blend_signals(
                prior_signals.get(backup[0]),
                current_signals.get(backup[0]),
                current_games=int(games_map.get(team, 0) or 0),
            ) or QbQualitySignal(
                player_id=backup[0],
                player_name=backup[1],
                team=team,
                season=int(season),
                fidelity="missing",
                source="missing",
            )

        prior_db = int((prior_signals.get(sid).dropbacks if prior_signals.get(sid) else 0) or 0)
        # Open competition heuristic: no clear QB1 in depth/current feed.
        open_comp = starter is None  # unreachable here; kept for API symmetry
        available = sid not in inactive

        out[team] = build_team_qb_premium_from_inputs(
            team,
            starter=starter,
            backup=backup,
            prior_qb=prior_qb,
            starter_signal=starter_sig,
            backup_signal=backup_sig,
            prior_signal_dropbacks=prior_db,
            starter_available=available,
            open_competition=open_comp,
        )
    return out


def documentation() -> Dict[str, Any]:
    return {
        "layer": "qb_premium",
        "module": "src.services.nfl_season_engine.qb_premium",
        "role": "offense_index_delta_on_true_pr",
        "not": [
            "continuity_redesign",
            "ol_premium",
            "kei_reprice",
            "future_sos",
            "fantasy_ui",
        ],
        "formula": (
            "quality_z = weighted(epa_z, success_z, cpoe_z) [counting fallback]; "
            "premium = clamp(tanh(z/1.75)*scale*sample_shrink*identity_weight, ±cap); "
            "same_qb identity_weight=0.40; new_qb=0.90; uncertain=0.55"
        ),
        "caps": {"premium_cap": PREMIUM_CAP, "premium_scale": PREMIUM_SCALE},
        "interaction_with_continuity": (
            "continuity = prior travel only; premium = current starter quality; "
            "new+good not erased by low travel alone; new+bad is harsh but coherent"
        ),
    }
