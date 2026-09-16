"""Phase 2A validation for KE Off/Def Efficiency.

Football only: next-game EPA / success. No ATS / close / ROI / CLV.
Composites must beat trailing EPA to earn inclusion.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.services.ke_football.aggregate import TeamGame
from src.services.ke_football.unit_features import EPA_ID, feature_policy, game_metric, trailing_metric
from src.services.ke_football.unit_ratings import (
    FORBIDDEN_OBJECTIVES,
    METHODS,
    MethodFit,
    UNIT_IDS,
    _pairs_for_method,
    clear_z_cache,
    fit_selection,
    method_layer,
    predict_method,
    snapshot_book,
)
from src.services.ke_football.validation import _corr, _mae, _rmse, ranking_sanity
from src.services.ke_football.component_validate import _spearman, early_late_persistence


RELATIVE_CUT = 0.02


def _pack(pairs: Sequence[Tuple[float, float]]) -> Dict[str, Any]:
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    return {
        "n": len(pairs),
        "mae": _mae(pairs),
        "rmse": _rmse(pairs),
        "pearson": _corr(xs, ys) if len(pairs) >= 3 else None,
        "spearman": _spearman(xs, ys),
    }


def _beats(mae: Optional[float], baseline: Optional[float], cut: float = RELATIVE_CUT) -> bool:
    if mae is None or baseline is None or baseline <= 0:
        return False
    return mae <= baseline * (1.0 - cut)


def evaluate_methods(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    fit: MethodFit,
    selection_weeks: Tuple[int, int],
    confirmation_weeks: Tuple[int, int],
    full_weeks: Tuple[int, int],
) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for name in METHODS:
        results[name] = {
            "layer": method_layer(name),
            "selection": _pack(
                _pairs_for_method(
                    games,
                    sport=sport,
                    side=side,
                    week_min=selection_weeks[0],
                    week_max=selection_weeks[1],
                    predict=lambda team, as_of_week, name=name: predict_method(
                        games,
                        sport=sport,
                        side=side,
                        team=team,
                        as_of_week=as_of_week,
                        method=name,
                        fit=fit,
                    ),
                )
            ),
            "confirmation": _pack(
                _pairs_for_method(
                    games,
                    sport=sport,
                    side=side,
                    week_min=confirmation_weeks[0],
                    week_max=confirmation_weeks[1],
                    predict=lambda team, as_of_week, name=name: predict_method(
                        games,
                        sport=sport,
                        side=side,
                        team=team,
                        as_of_week=as_of_week,
                        method=name,
                        fit=fit,
                    ),
                )
            ),
            "full": _pack(
                _pairs_for_method(
                    games,
                    sport=sport,
                    side=side,
                    week_min=full_weeks[0],
                    week_max=full_weeks[1],
                    predict=lambda team, as_of_week, name=name: predict_method(
                        games,
                        sport=sport,
                        side=side,
                        team=team,
                        as_of_week=as_of_week,
                        method=name,
                        fit=fit,
                    ),
                )
            ),
        }

    unadj = results["epa_raw"]["confirmation"]["mae"]
    shrunk = results["epa_shrunken"]["confirmation"]["mae"]
    constituent = unadj
    constituent_name = "epa_raw"
    if shrunk is not None and unadj is not None and shrunk < unadj:
        constituent = shrunk
        constituent_name = "epa_shrunken"
    elif shrunk is not None and unadj is None:
        constituent = shrunk
        constituent_name = "epa_shrunken"

    earned: List[str] = []
    for name, row in results.items():
        if name in {"epa_raw", "epa_shrunken"}:
            row["beats_strongest_constituent"] = False
            continue
        ok = _beats(row["confirmation"]["mae"], constituent)
        row["beats_strongest_constituent"] = ok
        if ok:
            earned.append(name)

    if len(earned) == 1:
        winner = earned[0]
        complexity_earned = True
    elif len(earned) > 1:
        winner = min(earned, key=lambda n: results[n]["confirmation"]["mae"] or 9)
        complexity_earned = True
    else:
        # Honest fallback: best simple EPA method on confirmation.
        winner = constituent_name
        if results["epa_shrunken"]["confirmation"]["mae"] is not None and results["epa_raw"]["confirmation"]["mae"] is not None:
            if results["epa_shrunken"]["confirmation"]["mae"] <= results["epa_raw"]["confirmation"]["mae"]:
                winner = "epa_shrunken"
            else:
                winner = "epa_raw"
        complexity_earned = False

    return {
        "side": side,
        "forbidden": list(FORBIDDEN_OBJECTIVES),
        "selection_weeks": list(selection_weeks),
        "confirmation_weeks": list(confirmation_weeks),
        "relative_cut": RELATIVE_CUT,
        "strongest_constituent": constituent_name,
        "complexity_earned": complexity_earned,
        "winner": winner,
        "earned_composites": earned,
        "earned_partial_features": list(fit.earned_partial),
        "shrink_k": fit.shrink_k,
        "partial_gate": fit.notes.get("partial_gate"),
        "finishing_earned": fit.notes.get("finishing_earned"),
        "candidates": results,
        "production_promote": False,
    }


def incremental_over_epa(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    fit: MethodFit,
    method: str,
    week_min: int,
    week_max: int,
) -> Dict[str, Any]:
    """Partial correlation of unit rating vs next-game EPA after trailing EPA."""
    epa_pairs: List[Tuple[float, float]] = []
    unit_pairs: List[Tuple[float, float]] = []
    xs: List[float] = []
    ys: List[float] = []
    zs: List[float] = []
    by_week: Dict[int, List[TeamGame]] = defaultdict(list)
    for g in games:
        by_week[g.week].append(g)
    for w, rows in by_week.items():
        if w < week_min or w > week_max:
            continue
        for g in rows:
            y = g.def_epa if side == "def" else g.off_epa
            epa_hat = trailing_metric(games, team=g.team, as_of_week=w, cid=EPA_ID[side])
            z_hat = predict_method(
                games, sport=sport, side=side, team=g.team, as_of_week=w, method=method, fit=fit
            )
            if y is None or epa_hat is None or z_hat is None:
                continue
            xs.append(epa_hat)
            ys.append(y)
            zs.append(z_hat)
            epa_pairs.append((epa_hat, y))
            unit_pairs.append((z_hat, y))
    n = len(xs)
    if n < 4:
        return {"n": n, "partial_pearson": None}
    mx = sum(xs) / n
    my = sum(ys) / n
    var = sum((xi - mx) ** 2 for xi in xs)
    if var <= 0:
        resid = [yi - my for yi in ys]
    else:
        b = sum((xi - mx) * (yi - my) for xi, yi in zip(xs, ys)) / var
        a = my - b * mx
        resid = [yi - (a + b * xi) for xi, yi in zip(xs, ys)]
    return {
        "n": n,
        "partial_pearson": _corr(zs, resid),
        "base_epa_pearson": _corr(xs, ys),
        "unit_pearson": _corr(zs, ys),
        "epa_mae": _mae(epa_pairs),
        "unit_mae": _mae(unit_pairs),
        "conditioned_on": EPA_ID[side],
        "target": "next_def_epa" if side == "def" else "next_off_epa",
    }


def week_stability(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    fit: MethodFit,
    method: str,
    as_of_weeks: Sequence[int],
) -> Dict[str, Any]:
    books: Dict[int, Dict[str, float]] = {}
    for w in as_of_weeks:
        books[w] = {}
        for team in {g.team for g in games if g.week < w}:
            val = predict_method(
                games, sport=sport, side=side, team=team, as_of_week=w, method=method, fit=fit
            )
            if val is not None:
                books[w][team] = val
    pairs = []
    weeks = sorted(as_of_weeks)
    for a, b in zip(weeks, weeks[1:]):
        teams = [t for t in books[a] if t in books[b]]
        xs = [books[a][t] for t in teams]
        ys = [books[b][t] for t in teams]
        pairs.append({"from": a, "to": b, "n": len(teams), "pearson": _corr(xs, ys) if len(teams) >= 3 else None})
    late = [p["pearson"] for p in pairs if p["from"] >= 8 and p["pearson"] is not None]
    return {"pairs": pairs, "late_mean_pearson": (sum(late) / len(late)) if late else None}


def outlier_sensitivity(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    fit: MethodFit,
    method: str,
    as_of_week: int,
    k_teams: int = 8,
) -> List[Dict[str, Any]]:
    """Drop each team's most extreme EPA game; report rating/rank movement."""
    teams = sorted({g.team for g in games if g.week < as_of_week})
    base = {}
    for team in teams:
        val = predict_method(
            games, sport=sport, side=side, team=team, as_of_week=as_of_week, method=method, fit=fit
        )
        if val is not None:
            base[team] = val
    reverse = side == "off"
    ranked = {t: i + 1 for i, t in enumerate(sorted(base, key=lambda t: base[t], reverse=reverse))}
    out = []
    for team, val in base.items():
        mine = [g for g in games if g.team == team and g.week < as_of_week]
        if len(mine) < 3:
            continue
        cid = EPA_ID[side]
        extreme = max(mine, key=lambda g: abs((game_metric(g, cid) or 0.0) - (val or 0.0)))
        dropped = [g for g in games if not (g.team == team and g.game_id == extreme.game_id)]
        new = predict_method(
            dropped, sport=sport, side=side, team=team, as_of_week=as_of_week, method=method, fit=fit
        )
        if new is None:
            continue
        out.append(
            {
                "team": team,
                "base": val,
                "dropped_game": extreme.game_id,
                "dropped_week": extreme.week,
                "after": new,
                "delta": new - val,
                "base_rank": ranked.get(team),
            }
        )
    out.sort(key=lambda r: -abs(r["delta"]))
    return out[:k_teams]


def future_week_changes_unit(
    games: Sequence[TeamGame],
    *,
    sport: str,
    side: str,
    team: str,
    as_of_week: int,
    method: str,
    fit: MethodFit,
    future_game: TeamGame,
) -> bool:
    before = predict_method(
        games, sport=sport, side=side, team=team, as_of_week=as_of_week, method=method, fit=fit
    )
    after = predict_method(
        list(games) + [future_game],
        sport=sport,
        side=side,
        team=team,
        as_of_week=as_of_week,
        method=method,
        fit=fit,
    )
    return before != after


def grade_unit(row: Dict[str, Any], *, persist: Optional[float], incremental: Dict[str, Any]) -> Dict[str, Any]:
    winner = row["winner"]
    earned = row["complexity_earned"]
    conf = row["candidates"][winner]["confirmation"]
    mae = conf.get("mae")
    pearson = conf.get("pearson")
    evidence = [
        f"winner={winner}",
        f"complexity_earned={earned}",
        f"confirmation MAE={mae} pearson={pearson} n={conf.get('n')}",
        f"strongest_constituent={row['strongest_constituent']}",
        f"earned_partial={row.get('earned_partial_features')}",
        f"finishing_earned={row.get('finishing_earned')}",
        f"early→late persist={persist}",
        f"incremental-on-EPA partial r={incremental.get('partial_pearson')}",
    ]
    if earned and persist is not None and persist >= 0.35 and pearson is not None and pearson >= 0.20:
        grade = "PASS"
        rec = (
            f"{winner} beat trailing EPA on frozen confirmation. "
            "Eligible as a KE unit rating. Not Team Strength."
        )
        eligible = True
    elif not earned:
        grade = "PARTIAL"
        rec = (
            "No composite earned inclusion over the strongest constituent. "
            f"Publish {winner} as the honest v1 unit rating (shrunken/raw EPA). "
            "Do not invent weights."
        )
        eligible = True
    else:
        grade = "PARTIAL"
        rec = f"{winner} earned a confirmation MAE edge but persistence/OOS is modest. Research only."
        eligible = True
    return {
        "id": UNIT_IDS[row["side"]],
        "side": row["side"],
        "grade": grade,
        "phase2b_eligible": eligible,
        "winner": winner,
        "complexity_earned": earned,
        "evidence": evidence,
        "recommendation": rec,
        "production_promote": False,
    }


def representative_profiles(
    games: Sequence[TeamGame],
    *,
    sport: str,
    season: int,
    as_of_week: int,
    fits: Dict[str, MethodFit],
    methods: Dict[str, str],
    teams: Sequence[str],
) -> List[Dict[str, Any]]:
    book = snapshot_book(
        games, sport=sport, season=season, as_of_week=as_of_week, fits=fits, methods=methods
    )
    by_team = {r["team"]: r for r in book}
    out = []
    for team in teams:
        row = by_team.get(team)
        if not row:
            continue
        out.append(
            {
                "team": team,
                "off": row["components"]["ke.off_unit"],
                "def": row["components"]["ke.def_unit"],
                "team_strength": row["components"]["ke.team_strength"],
            }
        )
    return out


def run_phase2a(
    games: Sequence[TeamGame],
    *,
    sport: str,
    season: int,
    as_of_week: int,
    example_teams: Sequence[str],
    selection_weeks: Tuple[int, int],
    confirmation_weeks: Tuple[int, int],
    full_weeks: Tuple[int, int],
    early_through: int,
    late_from: int,
) -> Dict[str, Any]:
    clear_z_cache()
    fits = {
        "off": fit_selection(games, sport=sport, side="off", selection_weeks=selection_weeks),
        "def": fit_selection(games, sport=sport, side="def", selection_weeks=selection_weeks),
    }
    evals = {
        side: evaluate_methods(
            games,
            sport=sport,
            side=side,
            fit=fits[side],
            selection_weeks=selection_weeks,
            confirmation_weeks=confirmation_weeks,
            full_weeks=full_weeks,
        )
        for side in ("off", "def")
    }
    methods = {"off": evals["off"]["winner"], "def": evals["def"]["winner"]}
    persist = {}
    incr = {}
    stability = {}
    outliers = {}
    for side in ("off", "def"):
        persist[side] = early_late_persistence(
            games, EPA_ID[side], early_through=early_through, late_from=late_from
        )
        incr[side] = incremental_over_epa(
            games,
            sport=sport,
            side=side,
            fit=fits[side],
            method=methods[side],
            week_min=confirmation_weeks[0],
            week_max=confirmation_weeks[1],
        )
        max_w = max((g.week for g in games), default=as_of_week)
        weeks = list(range(3, min(as_of_week, max_w + 1) + 1))
        stability[side] = week_stability(
            games,
            sport=sport,
            side=side,
            fit=fits[side],
            method=methods[side],
            as_of_weeks=weeks,
        )
        outliers[side] = outlier_sensitivity(
            games,
            sport=sport,
            side=side,
            fit=fits[side],
            method=methods[side],
            as_of_week=as_of_week,
        )

    book = snapshot_book(
        games, sport=sport, season=season, as_of_week=as_of_week, fits=fits, methods=methods
    )
    # Ranking sanity on unit values (n_games via snapshot notes).
    fake_snaps = []
    for row in book:
        off = row["components"]["ke.off_unit"]
        deff = row["components"]["ke.def_unit"]
        fake_snaps.append(
            {
                "team": row["team"],
                "off_epa_raw": off.get("value"),
                "def_epa_raw": deff.get("value"),
                "n_games": (off.get("notes") or {}).get("n_games") or 0,
                "n_off_plays": (off.get("notes") or {}).get("n_plays") or 0,
            }
        )
    grades = {
        "off": grade_unit(evals["off"], persist=persist["off"].get("pearson"), incremental=incr["off"]),
        "def": grade_unit(evals["def"], persist=persist["def"].get("pearson"), incremental=incr["def"]),
    }
    leak = None
    if games:
        future = deepcopy(games[0])
        future.week = as_of_week
        future.game_id = "LEAK_FUTURE"
        future.off_epa_sum = 50.0
        future.off_epa_n = 80
        leak = {
            side: future_week_changes_unit(
                games,
                sport=sport,
                side=side,
                team=future.team,
                as_of_week=as_of_week,
                method=methods[side],
                fit=fits[side],
                future_game=future,
            )
            for side in ("off", "def")
        }

    names = [t for t in example_teams if any(r["team"] == t for r in book)]
    if not names:
        ranked = ranking_sanity(fake_snaps, k=4)
        names = [r["team"] for r in ranked["best_offense"][:3]] + [r["team"] for r in ranked["best_defense"][:2]]

    return {
        "pipeline": "ke-football-v1-unit-ratings-phase2a",
        "production_promote": False,
        "taxonomy": ["RAW", "DERIVED", "ADJUSTED", "MODELED"],
        "sport": sport,
        "season": season,
        "as_of_week": as_of_week,
        "feature_policy": feature_policy(sport=sport),
        "opp_adj_reopened": False,
        "opp_adj_result": "NO_ADJUSTMENT_WINNER",
        "fits": {
            side: {
                "shrink_k": fits[side].shrink_k,
                "earned_partial": fits[side].earned_partial,
                "ridge_lam": fits[side].ridge_lam,
                "ridge_beta": fits[side].ridge_beta,
                "ridge_cids": fits[side].ridge_cids,
                "pca_w": fits[side].pca_w,
                "notes": fits[side].notes,
            }
            for side in ("off", "def")
        },
        "methods": methods,
        "bakeoff": evals,
        "persistence": persist,
        "incremental_over_epa": incr,
        "stability": stability,
        "outlier_sensitivity": outliers,
        "ranking_sanity": ranking_sanity(fake_snaps, k=8, min_games=4),
        "grades": grades,
        "examples": representative_profiles(
            games,
            sport=sport,
            season=season,
            as_of_week=as_of_week,
            fits=fits,
            methods=methods,
            teams=names,
        ),
        "n_snapshots": len(book),
        "leakage_live": {"future_week_changes_unit": leak, "expected": False},
        "hard_stops": {
            "team_strength": False,
            "off_def_st_overall_weights": False,
            "matchup": False,
            "scoring": False,
            "market": False,
            "ui": False,
            "boards": False,
            "opp_adj_reopen": False,
        },
        "stop": (
            "STOP before Team Strength, overall weights, matchup, scoring, "
            "market, ATS, UI, boards, production promote."
        ),
    }
