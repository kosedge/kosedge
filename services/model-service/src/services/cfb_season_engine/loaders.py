"""Universe loaders for the hierarchical CFB season engine.

Prefers packaged 2026 FBS priors shipped with the package. DB feeds for
portal/recruiting/returning production are a documented gap — loaders
never invent precision when rows are missing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from src.services.cfb_season_engine.conferences import load_conference_map
from src.services.cfb_season_engine.player_hooks import build_player_hooks
from src.services.cfb_season_engine.position_groups import build_position_groups
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.roster_construction import build_roster_construction
from src.services.cfb_season_engine.schedule import densify_schedule
from src.services.cfb_season_engine.team_projection import compose_team_projection
from src.services.cfb_season_engine.types import (
    EngineUniverse,
    PlayerHook,
    ScheduledGame,
    TeamProjectionState,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
PACKAGED_TEAMS = DATA_DIR / "cfb_fbs_team_priors_2026.json"
PACKAGED_SCHEDULE = DATA_DIR / "cfb_sample_schedule_2026.json"

# Packaged priors include a few duplicate codes for the same school.
# Collapse aliases so season-sim standings are not triple-counting A&M etc.
TEAM_CODE_ALIASES: Dict[str, str] = {
    "TXAM": "TAMU",
    "TA&M": "TAMU",
    "OLE": "MISS",
    "OREST": "ORST",
    "ULL": "UL",
    "FAU2": "FAU",
}

# Immutable-enough packaged universe (sim paths copy strength books).
_PACKAGED_UNIVERSE_CACHE: Dict[int, EngineUniverse] = {}


def canonicalize_team_code(code: str) -> str:
    team = str(code).upper()
    return TEAM_CODE_ALIASES.get(team, team)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_packaged_team_priors() -> Dict[str, Any]:
    if not PACKAGED_TEAMS.exists():
        raise FileNotFoundError(f"Missing packaged CFB priors: {PACKAGED_TEAMS}")
    return _load_json(PACKAGED_TEAMS)


def load_packaged_schedule(season: int = 2026) -> List[ScheduledGame]:
    if not PACKAGED_SCHEDULE.exists():
        return _build_round_robin_schedule(season, teams=["UGA", "ALA", "OSU", "MICH", "TEX", "ORE"])
    raw = _load_json(PACKAGED_SCHEDULE)
    games: List[ScheduledGame] = []
    for row in raw.get("games", []):
        home = canonicalize_team_code(row["home"])
        away = canonicalize_team_code(row["away"])
        if home == away:
            continue
        games.append(
            ScheduledGame(
                season=int(row.get("season", season)),
                week=int(row["week"]),
                game_id=str(row.get("game_id") or f"{season}_w{row['week']}_{away}@{home}"),
                home_team=home,
                away_team=away,
                neutral_site=bool(row.get("neutral_site", False)),
            )
        )
    return games


def _build_round_robin_schedule(season: int, teams: List[str]) -> List[ScheduledGame]:
    """Tiny offline schedule when packaged schedule missing."""
    games: List[ScheduledGame] = []
    week = 1
    for i, home in enumerate(teams):
        for away in teams[i + 1 :]:
            games.append(
                ScheduledGame(
                    season=season,
                    week=week,
                    game_id=f"{season}_w{week}_{away}@{home}",
                    home_team=home,
                    away_team=away,
                )
            )
            week = week + 1 if week < 12 else 1
    return games


def _team_state_from_payload(team: str, payload: Mapping[str, Any]) -> Tuple[TeamProjectionState, List[PlayerHook]]:
    roster = build_roster_construction(team, payload.get("roster"))
    groups_payload = payload.get("position_groups") or {}
    # Wire OL/skill grades into QB supporting cast when packaged.
    qb = build_qb_situation(
        team,
        payload.get("qb"),
        ol_grade=groups_payload.get("ol"),
        skill_grade=groups_payload.get("skill"),
    )
    groups = build_position_groups(
        team,
        groups_payload,
        roster=roster,
        qb=qb,
    )
    state = compose_team_projection(team, roster, qb, groups)
    # Optional pace / pass overrides from packaged strength hints.
    if "pace_factor" in payload:
        state.pace_factor = float(payload["pace_factor"])
    if "pass_rate_bias" in payload:
        state.pass_rate_bias = float(payload["pass_rate_bias"])
    hooks = build_player_hooks(team, payload.get("players"), qb=qb)
    return state, hooks


def build_packaged_universe(season: int = 2026) -> EngineUniverse:
    """Build FBS-focused universe from packaged priors + densified schedule."""
    cached = _PACKAGED_UNIVERSE_CACHE.get(int(season))
    if cached is not None:
        return cached
    blob = load_packaged_team_priors()
    teams_raw: Mapping[str, Any] = blob.get("teams", {})
    teams: Dict[str, TeamProjectionState] = {}
    hooks: Dict[str, List[PlayerHook]] = {}
    for code, payload in teams_raw.items():
        team = canonicalize_team_code(code)
        if team in teams:
            # Prefer first/canonical payload; skip alias duplicates.
            continue
        state, player_hooks = _team_state_from_payload(team, payload or {})
        teams[team] = state
        if player_hooks:
            hooks[team] = player_hooks

    seed = load_packaged_schedule(season=season)
    known = set(teams)
    seed = [g for g in seed if g.home_team in known and g.away_team in known]
    conferences = load_conference_map()
    # Only keep affiliations for teams present in this universe.
    conferences = {
        t: conferences.get(t, conferences.get(canonicalize_team_code(t), "Independent"))
        for t in known
    }
    strength_by_team = {
        code: float(state.roster.roster_strength) if state.roster else 50.0
        for code, state in teams.items()
    }
    schedule, sched_meta = densify_schedule(
        seed,
        sorted(known),
        season=season,
        conference_by_team=conferences,
        strength_by_team=strength_by_team,
    )

    notes = {
        "mode": "packaged",
        "priors_as_of": str(blob.get("as_of", "")),
        "priors_fidelity": str(blob.get("fidelity", "approximate")),
        "team_count": str(len(teams)),
        "schedule_source": str(sched_meta.get("schedule_source", "packaged_sample_densified")),
        "schedule_fidelity": str(sched_meta.get("fidelity", "approximate")),
        "official_schedule": "false",
        "schedule_games": str(sched_meta.get("total_games", len(schedule))),
        "schedule_seed_kept": str(sched_meta.get("seed_games_kept", 0)),
        "schedule_densified_added": str(sched_meta.get("densified_added", 0)),
        "games_per_team_mean": str(sched_meta.get("games_per_team_mean", "")),
        "gap_portal_feed": "No live portal/returning-production DB feed wired yet",
        "gap_recruiting_feed": "Recruiting class score is packaged approximate composite",
        "gap_official_schedule": "No official full 2026 FBS schedule in-repo; densified sample used",
        "primary_drivers": "roster_strength + qb_situation_index + position_groups",
        "scope": "FBS focus for 2026; v0.4 strengthens season sim + early uncertainty",
        "schedule_note": str(sched_meta.get("note", "")),
    }
    universe = EngineUniverse(
        season=season,
        schedule=schedule,
        teams=teams,
        player_hooks=hooks,
        conferences=conferences,
        notes=notes,
    )
    _PACKAGED_UNIVERSE_CACHE[int(season)] = universe
    return universe


def build_demo_universe(season: int = 2026) -> EngineUniverse:
    """Alias — packaged universe is the offline demo for CFB foundation."""
    return build_packaged_universe(season=season)


def load_universe_from_db(session: Any, *, season: int = 2026, as_of_week: int = 1) -> EngineUniverse:
    """Attempt DB-backed universe; foundation pass falls back by raising.

    Reserved for future portal/roster/returning-production tables. Callers
    should catch and use ``build_packaged_universe``.
    """
    raise NotImplementedError(
        "CFB season-engine DB universe not wired (portal/recruiting/returning "
        f"production tables pending); season={season} as_of_week={as_of_week}"
    )


def resolve_season_universe(
    *,
    season: int = 2026,
    as_of_week: int = 1,
    demo: bool = False,
    session: Any = None,
) -> Tuple[EngineUniverse, Dict[str, Any]]:
    """Resolve universe with explicit mode metadata."""
    if demo or session is None:
        universe = build_packaged_universe(season=season)
        meta = {
            "mode": "packaged",
            "schedule_source": universe.notes.get("schedule_source", "packaged"),
            "schedule_game_count": len(universe.schedule),
            "team_count": len(universe.teams),
            "as_of_week": as_of_week,
            "fidelity": "approximate",
        }
        return universe, meta
    try:
        universe = load_universe_from_db(session, season=season, as_of_week=as_of_week)
        meta = {
            "mode": "db",
            "schedule_source": universe.notes.get("schedule_source", "db"),
            "schedule_game_count": len(universe.schedule),
            "team_count": len(universe.teams),
            "as_of_week": as_of_week,
            "fidelity": universe.notes.get("priors_fidelity", "mixed"),
        }
        return universe, meta
    except Exception as exc:
        universe = build_packaged_universe(season=season)
        meta = {
            "mode": "packaged_fallback",
            "schedule_source": universe.notes.get("schedule_source", "packaged"),
            "schedule_game_count": len(universe.schedule),
            "team_count": len(universe.teams),
            "as_of_week": as_of_week,
            "fidelity": "approximate",
            "db_error": str(exc)[:240],
        }
        return universe, meta


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.cfb_season_engine.loaders",
        "packaged_teams": str(PACKAGED_TEAMS),
        "packaged_schedule": str(PACKAGED_SCHEDULE),
        "schedule_policy": "seed sample + densify_schedule (not official FBS slate)",
        "db_universe": "not_implemented (gap)",
        "real_vs_approximate": (
            "Packaged JSON ships with the package (REAL artifact). Numeric "
            "priors inside are APPROXIMATE. Densified schedule is APPROXIMATE "
            "synthetic paths. DB loaders are PLACEHOLDER stubs."
        ),
    }
