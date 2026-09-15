"""Canonical drive construction for finishing.

NFL Phase 1 defect: kickoffs sit at yardline_100 ≈ 35 and share ``fixed_drive``
with the receiving offense. Counting that snap as “reached the 40” marked
almost every drive as an opportunity (empirical: 99.4% of 2025 REG kickoffs
have yl ≤ 40). PPO/finish collapsed (~2.1 / ~0.41).

Repair (owned nflverse only):
- Drive key = (game_id, fixed_drive)
- Drive offense = possession/scrimmage posteam, **not** the kickoff-swapped ST team
- Opportunity yardline ignores kickoff / extra-point / kickoff-return snaps
- Points from ``fixed_drive_result`` + same-drive XP/2pt flags
- No synthetic PAT. No calibration toward a target PPO.

CFB keeps the #555 type.text heuristic (already football-sane).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from src.services.ke_football.plays import CanonicalPlay

OPP_YTE = 40
RZ_YTE = 20
NFL_IGNORE_YTE = frozenset({"kickoff", "extra_point", "kickoff_return"})
NFL_TD_RESULTS = frozenset({"touchdown"})
NFL_FG_RESULTS = frozenset({"field goal", "field_goal"})


def _norm_result(raw: Optional[str]) -> str:
    return " ".join(str(raw or "").strip().lower().replace("_", " ").split())


@dataclass
class Drive:
    sport: str
    season: int
    week: int
    game_id: str
    drive_id: str
    offense: str
    defense: str
    n_plays: int
    min_yte: Optional[float]
    scoring_opportunity: bool
    red_zone_opportunity: bool
    points: int
    points_source: str
    drive_result: Optional[str]
    finished: bool


def _nfl_drive_points(plays: Sequence[CanonicalPlay]) -> Tuple[int, str, Optional[str]]:
    result = None
    for play in plays:
        if play.drive_result:
            result = play.drive_result
            break
    norm = _norm_result(result)
    xp = 0
    two = 0
    safety = 0
    for play in plays:
        if play.play_type == "extra_point" and play.points == 1:
            xp += 1
        if play.play_type != "extra_point" and play.points == 2 and "two" in (play.points_source or ""):
            two += 1
        # two-point is encoded as +2 on the conversion play
        if play.points == 2 and play.play_type not in {"extra_point", "field_goal"}:
            # safety or 2pt — safety is rare; 2pt success is on two_point play type
            if play.play_type in {"", "pass", "run"} and "safety" not in norm:
                pass
        if play.play_type in {"safety"} or (play.points == 2 and _norm_result(play.drive_result) == "safety"):
            safety += 1
        extra_two = play.extra.get("two_point") if play.extra else None
        if extra_two:
            two += 1
    # Prefer official drive result over summing every scoring flag (avoids
    # defensive TD flags landing on the offense row).
    if norm in NFL_TD_RESULTS:
        pts = 6 + (1 if xp else 0)
        # 2pt instead of XP
        if two and not xp:
            pts = 8
        return pts, "fixed_drive_result+pat_flags", result
    if norm in NFL_FG_RESULTS:
        return 3, "fixed_drive_result", result
    if norm == "safety" or safety:
        return 2, "fixed_drive_result", result
    if norm in {"opp touchdown", "opponent touchdown"}:
        return 0, "fixed_drive_result", result
    # Result missing: fall back to offensive scoring flags only (td_team match).
    pts = 0
    for play in plays:
        if play.play_type in NFL_IGNORE_YTE:
            continue
        if play.touchdown is True:
            if play.td_team and play.possession_team and play.td_team != play.possession_team:
                continue
            pts += 6
        elif play.play_type == "field_goal" and play.points == 3:
            pts += 3
        elif play.play_type == "extra_point" and play.points == 1:
            pts += 1
        elif play.points == 2 and play.play_type not in NFL_IGNORE_YTE:
            pts += 2
    return pts, "offensive_scoring_flags_fallback", result


def _cfb_drive_points(plays: Sequence[CanonicalPlay]) -> Tuple[int, str, Optional[str]]:
    pts = sum(int(p.points or 0) for p in plays)
    return pts, "type_text_heuristic", None


def _drive_offense(plays: Sequence[CanonicalPlay]) -> str:
    for play in plays:
        if play.is_scrimmage and play.possession_team:
            return play.possession_team
    for play in plays:
        if play.possession_team and play.play_type not in {"kickoff"}:
            return play.possession_team
    for play in plays:
        if play.possession_team:
            return play.possession_team
    return ""


def _opportunity_yte(plays: Sequence[CanonicalPlay]) -> Tuple[Optional[float], bool, bool]:
    """Min yards-to-endzone on snaps that can establish field position."""
    ytes: List[float] = []
    rz_flag = False
    for play in plays:
        if play.play_type in NFL_IGNORE_YTE:
            continue
        if play.sport == "nfl" and play.play_type == "kickoff":
            continue
        if play.yards_to_endzone is not None:
            ytes.append(play.yards_to_endzone)
            if play.yards_to_endzone <= RZ_YTE:
                rz_flag = True
        if play.extra.get("rz_play") is True:
            rz_flag = True
        if play.extra.get("drive_inside20") is True:
            rz_flag = True
    min_yte = min(ytes) if ytes else None
    reached_40 = bool(min_yte is not None and min_yte <= OPP_YTE) or (
        any(play.extra.get("rz_play") is True for play in plays)
    )
    reached_rz = rz_flag or (min_yte is not None and min_yte <= RZ_YTE)
    return min_yte, reached_40, reached_rz


def build_drives(plays: Sequence[CanonicalPlay]) -> List[Drive]:
    grouped: Dict[Tuple[str, str], List[CanonicalPlay]] = defaultdict(list)
    for play in plays:
        if not play.drive_id or not play.game_id:
            continue
        grouped[(play.game_id, play.drive_id)].append(play)

    out: List[Drive] = []
    for (gid, did), group in grouped.items():
        offense = _drive_offense(group)
        if not offense:
            continue
        defense = ""
        for play in group:
            if play.possession_team == offense and play.defense and play.defense != offense:
                defense = play.defense
                break
        first = group[0]
        if not any(p.is_scrimmage for p in group):
            # Kickoff-only / XP-only rows share fixed_drive but are not
            # offensive possessions. Do not count them as drives.
            continue
        min_yte, opp, rz = _opportunity_yte(group)
        if first.sport == "nfl":
            pts, src, result = _nfl_drive_points(group)
        else:
            pts, src, result = _cfb_drive_points(group)
        out.append(
            Drive(
                sport=first.sport,
                season=first.season,
                week=first.week,
                game_id=gid,
                drive_id=did,
                offense=offense,
                defense=defense,
                n_plays=len(group),
                min_yte=min_yte,
                scoring_opportunity=opp,
                red_zone_opportunity=rz,
                points=int(pts),
                points_source=src,
                drive_result=result,
                finished=int(pts) > 0,
            )
        )
    return out


def attach_finishing(team_games: Sequence[Any], drives: Sequence[Drive]) -> None:
    """Stamp finishing counters onto TeamGame rows (mutates)."""
    by_key: Dict[Tuple[str, int, str, str], Any] = {}
    for tg in team_games:
        by_key[(tg.game_id, tg.week, tg.team, tg.sport)] = tg
    for drive in drives:
        tg = by_key.get((drive.game_id, drive.week, drive.offense, drive.sport))
        if tg is None:
            continue
        tg.n_drives += 1
        if drive.scoring_opportunity:
            tg.n_opp += 1
            tg.opp_points += drive.points
            if drive.finished:
                tg.finished_opp += 1
        if drive.red_zone_opportunity:
            tg.n_rz += 1
        tg.points_source = drive.points_source


def finishing_diagnosis(plays: Sequence[CanonicalPlay]) -> Dict[str, Any]:
    """Coverage note for the Phase 1 kickoff-at-35 defect."""
    nfl = [p for p in plays if p.sport == "nfl"]
    kos = [p for p in nfl if p.play_type == "kickoff"]
    kos_40 = [p for p in kos if p.yards_to_endzone is not None and p.yards_to_endzone <= OPP_YTE]
    drives = build_drives(nfl)
    opps = [d for d in drives if d.scoring_opportunity]
    ppo = (sum(d.points for d in opps) / len(opps)) if opps else None
    return {
        "defect": "kickoff_yardline_35_false_opportunity",
        "kickoffs": len(kos),
        "kickoffs_yle_40": len(kos_40),
        "kickoff_false_opp_rate": (len(kos_40) / len(kos)) if kos else None,
        "drives": len(drives),
        "opportunity_drives": len(opps),
        "opportunity_rate": (len(opps) / len(drives)) if drives else None,
        "ppo_repaired": ppo,
        "finish_repaired": (sum(1 for d in opps if d.finished) / len(opps)) if opps else None,
        "points_source": "fixed_drive_result+pat_flags",
        "calibrated": False,
    }
