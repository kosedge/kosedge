"""Unit math + market grading for the pick ledger."""

from __future__ import annotations

from typing import Any, Optional, Tuple

PLAY_UNITS = 1.0
LEAN_UNITS = 0.0
DEFAULT_ODDS_AMERICAN = -110

VALID_TAGS = frozenset({"PLAY", "LEAN"})
VALID_GRADES = frozenset({"pending", "win", "loss", "push", "void"})
VALID_MARKETS = frozenset({"spread", "total", "moneyline", "prop"})


def units_for_tag(tag: str, *, explicit_units: Optional[float] = None) -> float:
    t = str(tag or "").strip().upper()
    if t == "LEAN":
        return LEAN_UNITS
    if t == "PLAY":
        if explicit_units is not None:
            return max(0.0, float(explicit_units))
        return PLAY_UNITS
    raise ValueError(f"tag must be PLAY or LEAN, got {tag!r}")


def american_odds_profit(stake: float, odds_american: int = DEFAULT_ODDS_AMERICAN) -> float:
    """Profit (not including stake return) on a winning bet."""
    stake_f = float(stake)
    if stake_f <= 0:
        return 0.0
    odds = int(odds_american)
    if odds == 0:
        odds = DEFAULT_ODDS_AMERICAN
    if odds < 0:
        return round(stake_f * (100.0 / abs(odds)), 6)
    return round(stake_f * (odds / 100.0), 6)


def grade_to_units(
    *,
    tag: str,
    grade: str,
    odds_american: int = DEFAULT_ODDS_AMERICAN,
    units: Optional[float] = None,
) -> dict[str, float]:
    """Map grade → units_risked / won / lost / pnl.

    LEAN always zeros unit fields even on win/loss (hit-rate only).
    """
    t = str(tag).strip().upper()
    g = str(grade).strip().lower()
    risked = float(units) if units is not None else units_for_tag(t)
    if t == "LEAN":
        risked = 0.0

    out = {
        "units_risked": round(risked, 6) if g not in {"void", "pending"} else (
            round(risked, 6) if g == "pending" else 0.0
        ),
        "units_won": 0.0,
        "units_lost": 0.0,
        "units_pnl": 0.0,
    }
    if t == "LEAN" or risked <= 0 or g in {"pending", "push", "void"}:
        if g == "void":
            out["units_risked"] = 0.0
        return out

    if g == "win":
        profit = american_odds_profit(risked, odds_american)
        out["units_won"] = round(profit, 6)
        out["units_pnl"] = round(profit, 6)
    elif g == "loss":
        out["units_lost"] = round(risked, 6)
        out["units_pnl"] = round(-risked, 6)
    return out


def compute_clv(
    *,
    market_type: str,
    side: str,
    line_at_publish: Optional[float],
    line_at_close: Optional[float],
) -> Optional[float]:
    """Closing-line value for the bet side (positive = beat the close)."""
    if line_at_publish is None or line_at_close is None:
        return None
    pub = float(line_at_publish)
    close = float(line_at_close)
    mkt = str(market_type).strip().lower()
    s = str(side).strip().lower()

    if mkt == "total":
        if s in {"over", "o"}:
            return round(close - pub, 4)
        if s in {"under", "u"}:
            return round(pub - close, 4)
        return None

    # spread / moneyline / prop: home-relative line convention when numeric
    if s in {"home", "h"}:
        return round(pub - close, 4)
    if s in {"away", "a"}:
        return round(close - pub, 4)
    return round(pub - close, 4)


def _grade_cover(actual_margin: float, line: float) -> str:
    cover = float(actual_margin) + float(line)
    if abs(cover) < 1e-9:
        return "push"
    return "win" if cover > 0 else "loss"


def grade_market(
    *,
    market_type: str,
    side: str,
    line: Optional[float],
    home_score: int,
    away_score: int,
    odds_american: int = DEFAULT_ODDS_AMERICAN,
) -> Tuple[str, dict[str, Any]]:
    """Grade a single pick from final scores.

    Spread lines are **home-relative** (negative = home favored), matching
    proof_layer / CFB project-game.
    """
    hs = int(home_score)
    aws = int(away_score)
    margin = float(hs - aws)
    total = float(hs + aws)
    mkt = str(market_type).strip().lower()
    s = str(side).strip().lower()
    detail: dict[str, Any] = {
        "home_score": hs,
        "away_score": aws,
        "margin": margin,
        "total": total,
        "odds_american": int(odds_american),
    }

    if mkt == "spread":
        if line is None:
            return "void", {**detail, "reason": "missing_line"}
        line_f = float(line)
        detail["line"] = line_f
        home_cover = _grade_cover(margin, line_f)
        if s in {"home", "h"}:
            grade = home_cover
        elif s in {"away", "a"}:
            if home_cover == "push":
                grade = "push"
            else:
                grade = "win" if home_cover == "loss" else "loss"
        else:
            return "void", {**detail, "reason": f"unknown_side:{side}"}
        return grade, detail

    if mkt == "total":
        if line is None:
            return "void", {**detail, "reason": "missing_line"}
        line_f = float(line)
        detail["line"] = line_f
        diff = total - line_f
        if abs(diff) < 1e-9:
            return "push", detail
        went_over = diff > 0
        if s in {"over", "o"}:
            return ("win" if went_over else "loss"), detail
        if s in {"under", "u"}:
            return ("win" if not went_over else "loss"), detail
        return "void", {**detail, "reason": f"unknown_side:{side}"}

    if mkt == "moneyline":
        if hs == aws:
            return "push", detail
        home_won = hs > aws
        if s in {"home", "h"}:
            return ("win" if home_won else "loss"), detail
        if s in {"away", "a"}:
            return ("win" if not home_won else "loss"), detail
        return "void", {**detail, "reason": f"unknown_side:{side}"}

    # prop: require explicit grade upstream; scores alone are insufficient
    return "void", {**detail, "reason": "prop_requires_explicit_grade"}
