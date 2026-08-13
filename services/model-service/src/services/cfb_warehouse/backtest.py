"""Skeleton CFB backtest harness — columns ready, model fair optional.

Does not train a rating model. Placeholder / pass-through fairs are allowed.
Future preseason prior and efficiency features must register ``available_at``.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence

from src.services.cfb_warehouse.leakage import assert_available_before_kickoff


def _f(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def grade_row(
    game: Mapping[str, Any],
    *,
    model_spread_home: Optional[float] = None,
    model_total: Optional[float] = None,
    model_available_at: Any = None,
) -> dict[str, Any]:
    """Grade one historical game vs close/open + result.

    ``model_spread_home`` uses the same convention as project-game / Odds API:
    negative = home favored.
    """
    kickoff = game.get("kickoff") or game.get("game_date")
    if model_available_at is not None:
        assert_available_before_kickoff(
            available_at=model_available_at,
            kickoff=kickoff,
            game_date=game.get("game_date"),
            feature_week=None,
            game_week=game.get("week"),
            feature_name="model_fair",
        )

    close_spread = _f(game.get("close_spread_home"))
    close_total = _f(game.get("close_total"))
    open_spread = _f(game.get("open_spread_home"))
    home_score = _f(game.get("home_score"))
    away_score = _f(game.get("away_score"))
    margin = None
    if home_score is not None and away_score is not None:
        margin = home_score - away_score

    spread_error = None
    if model_spread_home is not None and close_spread is not None:
        spread_error = model_spread_home - close_spread

    ats_flag = None
    if model_spread_home is not None and margin is not None:
        # Model home side covers if actual margin beats model spread
        # (spread negative = home favored, so home covers if margin + spread > 0
        #  wait: close_spread_home negative = home favored. ATS vs *close*:
        #  home covers close if margin + close_spread > 0.
        #  Model ATS: did the model pick the covering side vs close?
        if close_spread is not None and abs(model_spread_home - close_spread) >= 0.5:
            model_home = model_spread_home < close_spread  # more home-favored than close
            home_covered = (margin + close_spread) > 0
            ats_flag = home_covered if model_home else (not home_covered and (margin + close_spread) != 0)
            if (margin + close_spread) == 0:
                ats_flag = None  # push

    clv_stub = None
    if model_spread_home is not None and open_spread is not None and close_spread is not None:
        # Positive CLV stub: close moved toward the model relative to open.
        clv_stub = abs(open_spread - close_spread)  # magnitude only until signed CLV lands

    return {
        "game_id": game.get("game_id"),
        "season": game.get("season"),
        "week": game.get("week"),
        "home_team_id": game.get("home_team_id"),
        "away_team_id": game.get("away_team_id"),
        "home_score": home_score,
        "away_score": away_score,
        "margin": margin,
        "open_spread_home": open_spread,
        "close_spread_home": close_spread,
        "close_total": close_total,
        "model_spread_home": model_spread_home,
        "model_total": model_total,
        "spread_error": spread_error,
        "ats_flag": ats_flag,
        "clv_stub": clv_stub,
        "su_home": (margin > 0) if margin is not None else None,
        "model_fair_present": model_spread_home is not None,
    }


def run_harness(
    games: Iterable[Mapping[str, Any]],
    *,
    fairs: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Grade a list of warehouse games. Missing fairs still emit result columns."""
    fairs = fairs or {}
    out: list[dict[str, Any]] = []
    for game in games:
        gid = str(game.get("game_id") or "")
        fair = fairs.get(gid) or {}
        out.append(
            grade_row(
                game,
                model_spread_home=_f(fair.get("model_spread_home")),
                model_total=_f(fair.get("model_total")),
                model_available_at=fair.get("available_at"),
            )
        )
    return out


def join_game_close_result(
    games: Sequence[Mapping[str, Any]],
    closes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Inner join games → closing_lines on game_id (sample / smoke helper)."""
    by_id = {str(c.get("game_id")): c for c in closes}
    joined: list[dict[str, Any]] = []
    for g in games:
        c = by_id.get(str(g.get("game_id")))
        if not c:
            continue
        row = dict(g)
        row.update(
            {
                "close_spread_home": c.get("close_spread_home"),
                "close_total": c.get("close_total"),
                "open_spread_home": c.get("open_spread_home"),
                "open_total": c.get("open_total"),
                "close_ml_home": c.get("close_ml_home"),
                "book": c.get("book"),
            }
        )
        joined.append(row)
    return joined
