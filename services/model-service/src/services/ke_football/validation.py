"""Football validation for Phase 1 measurement.

Forbidden objectives: ATS, closing-line error, betting ROI, KEI lift.
Primary: next-game same-unit EPA / success / pace / expl / finish.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.services.ke_football.aggregate import TeamGame, team_week_snapshot
from src.services.ke_football.opp_adj import adjust_team_week, derived_book, league_means


def _mae(pairs: Sequence[Tuple[float, float]]) -> Optional[float]:
    if not pairs:
        return None
    return sum(abs(a - b) for a, b in pairs) / len(pairs)


def _rmse(pairs: Sequence[Tuple[float, float]]) -> Optional[float]:
    if not pairs:
        return None
    return math.sqrt(sum((a - b) ** 2 for a, b in pairs) / len(pairs))


def _bias(pairs: Sequence[Tuple[float, float]]) -> Optional[float]:
    if not pairs:
        return None
    return sum(a - b for a, b in pairs) / len(pairs)


def _corr(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def next_game_epa(
    games: Sequence[TeamGame],
    *,
    min_as_of: int = 3,
) -> Dict[str, Any]:
    """Predict game-w EPA from as_of=w snapshot (week < w). Football only."""
    by_week: Dict[int, List[TeamGame]] = defaultdict(list)
    for g in games:
        by_week[g.week].append(g)
    weeks = sorted(by_week)
    off_model: List[Tuple[float, float]] = []
    off_unadj: List[Tuple[float, float]] = []
    off_league: List[Tuple[float, float]] = []
    def_model: List[Tuple[float, float]] = []
    def_unadj: List[Tuple[float, float]] = []
    def_league: List[Tuple[float, float]] = []

    for w in weeks:
        if w < min_as_of:
            continue
        prior = [g for g in games if g.week < w]
        book = derived_book(prior, as_of_week=w)
        league = league_means(book)
        for g in by_week[w]:
            if g.off_epa is None:
                continue
            snap = team_week_snapshot(prior, sport=g.sport, season=g.season, as_of_week=w, team=g.team)
            adj = adjust_team_week(prior, team=g.team, as_of_week=w)
            pred_off = adj["components"]["ke.opp_adj_epa.off"]["value"]
            raw_off = snap["off_epa_raw"]
            lg_off = league.get("off")
            if pred_off is not None:
                off_model.append((pred_off, g.off_epa))
            if raw_off is not None:
                off_unadj.append((raw_off, g.off_epa))
            if lg_off is not None:
                off_league.append((lg_off, g.off_epa))
            pred_def = adj["components"]["ke.opp_adj_epa.def"]["value"]
            raw_def = snap["def_epa_raw"]
            lg_def = league.get("def")
            if g.def_epa is not None and pred_def is not None:
                def_model.append((pred_def, g.def_epa))
            if g.def_epa is not None and raw_def is not None:
                def_unadj.append((raw_def, g.def_epa))
            if g.def_epa is not None and lg_def is not None:
                def_league.append((lg_def, g.def_epa))

    def pack(pairs: Sequence[Tuple[float, float]]) -> Dict[str, Any]:
        return {
            "n": len(pairs),
            "mae": _mae(pairs),
            "rmse": _rmse(pairs),
            "bias": _bias(pairs),
        }

    return {
        "objective": "next_game_epa_per_play",
        "forbidden": ["ats", "close", "roi", "kei", "issue_562_totals"],
        "offense": {
            "adjusted": pack(off_model),
            "unadjusted": pack(off_unadj),
            "league_mean": pack(off_league),
        },
        "defense": {
            "adjusted": pack(def_model),
            "unadjusted": pack(def_unadj),
            "league_mean": pack(def_league),
        },
    }


def week_to_week_stability(
    snapshots_by_week: Dict[int, List[Dict[str, Any]]],
    *,
    component_id: str = "ke.off_eff",
) -> Dict[str, Any]:
    weeks = sorted(snapshots_by_week)
    corrs: List[Dict[str, Any]] = []
    for a, b in zip(weeks, weeks[1:]):
        left = {r["team"]: r["components"].get(component_id, {}).get("value") for r in snapshots_by_week[a]}
        right = {r["team"]: r["components"].get(component_id, {}).get("value") for r in snapshots_by_week[b]}
        teams = [t for t in left if left[t] is not None and right.get(t) is not None]
        xs = [float(left[t]) for t in teams]
        ys = [float(right[t]) for t in teams]
        corrs.append({"from": a, "to": b, "n": len(teams), "pearson": _corr(xs, ys)})
    return {"component": component_id, "pairs": corrs}


def ranking_sanity(snapshots: Sequence[Dict[str, Any]], *, k: int = 6, min_games: int = 4) -> Dict[str, Any]:
    rows = []
    for snap in snapshots:
        off = snap.get("off_epa_raw")
        deff = snap.get("def_epa_raw")
        if off is None or deff is None:
            continue
        if int(snap.get("n_games") or 0) < min_games:
            continue
        rows.append(
            {
                "team": snap["team"],
                "off_epa_raw": off,
                "def_epa_raw": deff,
                "n_games": snap.get("n_games"),
                "n_off_plays": snap.get("n_off_plays"),
            }
        )
    by_off = sorted(rows, key=lambda r: r["off_epa_raw"], reverse=True)
    by_def = sorted(rows, key=lambda r: r["def_epa_raw"])  # lower allowed better
    return {
        "best_offense": by_off[:k],
        "worst_offense": list(reversed(by_off[-k:])) if by_off else [],
        "best_defense": by_def[:k],
        "worst_defense": list(reversed(by_def[-k:])) if by_def else [],
        "note": "sanity only — not a seal; not Team Strength",
    }


def missingness(snapshots: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for snap in snapshots:
        for cid, cell in (snap.get("components") or {}).items():
            counts[cid][str(cell.get("status"))] += 1
    return {cid: dict(st) for cid, st in counts.items()}


def provenance_audit(snapshots: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    layers: Dict[str, str] = {}
    bad: List[str] = []
    for snap in snapshots:
        for cid, cell in (snap.get("components") or {}).items():
            layer = cell.get("layer")
            layers[cid] = str(layer)
            if layer not in {"RAW", "DERIVED", "ADJUSTED", "MODELED"}:
                bad.append(cid)
            if cid == "ke.team_strength" and cell.get("status") != "OMIT":
                bad.append("team_strength_not_omitted")
            if cid == "ke.opp_adj_epa.off" and layer == "MODELED":
                bad.append("phase1_opp_adj_must_be_adjusted")
    return {
        "layers_by_id": layers,
        "violations": bad,
        "taxonomy": ["RAW", "DERIVED", "ADJUSTED", "MODELED"],
        "ok": not bad,
    }
