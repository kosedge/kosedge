"""Exact CLEAR 86257 risk1 settlement / ATS / ROI / line-CLV.

Isolated copies of already-correct repo arithmetic. CERT=0.
Sources (do not edit those shared files from B):
  - scripts/desk-record/rebuild_summary.py :: american_profit / ROI
  - docs/DESK_ATS_ROI_RECORD.md settlement table
  - services/model-service/src/services/book_ledger/grade.py :: grade_spread_result
  - services/model-service/src/services/nfl_clv_semantics.py :: *clv

No historical join. No invented flat −110. Missing inputs refuse.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional, Sequence

from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse

RISK1_U = 1.0
PUSH_EPS = 1e-12
MIN_ABS_JUICE = 100
RESULTS = frozenset({"win", "loss", "push", "void"})


def _require_finite(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OwnedMarketRefuse(f"{name} is not a number (bool-as-number refused)")
    number = float(value)
    if not math.isfinite(number):
        raise OwnedMarketRefuse(f"{name} is not finite")
    return number


def _require_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OwnedMarketRefuse(f"{name} is not an int (bool-as-number refused)")
    return int(value)


def american_profit(*, risk1_u: float, juice: int, won: bool) -> float:
    """Desk-record: L = −stake; W = stake × American win payout. No −110 invent."""
    stake = _require_finite(risk1_u, name="risk1_u")
    if abs(stake - RISK1_U) > 1e-12:
        raise OwnedMarketRefuse(f"risk1_u must be exactly {RISK1_U}")
    if not won:
        return -stake
    if juice == 0:
        raise OwnedMarketRefuse("juice must not be 0")
    if juice < 0:
        return stake * (100.0 / abs(juice))
    return stake * (juice / 100.0)


def require_stamped_juice(juice: Any, *, name: str = "juice") -> int:
    if juice is None or juice == "":
        raise OwnedMarketRefuse(f"{name} missing — DATA_GAP; do not invent flat -110")
    value = _require_int(juice, name=name)
    if abs(value) < MIN_ABS_JUICE:
        raise OwnedMarketRefuse(f"{name} abs < {MIN_ABS_JUICE} — DATA_GAP; do not invent")
    return value


def grade_spread_ats(*, side: str, line: Any, home_score: Any, away_score: Any) -> str:
    """Official ATS vs posted side line. Push on exact cover. grade.py identity."""
    if line is None or line == "":
        raise OwnedMarketRefuse("spread line required to grade")
    margin = _require_finite(home_score, name="home_score") - _require_finite(
        away_score, name="away_score"
    )
    posted = _require_finite(line, name="line")
    token = str(side or "").strip().lower()
    if token == "home":
        cover = margin + posted
    elif token == "away":
        cover = (-margin) + posted
    else:
        raise OwnedMarketRefuse(f"unsupported spread side: {side!r}")
    if abs(cover) < 1e-9:
        return "push"
    return "win" if cover > 0 else "loss"


def grade_total_ats(*, side: str, line: Any, home_score: Any, away_score: Any) -> str:
    if line is None or line == "":
        raise OwnedMarketRefuse("total line required to grade")
    points = _require_finite(home_score, name="home_score") + _require_finite(
        away_score, name="away_score"
    )
    posted = _require_finite(line, name="line")
    token = str(side or "").strip().lower()
    if token == "over":
        cover = points - posted
    elif token == "under":
        cover = posted - points
    else:
        raise OwnedMarketRefuse(f"unsupported total side: {side!r}")
    if abs(cover) < 1e-9:
        return "push"
    return "win" if cover > 0 else "loss"


def grade_ml_result(*, side: str, home_score: Any, away_score: Any) -> str:
    home = _require_finite(home_score, name="home_score")
    away = _require_finite(away_score, name="away_score")
    token = str(side or "").strip().lower()
    if home == away:
        return "push"
    home_won = home > away
    if token == "home":
        return "win" if home_won else "loss"
    if token == "away":
        return "win" if not home_won else "loss"
    raise OwnedMarketRefuse(f"unsupported ml side: {side!r}")


def american_implied_prob(price: int) -> float:
    if price > 0:
        return 100.0 / (price + 100.0)
    return abs(price) / (abs(price) + 100.0)


def moneyline_clv(*, open_price: int, close_price: int) -> float:
    return american_implied_prob(close_price) - american_implied_prob(open_price)


def total_clv(*, side: str, open_total: float, close_total: float) -> float:
    token = side.strip().lower()
    if token == "over":
        return close_total - open_total
    if token == "under":
        return open_total - close_total
    raise OwnedMarketRefuse(f"total side must be over or under, got {side!r}")


def spread_clv(*, side: str, open_spread_home: float, close_spread_home: float) -> float:
    token = side.strip().lower()
    if token == "home":
        return open_spread_home - close_spread_home
    if token == "away":
        return close_spread_home - open_spread_home
    raise OwnedMarketRefuse(f"spread side must be home or away, got {side!r}")


def line_clv(
    *,
    market: str,
    side: str,
    open_line: Any,
    close_line: Any,
    open_price: Any,
    close_price: Any,
) -> float:
    token = str(market).strip().lower()
    if token == "spread":
        if open_line is None or close_line is None:
            raise OwnedMarketRefuse("spread line-CLV requires open_line and close_line")
        side_tok = str(side).strip().lower()
        if side_tok == "home":
            open_home = _require_finite(open_line, name="open_line")
            close_home = _require_finite(close_line, name="close_line")
        elif side_tok == "away":
            open_home = -_require_finite(open_line, name="open_line")
            close_home = -_require_finite(close_line, name="close_line")
        else:
            raise OwnedMarketRefuse(f"unsupported spread side for CLV: {side!r}")
        return spread_clv(
            side=side_tok, open_spread_home=open_home, close_spread_home=close_home
        )
    if token == "total":
        if open_line is None or close_line is None:
            raise OwnedMarketRefuse("total line-CLV requires open_line and close_line")
        return total_clv(
            side=side,
            open_total=_require_finite(open_line, name="open_line"),
            close_total=_require_finite(close_line, name="close_line"),
        )
    if token == "ml":
        if open_price is None or close_price is None:
            raise OwnedMarketRefuse("ml line-CLV requires open_price and close_price")
        return moneyline_clv(
            open_price=require_stamped_juice(open_price, name="open_price"),
            close_price=require_stamped_juice(close_price, name="close_price"),
        )
    raise OwnedMarketRefuse(f"unsupported market for line-CLV: {market!r}")


def settle_ticket(ticket: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed risk1 settlement. Fictional typed inputs only."""
    status = str(ticket.get("settlement_status") or "final").strip().lower()
    if status == "void":
        return {
            "ats_result": "void",
            "profit_u": 0.0,
            "risked_u": 0.0,
            "roi_eligible": False,
            "juice_status": "excluded_void",
        }
    market = str(ticket.get("market") or "").strip().lower()
    side = str(ticket.get("side") or "").strip().lower()
    home = ticket.get("home_score")
    away = ticket.get("away_score")
    if home is None or away is None:
        raise OwnedMarketRefuse("home_score/away_score missing — cannot settle")
    if market == "spread":
        ats = grade_spread_ats(
            side=side, line=ticket.get("line"), home_score=home, away_score=away
        )
    elif market == "total":
        ats = grade_total_ats(
            side=side, line=ticket.get("line"), home_score=home, away_score=away
        )
    elif market == "ml":
        ats = grade_ml_result(side=side, home_score=home, away_score=away)
    else:
        raise OwnedMarketRefuse(f"unsupported market: {market!r}")

    clv = line_clv(
        market=market,
        side=side,
        open_line=ticket.get("open_line"),
        close_line=ticket.get("close_line"),
        open_price=ticket.get("open_price"),
        close_price=ticket.get("close_price"),
    )

    if ats == "push":
        return {
            "ats_result": "push",
            "profit_u": 0.0,
            "risked_u": 0.0,
            "roi_eligible": False,
            "line_clv": clv,
            "juice_status": "excluded_push",
        }

    juice = ticket.get("juice")
    juice_status = str(ticket.get("juice_status") or "").strip()
    if juice is None or juice_status == "DATA_GAP":
        raise OwnedMarketRefuse(
            "ROI juice missing — DATA_GAP; ATS known but ROI refused; no flat -110"
        )
    stamped = require_stamped_juice(juice)
    profit = american_profit(risk1_u=RISK1_U, juice=stamped, won=(ats == "win"))
    return {
        "ats_result": ats,
        "profit_u": profit,
        "risked_u": RISK1_U,
        "roi_eligible": True,
        "line_clv": clv,
        "juice_status": "stamped",
        "juice": stamped,
    }


def portfolio_roi(settled: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """W/L stamped-juice only. Push/void excluded from risked. No −110 invent."""
    profit_sum = 0.0
    risked = 0.0
    n_w = n_l = n_p = n_v = 0
    n_gap = 0
    for row in settled:
        ats = str(row.get("ats_result") or "")
        if ats == "void":
            n_v += 1
            continue
        if ats == "push":
            n_p += 1
            continue
        if ats not in {"win", "loss"}:
            raise OwnedMarketRefuse(f"unsettled ats_result {ats!r}")
        if not row.get("roi_eligible"):
            n_gap += 1
            continue
        profit_sum += _require_finite(row.get("profit_u"), name="profit_u")
        risked += _require_finite(row.get("risked_u"), name="risked_u")
        if ats == "win":
            n_w += 1
        else:
            n_l += 1
    if risked > 0:
        return {
            "status": "ok",
            "profit_u": profit_sum,
            "risked_u": risked,
            "roi": profit_sum / risked,
            "ats": {"w": n_w, "l": n_l, "p": n_p, "v": n_v},
            "n_data_gap": n_gap,
        }
    if n_gap > 0:
        raise OwnedMarketRefuse(
            "settled W/L lack stamped juice — ROI DATA_GAP; no flat -110 invent"
        )
    return {
        "status": "empty",
        "profit_u": 0.0,
        "risked_u": 0.0,
        "roi": None,
        "ats": {"w": n_w, "l": n_l, "p": n_p, "v": n_v},
        "n_data_gap": 0,
    }
