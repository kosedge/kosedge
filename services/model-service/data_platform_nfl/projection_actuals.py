"""Season-to-date actuals for the Projections Hub (Projected | Actual).

Pure aggregation + DB loaders. Writes the ops JSON consumed by
`apps/web/lib/nfl-projection-actuals.ts`.

Team wins: REG weeks 1–18 final scores from `nfl_dp_schedules`.
Player stats: REG rows from `nfl_dp_player_game_stats.metrics` (nflverse),
keyed by resolved `player_uid` when identity map exists, else gsis id /
`team:player_id` aliases so the hub can match projection `player_key`s.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

REG_WEEK_MAX = 18


def empty_bundle(season: int, *, notes: Optional[str] = None) -> Dict[str, Any]:
    return {
        "season": int(season),
        "asOfUtc": None,
        "source": "empty_preseason_scaffold",
        "teams": {},
        "players": {},
        "notes": notes
        or (
            "Actual cells stay null / UI '—' until REG weeks settle. "
            "Re-run with --from-db after kickoffs to populate."
        ),
    }


def _num(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def accumulate_team_result(
    teams: Dict[str, Dict[str, int]],
    *,
    home: str,
    away: str,
    home_score: int,
    away_score: int,
) -> None:
    """Update W/L/T from one final score row."""
    for team, scored, allowed in ((home, home_score, away_score), (away, away_score, home_score)):
        if not team:
            continue
        entry = teams.setdefault(str(team), {"wins": 0, "losses": 0, "ties": 0})
        if scored > allowed:
            entry["wins"] += 1
        elif scored < allowed:
            entry["losses"] += 1
        else:
            entry["ties"] += 1


def _empty_player_totals() -> Dict[str, Any]:
    return {
        "passYards": 0.0,
        "rushYards": 0.0,
        "receivingYards": 0.0,
        "receptions": 0.0,
        "passTds": 0.0,
        "rushTds": 0.0,
        "recTds": 0.0,
    }


def accumulate_player_game(
    players: Dict[str, Dict[str, Any]],
    *,
    player_keys: Sequence[str],
    metrics: Mapping[str, Any],
) -> None:
    """Add one REG game of nflverse player metrics into season totals.

    All keys in `player_keys` receive identical cumulative stats so hub
    lookups by uid / gsis / team:id all work.
    """
    keys = []
    for k in player_keys:
        s = str(k) if k is not None else ""
        if s and s not in keys:
            keys.append(s)
    if not keys:
        return
    delta = {
        "passYards": _num(metrics.get("passing_yards")),
        "rushYards": _num(metrics.get("rushing_yards")),
        "receivingYards": _num(metrics.get("receiving_yards")),
        "receptions": _num(metrics.get("receptions")),
        "passTds": _num(metrics.get("passing_tds")),
        "rushTds": _num(metrics.get("rushing_tds")),
        "recTds": _num(metrics.get("receiving_tds")),
    }
    # Skip pure-zero defensive / inactive rows that add noise to the hub.
    if sum(delta.values()) <= 0:
        return

    entry = None
    for key in keys:
        if key in players:
            entry = dict(players[key])
            break
    if entry is None:
        entry = _empty_player_totals()
    for field, value in delta.items():
        entry[field] = float(entry.get(field) or 0.0) + value
    for key in keys:
        players[key] = dict(entry)


def finalize_player_rows(players: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Round numeric fields for the hub JSON payload."""
    out: Dict[str, Dict[str, Any]] = {}
    for key, entry in players.items():
        out[key] = {
            "passYards": round(float(entry.get("passYards") or 0.0), 1),
            "rushYards": round(float(entry.get("rushYards") or 0.0), 1),
            "receivingYards": round(float(entry.get("receivingYards") or 0.0), 1),
            "receptions": round(float(entry.get("receptions") or 0.0), 1),
            "passTds": round(float(entry.get("passTds") or 0.0), 1),
            "rushTds": round(float(entry.get("rushTds") or 0.0), 1),
            "recTds": round(float(entry.get("recTds") or 0.0), 1),
        }
    return out


def build_bundle_from_rows(
    *,
    season: int,
    schedule_rows: Iterable[Mapping[str, Any]],
    player_rows: Iterable[Mapping[str, Any]],
    source: str = "nfl_dp_schedules+nfl_dp_player_game_stats",
) -> Dict[str, Any]:
    teams: Dict[str, Dict[str, int]] = {}
    for row in schedule_rows:
        week = row.get("week")
        if week is not None and int(week) > REG_WEEK_MAX:
            continue
        hs = row.get("home_score")
        aws = row.get("away_score")
        if hs is None or aws is None:
            continue
        accumulate_team_result(
            teams,
            home=str(row.get("home_team") or ""),
            away=str(row.get("away_team") or ""),
            home_score=int(hs),
            away_score=int(aws),
        )

    players: Dict[str, Dict[str, Any]] = {}
    for row in player_rows:
        metrics = row.get("metrics") or {}
        if isinstance(metrics, str):
            import json

            try:
                metrics = json.loads(metrics)
            except json.JSONDecodeError:
                metrics = {}
        season_type = str(metrics.get("season_type") or row.get("season_type") or "REG").upper()
        if season_type != "REG":
            continue
        week = row.get("week")
        if week is not None and int(week) > REG_WEEK_MAX:
            continue
        player_id = str(row.get("player_id") or "")
        team = str(row.get("team") or metrics.get("recent_team") or metrics.get("team") or "")
        player_uid = row.get("player_uid")
        keys: List[str] = []
        if player_uid:
            keys.append(str(player_uid))
        if player_id:
            keys.append(player_id)
        if team and player_id:
            keys.append(f"{team}:{player_id}")
        seen_keys: List[str] = []
        for k in keys:
            if k and k not in seen_keys:
                seen_keys.append(k)
        accumulate_player_game(players, player_keys=seen_keys, metrics=metrics)

    finalized_players = finalize_player_rows(players)
    # Hub TeamActuals only needs wins/losses (ties optional).
    hub_teams = {
        team: {"wins": v["wins"], "losses": v["losses"]}
        for team, v in teams.items()
    }
    return {
        "season": int(season),
        "asOfUtc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "teams": hub_teams,
        "players": finalized_players,
        "notes": (
            f"REG season-to-date through week ≤{REG_WEEK_MAX}. "
            f"Teams={len(hub_teams)} players={len({id(v) for v in finalized_players.values()})}."
        ),
        "meta": {
            "teamCount": len(hub_teams),
            "playerKeyCount": len(finalized_players),
            "uniquePlayers": len({id(v) for v in finalized_players.values()}),
            "tiesIncluded": {t: teams[t].get("ties", 0) for t in teams if teams[t].get("ties")},
        },
    }


def load_from_db(conn: Any, season: int) -> Dict[str, Any]:
    """Load schedule + player actuals. `conn` is a psycopg connection.

    Player totals are aggregated in SQL (one row per player) for speed.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT home_team, away_team, home_score, away_score, week
        FROM nfl_dp_schedules
        WHERE season = %s
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND COALESCE(week, 1) <= %s
        """,
        (season, REG_WEEK_MAX),
    )
    schedule_rows = [
        {
            "home_team": r[0],
            "away_team": r[1],
            "home_score": r[2],
            "away_score": r[3],
            "week": r[4],
        }
        for r in cur.fetchall()
    ]

    # Aggregate REG skill stats in SQL; alias keys applied in Python.
    cur.execute(
        """
        SELECT
          p.player_id,
          MAX(p.team) AS team,
          m.player_uid::text AS player_uid,
          SUM(COALESCE((p.metrics->>'passing_yards')::numeric, 0)) AS pass_yards,
          SUM(COALESCE((p.metrics->>'rushing_yards')::numeric, 0)) AS rush_yards,
          SUM(COALESCE((p.metrics->>'receiving_yards')::numeric, 0)) AS receiving_yards,
          SUM(COALESCE((p.metrics->>'receptions')::numeric, 0)) AS receptions,
          SUM(COALESCE((p.metrics->>'passing_tds')::numeric, 0)) AS pass_tds,
          SUM(COALESCE((p.metrics->>'rushing_tds')::numeric, 0)) AS rush_tds,
          SUM(COALESCE((p.metrics->>'receiving_tds')::numeric, 0)) AS rec_tds
        FROM nfl_dp_player_game_stats p
        LEFT JOIN nfl_player_source_id_map m
          ON m.external_id = p.player_id
         AND m.source_system = 'nfl_dp_player_usage_weekly'
        WHERE p.season = %s
          AND COALESCE(p.week, 1) <= %s
          AND COALESCE(p.metrics->>'season_type', 'REG') = 'REG'
        GROUP BY p.player_id, m.player_uid
        HAVING
          SUM(COALESCE((p.metrics->>'passing_yards')::numeric, 0))
          + SUM(COALESCE((p.metrics->>'rushing_yards')::numeric, 0))
          + SUM(COALESCE((p.metrics->>'receiving_yards')::numeric, 0))
          + SUM(COALESCE((p.metrics->>'receptions')::numeric, 0))
          + SUM(COALESCE((p.metrics->>'passing_tds')::numeric, 0))
          + SUM(COALESCE((p.metrics->>'rushing_tds')::numeric, 0))
          + SUM(COALESCE((p.metrics->>'receiving_tds')::numeric, 0))
          > 0
        """,
        (season, REG_WEEK_MAX),
    )
    players: Dict[str, Dict[str, Any]] = {}
    for (
        player_id,
        team,
        player_uid,
        pass_yards,
        rush_yards,
        receiving_yards,
        receptions,
        pass_tds,
        rush_tds,
        rec_tds,
    ) in cur.fetchall():
        stats = {
            "passYards": round(float(pass_yards or 0), 1),
            "rushYards": round(float(rush_yards or 0), 1),
            "receivingYards": round(float(receiving_yards or 0), 1),
            "receptions": round(float(receptions or 0), 1),
            "passTds": round(float(pass_tds or 0), 1),
            "rushTds": round(float(rush_tds or 0), 1),
            "recTds": round(float(rec_tds or 0), 1),
        }
        keys: List[str] = []
        if player_uid:
            keys.append(str(player_uid))
        if player_id:
            keys.append(str(player_id))
        if team and player_id:
            keys.append(f"{team}:{player_id}")
        for key in keys:
            players[key] = dict(stats)

    teams: Dict[str, Dict[str, int]] = {}
    for row in schedule_rows:
        accumulate_team_result(
            teams,
            home=str(row.get("home_team") or ""),
            away=str(row.get("away_team") or ""),
            home_score=int(row["home_score"]),
            away_score=int(row["away_score"]),
        )

    if not teams and not players:
        bundle = empty_bundle(
            season,
            notes="No final REG scores or player stats yet — wrote empty scaffold.",
        )
        bundle["asOfUtc"] = datetime.now(timezone.utc).isoformat()
        return bundle

    hub_teams = {
        team: {"wins": v["wins"], "losses": v["losses"]} for team, v in teams.items()
    }
    return {
        "season": int(season),
        "asOfUtc": datetime.now(timezone.utc).isoformat(),
        "source": "nfl_dp_schedules+nfl_dp_player_game_stats",
        "teams": hub_teams,
        "players": players,
        "notes": (
            f"REG season-to-date through week ≤{REG_WEEK_MAX}. "
            f"Teams={len(hub_teams)} players={len({json.dumps(v, sort_keys=True) for v in players.values()})}."
        ),
        "meta": {
            "teamCount": len(hub_teams),
            "playerKeyCount": len(players),
            "uniquePlayers": len({json.dumps(v, sort_keys=True) for v in players.values()}),
        },
    }


def validate_bundle(bundle: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if "season" not in bundle:
        errors.append("missing season")
    if not isinstance(bundle.get("teams"), dict):
        errors.append("teams must be object")
    if not isinstance(bundle.get("players"), dict):
        errors.append("players must be object")
    return (len(errors) == 0, errors)
