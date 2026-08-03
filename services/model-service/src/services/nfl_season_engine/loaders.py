"""Universe loaders for the hierarchical season engine.

Prefer real DB sources (schedule, EPA priors, depth charts) when a session
is available; otherwise fall back to a self-contained demo universe so the
engine can be exercised offline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.nfl_season_engine.team_strength import initialize_strengths
from src.services.nfl_season_engine.types import (
    EngineUniverse,
    PlayerRole,
    ScheduledGame,
)

NFL_TEAMS: List[str] = [
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
]

# Approximate 2025/26 style skill cores for demo / offline runs.
# PLACEHOLDER — not a live depth chart. Names are illustrative anchors.
_DEMO_SKILL: Dict[str, List[Dict[str, Any]]] = {
    "KC": [
        {"name": "P.Mahomes", "pos": "QB", "depth": 1, "snap": 0.98, "rush": 0.06, "tgt": 0.0, "ypa": 7.4},
        {"name": "I.Pacheco", "pos": "RB", "depth": 1, "snap": 0.58, "rush": 0.55, "tgt": 0.10, "ypc": 4.3},
        {"name": "R.Rice", "pos": "WR", "depth": 1, "snap": 0.82, "rush": 0.0, "tgt": 0.24, "ypr": 11.8},
        {"name": "X.Worthy", "pos": "WR", "depth": 2, "snap": 0.70, "rush": 0.02, "tgt": 0.16, "ypr": 13.5},
        {"name": "T.Kelce", "pos": "TE", "depth": 1, "snap": 0.72, "rush": 0.0, "tgt": 0.18, "ypr": 11.2},
    ],
    "BUF": [
        {"name": "J.Allen", "pos": "QB", "depth": 1, "snap": 0.98, "rush": 0.12, "tgt": 0.0, "ypa": 7.3},
        {"name": "J.Cook", "pos": "RB", "depth": 1, "snap": 0.60, "rush": 0.58, "tgt": 0.12, "ypc": 4.6},
        {"name": "K.Shakir", "pos": "WR", "depth": 1, "snap": 0.80, "rush": 0.0, "tgt": 0.20, "ypr": 11.0},
        {"name": "K.Coleman", "pos": "WR", "depth": 2, "snap": 0.65, "rush": 0.0, "tgt": 0.15, "ypr": 12.2},
        {"name": "D.Kincaid", "pos": "TE", "depth": 1, "snap": 0.68, "rush": 0.0, "tgt": 0.16, "ypr": 10.8},
    ],
    "PHI": [
        {"name": "J.Hurts", "pos": "QB", "depth": 1, "snap": 0.97, "rush": 0.14, "tgt": 0.0, "ypa": 7.1},
        {"name": "S.Barkley", "pos": "RB", "depth": 1, "snap": 0.72, "rush": 0.68, "tgt": 0.12, "ypc": 4.8},
        {"name": "A.Brown", "pos": "WR", "depth": 1, "snap": 0.88, "rush": 0.0, "tgt": 0.26, "ypr": 13.0},
        {"name": "D.Smith", "pos": "WR", "depth": 2, "snap": 0.80, "rush": 0.0, "tgt": 0.20, "ypr": 12.4},
        {"name": "D.Goedert", "pos": "TE", "depth": 1, "snap": 0.70, "rush": 0.0, "tgt": 0.14, "ypr": 11.0},
    ],
    "SF": [
        {"name": "B.Purdy", "pos": "QB", "depth": 1, "snap": 0.96, "rush": 0.05, "tgt": 0.0, "ypa": 7.6},
        {"name": "C.McCaffrey", "pos": "RB", "depth": 1, "snap": 0.75, "rush": 0.55, "tgt": 0.18, "ypc": 4.5},
        {"name": "D.Samuel", "pos": "WR", "depth": 1, "snap": 0.78, "rush": 0.04, "tgt": 0.20, "ypr": 12.0},
        {"name": "B.Aiyuk", "pos": "WR", "depth": 2, "snap": 0.82, "rush": 0.0, "tgt": 0.18, "ypr": 13.2},
        {"name": "G.Kittle", "pos": "TE", "depth": 1, "snap": 0.80, "rush": 0.0, "tgt": 0.16, "ypr": 12.8},
    ],
    "DET": [
        {"name": "J.Goff", "pos": "QB", "depth": 1, "snap": 0.98, "rush": 0.02, "tgt": 0.0, "ypa": 7.5},
        {"name": "J.Gibbs", "pos": "RB", "depth": 1, "snap": 0.62, "rush": 0.48, "tgt": 0.14, "ypc": 5.0},
        {"name": "D.Montgomery", "pos": "RB", "depth": 2, "snap": 0.40, "rush": 0.35, "tgt": 0.06, "ypc": 4.2},
        {"name": "A.St. Brown", "pos": "WR", "depth": 1, "snap": 0.88, "rush": 0.0, "tgt": 0.26, "ypr": 11.5},
        {"name": "J.Williams", "pos": "WR", "depth": 2, "snap": 0.75, "rush": 0.0, "tgt": 0.16, "ypr": 13.0},
        {"name": "S.LaPorta", "pos": "TE", "depth": 1, "snap": 0.78, "rush": 0.0, "tgt": 0.16, "ypr": 11.2},
    ],
}


def _generic_skill(team: str) -> List[Dict[str, Any]]:
    return [
        {"name": f"{team} QB1", "pos": "QB", "depth": 1, "snap": 0.97, "rush": 0.05, "tgt": 0.0, "ypa": 7.0},
        {"name": f"{team} RB1", "pos": "RB", "depth": 1, "snap": 0.60, "rush": 0.58, "tgt": 0.10, "ypc": 4.2},
        {"name": f"{team} RB2", "pos": "RB", "depth": 2, "snap": 0.28, "rush": 0.25, "tgt": 0.06, "ypc": 4.0},
        {"name": f"{team} WR1", "pos": "WR", "depth": 1, "snap": 0.85, "rush": 0.0, "tgt": 0.24, "ypr": 12.0},
        {"name": f"{team} WR2", "pos": "WR", "depth": 2, "snap": 0.72, "rush": 0.0, "tgt": 0.16, "ypr": 11.5},
        {"name": f"{team} WR3", "pos": "WR", "depth": 3, "snap": 0.50, "rush": 0.0, "tgt": 0.10, "ypr": 11.0},
        {"name": f"{team} TE1", "pos": "TE", "depth": 1, "snap": 0.68, "rush": 0.0, "tgt": 0.14, "ypr": 10.8},
    ]


def _role_from_demo(team: str, row: Mapping[str, Any]) -> PlayerRole:
    pos = str(row["pos"])
    depth = int(row.get("depth", 1))
    key = f"{team}-{pos}{depth}-{row['name']}".replace(" ", "")
    return PlayerRole(
        player_key=key,
        player_name=str(row["name"]),
        team=team,
        position=pos,
        depth_order=depth,
        snap_share=float(row.get("snap", 0.5)),
        target_share=float(row.get("tgt", 0.0)),
        rush_share=float(row.get("rush", 0.0)),
        route_share=float(row.get("tgt", 0.0)) * 1.15 if pos in ("WR", "TE", "RB") else 0.0,
        red_zone_share=float(row.get("tgt", row.get("rush", 0.1))) * 0.9,
        role_confidence=0.75 if depth == 1 else 0.55,
        ypa=float(row.get("ypa", 7.0)),
        ypc=float(row.get("ypc", 4.2)),
        ypr=float(row.get("ypr", 11.5)),
        catch_rate=0.65 if pos == "RB" else (0.68 if pos == "TE" else 0.60),
        pass_td_rate=0.046,
        rush_td_rate=0.038 if pos == "RB" else 0.02,
        rec_td_rate=0.07 if pos in ("WR", "TE") else 0.04,
        int_rate=0.022,
        source="demo_depth_chart",
    )


def _round_robin_schedule(season: int, teams: Sequence[str]) -> List[ScheduledGame]:
    """Build a 272-game (17×32/2) schedule via mirrored round-robin.

    PLACEHOLDER structure for offline demos. Prefer ``nfl_dp_schedules``
    when a DB session is available.
    """
    clubs = list(teams)
    if len(clubs) != 32:
        raise ValueError(f"Expected 32 teams, got {len(clubs)}")
    # Circle method for 17 rounds of 16 games.
    fixed = clubs[0]
    rotating = clubs[1:]
    games: List[ScheduledGame] = []
    gid = 0
    for week in range(1, 18):
        circle = [fixed] + rotating
        for i in range(16):
            home = circle[i]
            away = circle[-(i + 1)]
            if home == away:
                continue
            # Alternate home for balance across weeks.
            if week % 2 == 0:
                home, away = away, home
            gid += 1
            games.append(
                ScheduledGame(
                    season=season,
                    week=week,
                    game_id=f"{season}-W{week:02d}-{away}@{home}-{gid}",
                    home_team=home,
                    away_team=away,
                )
            )
        rotating = rotating[1:] + rotating[:1]
    # Trim / pad to exactly 272.
    if len(games) > 272:
        games = games[:272]
    while len(games) < 272:
        a, b = clubs[len(games) % 32], clubs[(len(games) + 7) % 32]
        if a == b:
            b = clubs[(len(games) + 3) % 32]
        games.append(
            ScheduledGame(
                season=season,
                week=17,
                game_id=f"{season}-pad-{len(games)}",
                home_team=a,
                away_team=b,
            )
        )
    return games


def build_demo_universe(season: int = 2026) -> EngineUniverse:
    """Self-contained universe for offline tests and sample projections."""
    strength_inputs = {
        t: {
            "offense_index": 1.0 + ((hash(t) % 17) - 8) * 0.015,
            "defense_index": 1.0 + ((hash(t[::-1]) % 17) - 8) * 0.015,
            "pace_factor": 1.0 + ((hash(t + "pace") % 11) - 5) * 0.012,
            "pass_rate_bias": ((hash(t + "pass") % 9) - 4) * 0.01,
            "source": "demo_prior",
        }
        for t in NFL_TEAMS
    }
    # Mild known-talent bumps for demo anchors.
    for team, bump in (("KC", 0.08), ("BUF", 0.07), ("PHI", 0.06), ("SF", 0.05), ("DET", 0.05)):
        strength_inputs[team]["offense_index"] = 1.0 + bump
        strength_inputs[team]["defense_index"] = 1.0 + bump * 0.6

    rosters: Dict[str, List[PlayerRole]] = {}
    for team in NFL_TEAMS:
        rows = _DEMO_SKILL.get(team) or _generic_skill(team)
        rosters[team] = [_role_from_demo(team, r) for r in rows]

    schedule = _round_robin_schedule(season, NFL_TEAMS)
    return EngineUniverse(
        season=season,
        schedule=schedule,
        strengths=initialize_strengths(strength_inputs),
        rosters=rosters,
        notes={
            "schedule": "PLACEHOLDER round-robin (272 games). Prefer nfl_dp_schedules in DB mode.",
            "strengths": "PLACEHOLDER demo priors with mild talent bumps for KC/BUF/PHI/SF/DET.",
            "rosters": "Mixed: named demo skill cores for 5 teams; generic depth for others.",
            "calibration": "Thin by design — structure + path coherence first.",
        },
    )


def load_universe_from_db(
    session: Any,
    *,
    season: int,
    as_of_week: int = 1,
) -> EngineUniverse:
    """Load schedule + EPA strength priors + best-effort depth roles from DB.

    Falls back to demo roles/strengths for any team missing data so the
    engine remains runnable. Does not modify Edge Board tables.
    """
    from sqlalchemy import text

    from src.tasks import _load_team_strength_priors

    # nfl_dp_schedules has no season_type column; REG weeks are 1–18.
    schedule_rows = session.execute(
        text(
            """
            SELECT season, week, home_team, away_team, game_id
            FROM nfl_dp_schedules
            WHERE season = :season
              AND week BETWEEN 1 AND 18
            ORDER BY week, home_team, away_team
            """
        ),
        {"season": int(season)},
    ).fetchall()

    schedule: List[ScheduledGame] = []
    if schedule_rows:
        for r in schedule_rows:
            home = str(r.home_team)
            away = str(r.away_team)
            if home == "LAR":
                home = "LA"
            if away == "LAR":
                away = "LA"
            gid = str(getattr(r, "game_id", None) or f"{season}-W{int(r.week):02d}-{away}@{home}")
            schedule.append(
                ScheduledGame(
                    season=int(r.season),
                    week=int(r.week),
                    game_id=gid,
                    home_team=home,
                    away_team=away,
                )
            )
        schedule_note = "REAL nfl_dp_schedules"
    else:
        schedule = _round_robin_schedule(season, NFL_TEAMS)
        schedule_note = "PLACEHOLDER round-robin (nfl_dp_schedules empty)"

    priors = _load_team_strength_priors(session, season_year=int(season), as_of_week=int(as_of_week))
    strength_inputs: Dict[str, Dict[str, float | str]] = {}
    for team in NFL_TEAMS:
        prior = priors.get(team) or {}
        if prior:
            strength_inputs[team] = {
                "offense_index": float(prior.get("offense_index", 1.0)),
                "defense_index": float(prior.get("defense_index", 1.0)),
                "pace_factor": 1.0,
                "pass_rate_bias": 0.0,
                "source": "epa_prior",
            }
        else:
            strength_inputs[team] = {
                "offense_index": 1.0,
                "defense_index": 1.0,
                "source": "placeholder_league_avg",
            }

    # Best-effort depth chart load (latest week <= as_of_week).
    depth_rows = session.execute(
        text(
            """
            SELECT DISTINCT ON (team, position, depth_order)
              team, player_name, position, depth_order
            FROM nfl_dp_depth_chart_weekly
            WHERE season = :season
              AND week <= :week
              AND position IN ('QB', 'RB', 'WR', 'TE')
            ORDER BY team, position, depth_order, week DESC
            """
        ),
        {"season": int(season), "week": int(as_of_week)},
    ).fetchall()

    rosters: Dict[str, List[PlayerRole]] = {t: [] for t in NFL_TEAMS}
    if depth_rows:
        for r in depth_rows:
            team = str(r.team)
            if team == "LAR":
                team = "LA"
            if team not in rosters:
                continue
            pos = str(r.position)
            depth = int(r.depth_order or 1)
            if depth > 3:
                continue
            name = str(r.player_name or f"{team} {pos}{depth}")
            # Thin efficiency defaults — REAL identity, PLACEHOLDER rates.
            rosters[team].append(
                PlayerRole(
                    player_key=f"{team}-{pos}{depth}-{name}".replace(" ", ""),
                    player_name=name,
                    team=team,
                    position=pos,
                    depth_order=depth,
                    snap_share={1: 0.9, 2: 0.45, 3: 0.2}.get(depth, 0.1) if pos == "QB" else {1: 0.7, 2: 0.4, 3: 0.2}.get(depth, 0.1),
                    target_share={1: 0.22, 2: 0.14, 3: 0.08}.get(depth, 0.05) if pos in ("WR", "TE") else ({1: 0.12, 2: 0.06}.get(depth, 0.03) if pos == "RB" else 0.0),
                    rush_share={1: 0.55, 2: 0.28, 3: 0.12}.get(depth, 0.05) if pos == "RB" else ({1: 0.08}.get(depth, 0.02) if pos == "QB" else 0.0),
                    route_share={1: 0.85, 2: 0.65, 3: 0.4}.get(depth, 0.2) if pos in ("WR", "TE") else 0.2,
                    role_confidence=0.7 if depth == 1 else 0.5,
                    source="depth_chart_weekly+default_efficiency",
                )
            )
        roster_note = "REAL depth chart identities; PLACEHOLDER efficiency priors"
    else:
        for team in NFL_TEAMS:
            rows = _DEMO_SKILL.get(team) or _generic_skill(team)
            rosters[team] = [_role_from_demo(team, r) for r in rows]
        roster_note = "PLACEHOLDER demo rosters (depth chart empty)"

    # Ensure every team has at least a minimal skill group.
    for team in NFL_TEAMS:
        if not rosters[team]:
            rosters[team] = [_role_from_demo(team, r) for r in _generic_skill(team)]

    return EngineUniverse(
        season=season,
        schedule=schedule[:272] if len(schedule) >= 272 else schedule,
        strengths=initialize_strengths(strength_inputs),
        rosters=rosters,
        notes={
            "schedule": schedule_note,
            "strengths": "REAL epa_prior where available; else placeholder_league_avg",
            "rosters": roster_note,
            "calibration": "Thin by design — structure + path coherence first.",
        },
    )
