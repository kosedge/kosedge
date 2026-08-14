"""CFB market diagnostic — model vs open/close. Report only.

Does not blend market into the fair line. Does not emit KEI / PLAY / LEAN.
``used_in_spread`` stays false. No training on this output.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.cfb_season_engine.conferences import conference_for
from src.services.cfb_warehouse.walkforward import (
    THIN_N,
    _f,
    _slice_metrics,
    signed_clv,
    wilson_interval,
)

USED_IN_SPREAD = False
DIAGNOSTIC_ID = "cfb-market-diagnostic-v0.14.1-20260814"
MOVE_EPS = 0.25
P4 = frozenset({"SEC", "Big Ten", "ACC", "Big 12"})
G5 = frozenset(
    {
        "AAC",
        "American",
        "American Athletic",
        "Sun Belt",
        "MAC",
        "CUSA",
        "Conference USA",
        "Mountain West",
        "MW",
        "MWC",
    }
)


def diagnostic_week_band(week: Any) -> str:
    w = int(week or 0)
    if w <= 1:
        return "w0_1"
    if w <= 4:
        return "w2_4"
    if w <= 9:
        return "w5_9"
    return "w10_plus"


def close_abs_bucket(close: Any) -> Optional[str]:
    val = _f(close)
    if val is None:
        return None
    mag = abs(val)
    if mag < 3.0:
        return "pickem_lt3"
    if mag < 7.0:
        return "mid_3_7"
    if mag < 14.0:
        return "large_7_14"
    return "blowout_14plus"


def conference_tier(home: str, away: str) -> str:
    hc = conference_for(home)
    ac = conference_for(away)
    if hc in P4 and ac in P4:
        return "p4_p4"
    if hc in G5 and ac in G5:
        return "g5_g5"
    if (hc in P4 and ac in G5) or (hc in G5 and ac in P4):
        return "p4_g5"
    if hc == "Independent" or ac == "Independent":
        return "indep_mix"
    return "other"


def clv_side_hit(
    model: Any, open_sp: Any, close: Any, *, move_eps: float = MOVE_EPS
) -> Optional[bool]:
    """True if the model sat on the side the market moved open→close.

    Open==close (or |move| < eps) → None (no information). Not lock CLV. Not PnL.
    """
    m = _f(model)
    o = _f(open_sp)
    c = _f(close)
    if m is None or o is None or c is None:
        return None
    move = c - o
    if abs(move) < float(move_eps):
        return None
    model_home_of_open = m < o
    market_moved_home = c < o
    return model_home_of_open == market_moved_home


def annotate_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    model = _f(row.get("model_spread_home"))
    open_sp = _f(row.get("open_spread_home"))
    close = _f(row.get("close_spread_home"))
    out["diag_week_band"] = diagnostic_week_band(row.get("week"))
    out["close_abs_bucket"] = close_abs_bucket(close)
    out["conference_tier"] = conference_tier(
        str(row.get("home_team_id") or ""),
        str(row.get("away_team_id") or ""),
    )
    out["error_vs_close"] = (model - close) if model is not None and close is not None else None
    out["error_vs_open"] = (
        (model - open_sp) if model is not None and open_sp is not None else None
    )
    out["clv_side_hit"] = clv_side_hit(model, open_sp, close)
    if model is not None and open_sp is not None and close is not None:
        out["clv_stub"] = signed_clv(model, open_sp, close)
    out["used_in_spread"] = USED_IN_SPREAD
    out["kei"] = False
    return out


def _error_stats(values: Sequence[float]) -> Dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "mae": None, "median_ae": None}
    srt = sorted(abs(v) for v in values)
    return {
        "n": len(values),
        "mean": round(sum(values) / len(values), 3),
        "mae": round(sum(abs(v) for v in values) / len(values), 3),
        "median_ae": round(srt[len(srt) // 2], 3),
    }


def slice_report(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Metrics vs close and vs open. Thin samples flagged. No KEI."""
    annotated = [annotate_row(r) for r in rows]
    fair_close = [
        r
        for r in annotated
        if r.get("model_fair_present") and r.get("close_spread_home") is not None
    ]
    vs_close = _error_stats(
        [e for e in (_f(r.get("error_vs_close")) for r in fair_close) if e is not None]
    )
    vs_open = _error_stats(
        [
            e
            for e in (_f(r.get("error_vs_open")) for r in annotated if r.get("model_fair_present"))
            if e is not None
        ]
    )
    base = _slice_metrics(rows)
    side = [r.get("clv_side_hit") for r in annotated if r.get("clv_side_hit") is not None]
    n_side = len(side)
    hits = sum(1 for x in side if x)
    ci = wilson_interval(hits, n_side) if n_side else None
    flag = "thin" if vs_close["n"] < THIN_N else base.get("sample_flag")
    return {
        **base,
        "diagnostic_id": DIAGNOSTIC_ID,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "vs_close": vs_close,
        "vs_open": vs_open,
        "clv_side_n": n_side,
        "clv_side_hits": hits,
        "clv_side_rate": round(hits / n_side, 4) if n_side else None,
        "clv_side_ci95": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
        "sample_flag": flag,
        "sigma_slice": "skipped_not_on_hist_rows",
    }


def group_slices(
    rows: Sequence[Mapping[str, Any]],
    key_fn,
) -> Dict[str, Dict[str, Any]]:
    buckets: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(key_fn(annotate_row(row)))].append(row)
    return {k: slice_report(v) for k, v in sorted(buckets.items())}


def diagnose(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    annotated = [annotate_row(r) for r in rows]
    return {
        "diagnostic_id": DIAGNOSTIC_ID,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "note": (
            "Research only. Model vs owned open/close. Close = last lake snap "
            "strictly before kickoff (not lock). No blend. No KEI."
        ),
        "overall": slice_report(rows),
        "by_diag_week_band": group_slices(rows, lambda r: r["diag_week_band"]),
        "by_close_abs_bucket": group_slices(
            [r for r in annotated if r.get("close_abs_bucket")],
            lambda r: r["close_abs_bucket"],
        ),
        "by_favorite_home": group_slices(
            [r for r in annotated if r.get("favorite_home") is not None],
            lambda r: "home_fav" if r.get("favorite_home") else "home_dog",
        ),
        "by_conference_tier": group_slices(rows, lambda r: r["conference_tier"]),
        "sigma_slice": "skipped — hist walk-forward rows do not store model σ",
    }


def documentation() -> Dict[str, Any]:
    return {
        "id": DIAGNOSTIC_ID,
        "used_in_spread": USED_IN_SPREAD,
        "kei": False,
        "blend": False,
        "ops": "data/ops/cfb-market-diagnostic-20260814.md",
        "script": "scripts/cfb/run_market_diagnostic.py",
        "read_only": True,
    }
