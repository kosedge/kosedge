"""Raw owned CFB PBP metrics (research-only).

No opponent adjustment. No KE ratings. No fair lines. No Edge Board / KEI.

Every rate names its numerator and denominator. ``EPA_success`` is treated as
an empirical column until ``audit_epa_success`` says what it matches.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

METRIC_VERSION = "cfb-owned-raw-metrics-v1"
RESEARCH_ONLY = True
OPPONENT_ADJUSTED = False

# Explosiveness knobs (same as efficiency_adj; documented, not a model fit).
EXPLOSIVE_EPA = 1.0
EXPLOSIVE_YARDS = 15

# Scoring opportunity: drive reaches opponent 40 (yards-to-endzone <= 40).
OPP_YARDS_TO_ENDZONE = 40
RED_ZONE_YARDS = 20

# Passing-down: 2nd & 7+ or 3rd/4th. Standard: 1st or 2nd & 6 or fewer.
STANDARD_2ND_MAX_DISTANCE = 6
PASSING_2ND_MIN_DISTANCE = 7

DEFINITIONS: Dict[str, str] = {
    "scrimmage_play": (
        "Denominator filter: truthy `scrimmage_play`. If the column is missing, "
        "fallback is truthy `pass` or truthy `rush`. Special-teams / untagged rows excluded."
    ),
    "success_rate": (
        "Numerator: count of scrimmage plays with truthy `EPA_success`. "
        "Denominator: scrimmage plays with a non-null `EPA_success`. "
        "This is the vendor column, not a recomputed standard-SR unless audit says they match."
    ),
    "standard_success_rate": (
        "Football Study Hall / SP+ style: 1st down ≥ 50% of `distance`, "
        "2nd ≥ 70%, 3rd/4th ≥ 100%, using `statYardage`. "
        "Denominator: scrimmage plays with finite down, distance, and yardage."
    ),
    "epa_per_play": (
        "Mean `EPA` on scrimmage plays with finite EPA. Not opponent-adjusted."
    ),
    "pace_plays_per_offense_game": (
        "Numerator: scrimmage plays for a team as `pos_team` in a game. "
        "Denominator: team-games (unique game_id × pos_team). "
        "League pace = mean of those team-game counts."
    ),
    "true_pace_competitive": (
        "Same as pace but only plays with |pos_score_diff| < 16 "
        "(warehouse competitive_margin). Clock not required."
    ),
    "explosive_rate": (
        f"Numerator: scrimmage plays with EPA ≥ {EXPLOSIVE_EPA} or "
        f"statYardage ≥ {EXPLOSIVE_YARDS}. Denominator: scrimmage plays "
        "with finite EPA or yardage. Created = offense; allowed = that rate "
        "from the opponent's offense (defense rows flip pos/def)."
    ),
    "early_down": "down ∈ {1, 2}.",
    "standard_down": (
        f"down == 1 or (down == 2 and distance ≤ {STANDARD_2ND_MAX_DISTANCE})."
    ),
    "passing_down": (
        f"down ≥ 3 or (down == 2 and distance ≥ {PASSING_2ND_MIN_DISTANCE})."
    ),
    "down_split_efficiency": (
        "Success rate and EPA/play inside each down bucket. "
        "Early and standard overlap on 1st down by design — they are not a partition."
    ),
    "scoring_opportunity": (
        f"A drive (game_id + drive.id) is an opportunity if any play has "
        f"start.yardsToEndzone ≤ {OPP_YARDS_TO_ENDZONE} or truthy rz_play. "
        "Red-zone subset uses yardsToEndzone ≤ 20."
    ),
    "points_on_drive": (
        "Heuristic from `type.text` only: TD (+6), Extra Point Good (+1), "
        "two-point success (+2), Field Goal Good (+3), Safety (+2). "
        "No synthetic PAT if XP is missing. Not official drive-result points."
    ),
    "points_per_opportunity": (
        "Numerator: points_on_drive for opportunity drives. "
        "Denominator: opportunity drives for that offense. Finishing = share with points > 0."
    ),
    "field_position": (
        "Mean start.yardsToEndzone on the first play of each drive "
        "(lowest play id within game_id+drive.id, else first seen). "
        "Higher yards-to-endzone = worse field position."
    ),
    "drive_efficiency": (
        "Mean sum of finite play EPA on scrimmage plays within a drive; "
        "also opportunity rate and score rate. Raw, not opponent-adjusted."
    ),
    "rolling_form": (
        "Same-season team aggregates using only plays with week < as_of_week (W−1). "
        "Unprovable weeks are dropped. Not a 2026 feature unless 2026 PBP is present."
    ),
    "not_in_scope": (
        "Opponent-adjusted EPA/PPA, KE ratings, havoc/PBU/official TFL, "
        "fair lines, Edge Board, KEI."
    ),
}


def _f(raw: Any, default: float = float("nan")) -> float:
    if raw is None or raw == "":
        return default
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(val):
        return default
    return val


def _truthy(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw in (None, "", 0, "0"):
        return False
    if isinstance(raw, float) and raw != raw:
        return False
    return str(raw).lower() in {"1", "true", "t", "yes"}


def is_scrimmage(play: Mapping[str, Any]) -> bool:
    if play.get("scrimmage_play") is not None and str(play.get("scrimmage_play")) not in {
        "",
        "nan",
        "NaN",
        "<NA>",
    }:
        return _truthy(play.get("scrimmage_play"))
    return _truthy(play.get("pass")) or _truthy(play.get("rush"))


def down_bucket(play: Mapping[str, Any]) -> Dict[str, bool]:
    down = _f(play.get("down"))
    dist = _f(play.get("distance"))
    if not math.isfinite(down):
        return {"early": False, "standard": False, "passing": False, "known": False}
    d = int(down)
    early = d in (1, 2)
    standard = d == 1 or (
        d == 2 and math.isfinite(dist) and dist <= STANDARD_2ND_MAX_DISTANCE
    )
    passing = d >= 3 or (
        d == 2 and math.isfinite(dist) and dist >= PASSING_2ND_MIN_DISTANCE
    )
    return {"early": early, "standard": standard, "passing": passing, "known": True}


def standard_success(play: Mapping[str, Any]) -> Optional[bool]:
    down = _f(play.get("down"))
    dist = _f(play.get("distance"))
    yards = _f(play.get("statYardage"))
    if not (math.isfinite(down) and math.isfinite(dist) and math.isfinite(yards) and dist > 0):
        return None
    d = int(down)
    if d <= 1:
        need = 0.50 * dist
    elif d == 2:
        need = 0.70 * dist
    else:
        need = dist
    return yards + 1e-9 >= need


def is_explosive(play: Mapping[str, Any]) -> bool:
    epa = _f(play.get("EPA"))
    yards = _f(play.get("statYardage"))
    return (math.isfinite(epa) and epa >= EXPLOSIVE_EPA) or (
        math.isfinite(yards) and yards >= EXPLOSIVE_YARDS
    )


def _type_text(play: Mapping[str, Any]) -> str:
    return str(play.get("type.text") or play.get("type_text") or "").strip().lower()


def play_points(play: Mapping[str, Any]) -> int:
    text = _type_text(play)
    if not text:
        return 0
    if "extra point good" in text or text == "extra point good":
        return 1
    if "two-point" in text or "two point" in text:
        if "good" in text or "success" in text or "conversion" in text:
            return 2
        return 0
    if "field goal good" in text:
        return 3
    if "safety" in text:
        return 2
    if "touchdown" in text and "no good" not in text and "nullified" not in text:
        return 6
    return 0


def audit_epa_success(plays: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """What does EPA_success actually represent on this sample?"""
    n = agree_pos = agree_nonneg = agree_std = usable = std_n = 0
    both_true = both_false = col_true_epa_neg = col_false_epa_pos = 0
    for play in plays:
        if not is_scrimmage(play):
            continue
        flag = play.get("EPA_success")
        if flag is None or flag == "":
            continue
        epa = _f(play.get("EPA"))
        if not math.isfinite(epa):
            continue
        usable += 1
        col = _truthy(flag)
        pos = epa > 0
        nonneg = epa >= 0
        if col == pos:
            agree_pos += 1
        if col == nonneg:
            agree_nonneg += 1
        if col and pos:
            both_true += 1
        if (not col) and (not pos):
            both_false += 1
        if col and not pos:
            col_true_epa_neg += 1
        if (not col) and pos:
            col_false_epa_pos += 1
        std = standard_success(play)
        if std is not None:
            std_n += 1
            if col == std:
                agree_std += 1
        n += 1
    if usable == 0:
        return {"usable_scrimmage": 0, "verdict": "no_usable_rows"}
    rate_pos = agree_pos / usable
    rate_nonneg = agree_nonneg / usable
    rate_std = (agree_std / std_n) if std_n else None
    if rate_pos >= 0.995:
        verdict = "EPA_success_matches_EPA_gt_0"
    elif rate_nonneg >= 0.995:
        verdict = "EPA_success_matches_EPA_ge_0"
    elif rate_std is not None and rate_std >= 0.995:
        verdict = "EPA_success_matches_standard_success_rate"
    elif rate_pos >= 0.95:
        verdict = "EPA_success_near_EPA_gt_0"
    else:
        verdict = "EPA_success_not_a_simple_EPA_or_standard_SR_rule"
    return {
        "usable_scrimmage": usable,
        "agree_EPA_gt_0": round(rate_pos, 6),
        "agree_EPA_ge_0": round(rate_nonneg, 6),
        "agree_standard_SR": None if rate_std is None else round(rate_std, 6),
        "standard_SR_n": std_n,
        "col_true_and_EPA_gt_0": both_true,
        "col_false_and_EPA_le_0": both_false,
        "col_true_EPA_le_0": col_true_epa_neg,
        "col_false_EPA_gt_0": col_false_epa_pos,
        "verdict": verdict,
    }


def _rate(num: float, den: float) -> Optional[float]:
    if den <= 0:
        return None
    return num / den


def team_game_raw_metrics(plays: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """One offense row per (season, week, game_id, pos_team). Raw only."""
    buckets: Dict[Tuple[Any, ...], Dict[str, float]] = {}
    meta: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for play in plays:
        if not is_scrimmage(play):
            continue
        off = str(play.get("pos_team") or "").strip()
        deff = str(play.get("def_pos_team") or "").strip()
        gid = str(play.get("game_id") or "").strip()
        if not off or not gid:
            continue
        season = int(_f(play.get("season"), 0))
        week = int(_f(play.get("week"), 0))
        key = (season, week, gid, off, deff)
        acc = buckets.setdefault(
            key,
            {
                "plays": 0.0,
                "success_n": 0.0,
                "success_d": 0.0,
                "std_n": 0.0,
                "std_d": 0.0,
                "epa_sum": 0.0,
                "epa_d": 0.0,
                "expl_n": 0.0,
                "expl_d": 0.0,
                "pass_plays": 0.0,
                "pass_expl": 0.0,
                "rush_plays": 0.0,
                "rush_expl": 0.0,
                "early_d": 0.0,
                "early_succ": 0.0,
                "early_epa": 0.0,
                "std_down_d": 0.0,
                "std_down_succ": 0.0,
                "std_down_epa": 0.0,
                "pass_down_d": 0.0,
                "pass_down_succ": 0.0,
                "pass_down_epa": 0.0,
                "comp_plays": 0.0,
            },
        )
        acc["plays"] += 1.0
        if play.get("EPA_success") is not None and play.get("EPA_success") != "":
            acc["success_d"] += 1.0
            if _truthy(play.get("EPA_success")):
                acc["success_n"] += 1.0
        std = standard_success(play)
        if std is not None:
            acc["std_d"] += 1.0
            if std:
                acc["std_n"] += 1.0
        epa = _f(play.get("EPA"))
        if math.isfinite(epa):
            acc["epa_sum"] += epa
            acc["epa_d"] += 1.0
        yards = _f(play.get("statYardage"))
        if math.isfinite(epa) or math.isfinite(yards):
            acc["expl_d"] += 1.0
            if is_explosive(play):
                acc["expl_n"] += 1.0
        if _truthy(play.get("pass")):
            acc["pass_plays"] += 1.0
            if is_explosive(play):
                acc["pass_expl"] += 1.0
        if _truthy(play.get("rush")):
            acc["rush_plays"] += 1.0
            if is_explosive(play):
                acc["rush_expl"] += 1.0
        buckets_down = down_bucket(play)
        succ = _truthy(play.get("EPA_success")) if play.get("EPA_success") not in (None, "") else None
        if buckets_down["early"]:
            acc["early_d"] += 1.0
            if succ:
                acc["early_succ"] += 1.0
            if math.isfinite(epa):
                acc["early_epa"] += epa
        if buckets_down["standard"]:
            acc["std_down_d"] += 1.0
            if succ:
                acc["std_down_succ"] += 1.0
            if math.isfinite(epa):
                acc["std_down_epa"] += epa
        if buckets_down["passing"]:
            acc["pass_down_d"] += 1.0
            if succ:
                acc["pass_down_succ"] += 1.0
            if math.isfinite(epa):
                acc["pass_down_epa"] += epa
        margin = _f(play.get("pos_score_diff"), 0.0)
        if math.isfinite(margin) and abs(margin) < 16:
            acc["comp_plays"] += 1.0
        meta[key] = {
            "season": season,
            "week": week,
            "game_id": gid,
            "offense": off,
            "defense": deff,
        }

    rows: List[Dict[str, Any]] = []
    for key, acc in buckets.items():
        info = meta[key]
        rows.append(
            {
                **info,
                "n_plays": int(acc["plays"]),
                "success_rate": _rate(acc["success_n"], acc["success_d"]),
                "standard_success_rate": _rate(acc["std_n"], acc["std_d"]),
                "epa_per_play": _rate(acc["epa_sum"], acc["epa_d"]),
                "explosive_rate": _rate(acc["expl_n"], acc["expl_d"]),
                "pass_explosive_rate": _rate(acc["pass_expl"], acc["pass_plays"]),
                "rush_explosive_rate": _rate(acc["rush_expl"], acc["rush_plays"]),
                "early_success_rate": _rate(acc["early_succ"], acc["early_d"]),
                "early_epa_per_play": _rate(acc["early_epa"], acc["early_d"]),
                "standard_down_success_rate": _rate(acc["std_down_succ"], acc["std_down_d"]),
                "standard_down_epa_per_play": _rate(acc["std_down_epa"], acc["std_down_d"]),
                "passing_down_success_rate": _rate(acc["pass_down_succ"], acc["pass_down_d"]),
                "passing_down_epa_per_play": _rate(acc["pass_down_epa"], acc["pass_down_d"]),
                "competitive_plays": int(acc["comp_plays"]),
                "opponent_adjusted": False,
                "metric_version": METRIC_VERSION,
            }
        )
    return rows


def pace_summary(team_games: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    plays = [int(r.get("n_plays") or 0) for r in team_games]
    comp = [int(r.get("competitive_plays") or 0) for r in team_games]
    n = len(plays)
    return {
        "team_games": n,
        "plays_per_offense_game": (sum(plays) / n) if n else None,
        "true_pace_competitive_plays_per_offense_game": (sum(comp) / n) if n else None,
        "definition": DEFINITIONS["pace_plays_per_offense_game"],
    }


def drive_metrics(plays: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for play in plays:
        gid = str(play.get("game_id") or "").strip()
        did = str(play.get("drive.id") or play.get("drive_id") or "").strip()
        off = str(play.get("pos_team") or "").strip()
        if not gid or not did or not off:
            continue
        grouped[(gid, did, off)].append(play)

    rows: List[Dict[str, Any]] = []
    for (gid, did, off), group in grouped.items():
        ordered = sorted(
            group,
            key=lambda p: (
                _f(p.get("id"), 0.0),
                _f(p.get("start.yardsToEndzone"), 99.0),
            ),
        )
        first = ordered[0]
        start_yte = _f(first.get("start.yardsToEndzone"))
        reached_40 = False
        reached_rz = False
        epa_sum = 0.0
        epa_n = 0.0
        points = 0
        deff = str(first.get("def_pos_team") or "")
        season = int(_f(first.get("season"), 0))
        week = int(_f(first.get("week"), 0))
        for play in group:
            yte = _f(play.get("start.yardsToEndzone"))
            if math.isfinite(yte) and yte <= OPP_YARDS_TO_ENDZONE:
                reached_40 = True
            if math.isfinite(yte) and yte <= RED_ZONE_YARDS:
                reached_rz = True
            if _truthy(play.get("rz_play")):
                reached_40 = True
                reached_rz = True
            if is_scrimmage(play):
                epa = _f(play.get("EPA"))
                if math.isfinite(epa):
                    epa_sum += epa
                    epa_n += 1.0
            points += play_points(play)
        opp = reached_40
        rows.append(
            {
                "season": season,
                "week": week,
                "game_id": gid,
                "drive_id": did,
                "offense": off,
                "defense": deff,
                "start_yards_to_endzone": start_yte if math.isfinite(start_yte) else None,
                "scoring_opportunity": opp,
                "red_zone_opportunity": reached_rz,
                "points": points,
                "finished": points > 0,
                "drive_epa": (epa_sum / epa_n) if epa_n else None,
                "drive_epa_sum": epa_sum if epa_n else None,
                "n_scrimmage": int(epa_n),
                "opponent_adjusted": False,
            }
        )
    return rows


def opportunity_summary(drives: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    opps = [d for d in drives if d.get("scoring_opportunity")]
    n = len(opps)
    pts = sum(int(d.get("points") or 0) for d in opps)
    finished = sum(1 for d in opps if d.get("finished"))
    fp = [
        float(d["start_yards_to_endzone"])
        for d in drives
        if d.get("start_yards_to_endzone") is not None
    ]
    epa = [float(d["drive_epa_sum"]) for d in drives if d.get("drive_epa_sum") is not None]
    return {
        "drives": len(drives),
        "scoring_opportunities": n,
        "opportunity_rate": (n / len(drives)) if drives else None,
        "points_per_opportunity": (pts / n) if n else None,
        "finish_rate": (finished / n) if n else None,
        "mean_start_yards_to_endzone": (sum(fp) / len(fp)) if fp else None,
        "mean_drive_epa_sum": (sum(epa) / len(epa)) if epa else None,
        "opponent_adjusted": False,
    }


def filter_plays_w_minus_1(
    plays: Iterable[Mapping[str, Any]],
    *,
    season: int,
    as_of_week: int,
) -> List[Dict[str, Any]]:
    """Pregame W−1: same season, week strictly before as_of_week."""
    out: List[Dict[str, Any]] = []
    for play in plays:
        if int(_f(play.get("season"), 0)) != int(season):
            continue
        week = play.get("week")
        if week is None or week == "":
            continue
        if int(_f(week, 99)) >= int(as_of_week):
            continue
        out.append(dict(play))
    return out


def rolling_form(
    plays: Sequence[Mapping[str, Any]],
    *,
    season: int,
    as_of_week: int,
) -> List[Dict[str, Any]]:
    prior = filter_plays_w_minus_1(plays, season=season, as_of_week=as_of_week)
    games = team_game_raw_metrics(prior)
    by_team: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in games:
        by_team[str(row["offense"])].append(row)
    out: List[Dict[str, Any]] = []
    for team, rows in sorted(by_team.items()):
        n = len(rows)
        def _avg(key: str) -> Optional[float]:
            vals = [float(r[key]) for r in rows if r.get(key) is not None]
            return (sum(vals) / len(vals)) if vals else None

        out.append(
            {
                "season": int(season),
                "as_of_week": int(as_of_week),
                "feature_week": max((int(r["week"]) for r in rows), default=0),
                "team": team,
                "n_games": n,
                "success_rate": _avg("success_rate"),
                "epa_per_play": _avg("epa_per_play"),
                "explosive_rate": _avg("explosive_rate"),
                "plays_per_game": _avg("n_plays"),
                "early_success_rate": _avg("early_success_rate"),
                "passing_down_success_rate": _avg("passing_down_success_rate"),
                "cutoff": "week < as_of_week",
                "opponent_adjusted": False,
                "research_only": True,
            }
        )
    return out


def league_rollups(team_games: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    def _avg(key: str) -> Optional[float]:
        vals = [float(r[key]) for r in team_games if r.get(key) is not None]
        return (sum(vals) / len(vals)) if vals else None

    return {
        "team_games": len(team_games),
        "success_rate": _avg("success_rate"),
        "standard_success_rate": _avg("standard_success_rate"),
        "epa_per_play": _avg("epa_per_play"),
        "explosive_rate": _avg("explosive_rate"),
        "pass_explosive_rate": _avg("pass_explosive_rate"),
        "rush_explosive_rate": _avg("rush_explosive_rate"),
        "early_success_rate": _avg("early_success_rate"),
        "standard_down_success_rate": _avg("standard_down_success_rate"),
        "passing_down_success_rate": _avg("passing_down_success_rate"),
        "opponent_adjusted": False,
        "metric_version": METRIC_VERSION,
    }
