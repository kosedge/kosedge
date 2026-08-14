"""Official 2026 FBS schedule — ESPN team-schedule SoT (not densified).

Densified sample paths are never treated as official. If this package is
missing or thin, ``slate_complete`` stays false and season win tables are
research-only / not final.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.services.cfb_season_engine.conferences import conference_for
from src.services.cfb_season_engine.fbs_universe import (
    fcs_or_unknown_label,
    is_official_fbs,
    official_fbs_codes,
)
from src.services.cfb_season_engine.types import (
    EfficiencyProfile,
    PositionGroupGrades,
    QbSituation,
    RosterConstruction,
    ScheduledGame,
    TeamProjectionState,
)
from src.services.cfb_warehouse.identity import canonical_code, resolve_team_code

DATA_DIR = Path(__file__).resolve().parent / "data"
OFFICIAL_SCHEDULE_PATH = DATA_DIR / "cfb_official_schedule_2026.json"
WAREHOUSE_COPY = (
    Path(__file__).resolve().parents[5]
    / "data"
    / "cfb"
    / "warehouse"
    / "clean"
    / "schedules"
    / "cfb_official_schedule_2026.json"
)

# Research placeholder for FCS / non-FBS sides on the official slate.
FCS_OFFENSE_INDEX = 0.72
FCS_DEFENSE_INDEX = 0.72
FCS_UNCERTAINTY = 0.78


def load_official_schedule_blob(season: int = 2026) -> Dict[str, Any]:
    path = OFFICIAL_SCHEDULE_PATH
    if not path.is_file():
        return {
            "present": False,
            "season": int(season),
            "official": False,
            "slate_complete": False,
            "games": [],
            "source": "missing",
        }
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["present"] = True
    return raw


def games_from_blob(blob: Dict[str, Any], *, season: int = 2026) -> List[ScheduledGame]:
    games: List[ScheduledGame] = []
    seen = set()
    for row in blob.get("games") or []:
        home = canonical_code(str(row.get("home") or row.get("home_team") or ""))
        away = canonical_code(str(row.get("away") or row.get("away_team") or ""))
        if not home or not away or home == away:
            continue
        gid = str(row.get("game_id") or f"{season}_w{row.get('week')}_{away}@{home}")
        if gid in seen:
            continue
        seen.add(gid)
        kickoff = str(row.get("kickoff") or row.get("date") or "")
        night = bool(row.get("night_game"))
        if not night and len(kickoff) >= 16:
            try:
                hour = int(kickoff[11:13])
                night = hour >= 23 or hour < 4
            except ValueError:
                night = False
        games.append(
            ScheduledGame(
                season=int(row.get("season") or season),
                week=int(row.get("week") or 0),
                game_id=gid,
                home_team=home,
                away_team=away,
                neutral_site=bool(row.get("neutral_site") or row.get("neutral")),
                night_game=night,
                kickoff=kickoff,
                conference_game=bool(row.get("conference_game")),
                fcs_home=bool(row.get("fcs_home")),
                fcs_away=bool(row.get("fcs_away")),
                source_game_id=str(row.get("source_game_id") or row.get("espn_game_id") or ""),
            )
        )
    return sorted(games, key=lambda g: (g.week, g.kickoff, g.game_id))


def coverage_report(games: Sequence[ScheduledGame], *, official: Sequence[str]) -> Dict[str, Any]:
    official_set = {canonical_code(c) for c in official}
    by_week: Dict[str, int] = {}
    team_games: Counter[str] = Counter()
    fcs = 0
    for g in games:
        by_week[str(g.week)] = by_week.get(str(g.week), 0) + 1
        if g.home_team in official_set:
            team_games[g.home_team] += 1
        if g.away_team in official_set:
            team_games[g.away_team] += 1
        if g.fcs_home or g.fcs_away:
            fcs += 1
    missing_teams = sorted(c for c in official_set if team_games[c] == 0)
    thin = sorted(c for c in official_set if 0 < team_games[c] < 8)
    n_with_8 = sum(1 for c in official_set if team_games[c] >= 8)
    week0 = by_week.get("0", 0)
    week1 = by_week.get("1", 0)
    complete = (
        len(games) >= 700
        and n_with_8 >= 130
        and (week0 + week1) >= 20
        and len(missing_teams) == 0
    )
    return {
        "n_games": len(games),
        "by_week": dict(sorted(by_week.items(), key=lambda kv: int(kv[0]))),
        "fcs_games": fcs,
        "teams_with_8plus": n_with_8,
        "missing_teams": missing_teams,
        "thin_teams": thin,
        "week0_games": week0,
        "week1_games": week1,
        "independents_on_slate": {
            "ND": team_games.get("ND", 0),
            "CONN": team_games.get("CONN", 0),
        },
        "slate_complete": complete,
    }


def fcs_placeholder_state(team: str) -> TeamProjectionState:
    label = fcs_or_unknown_label(team) or "FCS / non-FBS"
    code = team if team.startswith("fcs:") else f"fcs:{canonical_code(team) or team}"
    return TeamProjectionState(
        team=code,
        offense_index=FCS_OFFENSE_INDEX,
        defense_index=FCS_DEFENSE_INDEX,
        pace_factor=1.0,
        early_season_uncertainty=FCS_UNCERTAINTY,
        roster=RosterConstruction(
            team=code,
            roster_strength=38.0,
            fidelity="placeholder",
            source="fcs_placeholder",
            notes=label,
        ),
        qb=QbSituation(
            team=code,
            qb_class="unknown",
            uncertainty=0.7,
            fidelity="placeholder",
            source="fcs_placeholder",
            notes=label,
        ),
        groups=PositionGroupGrades(
            team=code, fidelity="placeholder", source="fcs_placeholder", notes=label
        ),
        efficiency=EfficiencyProfile(
            team=code,
            fidelity="placeholder",
            source="fcs_placeholder",
            notes=label,
        ),
        source="fcs_placeholder",
        fidelity="placeholder",
        notes={"fcs": label, "not_generic_minus_25": "true"},
    )


def attach_fcs_placeholders(
    teams: Dict[str, TeamProjectionState],
    games: Sequence[ScheduledGame],
) -> Tuple[Dict[str, TeamProjectionState], int]:
    """Ensure every official-slate side exists. FCS sides get a labeled placeholder."""
    out = dict(teams)
    added = 0
    for g in games:
        for side, is_fcs in ((g.home_team, g.fcs_home), (g.away_team, g.fcs_away)):
            if side in out:
                continue
            if is_fcs or not is_official_fbs(side, include_transition=True):
                key = side if side.startswith("fcs:") else side
                if key not in out:
                    state = fcs_placeholder_state(side)
                    out[key] = state
                    added += 1
    return out, added


def documentation(blob: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    blob = blob if blob is not None else load_official_schedule_blob()
    games = games_from_blob(blob) if blob.get("present") else []
    cov = coverage_report(games, official=official_fbs_codes()) if games else {}
    return {
        "layer": "schedule",
        "name": "official_schedule",
        "module": "src.services.cfb_season_engine.official_schedule",
        "path": str(OFFICIAL_SCHEDULE_PATH),
        "warehouse_copy": str(WAREHOUSE_COPY),
        "present": bool(blob.get("present")),
        "official": bool(blob.get("official")),
        "source": blob.get("source"),
        "as_of": blob.get("as_of"),
        "densified": False,
        **cov,
        "note": (
            "ESPN public team schedules (seasontype=regular). "
            "Not the densified sample seed. CFP/bowls listed only if ESPN emitted them."
        ),
    }


def resolve_side(abbr: str, name: str, *, official: Sequence[str]) -> Tuple[str, bool]:
    known = {c: True for c in official}
    code = resolve_team_code(abbr=abbr, name=name, known_codes=known)
    if code:
        return code, False
    raw = canonical_code(abbr) or (name or "UNK")
    return f"fcs:{raw}", True
