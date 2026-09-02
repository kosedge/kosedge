"""Overlay player-production spine means onto Game Boxes point estimates.

Game Boxes MC medians (p50) must not silently diverge from Props ``model_mean``.
Published yards / receptions headline = spine baselines (same vector as Props).
When the overlay rewrites a dist mean, MC p10/p50/p90 are location-shifted so
the typical range (p10–p90) still contains the spine mean.

Join must bridge nflverse abbrev baselines (``D.Maye``) to engine full names
(``Drake Maye``) and box ``player_key`` (``NE-QB1-DrakeMaye``). If the overlay
misses, do **not** stamp ``spine_version``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from src.services.nfl_player_identity import prop_player_match_keys
from src.services.nfl_player_production import (
    PRODUCTION_SOURCE,
    PRODUCTION_VERSION,
    production_from_baseline_row,
)

# ≈ Φ⁻¹(0.9) — rebuild p10/p90 from mean±z·std when a shifted band is still inconsistent.
_NORM_P90_Z = 1.2815515655446004

# Season-engine box keys → baseline / spine fields (yards + receptions only).
# TD headlines stay P(TD) from MC; do not overwrite with raw TD means.
_SPINE_STAT_MAP = {
    "pass_yards": "pass_yards",
    "rush_yards": "rush_yards",
    "rec_yards": "receiving_yards",
    "receptions": "receptions",
}

_MARKET_TO_SPINE = {
    "pass_yds": "pass_yards",
    "rush_yds": "rush_yards",
    "rec_yds": "receiving_yards",
    "receptions": "receptions",
}

# Compact engine keys: NE-QB1-DrakeMaye → "Drake Maye"
_PLAYER_KEY_RE = re.compile(
    r"^(?P<team>[A-Z]{2,3})-(?P<slot>[A-Z]{1,3}\d+)-(?P<name>.+)$"
)


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


def name_from_player_key(player_key: Any) -> Optional[str]:
    """Parse season-engine player_key ``NE-QB1-DrakeMaye`` → ``Drake Maye``."""
    raw = str(player_key or "").strip()
    if not raw:
        return None
    m = _PLAYER_KEY_RE.match(raw)
    if not m:
        return None
    compact = m.group("name")
    # Insert spaces before internal capitals: DrakeMaye → Drake Maye
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", compact)
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    return " ".join(spaced.split()) or None


def _index_keys_for_player(
    *,
    team: str,
    player_name: Any,
    player_uid: Any = None,
    player_key: Any = None,
) -> List[str]:
    """Team-scoped identity keys — uid / full name / initial+last / player_key."""
    team_n = _norm_team(team)
    names: List[str] = []
    primary = str(player_name or "").strip()
    if primary:
        names.append(primary)
    from_key = name_from_player_key(player_key)
    if from_key and from_key.lower() not in {n.lower() for n in names}:
        names.append(from_key)

    out: List[str] = []
    seen: set[str] = set()

    def _add(key: str) -> None:
        if key and key not in seen:
            seen.add(key)
            out.append(key)

    if player_key:
        _add(f"{team_n}|pk:{str(player_key).strip()}")

    for name in names:
        for k in prop_player_match_keys(
            player_uid=str(player_uid).strip() if player_uid else None,
            player_name=name,
        ):
            _add(f"{team_n}|{k}")
    # uid alone once if present and names empty
    if not names and player_uid:
        for k in prop_player_match_keys(
            player_uid=str(player_uid).strip(),
            player_name=None,
        ):
            _add(f"{team_n}|{k}")
    return out


def _index_means(
    out: Dict[str, Dict[str, float]],
    *,
    team: str,
    player_name: Any,
    player_uid: Any = None,
    means: Mapping[str, float],
) -> None:
    payload = dict(means)
    for key in _index_keys_for_player(
        team=team, player_name=player_name, player_uid=player_uid
    ):
        out.setdefault(key, payload)
    # Also index synthetic player_key forms used by season-engine boxes.
    name = str(player_name or "").strip()
    if name:
        compact = name.replace(" ", "")
        team_n = _norm_team(team)
        # Depth unknown — index last-token variants for pk lookup via name parse.
        for slot in ("QB1", "RB1", "WR1", "TE1", "FB1", "HB1"):
            pk = f"{team_n}-{slot}-{compact}"
            out.setdefault(f"{team_n}|pk:{pk}", payload)


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
        "source": None,
    }
    if not team_set or session is None:
        meta["error"] = "missing_session_or_teams"
        return {}, meta

    # Expand LA ↔ LAR for SQL IN.
    sql_teams = list(team_set)
    if "LA" in team_set and "LAR" not in sql_teams:
        sql_teams.append("LAR")

    out: Dict[str, Dict[str, float]] = {}
    row_count = 0

    try:
        # Baselines have pass/rush/rec_tds_mean — NOT total_tds_mean (box sims only).
        # CAST AS text[] — bare ANY(:teams) returns 0 rows under psycopg (live FAIL).
        rows = session.execute(
            text(
                """
                SELECT player_name, player_uid, team, position,
                       pass_yards_mean, rush_yards_mean, receiving_yards_mean,
                       receptions_mean, pass_tds_mean, rush_tds_mean, rec_tds_mean,
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
        try:
            session.rollback()
        except Exception:
            pass
        rows = []

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
        _index_means(
            out,
            team=team,
            player_name=getattr(row, "player_name", None),
            player_uid=getattr(row, "player_uid", None),
            means=means,
        )

    # Fallback: props edges already hold the published spine mean (Maye 216.2).
    if row_count == 0:
        try:
            edge_rows = session.execute(
                text(
                    """
                    SELECT player_name, player_uid, team, market_key, model_mean
                    FROM nfl_player_prop_model_edges
                    WHERE season = :season
                      AND week = :week
                      AND team = ANY(CAST(:teams AS text[]))
                      AND market_key = ANY(CAST(:markets AS text[]))
                    """
                ),
                {
                    "season": int(season),
                    "week": int(week),
                    "teams": sql_teams,
                    "markets": list(_MARKET_TO_SPINE.keys()),
                },
            ).fetchall()
        except Exception as exc:
            try:
                session.rollback()
            except Exception:
                pass
            meta["error"] = (
                f"{meta.get('error') or 'baseline_empty'};"
                f"props_edges_fallback_failed:{type(exc).__name__}:{exc}"
            )
            edge_rows = []

        # Sparse means only — never seed missing markets at 0.0 (that would
        # wipe live box yards/recs for stats not present in props edges).
        by_player: Dict[Tuple[str, str], Dict[str, float]] = {}
        uids: Dict[Tuple[str, str], Optional[str]] = {}
        for erow in edge_rows or []:
            team = _norm_team(getattr(erow, "team", None))
            name = str(getattr(erow, "player_name", None) or "")
            market = str(getattr(erow, "market_key", None) or "")
            field = _MARKET_TO_SPINE.get(market)
            if not field or not name:
                continue
            key = (team, name)
            try:
                by_player.setdefault(key, {})[field] = float(getattr(erow, "model_mean"))
            except (TypeError, ValueError):
                continue
            uid = getattr(erow, "player_uid", None)
            if uid is not None:
                uids[key] = str(uid)

        for (team, name), means in by_player.items():
            if not means:
                continue
            row_count += 1
            _index_means(
                out,
                team=team,
                player_name=name,
                player_uid=uids.get((team, name)),
                means=means,
            )
        if row_count > 0:
            meta["source"] = "nfl_player_prop_model_edges"
            meta["error"] = None
        elif meta.get("error") is None:
            meta["error"] = "baseline_rows_empty"
    else:
        meta["source"] = "nfl_player_projection_baselines"

    meta["rows"] = row_count
    meta["index_keys"] = len(out)
    meta["ok"] = row_count > 0
    return out, meta


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:  # NaN
        return None
    return out


def _rebuild_band_from_mean_std(dist: MutableMapping[str, Any], mean: float) -> None:
    """Rebuild p10/p50/p90 from mean + dist.std (fallback half-width if std missing)."""
    std = _as_float(dist.get("std"))
    if std is not None and std > 0:
        half = _NORM_P90_Z * std
    else:
        p10 = _as_float(dist.get("p10"))
        p90 = _as_float(dist.get("p90"))
        if p10 is not None and p90 is not None and p90 > p10:
            half = 0.5 * (p90 - p10)
        else:
            half = max(abs(mean) * 0.25, 1.0)
    dist["p10"] = max(0.0, mean - half)
    dist["p50"] = max(0.0, mean)
    dist["p90"] = max(0.0, mean + half)


def realign_distribution_to_overlay_mean(
    dist: MutableMapping[str, Any],
    new_mean: float,
) -> None:
    """Keep typical-range percentiles consistent with an overlayed spine mean.

    Location-shifts existing MC p10/p50/p90 by ``new_mean - old_anchor`` so the
    research band width/skew is preserved while ``p10 ≤ mean ≤ p90``. If the
    band is still inconsistent (or percentiles are missing), rebuild from std.
    """
    mean = float(new_mean)
    old_anchor = _as_float(dist.get("mean"))
    if old_anchor is None:
        old_anchor = _as_float(dist.get("p50"))

    dist["mean"] = mean

    if old_anchor is not None and abs(mean - old_anchor) > 1e-12:
        delta = mean - old_anchor
        for key in ("p10", "p50", "p90"):
            cur = _as_float(dist.get(key))
            if cur is None:
                continue
            dist[key] = max(0.0, cur + delta)

    p10 = _as_float(dist.get("p10"))
    p50 = _as_float(dist.get("p50"))
    p90 = _as_float(dist.get("p90"))

    # Missing band or mean outside p10–p90 → rebuild so UI "typical range" holds.
    needs_rebuild = p10 is None or p90 is None or not (p10 <= mean <= p90)
    if needs_rebuild:
        _rebuild_band_from_mean_std(dist, mean)
        return

    if p50 is None:
        dist["p50"] = max(0.0, mean)
    elif not (p10 <= p50 <= p90):
        dist["p50"] = max(0.0, min(p90, max(p10, mean)))


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
            player_key=player.get("player_key"),
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
            # Absent key = market never loaded; do not treat as 0.0 overwrite.
            if spine_field not in spine:
                continue
            val = spine[spine_field]
            if val is None:
                continue
            point[box_stat] = float(val)
            # Align dist mean + typical-range percentiles with Props spine mean.
            dist = dists.get(box_stat)
            if isinstance(dist, dict):
                realign_distribution_to_overlay_mean(dist, float(val))
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
    # MC width/skew preserved; percentiles location-shifted onto spine mean.
    notes["yards_range"] = "mc_typical_range_spine_anchored"

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
