"""Phase 2A feature book — eligible measurements for unit ratings.

PASS = initial candidate set.
PARTIAL = research only; must earn incremental signal after shrinkage.
DATA_INSUFFICIENT / opp-adj / named havoc / CFB ST / pace = excluded.

Pace is a distinct construct (not unit quality). ST is not Off/Def Efficiency.
Opponent adjustment is not reopened (NO_ADJUSTMENT_WINNER).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.services.ke_football.aggregate import TeamGame
from src.services.ke_football.component_validate import team_game_metric

# Phase 1B scorecard lock. Sport-specific. Do not copy NFL coefficients to CFB.
FEATURE_BOOK: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    "nfl": {
        "off": {
            "pass": [
                "ke.off_eff",
                "ke.success_native",
                "ke.success_standard",
                "ke.off_pass_epa",
                "ke.opp_rate",
            ],
            "partial_research": [
                "ke.expl",
                "ke.expl_pass",
                "ke.off_early_epa",
                "ke.ppo",
                "ke.finish",
            ],
        },
        "def": {
            "pass": ["ke.success_allowed"],
            "core": ["ke.def_eff"],
            "partial_research": ["ke.expl_allowed", "ke.disruption_proxy_nfl"],
        },
    },
    "cfb": {
        "off": {
            "pass": [
                "ke.off_eff",
                "ke.success_native",
                "ke.success_standard",
                "ke.expl",
                "ke.expl_pass",
                "ke.off_early_epa",
                "ke.opp_rate",
            ],
            "partial_research": ["ke.ppo", "ke.finish", "ke.off_pass_epa", "ke.expl_rush"],
        },
        "def": {
            "pass": [],
            "core": ["ke.def_eff"],
            "partial_research": ["ke.success_allowed", "ke.expl_allowed"],
        },
    },
}

EXCLUDED = {
    "ke.pace",
    "ke.pace_competitive",
    "ke.pace_seconds",
    "ke.st",
    "ke.havoc",
    "ke.rz_td",
    "ke.opp_adj_epa",
    "ke.opp_adj_epa.off",
    "ke.opp_adj_epa.def",
    "ke.team_strength",
    "ke.disruption_interception",
    "ke.disruption_fumble_forced",
    "ke.disruption_tfl",
    "ke.disruption_tackle_for_loss",
    "ke.disruption_pass_breakup",
    "ke.disruption_qb_hit",
    "ke.disruption_fumble",
    "ke.disruption_flags_cfb",
}

# CFB disruption stays out (DATA_INSUFFICIENT except sack, which is still
# not a unit-quality SoT). Named havoc never enters.
CFB_DISRUPTION_OUT = {
    "ke.disruption_sack",
    "ke.disruption_proxy_nfl",
    "ke.havoc",
}

LOWER_BETTER = {
    "ke.def_eff",
    "ke.success_allowed",
    "ke.expl_allowed",
}

EPA_ID = {"off": "ke.off_eff", "def": "ke.def_eff"}


@dataclass
class FeatureSpec:
    sport: str
    side: str
    cid: str
    grade: str  # PASS | PARTIAL | CORE
    higher_better: bool


def specs_for(sport: str, side: str) -> List[FeatureSpec]:
    book = FEATURE_BOOK[sport][side]
    out: List[FeatureSpec] = []
    for cid in book.get("core") or []:
        out.append(
            FeatureSpec(
                sport=sport,
                side=side,
                cid=cid,
                grade="CORE",
                higher_better=cid not in LOWER_BETTER,
            )
        )
    for cid in book.get("pass") or []:
        out.append(
            FeatureSpec(
                sport=sport,
                side=side,
                cid=cid,
                grade="PASS",
                higher_better=cid not in LOWER_BETTER,
            )
        )
    for cid in book.get("partial_research") or []:
        if sport != "nfl" and cid in CFB_DISRUPTION_OUT:
            continue
        out.append(
            FeatureSpec(
                sport=sport,
                side=side,
                cid=cid,
                grade="PARTIAL",
                higher_better=cid not in LOWER_BETTER,
            )
        )
    return out


def pass_core_ids(sport: str, side: str) -> List[str]:
    return [s.cid for s in specs_for(sport, side) if s.grade in {"PASS", "CORE"}]


def partial_ids(sport: str, side: str) -> List[str]:
    return [s.cid for s in specs_for(sport, side) if s.grade == "PARTIAL"]


def assert_not_excluded(cids: Sequence[str], *, sport: str) -> None:
    bad = [c for c in cids if c in EXCLUDED]
    if sport != "nfl":
        bad += [c for c in cids if c in CFB_DISRUPTION_OUT]
    if bad:
        raise AssertionError(f"excluded features entered unit rating: {bad}")


def _disruption_rate(g: TeamGame, attr: str) -> Optional[float]:
    scrim = [p for p in g.def_plays if p.is_scrimmage]
    if not scrim:
        return None
    if attr == "proxy":
        usable = [
            p
            for p in scrim
            if p.sack is not None or p.interception is not None or p.qb_hit is not None
        ]
        if not usable:
            return None
        hits = sum(1 for p in usable if p.sack is True or p.interception is True or p.qb_hit is True)
        return hits / len(usable)
    usable = [p for p in scrim if getattr(p, attr) is not None]
    if not usable:
        return None
    null_rate = 1.0 - (len(usable) / len(scrim))
    if null_rate > 0.05:
        return None
    return sum(1 for p in usable if getattr(p, attr) is True) / len(usable)


def game_metric(g: TeamGame, cid: str) -> Optional[float]:
    if cid == "ke.disruption_proxy_nfl":
        return _disruption_rate(g, "proxy")
    if cid == "ke.disruption_sack":
        return _disruption_rate(g, "sack")
    return team_game_metric(g, cid)


def _weight(g: TeamGame, cid: str) -> int:
    if cid in {"ke.off_eff", "ke.off_pass_epa", "ke.off_rush_epa", "ke.off_early_epa"}:
        return g.off_epa_n
    if cid == "ke.def_eff":
        return g.def_epa_n
    if cid == "ke.success_native":
        return g.success_d
    if cid == "ke.success_standard":
        return g.std_d
    if cid == "ke.success_allowed":
        return g.success_allowed_d
    if cid == "ke.expl":
        return g.expl_d
    if cid == "ke.expl_pass":
        return g.expl_pass_d
    if cid == "ke.expl_rush":
        return g.expl_rush_d
    if cid == "ke.expl_allowed":
        return g.expl_allowed_d
    if cid in {"ke.ppo", "ke.finish"}:
        return g.n_opp
    if cid == "ke.opp_rate":
        return g.n_drives
    if cid in {"ke.disruption_proxy_nfl", "ke.disruption_sack"}:
        return g.n_def_plays
    return max(g.n_off_plays, 1)


def trailing_metric(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    cid: str,
) -> Optional[float]:
    mine = [g for g in games if g.team == team and g.week < as_of_week]
    usable = [(game_metric(g, cid), _weight(g, cid)) for g in mine]
    usable = [(v, w) for v, w in usable if v is not None and w > 0]
    if not usable:
        return None
    den = sum(w for _v, w in usable)
    return sum(v * w for v, w in usable) / den


def trailing_n(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    side: str,
) -> Tuple[int, int]:
    mine = [g for g in games if g.team == team and g.week < as_of_week]
    if side == "def":
        return len(mine), int(sum(g.def_epa_n for g in mine))
    return len(mine), int(sum(g.off_epa_n for g in mine))


def trailing_vector(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    cids: Sequence[str],
) -> Dict[str, Optional[float]]:
    return {cid: trailing_metric(games, team=team, as_of_week=as_of_week, cid=cid) for cid in cids}


def teams_at(games: Sequence[TeamGame], *, as_of_week: int) -> List[str]:
    return sorted({g.team for g in games if g.week < as_of_week})


def feature_policy(*, sport: str) -> Dict[str, Any]:
    return {
        "sport": sport,
        "pass_off": pass_core_ids(sport, "off"),
        "partial_off": partial_ids(sport, "off"),
        "pass_def": pass_core_ids(sport, "def"),
        "partial_def": partial_ids(sport, "def"),
        "excluded": sorted(EXCLUDED),
        "cfb_disruption_out": sport != "nfl",
        "opp_adj_reopened": False,
        "opp_adj_result": "NO_ADJUSTMENT_WINNER",
        "pace_in_unit_rating": False,
        "named_havoc": False,
        "team_strength": False,
        "finishing_auto_promote": False,
        "note": "PARTIAL finishing stays available; it must earn incremental signal",
    }
