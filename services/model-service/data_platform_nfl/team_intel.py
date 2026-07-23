from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


def _to_int(v: Any) -> int | None:
    try:
        if v is None:
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> int:
    value = _to_int(v)
    return int(value) if value is not None else 0


def _status_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _injury_penalty(report_status: Any, practice_status: Any) -> float:
    report = _status_lower(report_status)
    practice = _status_lower(practice_status)
    report_penalty = {
        "out": 0.60,
        "doubtful": 0.38,
        "questionable": 0.22,
        "limited": 0.12,
        "probable": 0.05,
    }.get(report, 0.0)
    practice_penalty = {
        "dnp": 0.32,
        "did not practice": 0.32,
        "limited": 0.15,
        "full": 0.0,
    }.get(practice, 0.0)
    return max(report_penalty, practice_penalty)


def _position_group_rank(position: str) -> int:
    pos = str(position or "").upper()
    if pos == "QB":
        return 0
    if pos in {"RB", "FB"}:
        return 1
    if pos in {"WR", "TE"}:
        return 2
    if pos in {"LT", "LG", "C", "RG", "RT", "OL", "T", "G"}:
        return 3
    if pos in {"EDGE", "DE", "DT", "NT", "DL"}:
        return 4
    if pos in {"LB", "ILB", "OLB"}:
        return 5
    if pos in {"CB", "S", "SS", "FS", "DB"}:
        return 6
    if pos in {"K", "P", "LS"}:
        return 7
    return 8


def build_standings_rows(schedule_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    completed_games: List[Dict[str, Any]] = []
    for row in schedule_rows:
        season = _to_int(row.get("season"))
        week = _to_int(row.get("week"))
        home_team = str(row.get("home_team") or "")
        away_team = str(row.get("away_team") or "")
        home_score = _to_int(row.get("home_score"))
        away_score = _to_int(row.get("away_score"))
        if (
            season is None
            or week is None
            or not home_team
            or not away_team
            or home_score is None
            or away_score is None
        ):
            continue
        completed_games.append(
            {
                "season": season,
                "week": week,
                "home_team": home_team,
                "away_team": away_team,
                "home_score": int(home_score),
                "away_score": int(away_score),
            }
        )

    completed_games.sort(
        key=lambda g: (int(g["season"]), int(g["week"]), str(g["home_team"]), str(g["away_team"]))
    )
    weekly_updates: Dict[tuple[int, int, str], Dict[str, Any]] = {}
    team_totals: Dict[tuple[int, str], Dict[str, int]] = {}

    for game in completed_games:
        season = int(game["season"])
        week = int(game["week"])
        home_team = str(game["home_team"])
        away_team = str(game["away_team"])
        home_score = int(game["home_score"])
        away_score = int(game["away_score"])

        for team in (home_team, away_team):
            team_totals.setdefault(
                (season, team),
                {"wins": 0, "losses": 0, "ties": 0, "points_for": 0, "points_against": 0},
            )

        home = team_totals[(season, home_team)]
        away = team_totals[(season, away_team)]
        home["points_for"] += home_score
        home["points_against"] += away_score
        away["points_for"] += away_score
        away["points_against"] += home_score
        if home_score > away_score:
            home["wins"] += 1
            away["losses"] += 1
        elif away_score > home_score:
            away["wins"] += 1
            home["losses"] += 1
        else:
            home["ties"] += 1
            away["ties"] += 1

        weekly_updates[(season, week, home_team)] = dict(home)
        weekly_updates[(season, week, away_team)] = dict(away)

    standings_rows: List[Dict[str, Any]] = []
    for (season, week, team), totals in sorted(
        weekly_updates.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])
    ):
        wins = int(totals["wins"])
        losses = int(totals["losses"])
        ties = int(totals["ties"])
        games = wins + losses + ties
        pct = ((wins + 0.5 * ties) / games) if games > 0 else None
        points_for = int(totals["points_for"])
        points_against = int(totals["points_against"])
        standings_rows.append(
            {
                "season": season,
                "week": week,
                "team": team,
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "points_for": points_for,
                "points_against": points_against,
                "point_diff": points_for - points_against,
                "win_pct": pct,
                "conference": None,
                "division": None,
                "conference_wins": None,
                "conference_losses": None,
                "conference_ties": None,
                "conference_pct": None,
                "division_wins": None,
                "division_losses": None,
                "division_ties": None,
                "division_pct": None,
            }
        )
    return standings_rows


def infer_depth_chart_rows(
    *,
    season: int,
    week: int,
    roster_rows: List[Dict[str, Any]],
    usage_rows: List[Dict[str, Any]],
    injury_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    usage_index: Dict[tuple[str, str], Dict[str, Any]] = {}
    for row in usage_rows:
        team = str(row.get("team") or "")
        player_id = str(row.get("player_id") or "")
        if not team or not player_id:
            continue
        usage_index[(team, player_id)] = {
            "involvement": _safe_int(row.get("involvement")),
            "targets": _safe_int(row.get("targets")),
            "rush_attempts": _safe_int(row.get("rush_attempts")),
            "pass_attempts": _safe_int(row.get("pass_attempts")),
            "active_weeks": _safe_int(row.get("active_weeks")),
            "latest_week": _to_int(row.get("latest_week")),
        }

    injury_index: Dict[tuple[str, str], float] = {}
    for row in injury_rows:
        team = str(row.get("team") or "")
        player_id = str(row.get("player_id") or "")
        player_name = str(row.get("player_name") or "")
        if not team:
            continue
        penalty = _injury_penalty(row.get("report_status"), row.get("practice_status"))
        if player_id:
            injury_index[(team, player_id)] = max(injury_index.get((team, player_id), 0.0), penalty)
        if player_name:
            injury_index[(team, player_name)] = max(injury_index.get((team, player_name), 0.0), penalty)

    grouped: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in roster_rows:
        team = str(row.get("team") or "")
        player_id = str(row.get("player_id") or "")
        if not team or not player_id:
            continue
        position = str(row.get("position") or "UNK").upper()
        usage = usage_index.get((team, player_id), {})
        involvement = int(usage.get("involvement", 0))
        targets = int(usage.get("targets", 0))
        rush_attempts = int(usage.get("rush_attempts", 0))
        pass_attempts = int(usage.get("pass_attempts", 0))
        active_weeks = int(usage.get("active_weeks", 0))
        latest_week = _to_int(usage.get("latest_week"))
        recency_bonus = 0.0
        if latest_week is not None and latest_week >= max(1, week - 1):
            recency_bonus = 0.08
        injury_penalty = max(
            injury_index.get((team, player_id), 0.0),
            injury_index.get((team, str(row.get("player_name") or "")), 0.0),
        )
        usage_volume = (
            (0.55 * involvement)
            + (0.85 * targets)
            + (0.65 * rush_attempts)
            + (0.75 * pass_attempts)
            + (1.8 * active_weeks)
        )
        role_score = max(0.0, usage_volume + recency_bonus - (12.0 * injury_penalty))
        grouped[(team, position)].append(
            {
                "team": team,
                "position": position,
                "player_id": player_id,
                "player_name": row.get("player_name"),
                "usage_volume": usage_volume,
                "injury_penalty": injury_penalty,
                "role_score": role_score,
            }
        )

    out: List[Dict[str, Any]] = []
    for (team, position), players in sorted(
        grouped.items(), key=lambda x: (x[0][0], _position_group_rank(x[0][1]), x[0][1])
    ):
        players_sorted = sorted(
            players,
            key=lambda p: (
                -float(p["role_score"]),
                float(p["injury_penalty"]),
                str(p.get("player_name") or ""),
                str(p["player_id"]),
            ),
        )
        max_score = max((float(p["role_score"]) for p in players_sorted), default=0.0)
        for idx, player in enumerate(players_sorted, start=1):
            if idx == 1:
                slot = "starter"
            elif idx == 2:
                slot = "backup"
            elif idx <= 4:
                slot = "rotation"
            else:
                slot = "depth"
            rel_score = (float(player["role_score"]) / max_score) if max_score > 0 else 0.2
            confidence = max(
                0.1,
                min(0.99, (0.25 + (0.70 * rel_score) - (0.25 * float(player["injury_penalty"])))),
            )
            out.append(
                {
                    "season": season,
                    "week": week,
                    "team": team,
                    "position": position,
                    "depth_order": idx,
                    "depth_slot": slot,
                    "player_uid": None,
                    "player_id": player["player_id"],
                    "player_name": player.get("player_name"),
                    "role_confidence": confidence,
                    "inferred_source": "v1_usage_roster_injury",
                }
            )
    return out
