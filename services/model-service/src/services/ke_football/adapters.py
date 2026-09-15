"""Sport adapters: owned PBP rows → CanonicalPlay.

NFL = nflverse / mart columns. CFB = SportsDataverse espn_cfb_pbp.
No PFF. No CFBD. Missing columns stay None.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from src.services.ke_football.plays import CanonicalPlay, finite, standard_success, truthy

NFL_SCRIMMAGE = frozenset({"pass", "run"})
NFL_ST = frozenset({"field_goal", "extra_point", "punt", "kickoff"})
NFL_DROP = frozenset({"qb_kneel", "qb_spike", "kneel", "spike"})


def _s(raw: Any) -> str:
    return str(raw or "").strip()


def nfl_points(row: Mapping[str, Any]) -> tuple[int, str]:
    """Official-flag points on this play. No synthetic PAT."""
    pts = 0
    if truthy(row.get("touchdown")) is True:
        pts += 6
    fg = _s(row.get("field_goal_result")).lower()
    if fg in {"made", "good"}:
        pts += 3
    xp = _s(row.get("extra_point_result")).lower()
    if xp in {"good", "made"}:
        pts += 1
    two = _s(row.get("two_point_conv_result")).lower()
    if two in {"success", "good"}:
        pts += 2
    if truthy(row.get("safety")) is True:
        pts += 2
    return pts, "nflverse_scoring_flags"


def _cfb_points(row: Mapping[str, Any]) -> tuple[int, str]:
    text = _s(row.get("type.text") or row.get("type_text")).lower()
    if not text:
        return 0, "type_text_heuristic"
    if "extra point good" in text:
        return 1, "type_text_heuristic"
    if "two-point" in text or "two point" in text:
        if "good" in text or "success" in text or "conversion" in text:
            return 2, "type_text_heuristic"
        return 0, "type_text_heuristic"
    if "field goal good" in text:
        return 3, "type_text_heuristic"
    if "safety" in text:
        return 2, "type_text_heuristic"
    if "touchdown" in text and "no good" not in text and "nullified" not in text:
        return 6, "type_text_heuristic"
    return 0, "type_text_heuristic"


def _period(row: Mapping[str, Any], keys: Sequence[str]) -> Optional[int]:
    for key in keys:
        val = finite(row.get(key))
        if val is not None and val > 0:
            return int(val)
    return None


def from_nfl_row(row: Mapping[str, Any]) -> Optional[CanonicalPlay]:
    season = finite(row.get("season"))
    week = finite(row.get("week"))
    game_id = _s(row.get("game_id"))
    play_id = _s(row.get("play_id") or row.get("id"))
    possession = _s(row.get("posteam"))
    defense = _s(row.get("defteam"))
    if season is None or week is None or not game_id or not possession:
        return None
    play_type = _s(row.get("play_type")).lower()
    if play_type in NFL_DROP:
        return None
    is_scrim = play_type in NFL_SCRIMMAGE and finite(row.get("epa")) is not None
    is_st = play_type in NFL_ST
    epa = finite(row.get("epa"))
    offense = possession
    # Kickoff: kicking-side frame — EPA negated onto defteam (spec §7.3).
    # Possession team stays the receiving side for drive construction.
    if play_type == "kickoff" and defense:
        offense = defense
        defense = possession
        if epa is not None:
            epa = -epa
    yards = finite(row.get("yards_gained"))
    down = finite(row.get("down"))
    dist = finite(row.get("ydstogo") or row.get("yds_to_go"))
    yte = finite(row.get("yardline_100"))
    pts, pts_src = nfl_points(row)
    tfl = truthy(row.get("tackled_for_loss") if "tackled_for_loss" in row else row.get("tackle_for_loss"))
    return CanonicalPlay(
        sport="nfl",
        season=int(season),
        week=int(week),
        game_id=game_id,
        play_id=play_id or f"{game_id}:{row.get('play_id', '')}",
        offense=offense,
        defense=defense,
        home=_s(row.get("home_team")),
        away=_s(row.get("away_team")),
        is_scrimmage=is_scrim,
        is_st=is_st,
        play_type=play_type,
        epa=epa,
        success_native=truthy(row.get("success")),
        yards=yards,
        down=down,
        distance=dist,
        yards_to_endzone=yte,
        drive_id=_drive_id(row),
        score_diff=finite(row.get("score_differential")),
        game_seconds_remaining=finite(row.get("game_seconds_remaining")),
        period=_period(row, ("qtr", "quarter", "period")),
        is_pass=play_type == "pass",
        is_rush=play_type == "run",
        touchdown=truthy(row.get("touchdown")),
        points=pts,
        points_source=pts_src,
        sack=truthy(row.get("sack")),
        interception=truthy(row.get("interception")),
        qb_hit=truthy(row.get("qb_hit")),
        fumble=truthy(row.get("fumble")),
        fumble_forced=truthy(row.get("fumble_forced")),
        tfl=tfl,
        pass_breakup=truthy(row.get("pass_defense") or row.get("pass_breakup")),
        possession_team=possession,
        drive_result=_s(row.get("fixed_drive_result") or row.get("drive_end_transition")) or None,
        td_team=_s(row.get("td_team")) or None,
        extra={
            "season_type": _s(row.get("season_type") or row.get("game_type")),
            "drive_inside20": truthy(row.get("drive_inside20")),
            "drive_ended_with_score": truthy(row.get("drive_ended_with_score")),
            "two_point": _s(row.get("two_point_conv_result")).lower() in {"success", "good"},
        },
    )


def _drive_id(row: Mapping[str, Any]) -> Optional[str]:
    raw = row.get("fixed_drive")
    if raw is None or raw == "":
        raw = row.get("drive") or row.get("drive_id")
    val = finite(raw)
    if val is not None and abs(val - int(val)) < 1e-9:
        return str(int(val))
    text = _s(raw)
    return text or None


def _cfb_scrimmage(row: Mapping[str, Any]) -> bool:
    if row.get("scrimmage_play") not in (None, "", "nan", "NaN", "<NA>"):
        flag = truthy(row.get("scrimmage_play"))
        return bool(flag)
    return bool(truthy(row.get("pass")) or truthy(row.get("rush")))


def from_cfb_row(row: Mapping[str, Any]) -> Optional[CanonicalPlay]:
    season = finite(row.get("season"))
    week = finite(row.get("week"))
    game_id = _s(row.get("game_id"))
    offense = _s(row.get("pos_team"))
    defense = _s(row.get("def_pos_team"))
    if season is None or week is None or not game_id or not offense:
        return None
    is_scrim = _cfb_scrimmage(row) and finite(row.get("EPA") if "EPA" in row else row.get("epa")) is not None
    pts, pts_src = _cfb_points(row)
    play_type = _s(row.get("type.text") or row.get("type_text") or row.get("play_type"))
    return CanonicalPlay(
        sport="cfb",
        season=int(season),
        week=int(week),
        game_id=game_id,
        play_id=_s(row.get("id") or row.get("play_id")) or f"{game_id}:?",
        offense=offense,
        defense=defense,
        home=_s(row.get("homeTeamName") or row.get("home") or row.get("homeTeamAbbrev")),
        away=_s(row.get("awayTeamName") or row.get("away") or row.get("awayTeamAbbrev")),
        is_scrimmage=is_scrim,
        is_st=False,  # CFB ST uncertified — do not classify into ke.st
        play_type=play_type.lower(),
        epa=finite(row.get("EPA") if "EPA" in row else row.get("epa")),
        success_native=truthy(row.get("EPA_success")),
        yards=finite(row.get("statYardage") or row.get("yards_gained")),
        down=finite(row.get("down")),
        distance=finite(row.get("distance") or row.get("ydstogo")),
        yards_to_endzone=finite(row.get("start.yardsToEndzone") or row.get("yards_to_endzone")),
        drive_id=_s(row.get("drive.id") or row.get("drive_id")) or None,
        score_diff=finite(row.get("pos_score_diff") or row.get("score_differential")),
        game_seconds_remaining=finite(row.get("start.TimeSecsRem") or row.get("TimeSecsRem")),
        period=_period(row, ("period", "qtr", "quarter")),
        is_pass=bool(truthy(row.get("pass"))),
        is_rush=bool(truthy(row.get("rush"))),
        touchdown="touchdown" in play_type.lower(),
        points=pts,
        points_source=pts_src,
        sack=truthy(row.get("sack")),
        interception=truthy(row.get("int") or row.get("interception")),
        qb_hit=None,
        fumble=truthy(row.get("fumble")),
        fumble_forced=truthy(row.get("forced_fumble") or row.get("fumble_forced")),
        tfl=truthy(row.get("TFL") or row.get("tfl")),
        pass_breakup=truthy(row.get("pass_breakup") or row.get("PBU")),
        havoc_vendor=truthy(row.get("havoc")),
        possession_team=offense,
        extra={"rz_play": truthy(row.get("rz_play"))},
    )


def adapt_rows(sport: str, rows: Iterable[Mapping[str, Any]]) -> List[CanonicalPlay]:
    fn = from_nfl_row if sport == "nfl" else from_cfb_row
    out: List[CanonicalPlay] = []
    for row in rows:
        play = fn(row)
        if play is not None:
            out.append(play)
    return out


def is_explosive(play: CanonicalPlay) -> bool:
    """Sport-specific knobs. Do not copy NFL 20/10 onto CFB."""
    if play.sport == "nfl":
        if play.yards is None:
            return False
        if play.is_pass:
            return play.yards >= 20
        if play.is_rush:
            return play.yards >= 10
        return False
    epa_hit = play.epa is not None and play.epa >= 1.0
    yd_hit = play.yards is not None and play.yards >= 15
    return epa_hit or yd_hit


def play_standard_success(play: CanonicalPlay) -> Optional[bool]:
    return standard_success(down=play.down, distance=play.distance, yards=play.yards)
