"""Overlay player-production spine means onto Game Boxes point estimates.

Game Boxes MC medians (p50) must not silently diverge from Props ``model_mean``.
Published yards / receptions headline = spine baselines (same vector as Props).
MC p10/p90 remain research range bands.

Join must bridge nflverse abbrev baselines (``D.Maye``) to engine full names
(``Drake Maye``). If the overlay misses, do **not** stamp ``spine_version``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from src.services.nfl_player_identity import prop_player_match_keys
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


class SpineOverlayMissError(RuntimeError):
    """Raised when Game Boxes would stamp spine_version without replacing means."""

    def __init__(self, message: str, *, meta: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.meta = dict(meta or {})


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


def _index_keys_for_player(*, team: str, player_name: Any, player_uid: Any = None) -> List[str]:
    """Team-scoped identity keys — uid / full name / initial+last."""
    team_n = _norm_team(team)
    keys = prop_player_match_keys(
        player_uid=str(player_uid).strip() if player_uid else None,
        player_name=str(player_name or ""),
    )
    return [f"{team_n}|{k}" for k in keys]


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
        "error": None,
    }
    if not team_set or session is None:
        meta["error"] = "missing_session_or_teams"
        return {}, meta

    # Expand LA ↔ LAR for SQL IN.
    sql_teams = list(team_set)
    if "LA" in team_set and "LAR" not in sql_teams:
        sql_teams.append("LAR")

    try:
        # CAST AS text[] — bare ANY(:teams) silently fails under psycopg.
        rows = session.execute(
            text(
                """
                SELECT player_name, player_uid, team, position,
                       pass_yards_mean, rush_yards_mean, receiving_yards_mean,
                       receptions_mean, pass_tds_mean, rush_tds_mean, rec_tds_mean,
                       total_tds_mean,
                       pass_yards_std, rush_yards_std, receiving_yards_std, receptions_std
                FROM nfl_player_projection_baselines
                WHERE season = :season
                  AND week = :week
                  AND team = ANY(CAST(:teams AS text[]))
                """
            ),
            {"season": int(season), "week": int(week), "teams": sql_teams},
        ).fetchall()
    except Exception as exc:
        meta["error"] = f"baseline_query_failed:{type(exc).__name__}:{exc}"
        return {}, meta

    out: Dict[str, Dict[str, float]] = {}
    row_count = 0
    for row in rows or []:
        row_count += 1
        prod = production_from_baseline_row(row)
        team = _norm_team(getattr(row, "team", None))
        means = {
            "pass_yards": float(prod.pass_yards),
            "rush_yards": float(prod.rush_yards),
            "receiving_yards": float(prod.receiving_yards),
            "receptions": float(prod.receptions),
            "pass_tds": float(prod.pass_tds),
            "rush_tds": float(prod.rush_tds),
            "rec_tds": float(prod.rec_tds),
        }
        for key in _index_keys_for_player(
            team=team,
            player_name=getattr(row, "player_name", None),
            player_uid=getattr(row, "player_uid", None),
        ):
            # First writer wins — baselines should be unique per identity key.
            out.setdefault(key, means)
    meta["rows"] = row_count
    meta["index_keys"] = len(out)
    meta["ok"] = row_count > 0
    if row_count == 0:
        meta["error"] = "baseline_rows_empty"
    return out, meta


def overlay_spine_means_on_players(
    players: Sequence[MutableMapping[str, Any]],
    spine_by_key: Mapping[str, Mapping[str, float]],
) -> int:
    """Rewrite point_estimate yards/recs from spine. Returns overlay count."""
    hit = 0
    for player in players:
        team = _norm_team(player.get("team"))
        spine = None
        for key in _index_keys_for_player(
            team=team,
            player_name=player.get("player_name"),
            player_uid=player.get("player_uid") or player.get("player_id"),
        ):
            spine = spine_by_key.get(key)
            if spine:
                break
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
    *,
    require_overlay: bool = True,
) -> Dict[str, Any]:
    """Mutate game-boxes payload in place; return spine stamp meta.

    When ``require_overlay`` is True (default), raise ``SpineOverlayMissError``
    if skill players are present but none received a spine mean. Never stamp
    ``spine_version`` on a silent no-op.
    """
    season = int(payload.get("season") or 2026)
    week = int(payload.get("week") or 1)
    teams = [payload.get("home_team"), payload.get("away_team")]
    spine_by_key, meta = load_spine_means_for_game(
        session, season=season, week=week, teams=teams
    )
    players = payload.get("players") or []
    overlay_count = 0
    if isinstance(players, list) and spine_by_key:
        overlay_count = overlay_spine_means_on_players(players, spine_by_key)
    meta["overlay_count"] = int(overlay_count)

    notes = dict(payload.get("notes") or {})
    notes["spine_overlay"] = meta
    notes["yards_range"] = "mc_typical_range"

    skill_n = 0
    if isinstance(players, list):
        skill_n = sum(
            1
            for p in players
            if str(p.get("position") or "").upper() in {"QB", "RB", "WR", "TE", "FB", "HB"}
        )
    meta["skill_players"] = skill_n

    if overlay_count > 0:
        notes["spine_version"] = PRODUCTION_VERSION
        notes["spine_source"] = PRODUCTION_SOURCE
        notes["yards_headline"] = "spine_mean"
        payload["spine_version"] = PRODUCTION_VERSION
        payload["spine_source"] = PRODUCTION_SOURCE
        payload["notes"] = notes
        return meta

    # Miss path — strip any prior stamp; do not claim spine agreement.
    notes.pop("spine_version", None)
    notes.pop("spine_source", None)
    notes["yards_headline"] = "overlay_miss"
    payload.pop("spine_version", None)
    payload.pop("spine_source", None)
    payload["notes"] = notes
    meta["ok"] = False
    if meta.get("error") is None:
        meta["error"] = "overlay_count_zero"

    if require_overlay and skill_n > 0:
        raise SpineOverlayMissError(
            f"Game Boxes spine overlay missed (overlay_count=0, skill_players={skill_n}, "
            f"baseline_rows={meta.get('rows')}, error={meta.get('error')})",
            meta=meta,
        )
    return meta
