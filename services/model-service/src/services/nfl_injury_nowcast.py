from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .nfl_roster_continuity import fetch_roster_continuity_nowcast


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_team_key(name: Optional[str]) -> str:
    if not name:
        return ""
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _age_hours(updated_at: Any) -> float:
    if updated_at is None:
        return 999.0
    try:
        dt = updated_at
        if isinstance(updated_at, str):
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 3600.0)
    except Exception:
        return 999.0


def _status_weight(report_status: Optional[str]) -> float:
    raw = str(report_status or "").strip().lower()
    if not raw:
        return 0.03
    mapping = {
        "out": 1.00,
        "doubtful": 0.78,
        "questionable": 0.40,
        "limited": 0.26,
        "probable": 0.14,
        "healthy": 0.0,
    }
    if raw in mapping:
        return mapping[raw]
    if "injured reserve" in raw or raw == "ir":
        return 0.92
    if "questionable" in raw:
        return 0.40
    if "doubtful" in raw:
        return 0.78
    return 0.10


def _practice_weight(practice_status: Optional[str]) -> float:
    raw = str(practice_status or "").strip().lower()
    if not raw:
        return 0.08
    if "did not participate" in raw or raw == "dnp":
        return 1.0
    if "limited" in raw:
        return 0.58
    if "full" in raw:
        return 0.08
    return 0.20


def _position_weights(position: Optional[str]) -> Dict[str, float]:
    p = str(position or "").strip().upper()
    if p == "QB":
        return {"offense": 1.0, "defense": 0.0}
    if p in {"WR", "RB", "TE"}:
        return {"offense": 0.64, "defense": 0.0}
    if p in {"LT", "LG", "C", "RG", "RT", "OL"}:
        return {"offense": 0.54, "defense": 0.0}
    if p in {"DE", "DT", "DL", "EDGE"}:
        return {"offense": 0.0, "defense": 0.62}
    if p in {"LB", "CB", "S", "DB"}:
        return {"offense": 0.0, "defense": 0.52}
    if p in {"K", "P"}:
        return {"offense": 0.12, "defense": 0.0}
    return {"offense": 0.28, "defense": 0.24}


def _injury_severity_weight(injury: Optional[str]) -> float:
    raw = str(injury or "").lower()
    if not raw:
        return 0.0
    if "acl" in raw or "achilles" in raw:
        return 0.35
    if "concussion" in raw:
        return 0.26
    if "hamstring" in raw or "quad" in raw:
        return 0.18
    if "ankle" in raw or "knee" in raw:
        return 0.16
    if "shoulder" in raw or "elbow" in raw:
        return 0.14
    return 0.08


def _freshness_multiplier(age_hours: float) -> float:
    half_life = max(1.0, _safe_float(os.getenv("NFL_INJURY_HALFLIFE_HOURS"), 18.0))
    stale_hours = max(1.0, _safe_float(os.getenv("NFL_INJURY_STALE_HOURS"), 72.0))
    stale_floor = _clamp(_safe_float(os.getenv("NFL_INJURY_STALE_FLOOR"), 0.05), 0.0, 1.0)
    decay = math.pow(0.5, max(0.0, age_hours) / half_life)
    if age_hours > stale_hours:
        decay = min(decay, stale_floor)
    return _clamp(decay, stale_floor, 1.0)


def _report_severity_rank(report_status: Optional[str]) -> float:
    """Higher = worse availability. Used for upgrade/downgrade deltas."""
    return _status_weight(report_status)


def _practice_severity_rank(practice_status: Optional[str]) -> float:
    return _practice_weight(practice_status)


def compute_player_status_delta(
    *,
    prior_report: Optional[str],
    prior_practice: Optional[str],
    current_report: Optional[str],
    current_practice: Optional[str],
    position: Optional[str] = None,
) -> Dict[str, Any]:
    """Pure upgrade/downgrade delta for one player between two report snapshots.

    Positive delta_severity = downgrade (worse news). Negative = upgrade.
    """
    prior_sev = 0.7 * _report_severity_rank(prior_report) + 0.3 * _practice_severity_rank(prior_practice)
    curr_sev = 0.7 * _report_severity_rank(current_report) + 0.3 * _practice_severity_rank(current_practice)
    raw_delta = curr_sev - prior_sev
    pos_w = _position_weights(position)
    importance = max(pos_w["offense"], pos_w["defense"], 0.15)
    weighted = raw_delta * importance
    direction = "stable"
    if weighted > 0.04:
        direction = "downgrade"
    elif weighted < -0.04:
        direction = "upgrade"
    return {
        "direction": direction,
        "delta_severity": round(raw_delta, 4),
        "weighted_delta": round(weighted, 4),
        "importance": round(importance, 4),
    }


def compute_team_info_velocity(
    current_rows: List[Dict[str, Any]],
    prior_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Team-level injury/practice information velocity from week-over-week rows.

    Net velocity > 0 means net downgrades (worse availability). Bounded.
    hours_since_change uses freshest updated_at among changed players.
    """
    prior_by_key = {
        str(r.get("player_key") or r.get("player_id") or r.get("player_name") or ""): r
        for r in prior_rows
        if (r.get("player_key") or r.get("player_id") or r.get("player_name"))
    }
    upgrades = 0
    downgrades = 0
    net_weighted = 0.0
    hours_since_change: Optional[float] = None
    change_drivers: List[Dict[str, Any]] = []

    for row in current_rows:
        key = str(row.get("player_key") or row.get("player_id") or row.get("player_name") or "")
        if not key:
            continue
        prior = prior_by_key.get(key)
        if prior is None:
            # New listing vs prior week ≈ mild downgrade signal.
            delta = compute_player_status_delta(
                prior_report="healthy",
                prior_practice="full",
                current_report=row.get("report_status"),
                current_practice=row.get("practice_status"),
                position=row.get("position"),
            )
        else:
            delta = compute_player_status_delta(
                prior_report=prior.get("report_status"),
                prior_practice=prior.get("practice_status"),
                current_report=row.get("report_status"),
                current_practice=row.get("practice_status"),
                position=row.get("position"),
            )
        if delta["direction"] == "stable":
            continue
        if delta["direction"] == "upgrade":
            upgrades += 1
        else:
            downgrades += 1
        net_weighted += float(delta["weighted_delta"])
        age = _age_hours(row.get("updated_at"))
        if hours_since_change is None or age < hours_since_change:
            hours_since_change = age
        change_drivers.append(
            {
                "player_name": row.get("player_name"),
                "position": row.get("position"),
                "direction": delta["direction"],
                "weighted_delta": delta["weighted_delta"],
                "hours_since_update": round(age, 3) if age < 999 else None,
            }
        )

    # Removals from prior week (cleared) ≈ upgrade.
    curr_keys = {
        str(r.get("player_key") or r.get("player_id") or r.get("player_name") or "")
        for r in current_rows
    }
    for key, prior in prior_by_key.items():
        if key in curr_keys:
            continue
        delta = compute_player_status_delta(
            prior_report=prior.get("report_status"),
            prior_practice=prior.get("practice_status"),
            current_report="healthy",
            current_practice="full",
            position=prior.get("position"),
        )
        if delta["direction"] == "upgrade":
            upgrades += 1
            net_weighted += float(delta["weighted_delta"])
            change_drivers.append(
                {
                    "player_name": prior.get("player_name"),
                    "position": prior.get("position"),
                    "direction": "upgrade",
                    "weighted_delta": delta["weighted_delta"],
                    "hours_since_update": None,
                }
            )

    velocity_score = _clamp(net_weighted, -2.5, 2.5)
    change_drivers = sorted(change_drivers, key=lambda d: abs(float(d["weighted_delta"])), reverse=True)[:5]
    return {
        "velocity_score": round(velocity_score, 4),
        "upgrade_count": upgrades,
        "downgrade_count": downgrades,
        "change_count": upgrades + downgrades,
        "hours_since_change": round(hours_since_change, 3) if hours_since_change is not None else None,
        "top_change_drivers": change_drivers,
        "available": bool(current_rows or prior_rows),
    }


def _aggregate_team_nowcast(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "injury_count": 0,
            "freshness_hours": None,
            "freshness_multiplier": 0.0,
            "confidence": 0.0,
            "offense_multiplier": 1.0,
            "defense_multiplier": 1.0,
            "impact_score": 0.0,
            "top_drivers": [],
        }

    # Calibrated against real team-week distributions (2013-2025, ~9,600
    # team-weeks) *after* fixing position weighting (see
    # compute_team_week_injury_severity / the nfl_dp_rosters position join
    # in fetch_nfl_injury_nowcast) -- before that fix, every player fell
    # back to a generic weight and these ceilings were tuned for numbers
    # roughly 2x smaller than what position-aware weighting actually
    # produces, so most team-weeks were saturating near 1.0 and the score
    # barely discriminated. p95 offense_raw ~= 2.2, p95 defense_raw ~= 1.85.
    max_raw_offense = max(0.01, _safe_float(os.getenv("NFL_INJURY_MAX_RAW_OFFENSE"), 2.5))
    max_raw_defense = max(0.01, _safe_float(os.getenv("NFL_INJURY_MAX_RAW_DEFENSE"), 2.2))
    impact_scale = _clamp(_safe_float(os.getenv("NFL_INJURY_IMPACT_SCALE"), 0.09), 0.01, 0.25)
    confidence_scale = _clamp(_safe_float(os.getenv("NFL_INJURY_CONFIDENCE_SCALE"), 0.9), 0.1, 1.5)
    min_rows_for_conf = max(1.0, _safe_float(os.getenv("NFL_INJURY_ROWS_FOR_FULL_CONFIDENCE"), 14.0))

    offense_raw = 0.0
    defense_raw = 0.0
    freshest = 999.0
    drivers: List[Dict[str, Any]] = []
    for row in rows:
        status_weight = _status_weight(row.get("report_status"))
        practice_weight = _practice_weight(row.get("practice_status"))
        position_weights = _position_weights(row.get("position"))
        injury_weight = _injury_severity_weight(row.get("injury"))
        player_impact = _clamp(
            (0.62 * status_weight) + (0.23 * practice_weight) + (0.15 * injury_weight),
            0.0,
            1.0,
        )
        offense_raw += player_impact * position_weights["offense"]
        defense_raw += player_impact * position_weights["defense"]
        age = _age_hours(row.get("updated_at"))
        freshest = min(freshest, age)
        drivers.append(
            {
                "player_name": row.get("player_name"),
                "position": row.get("position"),
                "report_status": row.get("report_status"),
                "practice_status": row.get("practice_status"),
                "impact": round(player_impact, 4),
            }
        )

    freshness = _freshness_multiplier(freshest if freshest < 999.0 else 999.0)
    data_density = _clamp(len(rows) / min_rows_for_conf, 0.0, 1.0)
    confidence = _clamp(freshness * (0.35 + (0.65 * data_density)), 0.0, 1.0)
    offense_penalty = _clamp(offense_raw / max_raw_offense, 0.0, 1.0) * impact_scale * confidence_scale
    defense_penalty = _clamp(defense_raw / max_raw_defense, 0.0, 1.0) * impact_scale * confidence_scale

    offense_multiplier = _clamp(1.0 - (offense_penalty * confidence), 0.82, 1.04)
    # Higher defense_index means weaker defense in this simulator.
    defense_multiplier = _clamp(1.0 + (defense_penalty * confidence), 0.92, 1.18)
    impact_score = _clamp((offense_penalty + defense_penalty) * 0.5, 0.0, 1.0)

    drivers = sorted(drivers, key=lambda item: float(item["impact"]), reverse=True)[:5]
    return {
        "injury_count": len(rows),
        "freshness_hours": round(freshest, 3) if freshest < 999.0 else None,
        "freshness_multiplier": round(freshness, 4),
        "confidence": round(confidence, 4),
        "offense_multiplier": round(offense_multiplier, 4),
        "defense_multiplier": round(defense_multiplier, 4),
        "impact_score": round(impact_score, 4),
        "top_drivers": drivers,
    }


def _merge_roster_continuity_into_nowcast(
    nowcast: Dict[str, Any],
    continuity: Dict[str, Any],
) -> Dict[str, Any]:
    """Compose a live injury-report nowcast with the roster-continuity
    nowcast (see nfl_roster_continuity.py) by multiplying the two
    multiplier pairs together -- both are centered on 1.0, so a team with
    no roster-continuity entries (the common case) gets back exactly the
    original in-season nowcast untouched, and a team with no live injury
    rows (e.g. the 2026 preseason, before any weekly injury report
    exists) gets back exactly the roster-continuity nowcast.
    """
    if int(continuity.get("adjustment_count") or 0) <= 0:
        return nowcast

    merged_offense = _clamp(
        float(nowcast.get("offense_multiplier", 1.0)) * float(continuity.get("offense_multiplier", 1.0)),
        0.82,
        1.08,
    )
    merged_defense = _clamp(
        float(nowcast.get("defense_multiplier", 1.0)) * float(continuity.get("defense_multiplier", 1.0)),
        0.90,
        1.18,
    )
    merged_confidence = _clamp(
        max(float(nowcast.get("confidence", 0.0)), float(continuity.get("confidence", 0.0))),
        0.0,
        1.0,
    )
    merged_impact = _clamp(
        float(nowcast.get("impact_score", 0.0)) + float(continuity.get("impact_score", 0.0)),
        0.0,
        1.0,
    )
    merged_drivers = sorted(
        list(nowcast.get("top_drivers") or []) + list(continuity.get("top_drivers") or []),
        key=lambda item: abs(_safe_float(item.get("impact", item.get("impact_score")))),
        reverse=True,
    )[:5]

    merged = dict(nowcast)
    merged.update(
        {
            "offense_multiplier": round(merged_offense, 4),
            "defense_multiplier": round(merged_defense, 4),
            "confidence": round(merged_confidence, 4),
            "impact_score": round(merged_impact, 4),
            "top_drivers": merged_drivers,
            "roster_continuity_adjustment_count": int(continuity.get("adjustment_count") or 0),
        }
    )
    return merged


def compute_team_week_injury_severity(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """Position+status-weighted injury severity for a single team-week, with
    no freshness decay. Used for historical training features, where
    `updated_at` reflects our ingestion time rather than the original report
    time, so the live nowcast's recency decay (see `_aggregate_team_nowcast`)
    would be meaningless here. Shares the same status/position/severity
    weighting as the live path so training and inference stay consistent."""
    if not rows:
        return {"offense_impact": 0.0, "defense_impact": 0.0, "injury_count": 0.0}

    max_raw_offense = max(0.01, _safe_float(os.getenv("NFL_INJURY_MAX_RAW_OFFENSE"), 2.5))
    max_raw_defense = max(0.01, _safe_float(os.getenv("NFL_INJURY_MAX_RAW_DEFENSE"), 2.2))
    offense_raw = 0.0
    defense_raw = 0.0
    for row in rows:
        status_weight = _status_weight(row.get("report_status"))
        practice_weight = _practice_weight(row.get("practice_status"))
        position_weights = _position_weights(row.get("position"))
        injury_weight = _injury_severity_weight(row.get("injury"))
        player_impact = _clamp(
            (0.62 * status_weight) + (0.23 * practice_weight) + (0.15 * injury_weight),
            0.0,
            1.0,
        )
        offense_raw += player_impact * position_weights["offense"]
        defense_raw += player_impact * position_weights["defense"]

    offense_impact = _clamp(offense_raw / max_raw_offense, 0.0, 1.0)
    defense_impact = _clamp(defense_raw / max_raw_defense, 0.0, 1.0)
    return {
        "offense_impact": round(offense_impact, 4),
        "defense_impact": round(defense_impact, 4),
        # Matches the live nowcast's "impact_score" shape (see
        # _aggregate_team_nowcast) so training features and live-inference
        # features are computed the same way and don't skew apart.
        "impact_score": round(_clamp((offense_impact + defense_impact) * 0.5, 0.0, 1.0), 4),
        "injury_count": float(len(rows)),
    }


def _fetch_injury_rows_for_week(
    session: Any,
    *,
    season: int,
    home_team: str,
    away_team: str,
    week: Optional[int],
) -> List[Dict[str, Any]]:
    """Fetch injury rows for a specific week (or latest per player when week is None)."""
    if week is None:
        sql = """
            WITH latest AS (
              SELECT DISTINCT ON (i.team, i.player_key)
                i.season, i.week, i.team, i.player_key, i.player_id, i.player_name,
                i.report_status, i.practice_status, i.injury, i.updated_at
              FROM nfl_dp_injuries i
              WHERE i.season = :season
                AND (i.team = :home_team OR i.team = :away_team)
              ORDER BY i.team, i.player_key, i.week DESC, i.updated_at DESC
            )
            SELECT
              latest.season, latest.week, latest.team, latest.player_key, latest.player_name,
              latest.report_status, latest.practice_status, latest.injury, latest.updated_at,
              r.position
            FROM latest
            LEFT JOIN nfl_dp_rosters r
              ON r.season = latest.season
             AND r.team = latest.team
             AND r.player_id = latest.player_id
            """
        params: Dict[str, Any] = {
            "season": season,
            "home_team": home_team,
            "away_team": away_team,
        }
    else:
        sql = """
            SELECT
              i.season, i.week, i.team, i.player_key, i.player_name,
              i.report_status, i.practice_status, i.injury, i.updated_at,
              r.position
            FROM nfl_dp_injuries i
            LEFT JOIN nfl_dp_rosters r
              ON r.season = i.season
             AND r.team = i.team
             AND r.player_id = i.player_id
            WHERE i.season = :season
              AND i.week = :week
              AND (i.team = :home_team OR i.team = :away_team)
            """
        params = {
            "season": season,
            "week": int(week),
            "home_team": home_team,
            "away_team": away_team,
        }
    rows = session.execute(text(sql), params).fetchall()
    return [dict(row._mapping) for row in rows]


def fetch_nfl_injury_nowcast(
    session: Any,
    *,
    season_year: Optional[int],
    home_team: str,
    away_team: str,
) -> Dict[str, Any]:
    season = int(season_year) if season_year is not None else datetime.now(timezone.utc).year
    injury_rows = _fetch_injury_rows_for_week(
        session,
        season=season,
        home_team=home_team,
        away_team=away_team,
        week=None,
    )
    home_key = _normalize_team_key(home_team)
    away_key = _normalize_team_key(away_team)

    home_rows = [
        row
        for row in injury_rows
        if _normalize_team_key(str(row.get("team") or "")) == home_key
    ]
    away_rows = [
        row
        for row in injury_rows
        if _normalize_team_key(str(row.get("team") or "")) == away_key
    ]
    home_nowcast = _aggregate_team_nowcast(home_rows)
    away_nowcast = _aggregate_team_nowcast(away_rows)

    # Info velocity: compare latest week vs prior week listings (same season).
    latest_weeks = [int(r["week"]) for r in injury_rows if r.get("week") is not None]
    as_of_week = max(latest_weeks) if latest_weeks else None
    prior_week = (as_of_week - 1) if as_of_week is not None and as_of_week > 1 else None
    prior_rows: List[Dict[str, Any]] = []
    if prior_week is not None:
        try:
            prior_rows = _fetch_injury_rows_for_week(
                session,
                season=season,
                home_team=home_team,
                away_team=away_team,
                week=prior_week,
            )
        except Exception:
            prior_rows = []

    home_prior = [
        row
        for row in prior_rows
        if _normalize_team_key(str(row.get("team") or "")) == home_key
    ]
    away_prior = [
        row
        for row in prior_rows
        if _normalize_team_key(str(row.get("team") or "")) == away_key
    ]
    home_velocity = compute_team_info_velocity(home_rows, home_prior)
    away_velocity = compute_team_info_velocity(away_rows, away_prior)
    home_nowcast["info_velocity"] = home_velocity
    away_nowcast["info_velocity"] = away_velocity
    home_nowcast["info_velocity_score"] = home_velocity.get("velocity_score")
    away_nowcast["info_velocity_score"] = away_velocity.get("velocity_score")
    home_nowcast["hours_since_change"] = home_velocity.get("hours_since_change")
    away_nowcast["hours_since_change"] = away_velocity.get("hours_since_change")

    # Layer in known offseason roster moves (see nfl_roster_continuity.py)
    # -- e.g. a season-long free-agency/trade departure that the current
    # week's injury report has no way to reflect, since the player simply
    # isn't on the team anymore rather than being listed as questionable.
    # This is a no-op multiply-by-1.0 for the (common) case of a team with
    # no curated roster-continuity entries for the season.
    home_continuity = fetch_roster_continuity_nowcast(session, season_year=season, team=home_team)
    away_continuity = fetch_roster_continuity_nowcast(session, season_year=season, team=away_team)
    home_nowcast = _merge_roster_continuity_into_nowcast(home_nowcast, home_continuity)
    away_nowcast = _merge_roster_continuity_into_nowcast(away_nowcast, away_continuity)

    game_confidence = round(
        _clamp(
            (float(home_nowcast["confidence"]) + float(away_nowcast["confidence"])) / 2.0,
            0.0,
            1.0,
        ),
        4,
    )
    source = "nfl_dp_injuries"
    has_continuity = bool(home_nowcast.get("roster_continuity_adjustment_count") or away_nowcast.get("roster_continuity_adjustment_count"))
    if has_continuity:
        source = "nfl_dp_injuries+roster_continuity"
    return {
        "season_year": season,
        "source": source,
        "home_team": home_team,
        "away_team": away_team,
        "home": home_nowcast,
        "away": away_nowcast,
        "game_confidence": game_confidence,
        "info_velocity_as_of_week": as_of_week,
        "info_velocity_prior_week": prior_week,
    }

