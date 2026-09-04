"""Official NCAAM schedule — ESPN scoreboard SoT (Option A).

Mirrors CFB ``official_schedule.py`` shape, not football semantics.

Honesty:
  - Packaged JSON may be a B7-mapped subset of ESPN events (fail-closed).
  - ``slate_complete`` stays false unless the pack itself stamps true after an
    honest densified full-D1 join — never claim complete from a thin map.
  - Lab interim joins still use Odds ``event_id`` (track D). This package exposes
    ESPN ``game_id`` + null crosswalk stubs for a future E hybrid; do not invent
    Odds↔ESPN links without evidence.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TypedDict

DATA_DIR = Path(__file__).resolve().parent / "data"

# Season key = academic year label (start_year-end_year), e.g. "2022-23".
DEFAULT_SEASON_KEY = "2022-23"


class ScheduledNcaamGame(TypedDict, total=False):
    season: str
    season_end_year: int
    game_id: str
    espn_game_id: str
    tipoff: str
    date: str
    home: str
    away: str
    home_name: str
    away_name: str
    home_espn_id: str
    away_espn_id: str
    neutral_site: bool
    conference_game: bool
    venue: str
    venue_city: str
    venue_state: str
    home_score: Optional[float]
    away_score: Optional[float]
    status: str
    season_type: str
    odds_event_id: Optional[str]
    map_status: str


def schedule_path_for_season(season_key: str = DEFAULT_SEASON_KEY) -> Path:
    """Resolve packaged path for an academic season key (``2022-23``)."""
    safe = str(season_key).strip().replace("/", "-")
    return DATA_DIR / f"ncaam_official_schedule_{safe.replace('-', '_')}.json"


def load_official_schedule_blob(season_key: str = DEFAULT_SEASON_KEY) -> Dict[str, Any]:
    path = schedule_path_for_season(season_key)
    if not path.is_file():
        return {
            "present": False,
            "season": season_key,
            "official": False,
            "slate_complete": False,
            "games": [],
            "source": "missing",
        }
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["present"] = True
    # Hard honesty: never promote thin packs.
    if not bool(raw.get("slate_complete")):
        raw["slate_complete"] = False
    return raw


def games_from_blob(
    blob: Dict[str, Any], *, season_key: str = DEFAULT_SEASON_KEY
) -> List[ScheduledNcaamGame]:
    """Return mapped games only. Rows missing both B7 sides are skipped (fail-closed)."""
    games: List[ScheduledNcaamGame] = []
    seen: set[str] = set()
    for row in blob.get("games") or []:
        home = str(row.get("home") or row.get("home_team") or "").strip()
        away = str(row.get("away") or row.get("away_team") or "").strip()
        if not home or not away or home == away:
            continue
        espn_gid = str(row.get("espn_game_id") or row.get("source_game_id") or "").strip()
        gid = str(row.get("game_id") or espn_gid or "").strip()
        if not gid:
            tip = str(row.get("tipoff") or row.get("kickoff") or row.get("date") or "")
            date = tip[:10] if tip else "unknown"
            gid = f"ncaam:{date}:{away}@{home}"
        if gid in seen:
            continue
        seen.add(gid)
        tipoff = str(row.get("tipoff") or row.get("kickoff") or row.get("date") or "")
        home_score = _as_float(row.get("home_score"))
        away_score = _as_float(row.get("away_score"))
        status = str(row.get("status") or "").strip().lower()
        if home_score is not None and away_score is not None and not status:
            status = "final"
        # Crosswalk stub — never invent Odds links.
        odds_event_id = row.get("odds_event_id")
        if odds_event_id is not None and str(odds_event_id).strip() == "":
            odds_event_id = None
        games.append(
            ScheduledNcaamGame(
                season=str(row.get("season") or season_key),
                season_end_year=int(
                    row.get("season_end_year") or blob.get("season_end_year") or 0
                ),
                game_id=gid,
                espn_game_id=espn_gid or gid,
                tipoff=tipoff,
                date=str(row.get("date") or (tipoff[:10] if tipoff else "")),
                home=home,
                away=away,
                home_name=str(row.get("home_name") or ""),
                away_name=str(row.get("away_name") or ""),
                home_espn_id=str(row.get("home_espn_id") or ""),
                away_espn_id=str(row.get("away_espn_id") or ""),
                neutral_site=bool(row.get("neutral_site") or row.get("neutral")),
                conference_game=bool(row.get("conference_game")),
                venue=str(row.get("venue") or ""),
                venue_city=str(row.get("venue_city") or ""),
                venue_state=str(row.get("venue_state") or ""),
                home_score=home_score,
                away_score=away_score,
                status=status,
                season_type=str(row.get("season_type") or "regular"),
                odds_event_id=odds_event_id if odds_event_id is None else str(odds_event_id),
                map_status=str(row.get("map_status") or "b7_both"),
            )
        )
    return sorted(games, key=lambda g: (g.get("tipoff") or "", g.get("game_id") or ""))


def coverage_report(games: Sequence[ScheduledNcaamGame]) -> Dict[str, Any]:
    by_month: Dict[str, int] = {}
    team_games: Counter[str] = Counter()
    miami_fl = 0
    miami_oh = 0
    for g in games:
        tip = str(g.get("tipoff") or g.get("date") or "")
        month = tip[:7] if len(tip) >= 7 else "unknown"
        by_month[month] = by_month.get(month, 0) + 1
        home = str(g.get("home") or "")
        away = str(g.get("away") or "")
        if home:
            team_games[home] += 1
        if away:
            team_games[away] += 1
        sides = {home, away}
        if "miami fl" in sides:
            miami_fl += 1
        if "miami oh" in sides:
            miami_oh += 1
    # Completeness is never inferred from a mapped subset alone.
    return {
        "n_games": len(games),
        "n_teams": len(team_games),
        "by_month": dict(sorted(by_month.items())),
        "miami_fl_games": miami_fl,
        "miami_oh_games": miami_oh,
        "miami_fl_ne_miami_oh": miami_fl == 0
        or miami_oh == 0
        or ("miami fl" in team_games and "miami oh" in team_games),
        "slate_complete": False,
        "slate_complete_note": (
            "Mapped B7 subset of ESPN scoreboard — thin ≠ complete. "
            "Do not stamp slate_complete=true without an honest full-D1 densified join."
        ),
    }


def documentation(blob: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    blob = blob if blob is not None else load_official_schedule_blob()
    season_key = str(blob.get("season") or DEFAULT_SEASON_KEY)
    games = games_from_blob(blob, season_key=season_key) if blob.get("present") else []
    cov = coverage_report(games) if games else {"n_games": 0, "slate_complete": False}
    return {
        "layer": "schedule",
        "name": "ncaam_official_schedule",
        "module": "src.services.ncaam_schedule.official_schedule",
        "path": str(schedule_path_for_season(season_key)),
        "present": bool(blob.get("present")),
        "official": bool(blob.get("official")),
        "source": blob.get("source"),
        "as_of": blob.get("as_of"),
        "densified": False,
        "lab_join_note": (
            "Schedule SoT LOCKED Option A (ESPN). Lab interim joins still use Odds "
            "event_id (D). odds_event_id on rows stays null until evidenced E hybrid."
        ),
        **cov,
        "map_stats": blob.get("map_stats") or {},
        "note": (
            "ESPN public mens-college-basketball scoreboard (groups=50). "
            "B7 fail-closed map via apps/web ncaam identity / aliases.json. "
            "Unknown or ambiguous sides omitted — never invented."
        ),
    }


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
