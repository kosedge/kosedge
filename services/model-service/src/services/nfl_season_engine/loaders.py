"""Universe loaders for the hierarchical season engine.

Prefer real DB sources (schedule, EPA priors, depth charts, projection
baselines) when a session is available; otherwise fall back to a
self-contained demo universe so the engine can be exercised offline.

Efficiency rates are always passed through ``calibration.apply_efficiency_priors``
(or baseline-derived overrides) so Layer 4 is never left on uncalibrated
dataclass defaults alone.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.nfl_season_engine.calibration import (
    CALIBRATION_TAG,
    ELITE_INT_RATE,
    apply_efficiency_priors,
    calibration_notes,
    efficiency_from_baseline_row,
)
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
# Shares are absolute fractions of team volume (residual "other" absorbs rest).
_DEMO_SKILL: Dict[str, List[Dict[str, Any]]] = {
    "KC": [
        {"name": "P.Mahomes", "pos": "QB", "depth": 1, "snap": 0.98, "rush": 0.07, "tgt": 0.0, "ypa": 7.35, "int_rate": ELITE_INT_RATE},
        {"name": "I.Pacheco", "pos": "RB", "depth": 1, "snap": 0.58, "rush": 0.52, "tgt": 0.09, "ypc": 4.25},
        {"name": "R.Rice", "pos": "WR", "depth": 1, "snap": 0.82, "rush": 0.0, "tgt": 0.22, "ypr": 11.6},
        {"name": "X.Worthy", "pos": "WR", "depth": 2, "snap": 0.70, "rush": 0.02, "tgt": 0.14, "ypr": 13.2},
        {"name": "T.Kelce", "pos": "TE", "depth": 1, "snap": 0.72, "rush": 0.0, "tgt": 0.16, "ypr": 10.9},
    ],
    "BUF": [
        {"name": "J.Allen", "pos": "QB", "depth": 1, "snap": 0.98, "rush": 0.16, "tgt": 0.0, "ypa": 7.25, "int_rate": ELITE_INT_RATE, "ypc": 5.4},
        {"name": "J.Cook", "pos": "RB", "depth": 1, "snap": 0.60, "rush": 0.52, "tgt": 0.10, "ypc": 4.55},
        {"name": "K.Shakir", "pos": "WR", "depth": 1, "snap": 0.80, "rush": 0.0, "tgt": 0.19, "ypr": 11.0},
        {"name": "K.Coleman", "pos": "WR", "depth": 2, "snap": 0.65, "rush": 0.0, "tgt": 0.13, "ypr": 12.0},
        {"name": "D.Kincaid", "pos": "TE", "depth": 1, "snap": 0.68, "rush": 0.0, "tgt": 0.14, "ypr": 10.5},
    ],
    "PHI": [
        {"name": "J.Hurts", "pos": "QB", "depth": 1, "snap": 0.97, "rush": 0.18, "tgt": 0.0, "ypa": 7.05, "ypc": 5.2, "int_rate": 0.016},
        {"name": "S.Barkley", "pos": "RB", "depth": 1, "snap": 0.70, "rush": 0.58, "tgt": 0.10, "ypc": 4.65},
        {"name": "A.Brown", "pos": "WR", "depth": 1, "snap": 0.88, "rush": 0.0, "tgt": 0.24, "ypr": 12.8},
        {"name": "D.Smith", "pos": "WR", "depth": 2, "snap": 0.80, "rush": 0.0, "tgt": 0.18, "ypr": 12.2},
        {"name": "D.Goedert", "pos": "TE", "depth": 1, "snap": 0.70, "rush": 0.0, "tgt": 0.12, "ypr": 10.8},
    ],
    "SF": [
        {"name": "B.Purdy", "pos": "QB", "depth": 1, "snap": 0.96, "rush": 0.05, "tgt": 0.0, "ypa": 7.45, "int_rate": 0.016},
        {"name": "C.McCaffrey", "pos": "RB", "depth": 1, "snap": 0.72, "rush": 0.50, "tgt": 0.16, "ypc": 4.45},
        {"name": "D.Samuel", "pos": "WR", "depth": 1, "snap": 0.78, "rush": 0.04, "tgt": 0.18, "ypr": 11.8},
        {"name": "B.Aiyuk", "pos": "WR", "depth": 2, "snap": 0.80, "rush": 0.0, "tgt": 0.17, "ypr": 13.0},
        {"name": "G.Kittle", "pos": "TE", "depth": 1, "snap": 0.80, "rush": 0.0, "tgt": 0.14, "ypr": 12.4},
    ],
    "DET": [
        {"name": "J.Goff", "pos": "QB", "depth": 1, "snap": 0.98, "rush": 0.02, "tgt": 0.0, "ypa": 7.40, "int_rate": 0.016},
        {"name": "J.Gibbs", "pos": "RB", "depth": 1, "snap": 0.58, "rush": 0.45, "tgt": 0.12, "ypc": 4.85},
        {"name": "D.Montgomery", "pos": "RB", "depth": 2, "snap": 0.38, "rush": 0.32, "tgt": 0.05, "ypc": 4.15},
        {"name": "A.St. Brown", "pos": "WR", "depth": 1, "snap": 0.88, "rush": 0.0, "tgt": 0.24, "ypr": 11.3},
        {"name": "J.Williams", "pos": "WR", "depth": 2, "snap": 0.75, "rush": 0.0, "tgt": 0.15, "ypr": 12.8},
        {"name": "S.LaPorta", "pos": "TE", "depth": 1, "snap": 0.78, "rush": 0.0, "tgt": 0.14, "ypr": 11.0},
    ],
}

# Demo EPA-style talent bumps (offense / defense index deltas vs 1.0).
# Spread sized so projected win means ~5–12 (recent NFL projection band),
# with contenders clearly above replacement — not hash noise.
_DEMO_STRENGTH_BUMPS: Dict[str, Dict[str, float]] = {
    "KC": {"off": 0.15, "def": 0.10, "pace": 0.00, "pass": 0.02},
    "BUF": {"off": 0.14, "def": 0.09, "pace": 0.02, "pass": -0.01},
    "PHI": {"off": 0.13, "def": 0.09, "pace": 0.01, "pass": -0.02},
    "SF": {"off": 0.11, "def": 0.12, "pace": -0.01, "pass": 0.00},
    "DET": {"off": 0.13, "def": 0.07, "pace": 0.02, "pass": 0.01},
    "BAL": {"off": 0.12, "def": 0.10, "pace": 0.01, "pass": -0.03},
    "CIN": {"off": 0.10, "def": 0.03, "pace": 0.01, "pass": 0.02},
    "MIA": {"off": 0.06, "def": 0.01, "pace": 0.03, "pass": 0.03},
    "DAL": {"off": 0.05, "def": 0.05, "pace": 0.00, "pass": 0.01},
    "GB": {"off": 0.07, "def": 0.04, "pace": 0.00, "pass": 0.00},
    "HOU": {"off": 0.06, "def": 0.08, "pace": -0.01, "pass": 0.00},
    "LAC": {"off": 0.08, "def": 0.05, "pace": 0.00, "pass": 0.01},
    "MIN": {"off": 0.05, "def": 0.03, "pace": 0.01, "pass": 0.02},
    "SEA": {"off": 0.03, "def": 0.03, "pace": 0.01, "pass": 0.01},
    "TB": {"off": 0.04, "def": 0.02, "pace": 0.00, "pass": 0.02},
    "ATL": {"off": 0.02, "def": 0.00, "pace": 0.01, "pass": 0.00},
    "LA": {"off": 0.03, "def": 0.05, "pace": -0.01, "pass": 0.01},
    "PIT": {"off": 0.00, "def": 0.08, "pace": -0.02, "pass": -0.02},
    "DEN": {"off": 0.01, "def": 0.06, "pace": -0.01, "pass": 0.00},
    "NYJ": {"off": -0.04, "def": 0.06, "pace": -0.02, "pass": -0.01},
    "CLE": {"off": -0.05, "def": 0.04, "pace": -0.02, "pass": -0.02},
    "CHI": {"off": -0.02, "def": -0.01, "pace": 0.00, "pass": 0.00},
    "IND": {"off": -0.04, "def": -0.03, "pace": 0.00, "pass": 0.00},
    "JAX": {"off": -0.05, "def": -0.04, "pace": 0.01, "pass": 0.01},
    "LV": {"off": -0.06, "def": -0.04, "pace": 0.00, "pass": 0.00},
    "NO": {"off": -0.07, "def": -0.01, "pace": -0.01, "pass": 0.00},
    "NYG": {"off": -0.08, "def": -0.05, "pace": 0.00, "pass": 0.00},
    "TEN": {"off": -0.09, "def": -0.05, "pace": -0.01, "pass": -0.01},
    "CAR": {"off": -0.11, "def": -0.07, "pace": 0.00, "pass": 0.00},
    "NE": {"off": -0.09, "def": -0.03, "pace": -0.01, "pass": -0.01},
    "WAS": {"off": 0.02, "def": -0.02, "pace": 0.01, "pass": 0.01},
    "ARI": {"off": -0.01, "def": -0.04, "pace": 0.01, "pass": 0.01},
}


def _generic_skill(team: str) -> List[Dict[str, Any]]:
    return [
        {"name": f"{team} QB1", "pos": "QB", "depth": 1, "snap": 0.97, "rush": 0.06, "tgt": 0.0},
        {"name": f"{team} RB1", "pos": "RB", "depth": 1, "snap": 0.58, "rush": 0.52, "tgt": 0.09},
        {"name": f"{team} RB2", "pos": "RB", "depth": 2, "snap": 0.28, "rush": 0.24, "tgt": 0.05},
        {"name": f"{team} WR1", "pos": "WR", "depth": 1, "snap": 0.85, "rush": 0.0, "tgt": 0.22},
        {"name": f"{team} WR2", "pos": "WR", "depth": 2, "snap": 0.72, "rush": 0.0, "tgt": 0.15},
        {"name": f"{team} WR3", "pos": "WR", "depth": 3, "snap": 0.50, "rush": 0.0, "tgt": 0.09},
        {"name": f"{team} TE1", "pos": "TE", "depth": 1, "snap": 0.68, "rush": 0.0, "tgt": 0.12},
    ]


def _role_from_demo(team: str, row: Mapping[str, Any]) -> PlayerRole:
    pos = str(row["pos"])
    depth = int(row.get("depth", 1))
    key = f"{team}-{pos}{depth}-{row['name']}".replace(" ", "")
    overrides = {
        k: float(row[k])
        for k in ("ypa", "ypc", "ypr", "catch_rate", "pass_td_rate", "rush_td_rate", "rec_td_rate", "int_rate")
        if k in row and row[k] is not None
    }
    role = PlayerRole(
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
        source="demo_depth_chart",
    )
    return apply_efficiency_priors(role, overrides=overrides or None, source_suffix="league_efficiency_v1")


def _round_robin_schedule(season: int, teams: Sequence[str]) -> List[ScheduledGame]:
    """Build a 272-game (17×32/2) schedule via mirrored round-robin.

    PLACEHOLDER structure for offline demos. Prefer ``nfl_dp_schedules``
    when a DB session is available.
    """
    clubs = list(teams)
    if len(clubs) != 32:
        raise ValueError(f"Expected 32 teams, got {len(clubs)}")
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
    strength_inputs: Dict[str, Dict[str, float | str]] = {}
    for t in NFL_TEAMS:
        bump = _DEMO_STRENGTH_BUMPS.get(t, {"off": 0.0, "def": 0.0, "pace": 0.0, "pass": 0.0})
        # Tiny deterministic jitter so non-bumped teams are not identical.
        jitter = ((hash(t) % 7) - 3) * 0.008
        strength_inputs[t] = {
            "offense_index": 1.0 + float(bump.get("off", 0.0)) + jitter,
            "defense_index": 1.0 + float(bump.get("def", 0.0)) - 0.5 * jitter,
            "pace_factor": 1.0 + float(bump.get("pace", 0.0)),
            "pass_rate_bias": float(bump.get("pass", 0.0)),
            "source": "demo_epa_style_prior",
        }

    rosters: Dict[str, List[PlayerRole]] = {}
    for team in NFL_TEAMS:
        rows = _DEMO_SKILL.get(team) or _generic_skill(team)
        rosters[team] = [_role_from_demo(team, r) for r in rows]

    schedule = _round_robin_schedule(season, NFL_TEAMS)
    notes = {
        "schedule": "PLACEHOLDER round-robin (272 games). Prefer nfl_dp_schedules in DB mode.",
        "strengths": "Calibrated demo EPA-style priors with contender-tier bumps (KC/BUF/PHI/SF/DET/BAL...).",
        "rosters": "Mixed: named demo skill cores for 5 teams; generic depth for others. Absolute usage shares.",
        "calibration": CALIBRATION_TAG,
        **{f"cal_{k}": v for k, v in calibration_notes().items()},
    }
    return EngineUniverse(
        season=season,
        schedule=schedule,
        strengths=initialize_strengths(strength_inputs),
        rosters=rosters,
        notes=notes,
    )


def _load_baseline_efficiency_map(
    session: Any,
    *,
    season: int,
    as_of_week: int,
) -> Dict[str, Dict[str, float]]:
    """Best-effort map of player_name|team|pos → efficiency overrides from baselines.

    Returns empty dict when the table is missing or empty — callers fall back
    to league priors (documented, not invented player grades).
    """
    from sqlalchemy import text

    try:
        rows = session.execute(
            text(
                """
                SELECT DISTINCT ON (team, player_name, position)
                  team, player_name, position,
                  attempts_mean, pass_yards_mean, rush_yards_mean,
                  carries_mean, targets_mean, receptions_mean,
                  receiving_yards_mean, pass_tds_mean, rush_tds_mean,
                  rec_tds_mean, interceptions_mean
                FROM nfl_player_projection_baselines
                WHERE season = :season
                  AND week <= :week
                ORDER BY team, player_name, position, week DESC
                """
            ),
            {"season": int(season), "week": int(as_of_week)},
        ).fetchall()
    except Exception:
        # Column names vary across migrations — try a narrower select.
        try:
            rows = session.execute(
                text(
                    """
                    SELECT DISTINCT ON (team, player_name, position)
                      team, player_name, position,
                      pass_yards_mean, rush_yards_mean,
                      receptions_mean, receiving_yards_mean
                    FROM nfl_player_projection_baselines
                    WHERE season = :season
                      AND week <= :week
                    ORDER BY team, player_name, position, week DESC
                    """
                ),
                {"season": int(season), "week": int(as_of_week)},
            ).fetchall()
        except Exception:
            return {}

    out: Dict[str, Dict[str, float]] = {}
    for r in rows or []:
        team = str(r.team)
        if team == "LAR":
            team = "LA"
        pos = str(getattr(r, "position", "") or "")
        name = str(r.player_name or "")
        key = f"{team}|{pos}|{name}".upper()
        payload = {c: getattr(r, c, None) for c in r._mapping.keys()}  # type: ignore[attr-defined]
        out[key] = efficiency_from_baseline_row(payload, pos)
    return out


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
    epa_count = 0
    for team in NFL_TEAMS:
        prior = priors.get(team) or {}
        if prior:
            epa_count += 1
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

    baseline_eff = _load_baseline_efficiency_map(session, season=season, as_of_week=as_of_week)
    baseline_hits = 0

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
            role = PlayerRole(
                player_key=f"{team}-{pos}{depth}-{name}".replace(" ", ""),
                player_name=name,
                team=team,
                position=pos,
                depth_order=depth,
                snap_share={1: 0.9, 2: 0.45, 3: 0.2}.get(depth, 0.1) if pos == "QB" else {1: 0.65, 2: 0.38, 3: 0.18}.get(depth, 0.1),
                target_share={1: 0.22, 2: 0.14, 3: 0.08}.get(depth, 0.05) if pos in ("WR", "TE") else ({1: 0.10, 2: 0.05}.get(depth, 0.03) if pos == "RB" else 0.0),
                rush_share={1: 0.52, 2: 0.26, 3: 0.12}.get(depth, 0.05) if pos == "RB" else ({1: 0.07}.get(depth, 0.02) if pos == "QB" else 0.0),
                route_share={1: 0.85, 2: 0.65, 3: 0.4}.get(depth, 0.2) if pos in ("WR", "TE") else 0.2,
                role_confidence=0.7 if depth == 1 else 0.5,
                source="depth_chart_weekly",
            )
            key = f"{team}|{pos}|{name}".upper()
            overrides = baseline_eff.get(key)
            if overrides:
                baseline_hits += 1
                role = apply_efficiency_priors(role, overrides=overrides, source_suffix="baseline_efficiency")
            else:
                role = apply_efficiency_priors(role, source_suffix="league_efficiency_v1")
            rosters[team].append(role)
        if baseline_hits:
            roster_note = (
                f"REAL depth chart identities; efficiency from baselines "
                f"({baseline_hits} hits) else league priors"
            )
        else:
            roster_note = (
                "REAL depth chart identities; PLACEHOLDER league efficiency priors "
                "(nfl_player_projection_baselines unavailable or empty for as_of_week)"
            )
    else:
        for team in NFL_TEAMS:
            rows = _DEMO_SKILL.get(team) or _generic_skill(team)
            rosters[team] = [_role_from_demo(team, r) for r in rows]
        roster_note = "PLACEHOLDER demo rosters (depth chart empty)"

    for team in NFL_TEAMS:
        if not rosters[team]:
            rosters[team] = [_role_from_demo(team, r) for r in _generic_skill(team)]

    strength_note = (
        f"REAL epa_prior for {epa_count}/32 teams; else placeholder_league_avg"
        if epa_count
        else "PLACEHOLDER league-average strengths (EPA priors empty)"
    )

    return EngineUniverse(
        season=season,
        schedule=schedule[:272] if len(schedule) >= 272 else schedule,
        strengths=initialize_strengths(strength_inputs),
        rosters=rosters,
        notes={
            "schedule": schedule_note,
            "strengths": strength_note,
            "rosters": roster_note,
            "calibration": CALIBRATION_TAG,
            **{f"cal_{k}": v for k, v in calibration_notes().items()},
        },
    )
