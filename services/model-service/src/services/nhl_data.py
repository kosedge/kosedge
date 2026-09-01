"""NHL public data fetcher — raw snapshots only.

One vendor: official NHL (`*.nhle.com`). No shrink. No prior pack. No board emit.
No MoneyPuck / NST xG. Chapter 1 reads these files later and picks one ``s``.

Raw outputs (under ``nhl_season_engine/data/``):
  - nhl_schedule_2026.json       (2026–27 RS, ~84 games / team)
  - nhl_team_box_2025.json       (2025–26 GF/GA × 32)
  - nhl_skater_box_2023_2025.json
  - nhl_goalie_box_2023_2025.json
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx

log = logging.getLogger(__name__)

VENDOR = "nhl"
API_WEB_BASE = "https://api-web.nhle.com/v1"
STATS_REST_BASE = "https://api.nhle.com/stats/rest/en"

# Season ids used by NHL APIs (YYYYYYYY = startyear*10000+endyear).
SEASON_SCHEDULE = 20262027  # 2026–27 RS (open Sep 29)
SEASON_TEAM_BOX = 20252026  # 2025–26 GF/GA
TALENT_SEASONS = (20232024, 20242025, 20252026)  # 23–24 / 24–25 / 25–26
GAME_TYPE_RS = 2

FETCHER_VERSION = "nhl-fetcher-v1"

# 32 NHL clubs (2025–26 / 2026–27). Abbreviations match api-web.nhle.com.
NHL_TEAM_ABBREVS: Tuple[str, ...] = (
    "ANA",
    "BOS",
    "BUF",
    "CGY",
    "CAR",
    "CHI",
    "COL",
    "CBJ",
    "DAL",
    "DET",
    "EDM",
    "FLA",
    "LAK",
    "MIN",
    "MTL",
    "NSH",
    "NJD",
    "NYI",
    "NYR",
    "OTT",
    "PHI",
    "PIT",
    "SJS",
    "SEA",
    "STL",
    "TBL",
    "TOR",
    "UTA",
    "VAN",
    "VGK",
    "WPG",
    "WSH",
)

# …/services/model-service/src/services/nhl_data.py → repo root is parents[4]
ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = Path(__file__).resolve().parent / "nhl_season_engine" / "data"

SCHEDULE_PATH = DATA_DIR / "nhl_schedule_2026.json"
TEAM_BOX_PATH = DATA_DIR / "nhl_team_box_2025.json"
SKATER_BOX_PATH = DATA_DIR / "nhl_skater_box_2023_2025.json"
GOALIE_BOX_PATH = DATA_DIR / "nhl_goalie_box_2023_2025.json"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; KosEdgeNhlFetcher/1.0; +https://www.kosedge.com)"
    ),
    "Accept": "application/json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_label(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("default") or value.get("en") or None
    return str(value)


def raw_paths() -> Dict[str, Path]:
    return {
        "schedule": SCHEDULE_PATH,
        "team_box": TEAM_BOX_PATH,
        "skater_box": SKATER_BOX_PATH,
        "goalie_box": GOALIE_BOX_PATH,
    }


def _client(timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
    )


def _get_json(client: httpx.Client, url: str, *, params: Optional[Dict[str, Any]] = None) -> Any:
    last_exc: Optional[BaseException] = None
    for attempt in range(4):
        try:
            res = client.get(url, params=params)
            res.raise_for_status()
            return res.json()
        except Exception as exc:  # noqa: BLE001 — retry then raise
            last_exc = exc
            time.sleep(0.4 * (2**attempt))
    assert last_exc is not None
    raise last_exc


def fetch_standings_now(client: Optional[httpx.Client] = None) -> List[Dict[str, Any]]:
    """Current standings snapshot (api-web) — 32 teams with GF/GA."""
    own = client is None
    client = client or _client()
    try:
        payload = _get_json(client, f"{API_WEB_BASE}/standings/now")
        rows = payload.get("standings") or []
        if not isinstance(rows, list):
            raise RuntimeError("standings/now missing standings list")
        return rows
    finally:
        if own:
            client.close()


def build_team_box_2025(client: Optional[httpx.Client] = None) -> Dict[str, Any]:
    """Normalize 2025–26 team GF/GA for all 32 clubs from standings/now."""
    rows_raw = fetch_standings_now(client)
    teams: List[Dict[str, Any]] = []
    for row in rows_raw:
        abbrev = _default_label(row.get("teamAbbrev"))
        if not abbrev:
            continue
        abbrev = str(abbrev).upper()
        teams.append(
            {
                "team": abbrev,
                "team_name": _default_label(row.get("teamName")),
                "season_id": SEASON_TEAM_BOX,
                "games_played": row.get("gamesPlayed"),
                "gf": row.get("goalFor"),
                "ga": row.get("goalAgainst"),
                "wins": row.get("wins"),
                "losses": row.get("losses"),
                "ot_losses": row.get("otLosses"),
                "points": row.get("points"),
                "conference": row.get("conferenceAbbrev"),
                "division": row.get("divisionAbbrev"),
            }
        )
    teams.sort(key=lambda t: str(t.get("team") or ""))
    return {
        "vendor": VENDOR,
        "source": f"{API_WEB_BASE}/standings/now",
        "fetcher_version": FETCHER_VERSION,
        "season_id": SEASON_TEAM_BOX,
        "season_label": "2025-26",
        "game_type": GAME_TYPE_RS,
        "fetched_at": _utc_now(),
        "n_teams": len(teams),
        "teams": teams,
    }


def fetch_club_schedule_season(
    team: str,
    season_id: int = SEASON_SCHEDULE,
    client: Optional[httpx.Client] = None,
) -> List[Dict[str, Any]]:
    own = client is None
    client = client or _client()
    try:
        url = f"{API_WEB_BASE}/club-schedule-season/{team.upper()}/{season_id}"
        payload = _get_json(client, url)
        games = payload.get("games") or []
        return list(games) if isinstance(games, list) else []
    finally:
        if own:
            client.close()


def _normalize_schedule_game(raw: Dict[str, Any]) -> Dict[str, Any]:
    away = raw.get("awayTeam") or {}
    home = raw.get("homeTeam") or {}
    return {
        "game_id": raw.get("id"),
        "game_date": raw.get("gameDate") or (str(raw.get("startTimeUTC") or "")[:10] or None),
        "start_time_utc": raw.get("startTimeUTC"),
        "game_type": raw.get("gameType"),
        "game_state": raw.get("gameState"),
        "away": (away.get("abbrev") or "").upper() or None,
        "home": (home.get("abbrev") or "").upper() or None,
        "away_score": away.get("score"),
        "home_score": home.get("score"),
        "venue": _default_label((raw.get("venue") or {})),
    }


def build_schedule_2026(
    *,
    teams: Sequence[str] = NHL_TEAM_ABBREVS,
    client: Optional[httpx.Client] = None,
) -> Dict[str, Any]:
    """League RS schedule for 2026–27 via club-schedule-season (deduped)."""
    own = client is None
    client = client or _client()
    try:
        by_id: Dict[Any, Dict[str, Any]] = {}
        for i, team in enumerate(teams):
            games = fetch_club_schedule_season(team, SEASON_SCHEDULE, client=client)
            for g in games:
                if int(g.get("gameType") or 0) != GAME_TYPE_RS:
                    continue
                gid = g.get("id")
                if gid is None:
                    continue
                by_id[gid] = _normalize_schedule_game(g)
            if i < len(teams) - 1:
                time.sleep(0.05)
        rows = sorted(
            by_id.values(),
            key=lambda r: (
                str(r.get("game_date") or ""),
                str(r.get("game_id") or ""),
            ),
        )
        return {
            "vendor": VENDOR,
            "source": f"{API_WEB_BASE}/club-schedule-season/{{team}}/{SEASON_SCHEDULE}",
            "fetcher_version": FETCHER_VERSION,
            "season_id": SEASON_SCHEDULE,
            "season_label": "2026-27",
            "game_type": GAME_TYPE_RS,
            "fetched_at": _utc_now(),
            "n_games": len(rows),
            "n_teams": len(teams),
            "opening_night": "2026-09-29",
            "games": rows,
        }
    finally:
        if own:
            client.close()


def _paginate_stats_summary(
    client: httpx.Client,
    *,
    kind: str,
    season_id: int,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """kind = 'skater' | 'goalie'."""
    url = f"{STATS_REST_BASE}/{kind}/summary"
    cayenne = f"seasonId={season_id} and gameTypeId={GAME_TYPE_RS}"
    start = 0
    out: List[Dict[str, Any]] = []
    total: Optional[int] = None
    while True:
        payload = _get_json(
            client,
            url,
            params={"cayenneExp": cayenne, "limit": page_size, "start": start},
        )
        chunk = payload.get("data") or []
        if total is None:
            total = int(payload.get("total") or 0)
        if not chunk:
            break
        out.extend(chunk)
        start += len(chunk)
        if total is not None and start >= total:
            break
        if len(chunk) < page_size:
            break
        time.sleep(0.05)
    return out


def _normalize_skater(row: Dict[str, Any], season_id: int) -> Dict[str, Any]:
    return {
        "player_id": row.get("playerId"),
        "player_name": row.get("skaterFullName") or row.get("lastName"),
        "team": (row.get("teamAbbrevs") or "").upper() or None,
        "position": row.get("positionCode"),
        "season_id": season_id,
        "gp": row.get("gamesPlayed"),
        "g": row.get("goals"),
        "a": row.get("assists"),
        "p": row.get("points"),
        "sog": row.get("shots"),
        "toi_per_game": row.get("timeOnIcePerGame"),
        "plus_minus": row.get("plusMinus"),
        "pim": row.get("penaltyMinutes"),
    }


def _normalize_goalie(row: Dict[str, Any], season_id: int) -> Dict[str, Any]:
    return {
        "player_id": row.get("playerId"),
        "player_name": row.get("goalieFullName") or row.get("lastName"),
        "team": (row.get("teamAbbrevs") or "").upper() or None,
        "season_id": season_id,
        "gp": row.get("gamesPlayed"),
        "gs": row.get("gamesStarted"),
        "w": row.get("wins"),
        "l": row.get("losses"),
        "otl": row.get("otLosses"),
        "gaa": row.get("goalsAgainstAverage"),
        "sv_pct": row.get("savePct"),
        "saves": row.get("saves"),
        "sa": row.get("shotsAgainst"),
        "ga": row.get("goalsAgainst"),
        "so": row.get("shutouts"),
        "toi": row.get("timeOnIce"),
    }


def build_skater_box_2023_2025(client: Optional[httpx.Client] = None) -> Dict[str, Any]:
    own = client is None
    client = client or _client()
    try:
        by_season: Dict[str, List[Dict[str, Any]]] = {}
        for season_id in TALENT_SEASONS:
            raw = _paginate_stats_summary(client, kind="skater", season_id=season_id)
            by_season[str(season_id)] = [
                _normalize_skater(r, season_id) for r in raw
            ]
        n = sum(len(v) for v in by_season.values())
        return {
            "vendor": VENDOR,
            "source": f"{STATS_REST_BASE}/skater/summary",
            "fetcher_version": FETCHER_VERSION,
            "seasons": list(TALENT_SEASONS),
            "season_labels": ["2023-24", "2024-25", "2025-26"],
            "game_type": GAME_TYPE_RS,
            "fetched_at": _utc_now(),
            "n_rows": n,
            "by_season": by_season,
        }
    finally:
        if own:
            client.close()


def build_goalie_box_2023_2025(client: Optional[httpx.Client] = None) -> Dict[str, Any]:
    own = client is None
    client = client or _client()
    try:
        by_season: Dict[str, List[Dict[str, Any]]] = {}
        for season_id in TALENT_SEASONS:
            raw = _paginate_stats_summary(client, kind="goalie", season_id=season_id)
            by_season[str(season_id)] = [
                _normalize_goalie(r, season_id) for r in raw
            ]
        n = sum(len(v) for v in by_season.values())
        return {
            "vendor": VENDOR,
            "source": f"{STATS_REST_BASE}/goalie/summary",
            "fetcher_version": FETCHER_VERSION,
            "seasons": list(TALENT_SEASONS),
            "season_labels": ["2023-24", "2024-25", "2025-26"],
            "game_type": GAME_TYPE_RS,
            "fetched_at": _utc_now(),
            "n_rows": n,
            "by_season": by_season,
        }
    finally:
        if own:
            client.close()


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_raw_snapshots(*, client: Optional[httpx.Client] = None) -> Dict[str, Any]:
    """Fetch all raw tables and write checked-in snapshot files."""
    own = client is None
    client = client or _client()
    try:
        schedule = build_schedule_2026(client=client)
        team_box = build_team_box_2025(client=client)
        skaters = build_skater_box_2023_2025(client=client)
        goalies = build_goalie_box_2023_2025(client=client)

        _write_json(SCHEDULE_PATH, schedule)
        _write_json(TEAM_BOX_PATH, team_box)
        _write_json(SKATER_BOX_PATH, skaters)
        _write_json(GOALIE_BOX_PATH, goalies)

        summary = {
            "fetcher_version": FETCHER_VERSION,
            "vendor": VENDOR,
            "written_at": _utc_now(),
            "paths": {k: str(v.relative_to(ROOT)) for k, v in raw_paths().items()},
            "n_schedule_games": schedule.get("n_games"),
            "n_teams": team_box.get("n_teams"),
            "n_skater_rows": skaters.get("n_rows"),
            "n_goalie_rows": goalies.get("n_rows"),
            "does_not": [
                "NHL_TEAM_CARRY_SHRINK",
                "nhl_team_prior_2026.json",
                "KEI / Edge tags",
                "xG from MoneyPuck/NST",
                "NBA/WNBA/CFB/NFL",
            ],
        }
        return summary
    finally:
        if own:
            client.close()


def load_schedule_pack() -> Dict[str, Any]:
    if not SCHEDULE_PATH.exists():
        return {"present": False, "games": []}
    return json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))


def load_team_box_pack() -> Dict[str, Any]:
    if not TEAM_BOX_PATH.exists():
        return {"present": False, "teams": []}
    return json.loads(TEAM_BOX_PATH.read_text(encoding="utf-8"))


def load_skater_box_pack() -> Dict[str, Any]:
    if not SKATER_BOX_PATH.exists():
        return {"present": False, "by_season": {}}
    return json.loads(SKATER_BOX_PATH.read_text(encoding="utf-8"))


def load_goalie_box_pack() -> Dict[str, Any]:
    if not GOALIE_BOX_PATH.exists():
        return {"present": False, "by_season": {}}
    return json.loads(GOALIE_BOX_PATH.read_text(encoding="utf-8"))


def opening_night_has_fla_at_car(schedule: Optional[Dict[str, Any]] = None) -> bool:
    pack = schedule if schedule is not None else load_schedule_pack()
    for g in pack.get("games") or []:
        if (
            str(g.get("game_date") or "") == "2026-09-29"
            and str(g.get("away") or "").upper() == "FLA"
            and str(g.get("home") or "").upper() == "CAR"
        ):
            return True
    return False


def documentation() -> Dict[str, Any]:
    return {
        "module": "src.services.nhl_data",
        "fetcher_version": FETCHER_VERSION,
        "vendor": VENDOR,
        "api_web": API_WEB_BASE,
        "stats_rest": STATS_REST_BASE,
        "data_dir": str(DATA_DIR.relative_to(ROOT)),
        "files": {k: str(v.relative_to(ROOT)) for k, v in raw_paths().items()},
        "refresh": "python3 scripts/nhl/fetch_raw.py",
        "does_not": [
            "shrink / prior pack",
            "KEINHL board emit",
            "MoneyPuck/NST xG",
            "Ch1 s pick",
        ],
    }
