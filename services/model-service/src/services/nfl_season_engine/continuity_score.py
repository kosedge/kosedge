"""NFL Continuity Score — prior-travel weight for true PR construction.

Continuity scales how hard the prior pulls (especially early). It does **not**
invent a new rating scale, replace the games/8 blend curve, or implement a
full QB premium layer (that is a separate brief).

Formula (exact):
  w_current = clamp(completed_reg / 8, 0, 1)          # unchanged #140 curve
  prior_travel = travel_from_continuity(score)         # in [TRAVEL_FLOOR, 1]
  w_prior  = (1 - w_current) * prior_travel
  w_anchor = (1 - w_current) * (1 - prior_travel)      # league-mean shrink
  blended  = w_prior * prior + w_current * current + w_anchor * league_anchor

At 0 REG games, low-continuity teams are not "last year locked" — residual
mass shrinks toward league mean and uncertainty widens.

North star: ``data/ops/nfl-model-vision.md``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# Factor weights (sum = 1.0). Missing factors are dropped and weights renormalized.
_W_QB = 0.40
_W_STAFF = 0.25
_W_RETURNING_PROD = 0.25
_W_CHURN = 0.10

# prior_travel = TRAVEL_FLOOR + (1 - TRAVEL_FLOOR) * continuity_score
TRAVEL_FLOOR = 0.35
# Extra variance when continuity is low (added on top of uncertainty_from_games).
CONTINUITY_VARIANCE_BOOST = 0.24

BAND_HIGH = 0.72
BAND_LOW = 0.45

_SKILL_POS = frozenset({"QB", "RB", "WR", "TE", "FB"})
_OL_POS = frozenset({"OL", "T", "G", "C", "OT", "OG", "LS", "C/G", "G/C"})

_PACKAGE_DATA_DIR = Path(__file__).resolve().parent / "data"

# Curated HC/OC change flags for the upcoming season (approximate until a live
# coaching feed exists). Only material known breaks are listed; missing teams
# contribute a neutral staff factor labeled approximate.
#
# 2026 offseason: record-tying HC carousel (ARI/BUF/LV/CLE/ATL/NYG/TEN/PIT/MIA/BAL)
# plus OC losses on LA (LaFleur→ARI) and SEA (Kubiak→LV).
CURATED_STAFF_BY_SEASON: Dict[int, Dict[str, Dict[str, Any]]] = {
    2026: {
        "ARI": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: Mike LaFleur HC (new regime)",
        },
        "BUF": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: Joe Brady promoted OC→HC; new OC",
        },
        "LV": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: Klint Kubiak HC (new regime)",
        },
        "CLE": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: Todd Monken HC (new regime)",
        },
        "ATL": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: Kevin Stefanski HC (new regime)",
        },
        "NYG": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: John Harbaugh HC (new regime)",
        },
        "TEN": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: Robert Saleh HC (new regime)",
        },
        "PIT": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: Mike McCarthy HC (new regime)",
        },
        "MIA": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: Jeff Hafley HC (new regime)",
        },
        "BAL": {
            "new_hc": True,
            "new_oc": True,
            "notes": "curated: Jesse Minter HC (new regime)",
        },
        "LA": {
            "new_hc": False,
            "new_oc": True,
            "notes": "curated: McVay returns; OC LaFleur departed",
        },
        "SEA": {
            "new_hc": False,
            "new_oc": True,
            "notes": "curated: Macdonald returns; OC Kubiak departed",
        },
    }
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def normalize_team(team: str) -> str:
    t = str(team or "").strip().upper()
    if t == "LAR":
        return "LA"
    return t


@dataclass(frozen=True)
class ContinuityFactor:
    """One inspectable continuity factor contribution."""

    name: str
    score: float  # 0–1 within-factor
    weight: float
    status: str  # real | approximate | missing
    detail: str = ""


@dataclass
class TeamContinuity:
    """Team continuity score + prior-travel modulation."""

    team: str
    continuity_score: float  # 0–1
    band: str  # high | mid | low
    prior_travel_weight: float  # 0–1 travel on residual prior mass
    factors: List[ContinuityFactor] = field(default_factory=list)
    drivers: Dict[str, Any] = field(default_factory=dict)
    fidelity: str = "approximate"  # real | mixed | approximate

    def to_drivers(self) -> Dict[str, Any]:
        return {
            "continuity_score": round(float(self.continuity_score), 4),
            "band": self.band,
            "prior_travel_weight": round(float(self.prior_travel_weight), 4),
            "fidelity": self.fidelity,
            "factors": [
                {
                    "name": f.name,
                    "score": round(float(f.score), 4),
                    "weight": round(float(f.weight), 4),
                    "status": f.status,
                    "detail": f.detail,
                }
                for f in self.factors
            ],
            "note": (
                "Continuity modulates prior travel only — not a new PR scale. "
                "QB factor ≠ full QB premium layer (next brief)."
            ),
            **dict(self.drivers or {}),
        }


def band_from_score(score: float) -> str:
    s = float(score)
    if s >= BAND_HIGH:
        return "high"
    if s <= BAND_LOW:
        return "low"
    return "mid"


def travel_from_continuity(continuity_score: float) -> float:
    """Map continuity score → prior travel weight on the residual prior mass."""
    s = _clamp(continuity_score, 0.0, 1.0)
    return round(TRAVEL_FLOOR + (1.0 - TRAVEL_FLOOR) * s, 4)


def continuity_uncertainty_boost(continuity_score: float) -> float:
    """Widen early uncertainty when continuity is low (not fake precision)."""
    return round((1.0 - _clamp(continuity_score, 0.0, 1.0)) * CONTINUITY_VARIANCE_BOOST, 4)


def score_qb_factor(
    *,
    prior_qb_id: Optional[str],
    prior_qb_name: str = "",
    current_qb_id: Optional[str],
    current_qb_name: str = "",
    prior_qb_on_roster: Optional[bool] = None,
) -> ContinuityFactor:
    """QB returning / new starter factor (continuity only — not QB premium)."""
    prior_id = str(prior_qb_id or "").strip() or None
    current_id = str(current_qb_id or "").strip() or None

    if prior_id is None and current_id is None:
        return ContinuityFactor(
            name="qb",
            score=0.50,
            weight=_W_QB,
            status="missing",
            detail="no prior or current QB identity",
        )

    if prior_id and current_id and prior_id == current_id:
        return ContinuityFactor(
            name="qb",
            score=1.0,
            weight=_W_QB,
            status="real",
            detail=f"same starter ({current_qb_name or prior_qb_name or prior_id})",
        )

    if prior_id and prior_qb_on_roster is False:
        return ContinuityFactor(
            name="qb",
            score=0.12,
            weight=_W_QB,
            status="real",
            detail=(
                f"new QB — prior starter left roster "
                f"({prior_qb_name or prior_id} → {current_qb_name or current_id or '?'})"
            ),
        )

    if prior_id and current_id and prior_id != current_id:
        # Starter identity changed; if prior QB remains, softer hit + approximate
        # (depth charts can be noisy in camp).
        if prior_qb_on_roster:
            return ContinuityFactor(
                name="qb",
                score=0.32,
                weight=_W_QB,
                status="approximate",
                detail=(
                    f"starter change with prior QB still rostered "
                    f"({prior_qb_name or prior_id} → {current_qb_name or current_id})"
                ),
            )
        return ContinuityFactor(
            name="qb",
            score=0.15,
            weight=_W_QB,
            status="real",
            detail=(
                f"new starting QB "
                f"({prior_qb_name or prior_id} → {current_qb_name or current_id})"
            ),
        )

    if prior_id and prior_qb_on_roster and current_id is None:
        return ContinuityFactor(
            name="qb",
            score=0.78,
            weight=_W_QB,
            status="approximate",
            detail=f"prior QB on roster; current starter thin ({prior_qb_name or prior_id})",
        )

    return ContinuityFactor(
        name="qb",
        score=0.50,
        weight=_W_QB,
        status="approximate",
        detail="partial QB evidence only",
    )


def score_staff_factor(
    *,
    new_hc: Optional[bool],
    new_oc: Optional[bool],
    notes: str = "",
    status: str = "approximate",
) -> ContinuityFactor:
    """HC / OC continuity. Missing → neutral + approximate."""
    if new_hc is None and new_oc is None:
        return ContinuityFactor(
            name="staff",
            score=0.50,
            weight=_W_STAFF,
            status="missing",
            detail="no HC/OC continuity feed",
        )

    hc_new = bool(new_hc) if new_hc is not None else False
    oc_new = bool(new_oc) if new_oc is not None else False
    # If only one flag known, treat unknown sibling as returning (soft).
    if new_hc is None:
        hc_new = False
    if new_oc is None:
        oc_new = False

    if not hc_new and not oc_new:
        score = 1.0
        detail = "HC + OC returning"
    elif not hc_new and oc_new:
        score = 0.55
        detail = "HC returning, new OC"
    elif hc_new and not oc_new:
        score = 0.35
        detail = "new HC, OC continuity"
    else:
        score = 0.18
        detail = "new HC + new OC"

    if notes:
        detail = f"{detail} ({notes})"
    return ContinuityFactor(
        name="staff",
        score=score,
        weight=_W_STAFF,
        status=status,
        detail=detail,
    )


def score_returning_production_factor(
    returning_share: Optional[float],
    *,
    skill_share: Optional[float] = None,
    ol_share: Optional[float] = None,
) -> ContinuityFactor:
    """Returning production share (skill yards + OL roster where available)."""
    if returning_share is None and skill_share is None and ol_share is None:
        return ContinuityFactor(
            name="returning_production",
            score=0.50,
            weight=_W_RETURNING_PROD,
            status="missing",
            detail="no returning production inputs",
        )

    parts: List[Tuple[float, float]] = []
    detail_bits: List[str] = []
    if skill_share is not None:
        parts.append((_clamp(skill_share, 0.0, 1.0), 0.70))
        detail_bits.append(f"skill={skill_share:.3f}")
    if ol_share is not None:
        parts.append((_clamp(ol_share, 0.0, 1.0), 0.30))
        detail_bits.append(f"ol={ol_share:.3f}")
    if not parts and returning_share is not None:
        parts.append((_clamp(returning_share, 0.0, 1.0), 1.0))
        detail_bits.append(f"share={returning_share:.3f}")

    wsum = sum(w for _, w in parts) or 1.0
    score = sum(s * w for s, w in parts) / wsum
    status = "real" if skill_share is not None else "approximate"
    return ContinuityFactor(
        name="returning_production",
        score=round(score, 4),
        weight=_W_RETURNING_PROD,
        status=status,
        detail="returning production " + ", ".join(detail_bits),
    )


def score_churn_factor(
    *,
    roster_return_share: Optional[float] = None,
    major_churn: Optional[bool] = None,
) -> ContinuityFactor:
    """Major roster churn / FA overhaul — inverse of stability."""
    if roster_return_share is None and major_churn is None:
        return ContinuityFactor(
            name="roster_churn",
            score=0.50,
            weight=_W_CHURN,
            status="missing",
            detail="no roster churn inputs",
        )

    if roster_return_share is not None:
        # High return → high continuity contribution.
        score = _clamp(float(roster_return_share), 0.0, 1.0)
        # Soft threshold: heavy overhaul (<40% return) floors lower.
        if score < 0.40:
            score = score * 0.85
        detail = f"roster_return_share={roster_return_share:.3f}"
        status = "real"
    else:
        score = 0.25 if major_churn else 0.75
        detail = "major_churn flag" if major_churn else "no major_churn flag"
        status = "approximate"

    if major_churn:
        score = min(score, 0.30)
        detail += "; major FA/overhaul flagged"
        status = "approximate" if status == "real" else status

    return ContinuityFactor(
        name="roster_churn",
        score=round(_clamp(score, 0.0, 1.0), 4),
        weight=_W_CHURN,
        status=status,
        detail=detail,
    )


def compose_continuity(
    team: str,
    factors: Sequence[ContinuityFactor],
    *,
    extra_drivers: Optional[Mapping[str, Any]] = None,
) -> TeamContinuity:
    """Weighted continuity score with honest missing-factor handling.

    Per-factor missing → **neutral 0.5 contribution** labeled approximate
    (never invent a directional signal).
    If **all** factors lack evidence → travel stays 1.0 (do not invent a
    league-wide mid discount with zero inputs).
    """
    used: List[ContinuityFactor] = []
    has_evidence = False
    for f in factors:
        if f.status == "missing":
            used.append(
                ContinuityFactor(
                    name=f.name,
                    score=0.50,
                    weight=f.weight,
                    status="approximate",
                    detail=(f.detail or "missing") + " → neutral",
                )
            )
        else:
            has_evidence = True
            used.append(f)

    if not has_evidence:
        score = 0.50
        fidelity = "missing"
        travel = 1.0
    else:
        wsum = sum(float(f.weight) for f in used) or 1.0
        score = sum(float(f.score) * float(f.weight) for f in used) / wsum
        # Prefer fidelity from evidenced factors only.
        evidenced = [f for f in factors if f.status != "missing"]
        ev_statuses = {f.status for f in evidenced}
        if ev_statuses == {"real"}:
            fidelity = "real"
        elif "real" in ev_statuses:
            fidelity = "mixed"
        else:
            fidelity = "approximate"
        travel = travel_from_continuity(score)

    return TeamContinuity(
        team=normalize_team(team),
        continuity_score=round(_clamp(score, 0.0, 1.0), 4),
        band=band_from_score(score),
        prior_travel_weight=travel,
        factors=used,
        drivers=dict(extra_drivers or {}),
        fidelity=fidelity,
    )


def blend_weights_with_continuity(
    *,
    current_games: int,
    prior_travel_weight: float,
) -> Dict[str, float]:
    """Expose exact blend weights used with continuity travel.

    Does **not** replace games/8 — only scales the residual prior mass.
    """
    from src.services.nfl_season_engine.efficiency_backbone import (
        prior_current_blend_weight,
    )

    w_cur = float(prior_current_blend_weight(current_games=int(current_games)))
    travel = _clamp(float(prior_travel_weight), 0.0, 1.0)
    w_prior = (1.0 - w_cur) * travel
    w_anchor = (1.0 - w_cur) * (1.0 - travel)
    return {
        "w_current": round(w_cur, 4),
        "w_prior": round(w_prior, 4),
        "w_anchor": round(w_anchor, 4),
        "prior_travel_weight": round(travel, 4),
        "residual_prior_mass": round(1.0 - w_cur, 4),
    }


# ---------------------------------------------------------------------------
# Data loaders (DB + packaged depth fallback)
# ---------------------------------------------------------------------------


def _load_packaged_qb1(season: int) -> Dict[str, Tuple[str, str]]:
    """Return {team: (player_id, player_name)} from packaged depth chart."""
    path = _PACKAGE_DATA_DIR / f"nfl_depth_chart_{int(season)}_w1.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: Dict[str, Tuple[str, str]] = {}
    for row in payload.get("rows") or []:
        if str(row.get("position") or "").upper() != "QB":
            continue
        if int(row.get("depth_order") or 99) != 1:
            continue
        team = normalize_team(str(row.get("team") or ""))
        pid = str(row.get("player_id") or "").strip()
        if not team or not pid:
            continue
        out[team] = (pid, str(row.get("player_name") or ""))
    return out


def fetch_prior_primary_qbs(session: Any, *, prior_season: int) -> Dict[str, Tuple[str, str]]:
    """Prior-season primary passer by attempts → {team: (player_id, name)}."""
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            SELECT COALESCE(team, metrics->>'team') AS team,
                   player_id,
                   MAX(player_name) AS player_name,
                   SUM(COALESCE((metrics->>'attempts')::int, 0)) AS att
            FROM nfl_dp_player_game_stats
            WHERE season = :season
              AND COALESCE((metrics->>'attempts')::int, 0) > 0
            GROUP BY 1, 2
            """
        ),
        {"season": int(prior_season)},
    ).fetchall()
    best: Dict[str, Tuple[str, str, int]] = {}
    for row in rows:
        team = normalize_team(str(getattr(row, "team", None) or row[0] or ""))
        pid = str(getattr(row, "player_id", None) or row[1] or "").strip()
        name = str(getattr(row, "player_name", None) or row[2] or "")
        att = int(getattr(row, "att", None) or row[3] or 0)
        if not team or not pid:
            continue
        cur = best.get(team)
        if cur is None or att > cur[2]:
            best[team] = (pid, name, att)
    return {t: (pid, name) for t, (pid, name, _) in best.items()}


def fetch_current_qb1(
    session: Any,
    *,
    season: int,
    as_of_week: Optional[int] = None,
) -> Dict[str, Tuple[str, str]]:
    """Current projected QB1 from packaged depth SoT (exclusive when present)."""
    from sqlalchemy import text

    week = int(as_of_week or 1)
    packaged = _load_packaged_qb1(int(season))
    if len(packaged) >= 24:
        return packaged

    # No packaged SoT — bridge from official depth only.
    out: Dict[str, Tuple[str, str]] = dict(packaged)
    try:
        rows = session.execute(
            text(
                """
                SELECT team, player_id, player_name, depth_team
                FROM nfl_dp_official_depth_charts
                WHERE season = :season AND week = :week AND position = 'QB'
                  AND depth_team = 1
                """
            ),
            {"season": int(season), "week": week},
        ).fetchall()
        for row in rows:
            team = normalize_team(str(getattr(row, "team", None) or row[0] or ""))
            pid = str(getattr(row, "player_id", None) or row[1] or "").strip()
            name = str(getattr(row, "player_name", None) or row[2] or "")
            if team and pid:
                out.setdefault(team, (pid, name))
    except Exception:
        pass
    return out


def fetch_roster_sets(
    session: Any, *, season: int
) -> Dict[str, Dict[str, str]]:
    """{team: {player_id: position}} for a season."""
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            SELECT team, player_id, position
            FROM nfl_dp_rosters
            WHERE season = :season
            """
        ),
        {"season": int(season)},
    ).fetchall()
    out: Dict[str, Dict[str, str]] = {}
    for row in rows:
        team = normalize_team(str(getattr(row, "team", None) or row[0] or ""))
        pid = str(getattr(row, "player_id", None) or row[1] or "").strip()
        pos = str(getattr(row, "position", None) or row[2] or "").strip().upper()
        if not team or not pid:
            continue
        out.setdefault(team, {})[pid] = pos
    return out


def fetch_skill_yards_by_player(
    session: Any, *, prior_season: int
) -> Dict[str, Dict[str, float]]:
    """{team: {player_id: yards}} skill production in prior season."""
    from sqlalchemy import text

    rows = session.execute(
        text(
            """
            SELECT COALESCE(team, metrics->>'team') AS team,
                   player_id,
                   UPPER(COALESCE(position, metrics->>'position', '')) AS position,
                   SUM(
                     COALESCE((metrics->>'passing_yards')::float, 0)
                     + COALESCE((metrics->>'rushing_yards')::float, 0)
                     + COALESCE((metrics->>'receiving_yards')::float, 0)
                   ) AS yards
            FROM nfl_dp_player_game_stats
            WHERE season = :season
            GROUP BY 1, 2, 3
            """
        ),
        {"season": int(prior_season)},
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for row in rows:
        team = normalize_team(str(getattr(row, "team", None) or row[0] or ""))
        pid = str(getattr(row, "player_id", None) or row[1] or "").strip()
        pos = str(getattr(row, "position", None) or row[2] or "").strip().upper()
        yards = float(getattr(row, "yards", None) or row[3] or 0.0)
        if not team or not pid or pos not in _SKILL_POS:
            continue
        if yards <= 0:
            continue
        out.setdefault(team, {})[pid] = out.get(team, {}).get(pid, 0.0) + yards
    return out


def build_team_continuity_from_inputs(
    team: str,
    *,
    prior_qb: Optional[Tuple[str, str]] = None,
    current_qb: Optional[Tuple[str, str]] = None,
    prior_qb_on_roster: Optional[bool] = None,
    staff: Optional[Mapping[str, Any]] = None,
    skill_return_share: Optional[float] = None,
    ol_return_share: Optional[float] = None,
    roster_return_share: Optional[float] = None,
    major_churn: Optional[bool] = None,
) -> TeamContinuity:
    """Pure compose path for tests + loaders."""
    prior_id = prior_qb[0] if prior_qb else None
    prior_name = prior_qb[1] if prior_qb else ""
    cur_id = current_qb[0] if current_qb else None
    cur_name = current_qb[1] if current_qb else ""

    qb_f = score_qb_factor(
        prior_qb_id=prior_id,
        prior_qb_name=prior_name,
        current_qb_id=cur_id,
        current_qb_name=cur_name,
        prior_qb_on_roster=prior_qb_on_roster,
    )

    if staff is None:
        staff_f = score_staff_factor(new_hc=None, new_oc=None)
    else:
        staff_f = score_staff_factor(
            new_hc=staff.get("new_hc"),
            new_oc=staff.get("new_oc"),
            notes=str(staff.get("notes") or ""),
            status=str(staff.get("status") or "approximate"),
        )

    ret_f = score_returning_production_factor(
        None,
        skill_share=skill_return_share,
        ol_share=ol_return_share,
    )
    churn_f = score_churn_factor(
        roster_return_share=roster_return_share,
        major_churn=major_churn,
    )
    return compose_continuity(team, [qb_f, staff_f, ret_f, churn_f])


def build_continuity_book(
    session: Any,
    *,
    season: int,
    as_of_week: Optional[int] = None,
    teams: Optional[Iterable[str]] = None,
) -> Dict[str, TeamContinuity]:
    """Build per-team continuity from roster / QB / curated staff inputs."""
    prior_season = int(season) - 1
    team_list = [normalize_team(t) for t in (teams or [])]
    try:
        prior_qbs = fetch_prior_primary_qbs(session, prior_season=prior_season)
    except Exception:
        prior_qbs = {}
    try:
        current_qbs = fetch_current_qb1(
            session, season=int(season), as_of_week=as_of_week
        )
    except Exception:
        current_qbs = _load_packaged_qb1(int(season))
    try:
        roster_prior = fetch_roster_sets(session, season=prior_season)
    except Exception:
        roster_prior = {}
    try:
        roster_curr = fetch_roster_sets(session, season=int(season))
    except Exception:
        roster_curr = {}
    try:
        skill_yards = fetch_skill_yards_by_player(session, prior_season=prior_season)
    except Exception:
        skill_yards = {}

    # Packaged HC/OC/DC book is the product SoT; curated flags backfill only.
    try:
        from src.services.nfl_season_engine.coaching_staff import (
            continuity_staff_from_packaged,
        )

        staff_book = dict(continuity_staff_from_packaged(int(season)))
    except Exception:
        staff_book = {}
    for team_key, raw in CURATED_STAFF_BY_SEASON.get(int(season), {}).items():
        if team_key not in staff_book:
            staff_book[team_key] = dict(raw)

    if not team_list:
        team_list = sorted(
            set(prior_qbs)
            | set(current_qbs)
            | set(roster_curr)
            | set(roster_prior)
            | set(staff_book)
        )

    out: Dict[str, TeamContinuity] = {}
    for team in team_list:
        prior_qb = prior_qbs.get(team)
        current_qb = current_qbs.get(team)
        curr_ids = set(roster_curr.get(team, {}))
        prior_ids = set(roster_prior.get(team, {}))
        prior_on = None
        if prior_qb:
            prior_on = prior_qb[0] in curr_ids if curr_ids else None

        # Returning skill yards share.
        skill_map = skill_yards.get(team, {})
        skill_total = sum(skill_map.values())
        skill_ret = (
            sum(y for pid, y in skill_map.items() if pid in curr_ids) / skill_total
            if skill_total > 0 and curr_ids
            else None
        )

        # OL return: prior-roster OL still on current roster.
        ol_prior = {
            pid
            for pid, pos in roster_prior.get(team, {}).items()
            if pos in _OL_POS
        }
        ol_ret = (
            len(ol_prior & curr_ids) / len(ol_prior) if ol_prior and curr_ids else None
        )

        roster_ret = (
            len(prior_ids & curr_ids) / len(prior_ids)
            if prior_ids and curr_ids
            else None
        )

        staff_raw = staff_book.get(team)
        staff = None
        if staff_raw is not None:
            # Only pass known continuity flags — never coerce missing → False/new.
            staff = {
                "notes": str(staff_raw.get("notes") or ""),
                "status": "approximate",
            }
            if staff_raw.get("new_hc") is not None:
                staff["new_hc"] = bool(staff_raw.get("new_hc"))
            if staff_raw.get("new_oc") is not None:
                staff["new_oc"] = bool(staff_raw.get("new_oc"))

        # Major churn heuristic: very low roster return.
        major = bool(roster_ret is not None and roster_ret < 0.42)

        cont = build_team_continuity_from_inputs(
            team,
            prior_qb=prior_qb,
            current_qb=current_qb,
            prior_qb_on_roster=prior_on,
            staff=staff,
            skill_return_share=skill_ret,
            ol_return_share=ol_ret,
            roster_return_share=roster_ret,
            major_churn=major if roster_ret is not None else None,
        )
        out[team] = cont
    return out


def attach_continuity_drivers(
    drivers: Dict[str, Any],
    continuity: Optional[TeamContinuity],
) -> Dict[str, Any]:
    """Merge continuity into true-PR drivers; do not clobber applied QB premium."""
    out = dict(drivers or {})
    stubs = dict(out.get("stubs") or {})
    stubs.setdefault("qb_premium", "stub_not_applied")
    if continuity is None:
        stubs["continuity"] = "stub_not_applied"
        out["stubs"] = stubs
        out["continuity"] = {
            "status": "stub_not_applied",
            "note": "continuity not applied",
        }
        return out

    if continuity.fidelity == "missing":
        stubs["continuity"] = "stub_not_applied"
    else:
        stubs["continuity"] = "applied"
    # Preserve qb_premium stub/applied status set by qb_premium layer.
    out["stubs"] = stubs
    out["continuity"] = continuity.to_drivers()
    # Surface blend travel beside existing blend block when present.
    blend = dict(out.get("blend") or {})
    blend["prior_travel_weight"] = round(float(continuity.prior_travel_weight), 4)
    blend["continuity_score"] = round(float(continuity.continuity_score), 4)
    out["blend"] = blend
    return out


def documentation() -> Dict[str, Any]:
    return {
        "layer": "continuity_score",
        "module": "src.services.nfl_season_engine.continuity_score",
        "role": "prior_travel_weight",
        "not": [
            "new_rating_scale",
            "full_qb_premium",
            "future_sos",
            "replacement_for_games_over_8_blend",
        ],
        "formula": (
            "w_current = games/8; "
            "prior_travel = 0.35 + 0.65 * continuity_score; "
            "w_prior = (1-w_current)*prior_travel; "
            "w_anchor = (1-w_current)*(1-prior_travel)"
        ),
        "factor_weights": {
            "qb": _W_QB,
            "staff": _W_STAFF,
            "returning_production": _W_RETURNING_PROD,
            "roster_churn": _W_CHURN,
        },
        "bands": {"high": f">={BAND_HIGH}", "mid": "else", "low": f"<={BAND_LOW}"},
    }
