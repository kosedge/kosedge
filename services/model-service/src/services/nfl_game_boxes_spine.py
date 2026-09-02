"""Overlay player-production spine means onto Game Boxes point estimates.

Game Boxes MC medians (p50) must not silently diverge from Props ``model_mean``.
Published yards / receptions headline = spine baselines (same vector as Props).
MC p10/p90 remain research range bands.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence, Tuple

from src.services.nfl_player_production import (
    PRODUCTION_SOURCE,
    PRODUCTION_VERSION,
    production_from_baseline_row,
)

# Season-engine box keys → baseline / spine fields (yards + receptions only).
# TD headlines stay P(TD) from MC; do not overwrite with raw TD means.
_SPINE_STAT_MAP = {
    "pass_yards": "pass_yards",
    "rush_yards": "rush_yards",
    "rec_yards": "receiving_yards",
    "receptions": "receptions",
}


def _norm_team(abbr: Any) -> str:
    token = str(abbr or "").strip().upper()
    if token in {"LAR", "LA"}:
        return "LA"
    if token == "AZ":
        return "ARI"
    if token == "WSH":
        return "WAS"
    if token == "JAC":
        return "JAX"
    return token


def _name_key(name: Any) -> str:
    return " ".join(str(name or "").strip().lower().split())


def load_spine_means_for_game(
    session: Any,
    *,
    season: int,
    week: int,
    teams: Sequence[str],
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Any]]:
    """Load baseline means for teams in a matchup. Returns (by_key, meta)."""
    from sqlalchemy import text

    team_set = sorted({_norm_team(t) for t in teams if t})
    meta: Dict[str, Any] = {
        "spine_version": PRODUCTION_VERSION,
        "spine_source": PRODUCTION_SOURCE,
        "season": int(season),
        "week": int(week),
        "teams": team_set,
        "rows": 0,
        "ok": False,
    }
    if not team_set or session is None:
        return {}, meta

    # Expand LA ↔ LAR for SQL IN.
    sql_teams = list(team_set)
    if "LA" in team_set and "LAR" not in sql_teams:
        sql_teams.append("LAR")

    try:
        rows = session.execute(
            text(
                """
                SELECT player_name, team, position,
                       pass_yards_mean, rush_yards_mean, receiving_yards_mean,
                       receptions_mean, pass_tds_mean, rush_tds_mean, rec_tds_mean,
                       total_tds_mean,
                       pass_yards_std, rush_yards_std, receiving_yards_std, receptions_std
                FROM nfl_player_projection_baselines
                WHERE season = :season
                  AND week = :week
                  AND team = ANY(:teams)
                """
            ),
            {"season": int(season), "week": int(week), "teams": sql_teams},
        ).fetchall()
    except Exception:
        return {}, meta

    out: Dict[str, Dict[str, float]] = {}
    for row in rows or []:
        prod = production_from_baseline_row(row)
        team = _norm_team(getattr(row, "team", None))
        key = f"{team}|{_name_key(getattr(row, 'player_name', None))}"
        out[key] = {
            "pass_yards": float(prod.pass_yards),
            "rush_yards": float(prod.rush_yards),
            "receiving_yards": float(prod.receiving_yards),
            "receptions": float(prod.receptions),
            "pass_tds": float(prod.pass_tds),
            "rush_tds": float(prod.rush_tds),
            "rec_tds": float(prod.rec_tds),
        }
    meta["rows"] = len(out)
    meta["ok"] = len(out) > 0
    return out, meta


def overlay_spine_means_on_players(
    players: Sequence[MutableMapping[str, Any]],
    spine_by_key: Mapping[str, Mapping[str, float]],
) -> int:
    """Rewrite point_estimate yards/recs from spine. Returns overlay count."""
    hit = 0
    for player in players:
        team = _norm_team(player.get("team"))
        key = f"{team}|{_name_key(player.get('player_name'))}"
        spine = spine_by_key.get(key)
        if not spine:
            continue
        point = dict(player.get("point_estimate") or {})
        dists = player.get("distributions") or {}
        changed = False
        for box_stat, spine_field in _SPINE_STAT_MAP.items():
            if box_stat not in point and box_stat not in dists:
                continue
            val = spine.get(spine_field)
            if val is None:
                continue
            point[box_stat] = float(val)
            # Align distribution mean so mean-preferring UI matches Props.
            dist = dists.get(box_stat)
            if isinstance(dist, dict):
                dist["mean"] = float(val)
            changed = True
        if changed:
            player["point_estimate"] = point
            player["spine_version"] = PRODUCTION_VERSION
            player["spine_source"] = PRODUCTION_SOURCE
            hit += 1
    return hit


def apply_spine_overlay_to_game_boxes_payload(
    payload: MutableMapping[str, Any],
    session: Any,
) -> Dict[str, Any]:
    """Mutate game-boxes payload in place; return spine stamp meta."""
    season = int(payload.get("season") or 2026)
    week = int(payload.get("week") or 1)
    teams = [payload.get("home_team"), payload.get("away_team")]
    spine_by_key, meta = load_spine_means_for_game(
        session, season=season, week=week, teams=teams
    )
    players = payload.get("players") or []
    if isinstance(players, list) and spine_by_key:
        meta["overlay_count"] = overlay_spine_means_on_players(players, spine_by_key)
    else:
        meta["overlay_count"] = 0

    notes = dict(payload.get("notes") or {})
    notes["spine_version"] = PRODUCTION_VERSION
    notes["spine_source"] = PRODUCTION_SOURCE
    notes["yards_headline"] = "spine_mean"
    notes["yards_range"] = "mc_typical_range"
    notes["spine_overlay"] = meta
    payload["notes"] = notes
    payload["spine_version"] = PRODUCTION_VERSION
    payload["spine_source"] = PRODUCTION_SOURCE
    return meta
