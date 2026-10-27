"""Pregame same-season trailing EPA features for research walk-forward.

CERT_CANDIDATE=0. RESEARCH_DIAGNOSTIC only. Not a warehouse remat.
Does not invent EPA win probabilities. Does not write production tables.

PIT: for target week W, average the last 3/5 same-season team-weeks with
week < W (bye weeks skip). Warehouse SQL includes CURRENT ROW; this emit
does not, so a LEFT JOIN at (season, week, team) is pregame-safe.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

RESEARCH_LABEL = "RESEARCH_DIAGNOSTIC"
CERT_CANDIDATE = 0
PIT_RULE = "same_season_weeks_lt_target"
FEATURE_SOURCE = "nflverse_pbp_pass_run_agg"
ORDER_ID = "65b1c0fb"

ROLL_METRICS: Tuple[str, ...] = (
    "epa_per_play_offense",
    "epa_per_play_defense_allowed",
    "pressure_rate_allowed",
    "pressure_rate_generated",
    "pass_rate",
    "early_down_pass_rate",
    "red_zone_td_rate",
    "success_rate_offense",
    "success_rate_defense_allowed",
)

ROLLED_NAME = {
    "epa_per_play_offense": "off_epa_per_play",
    "epa_per_play_defense_allowed": "def_epa_allowed_per_play",
    "pressure_rate_allowed": "pressure_rate_allowed",
    "pressure_rate_generated": "pressure_rate_generated",
    "pass_rate": "pass_rate",
    "early_down_pass_rate": "early_down_pass_rate",
    "red_zone_td_rate": "red_zone_td_rate",
    "success_rate_offense": "success_rate_offense",
    "success_rate_defense_allowed": "success_rate_defense_allowed",
}


def normalize_pbp_team(raw: Any) -> str:
    team = str(raw or "").strip().upper()
    if team == "JAC":
        return "JAX"
    return team


def oos_team_from_pbp(pbp_team: Any, season: int) -> str:
    """Map nflverse PBP modern abbrs onto historical-OOS labels."""
    team = normalize_pbp_team(pbp_team)
    if team in ("LA", "LAR"):
        return "STL" if int(season) <= 2015 else "LAR"
    if team == "LAC":
        return "SD" if int(season) <= 2016 else "LAC"
    if team == "LV":
        return "OAK" if int(season) <= 2019 else "LV"
    if team in ("WAS", "WSH"):
        return "WSH"
    return team


def pbp_team_from_oos(oos_team: Any, season: int) -> str:
    team = str(oos_team or "").strip().upper()
    if team in ("STL", "LAR", "LA"):
        return "LA"
    if team in ("SD", "LAC"):
        return "LAC"
    if team in ("OAK", "LV"):
        return "LV"
    if team in ("WAS", "WSH"):
        return "WAS"
    if team == "JAC":
        return "JAX"
    return team


def _f(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if value in (False, None, ""):
        return False
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return bool(value)


def aggregate_team_weeks(plays: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Match data_platform_nfl.ingest team-situational pass/run aggregation."""
    off: Dict[Tuple[int, int, str], Dict[str, Any]] = {}
    deff: Dict[Tuple[int, int, str], Dict[str, Any]] = {}

    def _off(season: int, week: int, team: str) -> Dict[str, Any]:
        key = (season, week, team)
        row = off.get(key)
        if row is None:
            row = {
                "season": season,
                "week": week,
                "pbp_team": team,
                "game_ids": set(),
                "offensive_plays": 0,
                "pass_plays": 0,
                "run_plays": 0,
                "early_down_plays": 0,
                "early_down_pass_plays": 0,
                "red_zone_plays": 0,
                "red_zone_touchdowns": 0,
                "success_sum": 0.0,
                "success_n": 0,
                "epa_sum": 0.0,
                "epa_n": 0,
                "offensive_pressures_allowed": 0,
                "offensive_dropbacks": 0,
            }
            off[key] = row
        return row

    def _def(season: int, week: int, team: str) -> Dict[str, Any]:
        key = (season, week, team)
        row = deff.get(key)
        if row is None:
            row = {
                "season": season,
                "week": week,
                "pbp_team": team,
                "defensive_plays": 0,
                "success_sum": 0.0,
                "success_n": 0,
                "epa_sum": 0.0,
                "epa_n": 0,
                "defensive_pressures_generated": 0,
                "defensive_dropbacks_faced": 0,
            }
            deff[key] = row
        return row

    for play in plays:
        play_type = str(play.get("play_type") or "")
        if play_type not in ("pass", "run"):
            continue
        posteam = normalize_pbp_team(play.get("posteam"))
        defteam = normalize_pbp_team(play.get("defteam"))
        if not posteam:
            continue
        try:
            season = int(play["season"])
            week = int(play["week"])
        except (KeyError, TypeError, ValueError):
            continue
        down = play.get("down")
        try:
            down_i = int(down) if down not in (None, "") else None
        except (TypeError, ValueError):
            down_i = None
        is_pass = play_type == "pass"
        is_run = play_type == "run"
        first_down = _truthy(play.get("first_down"))
        yardline = _f(play.get("yardline_100"))
        in_rz = yardline is not None and yardline <= 20
        td = _truthy(play.get("touchdown"))
        sack = _truthy(play.get("sack"))
        qb_hit = _truthy(play.get("qb_hit"))
        success = play.get("success")
        epa = _f(play.get("epa"))
        game_id = play.get("game_id")

        o = _off(season, week, posteam)
        if game_id:
            o["game_ids"].add(str(game_id))
        o["offensive_plays"] += 1
        if is_pass:
            o["pass_plays"] += 1
            o["offensive_dropbacks"] += 1
            if sack or qb_hit:
                o["offensive_pressures_allowed"] += 1
        if is_run:
            o["run_plays"] += 1
        if down_i in (1, 2):
            o["early_down_plays"] += 1
            if is_pass:
                o["early_down_pass_plays"] += 1
        if in_rz:
            o["red_zone_plays"] += 1
            if td:
                o["red_zone_touchdowns"] += 1
        if success is not None and success != "":
            o["success_n"] += 1
            if _truthy(success):
                o["success_sum"] += 1.0
        if epa is not None:
            o["epa_n"] += 1
            o["epa_sum"] += epa

        if not defteam:
            continue
        d = _def(season, week, defteam)
        d["defensive_plays"] += 1
        if is_pass:
            d["defensive_dropbacks_faced"] += 1
            if sack or qb_hit:
                d["defensive_pressures_generated"] += 1
        if success is not None and success != "":
            d["success_n"] += 1
            if _truthy(success):
                d["success_sum"] += 1.0
        if epa is not None:
            d["epa_n"] += 1
            d["epa_sum"] += epa

    out: List[Dict[str, Any]] = []
    for key, o in sorted(off.items()):
        season, week, pbp_team = key
        d = deff.get(key, {})
        offensive_plays = int(o["offensive_plays"])
        dropbacks = int(o["offensive_dropbacks"])
        def_dropbacks = int(d.get("defensive_dropbacks_faced") or 0)
        out.append(
            {
                "season": season,
                "week": week,
                "pbp_team": pbp_team,
                "oos_team": oos_team_from_pbp(pbp_team, season),
                "games_played": len(o["game_ids"]) or 1,
                "offensive_plays": offensive_plays,
                "pass_rate": (o["pass_plays"] / offensive_plays) if offensive_plays else None,
                "early_down_pass_rate": (
                    o["early_down_pass_plays"] / o["early_down_plays"]
                    if o["early_down_plays"]
                    else None
                ),
                "red_zone_td_rate": (
                    o["red_zone_touchdowns"] / o["red_zone_plays"]
                    if o["red_zone_plays"]
                    else None
                ),
                "pressure_rate_allowed": (
                    o["offensive_pressures_allowed"] / dropbacks if dropbacks else None
                ),
                "pressure_rate_generated": (
                    (d.get("defensive_pressures_generated") or 0) / def_dropbacks
                    if def_dropbacks
                    else None
                ),
                "success_rate_offense": (
                    o["success_sum"] / o["success_n"] if o["success_n"] else None
                ),
                "success_rate_defense_allowed": (
                    (d.get("success_sum") or 0.0) / d["success_n"]
                    if d.get("success_n")
                    else None
                ),
                "epa_per_play_offense": (
                    o["epa_sum"] / o["epa_n"] if o["epa_n"] else None
                ),
                "epa_per_play_defense_allowed": (
                    (d.get("epa_sum") or 0.0) / d["epa_n"] if d.get("epa_n") else None
                ),
            }
        )
    return out


def _mean(values: Sequence[Optional[float]]) -> Optional[float]:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _empty_rolled() -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "games_in_window_3": 0,
        "games_in_window_5": 0,
        "asof_max_week": None,
    }
    for raw, rolled in ROLLED_NAME.items():
        row[f"{rolled}_3g"] = None
        row[f"{rolled}_5g"] = None
    return row


def roll_pregame(team_weeks: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Emit one pregame rolled row per observed (season, week, team)."""
    by_team: Dict[Tuple[int, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in team_weeks:
        by_team[(int(row["season"]), str(row["oos_team"]))].append(row)
    out: List[Dict[str, Any]] = []
    for (season, oos_team), rows in sorted(by_team.items()):
        ordered = sorted(rows, key=lambda r: int(r["week"]))
        for i, target in enumerate(ordered):
            prior = ordered[:i]
            win3 = prior[-3:]
            win5 = prior[-5:]
            rolled = _empty_rolled()
            rolled["games_in_window_3"] = len(win3)
            rolled["games_in_window_5"] = len(win5)
            if prior:
                rolled["asof_max_week"] = int(prior[-1]["week"])
            for raw, name in ROLLED_NAME.items():
                rolled[f"{name}_3g"] = _mean([_f(r.get(raw)) for r in win3])
                rolled[f"{name}_5g"] = _mean([_f(r.get(raw)) for r in win5])
            out.append(
                {
                    "season": season,
                    "week": int(target["week"]),
                    "oos_team": oos_team,
                    "pbp_team": str(target.get("pbp_team") or pbp_team_from_oos(oos_team, season)),
                    "pit_rule": PIT_RULE,
                    "source": FEATURE_SOURCE,
                    **rolled,
                }
            )
    return out


def expand_pregame_to_oos_weeks(
    team_weeks: Sequence[Mapping[str, Any]],
    oos_games: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Rolled features at every OOS (season, week, team), including W1 empty windows."""
    rolled = {(r["season"], r["week"], r["oos_team"]): r for r in roll_pregame(team_weeks)}
    history: Dict[Tuple[int, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in team_weeks:
        history[(int(row["season"]), str(row["oos_team"]))].append(row)
    for key in history:
        history[key] = sorted(history[key], key=lambda r: int(r["week"]))

    needed: Dict[Tuple[int, int, str], None] = {}
    for game in oos_games:
        season = int(game["season"])
        week = int(game["week"])
        needed[(season, week, str(game["home"]))] = None
        needed[(season, week, str(game["away"]))] = None

    out: List[Dict[str, Any]] = []
    for season, week, oos_team in sorted(needed):
        hit = rolled.get((season, week, oos_team))
        if hit is not None:
            out.append(dict(hit))
            continue
        prior = [r for r in history.get((season, oos_team), []) if int(r["week"]) < week]
        win3 = prior[-3:]
        win5 = prior[-5:]
        row = _empty_rolled()
        row.update(
            {
                "season": season,
                "week": week,
                "oos_team": oos_team,
                "pbp_team": pbp_team_from_oos(oos_team, season),
                "pit_rule": PIT_RULE,
                "source": FEATURE_SOURCE,
                "games_in_window_3": len(win3),
                "games_in_window_5": len(win5),
                "asof_max_week": int(prior[-1]["week"]) if prior else None,
            }
        )
        for raw, name in ROLLED_NAME.items():
            row[f"{name}_3g"] = _mean([_f(r.get(raw)) for r in win3])
            row[f"{name}_5g"] = _mean([_f(r.get(raw)) for r in win5])
        out.append(row)
    return out


def feature_status(home: Mapping[str, Any], away: Mapping[str, Any]) -> str:
    h = int(home.get("games_in_window_5") or 0)
    a = int(away.get("games_in_window_5") or 0)
    if h == 0 or a == 0:
        return "EMPTY_WINDOW"
    if h < 3 or a < 3:
        return "THIN_WINDOW"
    return "PRESENT"


def join_game_id(season: int, week: int, home: str, away: str) -> str:
    return f"{int(season)}_{int(week):02d}_{away}_{home}"


def join_oos_games(
    oos_games: Sequence[Mapping[str, Any]],
    rolled_rows: Sequence[Mapping[str, Any]],
    pbp_game_ids: Optional[Mapping[Tuple[int, int, str, str], str]] = None,
) -> List[Dict[str, Any]]:
    idx = {(r["season"], r["week"], r["oos_team"]): r for r in rolled_rows}
    empty = _empty_rolled()
    out: List[Dict[str, Any]] = []
    for game in oos_games:
        season = int(game["season"])
        week = int(game["week"])
        home = str(game["home"])
        away = str(game["away"])
        home_f = idx.get((season, week, home), {"oos_team": home, **empty})
        away_f = idx.get((season, week, away), {"oos_team": away, **empty})
        pbp_id = None
        if pbp_game_ids:
            pbp_home = pbp_team_from_oos(home, season)
            pbp_away = pbp_team_from_oos(away, season)
            pbp_id = pbp_game_ids.get((season, week, pbp_home, pbp_away))
        status = feature_status(home_f, away_f)
        row: Dict[str, Any] = {
            "season": season,
            "week": week,
            "oos_key": str(game.get("key") or f"{away}@{home}"),
            "home": home,
            "away": away,
            "join_game_id": join_game_id(season, week, home, away),
            "pbp_game_id": pbp_id or "",
            "feature_status": status,
            "research_label": RESEARCH_LABEL,
            "cert_candidate": CERT_CANDIDATE,
            "pit_rule": PIT_RULE,
            "order_id": ORDER_ID,
            "epa_home_win_prob": "",
            "epa_away_win_prob": "",
            "epa_win_prob_status": "NOT_EMITTED",
            "epa_win_prob_blocker": (
                "Feature emit only. Do not invent simulate_nfl_game EPA win "
                "probs from these trailing means."
            ),
        }
        for side, feat in (("home", home_f), ("away", away_f)):
            row[f"{side}_games_in_window_3"] = feat.get("games_in_window_3", 0)
            row[f"{side}_games_in_window_5"] = feat.get("games_in_window_5", 0)
            row[f"{side}_asof_max_week"] = feat.get("asof_max_week")
            for raw, name in ROLLED_NAME.items():
                row[f"{side}_{name}_3g"] = feat.get(f"{name}_3g")
                row[f"{side}_{name}_5g"] = feat.get(f"{name}_5g")
        out.append(row)
    return out


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fmt_num(value: Any, digits: int = 6) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)
