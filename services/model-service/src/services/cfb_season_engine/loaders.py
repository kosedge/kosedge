"""Universe loaders for the hierarchical CFB season engine.

Preference order (same spirit as NFL depth cutover):

1. DB universe when session rows exist (optional / often empty on Railway)
2. Packaged ESPN 2026 real-roster snapshot overlay on team priors
3. Legacy curated / placeholder priors alone

Loaders never invent precision when rows are missing — derived returning /
portal-out numerics stay labeled approximate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from src.services.cfb_season_engine.coaching_continuity import build_coaching_continuity
from src.services.cfb_season_engine.conferences import load_conference_map
from src.services.cfb_season_engine.home_field import build_home_field_profile
from src.services.cfb_season_engine.player_hooks import build_player_hooks
from src.services.cfb_season_engine.position_groups import build_position_groups
from src.services.cfb_season_engine.qb_situation import build_qb_situation
from src.services.cfb_season_engine.real_roster import (
    ROSTER_SOURCE_LEGACY_PRIORS,
    ROSTER_SOURCE_PACKAGED_ESPN,
    apply_snapshot_team_payload,
    load_real_roster_snapshot,
    snapshot_meta,
)
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
PACKAGED_REAL_ROSTER = DATA_DIR / "cfb_real_roster_snapshot_2026.json"

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
                night_game=bool(row.get("night_game", False)),
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


def _team_state_from_payload(
    team: str,
    payload: Mapping[str, Any],
    *,
    default_source: str = "packaged_prior",
) -> Tuple[TeamProjectionState, List[PlayerHook]]:
    roster = build_roster_construction(
        team, payload.get("roster"), default_source=default_source
    )
    groups_payload = payload.get("position_groups") or {}
    # Wire OL/skill grades into QB supporting cast when packaged.
    qb = build_qb_situation(
        team,
        payload.get("qb"),
        ol_grade=groups_payload.get("ol"),
        skill_grade=groups_payload.get("skill"),
        default_source=default_source,
    )
    groups = build_position_groups(
        team,
        groups_payload,
        roster=roster,
        qb=qb,
        default_source=default_source,
    )
    home_field = build_home_field_profile(
        team,
        payload.get("home_field"),
        team_payload=payload,
    )
    coaching = build_coaching_continuity(team, payload.get("coaching"))
    state = compose_team_projection(
        team,
        roster,
        qb,
        groups,
        home_field=home_field,
        coaching=coaching,
    )
    # Optional pace / pass overrides from packaged strength hints.
    if "pace_factor" in payload:
        state.pace_factor = float(payload["pace_factor"])
    if "pass_rate_bias" in payload:
        state.pass_rate_bias = float(payload["pass_rate_bias"])
    hooks = build_player_hooks(team, payload.get("players"), qb=qb)
    return state, hooks


def _build_universe_from_team_payloads(
    *,
    season: int,
    teams_raw: Mapping[str, Any],
    blob_meta: Mapping[str, Any],
    roster_meta: Mapping[str, Any],
    mode: str,
    default_source: str,
) -> EngineUniverse:
    teams: Dict[str, TeamProjectionState] = {}
    hooks: Dict[str, List[PlayerHook]] = {}
    for code, payload in teams_raw.items():
        team = canonicalize_team_code(code)
        if team in teams:
            continue
        state, player_hooks = _team_state_from_payload(
            team, payload or {}, default_source=default_source
        )
        teams[team] = state
        if player_hooks:
            hooks[team] = player_hooks

    seed = load_packaged_schedule(season=season)
    known = set(teams)
    seed = [g for g in seed if g.home_team in known and g.away_team in known]
    conferences = load_conference_map()
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
        "mode": mode,
        "priors_as_of": str(blob_meta.get("as_of", "")),
        "priors_fidelity": str(blob_meta.get("fidelity", "approximate")),
        "team_count": str(len(teams)),
        "schedule_source": str(sched_meta.get("schedule_source", "packaged_sample_densified")),
        "schedule_fidelity": str(sched_meta.get("fidelity", "approximate")),
        "official_schedule": "false",
        "schedule_games": str(sched_meta.get("total_games", len(schedule))),
        "schedule_seed_kept": str(sched_meta.get("seed_games_kept", 0)),
        "schedule_densified_added": str(sched_meta.get("densified_added", 0)),
        "games_per_team_mean": str(sched_meta.get("games_per_team_mean", "")),
        "roster_source": str(roster_meta.get("roster_source", default_source)),
        "depth_source": str(roster_meta.get("depth_source", "")),
        "portal_source": str(roster_meta.get("portal_source", "")),
        "returning_source": str(roster_meta.get("returning_source", "")),
        "recruiting_source": str(roster_meta.get("recruiting_source", "")),
        "roster_as_of": str(roster_meta.get("as_of", blob_meta.get("as_of", ""))),
        "gap_official_schedule": "No official full 2026 FBS schedule in-repo; densified sample used",
        "primary_drivers": (
            "roster_strength + qb_situation_index + position_groups + "
            "variable_hfa + coaching_continuity"
        ),
        "scope": "FBS focus for 2026; v0.6 real-roster overlay",
        "schedule_note": str(sched_meta.get("note", "")),
        "gap_home_splits_feed": "No live home ATS / scoring-margin feed; venue proxies",
        "gap_coaching_feed": "No live coaching-change feed; curated/approximate flags",
        "gap_portal_out_feed": "Portal-out incomplete without full departure feed",
        "gap_measured_snap_pct": (
            "Returning snap/start shares are class-year proxies unless CFBD "
            "returning overlay was packaged"
        ),
    }
    return EngineUniverse(
        season=season,
        schedule=schedule,
        teams=teams,
        player_hooks=hooks,
        conferences=conferences,
        notes=notes,
    )


def build_packaged_universe(season: int = 2026) -> EngineUniverse:
    """Build FBS universe from packaged priors + real-roster snapshot when present."""
    cached = _PACKAGED_UNIVERSE_CACHE.get(int(season))
    if cached is not None:
        return cached

    blob = load_packaged_team_priors()
    teams_raw: Dict[str, Any] = dict(blob.get("teams") or {})
    snap = load_real_roster_snapshot()
    meta = snapshot_meta(snap)
    if snap and snap.get("teams"):
        for code, snap_team in (snap.get("teams") or {}).items():
            base = teams_raw.get(code) or {}
            teams_raw[code] = apply_snapshot_team_payload(base, snap_team)
        mode = "packaged_real_roster"
        default_source = str(meta.get("roster_source") or ROSTER_SOURCE_PACKAGED_ESPN)
    else:
        # Priors file may already contain a merged real-roster overlay.
        real_flag = blob.get("real_roster") or {}
        if real_flag.get("enabled"):
            mode = "packaged_real_roster"
            default_source = str(
                real_flag.get("roster_source") or ROSTER_SOURCE_PACKAGED_ESPN
            )
            sample_roster = (next(iter(teams_raw.values()), {}) or {}).get("roster") or {}
            meta = {
                "roster_source": default_source,
                "depth_source": str(real_flag.get("depth_source") or ""),
                "portal_source": str(real_flag.get("portal_source") or ""),
                "returning_source": str(sample_roster.get("returning_source") or ""),
                "as_of": str(blob.get("as_of") or ""),
                "coverage": {"team_count": len(teams_raw)},
            }
        else:
            mode = "packaged"
            default_source = ROSTER_SOURCE_LEGACY_PRIORS
            meta = {
                "roster_source": default_source,
                "depth_source": "none",
                "portal_source": "none",
                "returning_source": "none",
                "as_of": str(blob.get("as_of") or ""),
                "coverage": {},
            }

    universe = _build_universe_from_team_payloads(
        season=season,
        teams_raw=teams_raw,
        blob_meta=blob,
        roster_meta=meta,
        mode=mode,
        default_source=default_source,
    )
    _PACKAGED_UNIVERSE_CACHE[int(season)] = universe
    return universe


def build_demo_universe(season: int = 2026) -> EngineUniverse:
    """Alias — packaged universe (with real snapshot when present) is the offline demo."""
    return build_packaged_universe(season=season)


def load_universe_from_db(session: Any, *, season: int = 2026, as_of_week: int = 1) -> EngineUniverse:
    """Attempt DB-backed universe; falls back by raising when tables empty/unwired.

    Reserved for ``cfb_dp_*`` portal/roster/returning-production tables. Railway
    Postgres has been flaky — packaged ESPN snapshot is the reliable path.
    """
    raise NotImplementedError(
        "CFB season-engine DB universe not populated "
        f"(season={season} as_of_week={as_of_week}); use packaged ESPN snapshot"
    )


def resolve_season_universe(
    *,
    season: int = 2026,
    as_of_week: int = 1,
    demo: bool = False,
    session: Any = None,
) -> Tuple[EngineUniverse, Dict[str, Any]]:
    """Resolve universe with explicit mode + roster/depth/portal source metadata."""
    def _meta_from_universe(universe: EngineUniverse, mode: str, **extra: Any) -> Dict[str, Any]:
        notes = universe.notes or {}
        return {
            "mode": mode,
            "schedule_source": notes.get("schedule_source", "packaged"),
            "schedule_game_count": len(universe.schedule),
            "team_count": len(universe.teams),
            "as_of_week": as_of_week,
            "fidelity": notes.get("priors_fidelity", "approximate"),
            "roster_source": notes.get("roster_source", ROSTER_SOURCE_LEGACY_PRIORS),
            "depth_source": notes.get("depth_source", ""),
            "portal_source": notes.get("portal_source", ""),
            "returning_source": notes.get("returning_source", ""),
            "roster_as_of": notes.get("roster_as_of", ""),
            **extra,
        }

    # demo=True still prefers real packaged snapshot when present (not weak demo depth).
    if demo or session is None:
        universe = build_packaged_universe(season=season)
        return universe, _meta_from_universe(universe, universe.notes.get("mode", "packaged"))

    try:
        universe = load_universe_from_db(session, season=season, as_of_week=as_of_week)
        return universe, _meta_from_universe(universe, "db")
    except Exception as exc:
        universe = build_packaged_universe(season=season)
        return universe, _meta_from_universe(
            universe,
            "packaged_fallback",
            db_error=str(exc)[:240],
        )


def documentation() -> Dict[str, Any]:
    snap = load_real_roster_snapshot()
    meta = snapshot_meta(snap)
    return {
        "module": "src.services.cfb_season_engine.loaders",
        "packaged_teams": str(PACKAGED_TEAMS),
        "packaged_schedule": str(PACKAGED_SCHEDULE),
        "packaged_real_roster": str(PACKAGED_REAL_ROSTER),
        "schedule_policy": "seed sample + densify_schedule (not official FBS slate)",
        "preference_order": "DB → packaged ESPN real-roster snapshot → legacy priors",
        "db_universe": "not_populated (packaged snapshot is the Railway-safe path)",
        "roster_source": meta.get("roster_source"),
        "depth_source": meta.get("depth_source"),
        "portal_source": meta.get("portal_source"),
        "as_of": meta.get("as_of"),
        "coverage": meta.get("coverage"),
        "real_vs_approximate": (
            "Packaged ESPN roster snapshot is a REAL in-image artifact. Athlete "
            "identities / QB1 selection inputs are from ESPN 2026 rosters. "
            "Returning snap% and portal-out remain APPROXIMATE proxies. "
            "Densified schedule is APPROXIMATE. DB path is optional."
        ),
    }
