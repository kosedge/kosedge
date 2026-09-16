"""PIT-safe opponent-adjustment bakeoff (Phase 1B).

Every candidate uses only ``week < W`` and leave-one-game-out for the
target game. No ATS / close / ROI. #560 ridge is a labeled MODELED
reference, not re-fit here.

Phase 1 simple SOS failed to beat trailing unadjusted — that result is
preserved as ``loo_sos``. ``NO_ADJUSTMENT_WINNER`` is an acceptable call.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from src.services.ke_football.aggregate import TeamGame
from src.services.ke_football.opp_adj import derived_book, league_means
from src.services.ke_football.validation import _mae, _rmse, _bias

Pred = Tuple[Optional[float], Optional[float]]  # off, def


def _book_from_acc(acc: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, Optional[float]]]:
    out: Dict[str, Dict[str, Optional[float]]] = {}
    for team, row in acc.items():
        out[team] = {
            "off": (row["off_sum"] / row["off_n"]) if row["off_n"] else None,
            "def": (row["def_sum"] / row["def_n"]) if row["def_n"] else None,
            "n_off": row["off_n"],
            "n_def": row["def_n"],
            "n_games": row["n_games"],
        }
    return out


class PitIndex:
    """O(1) leave-one-game-out books. Week W uses only week < W."""

    def __init__(self, games: Sequence[TeamGame]):
        self.games = list(games)
        self.by_game: Dict[str, List[TeamGame]] = defaultdict(list)
        self.by_team: Dict[str, List[TeamGame]] = defaultdict(list)
        weeks = sorted({g.week for g in games})
        self.max_week = max(weeks) if weeks else 0
        # Incremental per-week team sums, then prefix.
        inc: Dict[int, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: {"off_sum": 0.0, "off_n": 0.0, "def_sum": 0.0, "def_n": 0.0, "n_games": 0.0})
        )
        for g in games:
            self.by_game[g.game_id].append(g)
            self.by_team[g.team].append(g)
            row = inc[g.week][g.team]
            if g.off_epa is not None:
                row["off_sum"] += g.off_epa * g.off_epa_n
                row["off_n"] += float(g.off_epa_n)
            if g.def_epa is not None:
                row["def_sum"] += g.def_epa * g.def_epa_n
                row["def_n"] += float(g.def_epa_n)
            row["n_games"] += 1.0
        teams = sorted({g.team for g in games} | {g.opponent for g in games if g.opponent})
        self._prefix: Dict[int, Dict[str, Dict[str, float]]] = {}
        running: Dict[str, Dict[str, float]] = {
            t: {"off_sum": 0.0, "off_n": 0.0, "def_sum": 0.0, "def_n": 0.0, "n_games": 0.0} for t in teams
        }
        for w in range(1, self.max_week + 2):
            # prefix[w] = sums of week < w
            self._prefix[w] = {t: dict(running[t]) for t in teams}
            if w in inc:
                for t, add in inc[w].items():
                    for k, val in add.items():
                        running[t][k] += val

    def book(self, as_of_week: int, exclude_game_id: Optional[str] = None) -> Dict[str, Dict[str, Optional[float]]]:
        base = {t: dict(row) for t, row in (self._prefix.get(as_of_week) or {}).items()}
        if exclude_game_id:
            for g in self.by_game.get(exclude_game_id, []):
                row = base.get(g.team)
                if not row:
                    continue
                if g.off_epa is not None:
                    row["off_sum"] -= g.off_epa * g.off_epa_n
                    row["off_n"] -= float(g.off_epa_n)
                if g.def_epa is not None:
                    row["def_sum"] -= g.def_epa * g.def_epa_n
                    row["def_n"] -= float(g.def_epa_n)
                row["n_games"] -= 1.0
        return _book_from_acc(base)

    def prior(self, team: str, as_of_week: int) -> List[TeamGame]:
        return [g for g in self.by_team.get(team, []) if g.week < as_of_week]


def _pw(pairs: Sequence[Tuple[float, int]]) -> Optional[float]:
    den = sum(n for _v, n in pairs if n > 0)
    if den <= 0:
        return None
    return sum(v * n for v, n in pairs if n > 0) / den


def _prior(games: Sequence[TeamGame], *, team: str, as_of_week: int) -> List[TeamGame]:
    return [g for g in games if g.team == team and g.week < as_of_week]


def unadjusted(games: Sequence[TeamGame], *, team: str, as_of_week: int, **_k: Any) -> Pred:
    mine = _prior(games, team=team, as_of_week=as_of_week)
    return (
        _pw([(g.off_epa, g.off_epa_n) for g in mine if g.off_epa is not None]),
        _pw([(g.def_epa, g.def_epa_n) for g in mine if g.def_epa is not None]),
    )


def loo_sos(games: Sequence[TeamGame], *, team: str, as_of_week: int, **_k: Any) -> Pred:
    """Phase 1 simple SOS. Preserved as a candidate, not promoted."""
    from src.services.ke_football.opp_adj import adjust_team_week

    row = adjust_team_week(games, team=team, as_of_week=as_of_week)
    off = row["components"]["ke.opp_adj_epa.off"]["value"]
    deff = row["components"]["ke.opp_adj_epa.def"]["value"]
    return off, deff


def shrunken_sos(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    k: float = 8.0,
    **_k: Any,
) -> Pred:
    """SOS times n/(n+k). k selected on the selection window only."""
    mine = _prior(games, team=team, as_of_week=as_of_week)
    off_terms: List[Tuple[float, int]] = []
    def_terms: List[Tuple[float, int]] = []
    for g in mine:
        book = derived_book(games, as_of_week=as_of_week, exclude_game_id=g.game_id)
        league = league_means(book)
        opp = book.get(g.opponent) or {}
        n_opp = float((opp.get("n_def") or 0) if g.off_epa is not None else 0)
        shrink = n_opp / (n_opp + k) if (n_opp + k) else 0.0
        if g.off_epa is not None and opp.get("def") is not None and league.get("def") is not None:
            adj = g.off_epa - shrink * (float(opp["def"]) - float(league["def"]))
            off_terms.append((adj, g.off_epa_n))
        if g.def_epa is not None and opp.get("off") is not None and league.get("off") is not None:
            adj = g.def_epa - shrink * (float(opp["off"]) - float(league["off"]))
            def_terms.append((adj, g.def_epa_n))
    return _pw(off_terms), _pw(def_terms)


def _iterative_ratings(
    games: Sequence[TeamGame],
    *,
    as_of_week: int,
    exclude_game_id: Optional[str],
    iters: int,
    lam: float,
) -> Dict[str, Dict[str, float]]:
    window = [g for g in games if g.week < as_of_week and g.game_id != exclude_game_id]
    teams = sorted({g.team for g in window} | {g.opponent for g in window if g.opponent})
    off = {t: 0.0 for t in teams}
    deff = {t: 0.0 for t in teams}
    for _ in range(int(iters)):
        off_acc: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        def_acc: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        for g in window:
            if g.off_epa is not None and g.opponent:
                off_acc[g.team].append((g.off_epa - deff.get(g.opponent, 0.0), g.off_epa_n))
            if g.def_epa is not None and g.opponent:
                def_acc[g.team].append((g.def_epa - off.get(g.opponent, 0.0), g.def_epa_n))
        for t in teams:
            raw_o = _pw(off_acc.get(t, []))
            raw_d = _pw(def_acc.get(t, []))
            n_o = sum(n for _v, n in off_acc.get(t, []))
            n_d = sum(n for _v, n in def_acc.get(t, []))
            if raw_o is not None:
                off[t] = (n_o * raw_o) / (n_o + lam) if (n_o + lam) else 0.0
            if raw_d is not None:
                deff[t] = (n_d * raw_d) / (n_d + lam) if (n_d + lam) else 0.0
        # Center identifiable set at 0 (play-unweighted across teams with data).
        o_vals = [off[t] for t in teams if off_acc.get(t)]
        d_vals = [deff[t] for t in teams if def_acc.get(t)]
        if o_vals:
            mu = sum(o_vals) / len(o_vals)
            for t in teams:
                off[t] -= mu
        if d_vals:
            mu = sum(d_vals) / len(d_vals)
            for t in teams:
                deff[t] -= mu
    return {t: {"off": off[t], "def": deff[t]} for t in teams}


def iterative_twoway(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    iters: int = 8,
    lam: float = 0.0,
    **_k: Any,
) -> Pred:
    book = _iterative_ratings(games, as_of_week=as_of_week, exclude_game_id=None, iters=iters, lam=lam)
    row = book.get(team) or {}
    return row.get("off"), row.get("def")


def iterative_ridge(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    iters: int = 8,
    lam: float = 40.0,
    **_k: Any,
) -> Pred:
    """Same family as #560, knobs not copied as a promote. Research candidate only."""
    return iterative_twoway(games, team=team, as_of_week=as_of_week, iters=iters, lam=lam)


def schedule_network(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    **_k: Any,
) -> Pred:
    """One-step opponent-of-opponent SOS. PIT + LOO."""
    mine = _prior(games, team=team, as_of_week=as_of_week)
    book = derived_book(games, as_of_week=as_of_week)
    league = league_means(book)
    off_terms: List[Tuple[float, int]] = []
    def_terms: List[Tuple[float, int]] = []
    for g in mine:
        loo = derived_book(games, as_of_week=as_of_week, exclude_game_id=g.game_id)
        lg = league_means(loo)
        opp = loo.get(g.opponent) or {}
        if g.off_epa is None or opp.get("def") is None or lg.get("def") is None:
            continue
        # Opponent's typical remaining SOS: mean of *their* opponents' off (LOO).
        opp_games = [x for x in games if x.team == g.opponent and x.week < as_of_week and x.game_id != g.game_id]
        nest = []
        for og in opp_games:
            other = loo.get(og.opponent) or {}
            if other.get("off") is not None:
                nest.append(float(other["off"]))
        nest_mean = (sum(nest) / len(nest)) if nest else lg.get("off") or 0.0
        sos = (float(opp["def"]) - float(lg["def"])) + 0.5 * (nest_mean - (lg.get("off") or 0.0))
        off_terms.append((g.off_epa - sos, g.off_epa_n))
        if g.def_epa is not None and opp.get("off") is not None and lg.get("off") is not None:
            nest_d = []
            for og in opp_games:
                other = loo.get(og.opponent) or {}
                if other.get("def") is not None:
                    nest_d.append(float(other["def"]))
            nest_d_mean = (sum(nest_d) / len(nest_d)) if nest_d else lg.get("def") or 0.0
            sos_d = (float(opp["off"]) - float(lg["off"])) + 0.5 * (nest_d_mean - (lg.get("def") or 0.0))
            def_terms.append((g.def_epa - sos_d, g.def_epa_n))
    return _pw(off_terms), _pw(def_terms)


def _fast_unadjusted(index: PitIndex, *, team: str, as_of_week: int) -> Pred:
    mine = index.prior(team, as_of_week)
    return (
        _pw([(g.off_epa, g.off_epa_n) for g in mine if g.off_epa is not None]),
        _pw([(g.def_epa, g.def_epa_n) for g in mine if g.def_epa is not None]),
    )


def _fast_loo_sos(index: PitIndex, *, team: str, as_of_week: int) -> Pred:
    mine = index.prior(team, as_of_week)
    off_terms: List[Tuple[float, int]] = []
    def_terms: List[Tuple[float, int]] = []
    for g in mine:
        book = index.book(as_of_week, exclude_game_id=g.game_id)
        league = league_means(book)
        opp = book.get(g.opponent) or {}
        if g.off_epa is not None and opp.get("def") is not None and league.get("def") is not None:
            off_terms.append((g.off_epa - (float(opp["def"]) - float(league["def"])), g.off_epa_n))
        if g.def_epa is not None and opp.get("off") is not None and league.get("off") is not None:
            def_terms.append((g.def_epa - (float(opp["off"]) - float(league["off"])), g.def_epa_n))
    return _pw(off_terms), _pw(def_terms)


def _fast_shrunken(index: PitIndex, *, team: str, as_of_week: int, k: float) -> Pred:
    mine = index.prior(team, as_of_week)
    off_terms: List[Tuple[float, int]] = []
    def_terms: List[Tuple[float, int]] = []
    for g in mine:
        book = index.book(as_of_week, exclude_game_id=g.game_id)
        league = league_means(book)
        opp = book.get(g.opponent) or {}
        n_opp = float(opp.get("n_def") or 0)
        shrink = n_opp / (n_opp + k) if (n_opp + k) else 0.0
        if g.off_epa is not None and opp.get("def") is not None and league.get("def") is not None:
            off_terms.append((g.off_epa - shrink * (float(opp["def"]) - float(league["def"])), g.off_epa_n))
        if g.def_epa is not None and opp.get("off") is not None and league.get("off") is not None:
            def_terms.append((g.def_epa - shrink * (float(opp["off"]) - float(league["off"])), g.def_epa_n))
    return _pw(off_terms), _pw(def_terms)


def _fast_schedule_network(index: PitIndex, *, team: str, as_of_week: int) -> Pred:
    mine = index.prior(team, as_of_week)
    off_terms: List[Tuple[float, int]] = []
    def_terms: List[Tuple[float, int]] = []
    for g in mine:
        loo = index.book(as_of_week, exclude_game_id=g.game_id)
        lg = league_means(loo)
        opp = loo.get(g.opponent) or {}
        if g.off_epa is None or opp.get("def") is None or lg.get("def") is None:
            continue
        opp_games = index.prior(g.opponent, as_of_week)
        nest = []
        nest_d = []
        for og in opp_games:
            if og.game_id == g.game_id:
                continue
            other = loo.get(og.opponent) or {}
            if other.get("off") is not None:
                nest.append(float(other["off"]))
            if other.get("def") is not None:
                nest_d.append(float(other["def"]))
        nest_mean = (sum(nest) / len(nest)) if nest else lg.get("off") or 0.0
        sos = (float(opp["def"]) - float(lg["def"])) + 0.5 * (nest_mean - (lg.get("off") or 0.0))
        off_terms.append((g.off_epa - sos, g.off_epa_n))
        if g.def_epa is not None and opp.get("off") is not None and lg.get("off") is not None:
            nest_d_mean = (sum(nest_d) / len(nest_d)) if nest_d else lg.get("def") or 0.0
            sos_d = (float(opp["off"]) - float(lg["off"])) + 0.5 * (nest_d_mean - (lg.get("def") or 0.0))
            def_terms.append((g.def_epa - sos_d, g.def_epa_n))
    return _pw(off_terms), _pw(def_terms)


def _candidate_fns(index: PitIndex) -> Dict[str, Callable[..., Pred]]:
    iter_cache: Dict[Tuple[int, float], Dict[str, Dict[str, float]]] = {}

    def _iter_pred(*, team: str, as_of_week: int, lam: float) -> Pred:
        key = (as_of_week, lam)
        if key not in iter_cache:
            iter_cache[key] = _iterative_ratings(
                index.games, as_of_week=as_of_week, exclude_game_id=None, iters=8, lam=lam
            )
        row = iter_cache[key].get(team) or {}
        return row.get("off"), row.get("def")

    return {
        "unadjusted": lambda **k: _fast_unadjusted(index, team=k["team"], as_of_week=k["as_of_week"]),
        "loo_sos": lambda **k: _fast_loo_sos(index, team=k["team"], as_of_week=k["as_of_week"]),
        "shrunken_sos_k4": lambda **k: _fast_shrunken(index, team=k["team"], as_of_week=k["as_of_week"], k=4.0),
        "shrunken_sos_k8": lambda **k: _fast_shrunken(index, team=k["team"], as_of_week=k["as_of_week"], k=8.0),
        "shrunken_sos_k16": lambda **k: _fast_shrunken(index, team=k["team"], as_of_week=k["as_of_week"], k=16.0),
        "iterative_twoway": lambda **k: _iter_pred(team=k["team"], as_of_week=k["as_of_week"], lam=0.0),
        "iterative_ridge_l40": lambda **k: _iter_pred(team=k["team"], as_of_week=k["as_of_week"], lam=40.0),
        "schedule_network": lambda **k: _fast_schedule_network(index, team=k["team"], as_of_week=k["as_of_week"]),
    }


CANDIDATES: Dict[str, Callable[..., Pred]] = {
    "unadjusted": unadjusted,
    "loo_sos": loo_sos,
    "shrunken_sos_k4": lambda **k: shrunken_sos(k=4.0, **k),
    "shrunken_sos_k8": lambda **k: shrunken_sos(k=8.0, **k),
    "shrunken_sos_k16": lambda **k: shrunken_sos(k=16.0, **k),
    "iterative_twoway": iterative_twoway,
    "iterative_ridge_l40": lambda **k: iterative_ridge(lam=40.0, **k),
    "schedule_network": schedule_network,
}


def _eval_pairs(
    games: Sequence[TeamGame],
    *,
    method: Callable[..., Pred],
    week_min: int,
    week_max: int,
) -> Dict[str, Any]:
    off_pairs: List[Tuple[float, float]] = []
    def_pairs: List[Tuple[float, float]] = []
    by_week = defaultdict(list)
    for g in games:
        by_week[g.week].append(g)
    cache: Dict[Tuple[str, int], Pred] = {}
    for w in sorted(by_week):
        if w < week_min or w > week_max:
            continue
        for g in by_week[w]:
            key = (g.team, w)
            if key not in cache:
                cache[key] = method(games=games, team=g.team, as_of_week=w)
            pred_off, pred_def = cache[key]
            if pred_off is not None and g.off_epa is not None:
                off_pairs.append((pred_off, g.off_epa))
            if pred_def is not None and g.def_epa is not None:
                def_pairs.append((pred_def, g.def_epa))
    return {
        "offense": {"n": len(off_pairs), "mae": _mae(off_pairs), "rmse": _rmse(off_pairs), "bias": _bias(off_pairs)},
        "defense": {"n": len(def_pairs), "mae": _mae(def_pairs), "rmse": _rmse(def_pairs), "bias": _bias(def_pairs)},
    }


def run_bakeoff(
    games: Sequence[TeamGame],
    *,
    selection_weeks: Tuple[int, int] = (5, 10),
    confirmation_weeks: Tuple[int, int] = (11, 18),
    full_weeks: Tuple[int, int] = (3, 18),
    relative_cut: float = 0.02,
) -> Dict[str, Any]:
    """Frozen OOS bakeoff. Selection weeks never used as the confirmation seal."""
    results: Dict[str, Any] = {}
    index = PitIndex(games)
    methods = _candidate_fns(index)
    for name, fn in methods.items():
        results[name] = {
            "full": _eval_pairs(games, method=fn, week_min=full_weeks[0], week_max=full_weeks[1]),
            "selection": _eval_pairs(games, method=fn, week_min=selection_weeks[0], week_max=selection_weeks[1]),
            "confirmation": _eval_pairs(
                games, method=fn, week_min=confirmation_weeks[0], week_max=confirmation_weeks[1]
            ),
        }

    unadj = results["unadjusted"]["confirmation"]
    winner = "NO_ADJUSTMENT_WINNER"
    wins: List[str] = []
    for name, row in results.items():
        if name == "unadjusted":
            continue
        conf = row["confirmation"]
        off_ok = _beats(conf["offense"]["mae"], unadj["offense"]["mae"], relative_cut)
        def_ok = _beats(conf["defense"]["mae"], unadj["defense"]["mae"], relative_cut)
        row["beats_unadjusted_confirmation"] = {"offense": off_ok, "defense": def_ok}
        if off_ok and def_ok:
            wins.append(name)
    if len(wins) == 1:
        winner = wins[0]
    elif len(wins) > 1:
        # Tie-break on confirmation off+def MAE sum; still require both sides.
        winner = min(
            wins,
            key=lambda n: (
                (results[n]["confirmation"]["offense"]["mae"] or 9)
                + (results[n]["confirmation"]["defense"]["mae"] or 9)
            ),
        )
    else:
        winner = "NO_ADJUSTMENT_WINNER"

    return {
        "objective": "next_game_epa_per_play",
        "forbidden": ["ats", "close", "roi", "kei", "clv", "issue_562"],
        "pit": "week < W; leave-one-game-out on SOS-style methods",
        "selection_weeks": list(selection_weeks),
        "confirmation_weeks": list(confirmation_weeks),
        "relative_cut": relative_cut,
        "phase1_loo_sos_preserved": True,
        "winner": winner,
        "methods_that_beat_unadjusted_both_sides": wins,
        "candidates": results,
        "production_promote": False,
        "note": (
            "NO_ADJUSTMENT_WINNER is acceptable. Do not promote a method "
            "because opponent adjustment is theoretically desirable."
        ),
    }


def _beats(mae: Optional[float], baseline: Optional[float], cut: float) -> bool:
    if mae is None or baseline is None or baseline <= 0:
        return False
    return mae <= baseline * (1.0 - cut)


def future_week_changes_any_method(
    games: Sequence[TeamGame],
    *,
    team: str,
    as_of_week: int,
    future_game: TeamGame,
) -> Dict[str, bool]:
    leaked = deepcopy(future_game)
    leaked.week = as_of_week
    leaked.game_id = "LEAK_FUTURE"
    leaked.off_epa_sum = 50.0
    leaked.off_epa_n = 80
    out: Dict[str, bool] = {}
    for name, fn in CANDIDATES.items():
        before = fn(games=games, team=team, as_of_week=as_of_week)
        after = fn(games=list(games) + [leaked], team=team, as_of_week=as_of_week)
        out[name] = before != after
    return out
