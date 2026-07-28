from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

NFL_COM_BASE_URL = "https://api.nfl.com"
NFL_COM_DEFAULT_TIMEOUT_SECONDS = float(os.getenv("NFL_COM_TIMEOUT_SECONDS", "8.0"))
NFL_COM_DEFAULT_RETRIES = int(os.getenv("NFL_COM_RETRIES", "2"))
NFL_COM_USER_AGENT = os.getenv(
    "NFL_COM_USER_AGENT",
    "kosedge-data-platform-nfl/0.1 (+https://kosedge.local; team-intel-ingest)",
)


class NflComError(RuntimeError):
    pass


class NflComAuthError(NflComError):
    pass


@dataclass
class NflComDiagnostics:
    auth_mode: str
    season: int
    week: Optional[int]
    season_type: Optional[str]
    rosters_endpoint: str
    standings_endpoint: str
    team_stats_endpoint: str
    errors: List[str]


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _iter_candidates(payload: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(payload, dict):
        for key in ("items", "data", "teams", "results"):
            maybe_items = payload.get(key)
            if isinstance(maybe_items, list):
                for item in maybe_items:
                    if isinstance(item, dict):
                        yield item
                return
        yield payload


def _extract_team_code(row: Dict[str, Any]) -> Optional[str]:
    direct_keys = (
        "team_abbreviation",
        "teamAbbreviation",
        "abbreviation",
        "abbr",
        "team",
        "team_code",
        "teamCode",
    )
    for key in direct_keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    team_obj = row.get("team")
    if isinstance(team_obj, dict):
        for key in ("abbreviation", "abbr", "team_abbreviation"):
            value = team_obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
    return None


def _pick_metric(source: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key in source:
            parsed = _to_float(source.get(key))
            if parsed is not None:
                return parsed
    return None


def _fetch_json(
    *,
    path: str,
    query: Optional[Dict[str, Any]],
    token: str,
    timeout_seconds: float = NFL_COM_DEFAULT_TIMEOUT_SECONDS,
    retries: int = NFL_COM_DEFAULT_RETRIES,
) -> Any:
    query = query or {}
    query_text = urlencode({k: v for k, v in query.items() if v is not None})
    url = f"{NFL_COM_BASE_URL}{path}"
    if query_text:
        url = f"{url}?{query_text}"

    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {token}",
        "user-agent": NFL_COM_USER_AGENT,
    }
    attempts = max(1, retries + 1)
    last_error: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        request = Request(url=url, method="GET", headers=headers)
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                if not body:
                    return {}
                return json.loads(body)
        except HTTPError as exc:
            body_text = ""
            try:
                body_text = exc.read().decode("utf-8")
            except Exception:
                body_text = ""
            if exc.code in (401, 403):
                raise NflComAuthError(
                    f"NFL.com auth failed ({exc.code}) for {path}: {body_text[:200]}"
                ) from exc
            if exc.code in (404, 429, 500, 502, 503, 504):
                last_error = exc
                if attempt < attempts:
                    time.sleep(0.45 * attempt)
                    continue
            raise NflComError(f"NFL.com request failed ({exc.code}) for {path}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(0.45 * attempt)
                continue
            raise NflComError(f"NFL.com request failed for {path}: {exc}") from exc

    raise NflComError(f"NFL.com request exhausted retries for {path}: {last_error}")


def _mint_token_from_client_credentials() -> Optional[str]:
    client_id = os.getenv("NFL_COM_CLIENT_ID")
    client_key = os.getenv("NFL_COM_CLIENT_KEY")
    client_secret = os.getenv("NFL_COM_CLIENT_SECRET")
    device_id = os.getenv("NFL_COM_DEVICE_ID")
    if not client_id or not client_key or not client_secret or not device_id:
        return None

    request = Request(
        url=f"{NFL_COM_BASE_URL}/identity/v1/token/client",
        method="POST",
        headers={
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": NFL_COM_USER_AGENT,
        },
        data=json.dumps(
            {
                "clientId": client_id,
                "clientKey": client_key,
                "clientSecret": client_secret,
                "deviceId": device_id,
                "useRefreshToken": False,
            }
        ).encode("utf-8"),
    )
    try:
        with urlopen(request, timeout=NFL_COM_DEFAULT_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
            token = payload.get("accessToken")
            if isinstance(token, str) and token.strip():
                return token.strip()
    except Exception:
        return None
    return None


def _resolve_auth_token() -> Tuple[str, str]:
    static_token = os.getenv("NFL_COM_BEARER_TOKEN")
    if static_token and static_token.strip():
        return static_token.strip(), "bearer_env"
    minted = _mint_token_from_client_credentials()
    if minted:
        return minted, "client_credentials"
    raise NflComAuthError("NFL.com auth is not configured")


def _resolve_week_context(token: str) -> Tuple[Optional[int], Optional[str]]:
    today = date.today().isoformat()
    payload = _fetch_json(path=f"/football/v2/weeks/date/{today}", query=None, token=token)
    row = next(iter(_iter_candidates(payload)), {})
    week = _to_int(row.get("week") or row.get("week_number") or row.get("number"))
    season_type = (
        str(
            row.get("seasonType")
            or row.get("season_type")
            or row.get("type")
            or "REG"
        )
        .strip()
        .upper()
    )
    if season_type not in {"PRE", "REG", "POST"}:
        season_type = "REG"
    return week, season_type


def _parse_rosters(payload: Any, season: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for team_row in _iter_candidates(payload):
        team = _extract_team_code(team_row)
        if not team:
            continue
        persons = team_row.get("persons") or team_row.get("players") or []
        if not isinstance(persons, list):
            continue
        for person in persons:
            if not isinstance(person, dict):
                continue
            player_id = (
                str(
                    person.get("person_gsis_id")
                    or person.get("gsis_id")
                    or person.get("id")
                    or person.get("player_id")
                    or ""
                )
                .strip()
            )
            if not player_id:
                continue
            first = str(person.get("person_first_name") or person.get("first_name") or "").strip()
            last = str(person.get("person_last_name") or person.get("last_name") or "").strip()
            display_name = str(
                person.get("person_display_name")
                or person.get("display_name")
                or f"{first} {last}".strip()
                or ""
            ).strip()
            rows.append(
                {
                    "season": season,
                    "team": team,
                    "player_id": player_id,
                    "player_name": display_name or None,
                    "position": (
                        str(person.get("position") or person.get("position_abbr") or "")
                        .strip()
                        .upper()
                        or None
                    ),
                    "jersey_number": str(person.get("jersey_number") or person.get("jersey") or "").strip(),
                }
            )
    return rows


def _parse_standings(payload: Any, season: int, week: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for team_row in _iter_candidates(payload):
        team = _extract_team_code(team_row)
        if not team:
            continue
        wins = _to_int(team_row.get("wins")) or 0
        losses = _to_int(team_row.get("losses")) or 0
        ties = _to_int(team_row.get("ties")) or 0
        points_for = _to_int(team_row.get("points_for") or team_row.get("pointsFor")) or 0
        points_against = _to_int(team_row.get("points_against") or team_row.get("pointsAgainst")) or 0
        win_pct = _to_float(team_row.get("win_pct") or team_row.get("winPct"))
        rows.append(
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
                "win_pct": win_pct,
                "conference": team_row.get("conference"),
                "division": team_row.get("division"),
                "conference_wins": _to_int(team_row.get("conference_wins")),
                "conference_losses": _to_int(team_row.get("conference_losses")),
                "conference_ties": _to_int(team_row.get("conference_ties")),
                "conference_pct": _to_float(team_row.get("conference_pct")),
                "division_wins": _to_int(team_row.get("division_wins")),
                "division_losses": _to_int(team_row.get("division_losses")),
                "division_ties": _to_int(team_row.get("division_ties")),
                "division_pct": _to_float(team_row.get("division_pct")),
            }
        )
    return rows


def _parse_team_stats(payload: Any, season: int, week: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in _iter_candidates(payload):
        team = _extract_team_code(item)
        if not team:
            continue
        stats_obj = item.get("stats")
        if not isinstance(stats_obj, dict):
            stats_obj = item

        offensive_plays = _to_int(
            _pick_metric(stats_obj, "offensive_plays", "offensivePlays", "total_plays")
        )
        pass_plays = _to_int(_pick_metric(stats_obj, "pass_plays", "passPlays", "pass_attempts"))
        run_plays = _to_int(_pick_metric(stats_obj, "run_plays", "runPlays", "rush_attempts"))

        if offensive_plays is None and pass_plays is not None and run_plays is not None:
            offensive_plays = pass_plays + run_plays
        if offensive_plays is None:
            continue

        early_down_plays = _to_int(_pick_metric(stats_obj, "early_down_plays", "earlyDownPlays"))
        early_down_pass_plays = _to_int(
            _pick_metric(stats_obj, "early_down_pass_plays", "earlyDownPassPlays")
        )
        third_down_attempts = _to_int(
            _pick_metric(stats_obj, "third_down_attempts", "thirdDownAttempts")
        )
        third_down_conversions = _to_int(
            _pick_metric(stats_obj, "third_down_conversions", "thirdDownConversions")
        )
        fourth_down_attempts = _to_int(
            _pick_metric(stats_obj, "fourth_down_attempts", "fourthDownAttempts")
        )
        fourth_down_conversions = _to_int(
            _pick_metric(stats_obj, "fourth_down_conversions", "fourthDownConversions")
        )
        red_zone_plays = _to_int(_pick_metric(stats_obj, "red_zone_plays", "redZonePlays"))
        red_zone_touchdowns = _to_int(
            _pick_metric(stats_obj, "red_zone_touchdowns", "redZoneTouchdowns")
        )

        pass_rate = _to_float(_pick_metric(stats_obj, "pass_rate", "passRate"))
        if pass_rate is None and offensive_plays and pass_plays is not None:
            pass_rate = float(pass_plays) / float(offensive_plays)

        early_down_pass_rate = _to_float(
            _pick_metric(stats_obj, "early_down_pass_rate", "earlyDownPassRate")
        )
        if (
            early_down_pass_rate is None
            and early_down_plays
            and early_down_pass_plays is not None
            and early_down_plays > 0
        ):
            early_down_pass_rate = float(early_down_pass_plays) / float(early_down_plays)

        third_down_conversion_rate = _to_float(
            _pick_metric(stats_obj, "third_down_conversion_rate", "thirdDownConversionRate")
        )
        if (
            third_down_conversion_rate is None
            and third_down_attempts
            and third_down_conversions is not None
            and third_down_attempts > 0
        ):
            third_down_conversion_rate = float(third_down_conversions) / float(third_down_attempts)

        fourth_down_conversion_rate = _to_float(
            _pick_metric(stats_obj, "fourth_down_conversion_rate", "fourthDownConversionRate")
        )
        if (
            fourth_down_conversion_rate is None
            and fourth_down_attempts
            and fourth_down_conversions is not None
            and fourth_down_attempts > 0
        ):
            fourth_down_conversion_rate = float(fourth_down_conversions) / float(fourth_down_attempts)

        red_zone_td_rate = _to_float(_pick_metric(stats_obj, "red_zone_td_rate", "redZoneTdRate"))
        if red_zone_td_rate is None and red_zone_plays and red_zone_touchdowns is not None and red_zone_plays > 0:
            red_zone_td_rate = float(red_zone_touchdowns) / float(red_zone_plays)

        rows.append(
            {
                "season": season,
                "week": week,
                "team": team,
                "games_played": _to_int(_pick_metric(stats_obj, "games_played", "gamesPlayed")) or 1,
                "offensive_plays": offensive_plays,
                "defensive_plays": _to_int(
                    _pick_metric(stats_obj, "defensive_plays", "defensivePlays")
                )
                or 0,
                "pass_plays": pass_plays or 0,
                "run_plays": run_plays or 0,
                "early_down_plays": early_down_plays or 0,
                "early_down_pass_plays": early_down_pass_plays or 0,
                "third_down_attempts": third_down_attempts or 0,
                "third_down_conversions": third_down_conversions or 0,
                "fourth_down_attempts": fourth_down_attempts or 0,
                "fourth_down_conversions": fourth_down_conversions or 0,
                "red_zone_plays": red_zone_plays or 0,
                "red_zone_touchdowns": red_zone_touchdowns or 0,
                "sacks_allowed": _to_int(_pick_metric(stats_obj, "sacks_allowed", "sacksAllowed")) or 0,
                "qb_hits_allowed": _to_int(_pick_metric(stats_obj, "qb_hits_allowed", "qbHitsAllowed")) or 0,
                "sacks_generated": _to_int(_pick_metric(stats_obj, "sacks_generated", "sacksGenerated")) or 0,
                "qb_hits_generated": _to_int(
                    _pick_metric(stats_obj, "qb_hits_generated", "qbHitsGenerated")
                )
                or 0,
                "explosive_pass_plays": _to_int(
                    _pick_metric(stats_obj, "explosive_pass_plays", "explosivePassPlays")
                )
                or 0,
                "explosive_pass_allowed": _to_int(
                    _pick_metric(stats_obj, "explosive_pass_allowed", "explosivePassAllowed")
                )
                or 0,
                "pass_rate": pass_rate,
                "early_down_pass_rate": early_down_pass_rate,
                "third_down_conversion_rate": third_down_conversion_rate,
                "fourth_down_conversion_rate": fourth_down_conversion_rate,
                "red_zone_td_rate": red_zone_td_rate,
                "pressure_rate_allowed": _to_float(
                    _pick_metric(stats_obj, "pressure_rate_allowed", "pressureRateAllowed")
                ),
                "pressure_rate_generated": _to_float(
                    _pick_metric(stats_obj, "pressure_rate_generated", "pressureRateGenerated")
                ),
                "success_rate_offense": _to_float(
                    _pick_metric(stats_obj, "success_rate_offense", "successRateOffense")
                ),
                "success_rate_defense_allowed": _to_float(
                    _pick_metric(
                        stats_obj,
                        "success_rate_defense_allowed",
                        "successRateDefenseAllowed",
                    )
                ),
                "epa_per_play_offense": _to_float(
                    _pick_metric(stats_obj, "epa_per_play_offense", "epaPerPlayOffense")
                ),
                "epa_per_play_defense_allowed": _to_float(
                    _pick_metric(
                        stats_obj,
                        "epa_per_play_defense_allowed",
                        "epaPerPlayDefenseAllowed",
                    )
                ),
            }
        )
    return rows


def fetch_nfl_com_team_intel_snapshot(
    *,
    season: int,
    week: Optional[int] = None,
    season_type: Optional[str] = None,
) -> Dict[str, Any]:
    token, auth_mode = _resolve_auth_token()
    resolved_week = week
    resolved_season_type = season_type
    errors: List[str] = []

    if resolved_week is None or not resolved_season_type:
        try:
            week_from_date, season_type_from_date = _resolve_week_context(token)
            if resolved_week is None:
                resolved_week = week_from_date
            if not resolved_season_type:
                resolved_season_type = season_type_from_date
        except Exception as exc:
            errors.append(f"week_context:{exc}")

    if not resolved_season_type:
        resolved_season_type = "REG"

    rosters_path = "/football/v2/rosters"
    standings_path = "/football/v2/standings"
    team_stats_path = "/football/v2/stats/team-stats"

    rosters_rows: List[Dict[str, Any]] = []
    standings_rows: List[Dict[str, Any]] = []
    team_stats_rows: List[Dict[str, Any]] = []

    try:
        rosters_payload = _fetch_json(
            path=rosters_path,
            query={"season": season, "limit": 300},
            token=token,
        )
        rosters_rows = _parse_rosters(rosters_payload, season)
    except Exception as exc:
        errors.append(f"rosters:{exc}")

    if resolved_week is not None:
        try:
            standings_payload = _fetch_json(
                path=standings_path,
                query={
                    "season": season,
                    "seasonType": resolved_season_type,
                    "week": resolved_week,
                    "limit": 100,
                },
                token=token,
            )
            standings_rows = _parse_standings(standings_payload, season, resolved_week)
        except Exception as exc:
            errors.append(f"standings:{exc}")

        try:
            team_stats_payload = _fetch_json(
                path=team_stats_path,
                query={
                    "season": season,
                    "seasonType": resolved_season_type,
                    "week": resolved_week,
                    "limit": 100,
                },
                token=token,
            )
            team_stats_rows = _parse_team_stats(team_stats_payload, season, resolved_week)
        except Exception as exc:
            errors.append(f"team_stats:{exc}")

    diagnostics = NflComDiagnostics(
        auth_mode=auth_mode,
        season=season,
        week=resolved_week,
        season_type=resolved_season_type,
        rosters_endpoint=f"{NFL_COM_BASE_URL}{rosters_path}",
        standings_endpoint=f"{NFL_COM_BASE_URL}{standings_path}",
        team_stats_endpoint=f"{NFL_COM_BASE_URL}{team_stats_path}",
        errors=errors,
    )
    return {
        "season": season,
        "week": resolved_week,
        "season_type": resolved_season_type,
        "rosters": rosters_rows,
        "standings": standings_rows,
        "team_stats": team_stats_rows,
        "diagnostics": {
            "auth_mode": diagnostics.auth_mode,
            "season": diagnostics.season,
            "week": diagnostics.week,
            "season_type": diagnostics.season_type,
            "rosters_endpoint": diagnostics.rosters_endpoint,
            "standings_endpoint": diagnostics.standings_endpoint,
            "team_stats_endpoint": diagnostics.team_stats_endpoint,
            "errors": diagnostics.errors,
        },
    }
