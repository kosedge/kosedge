"""Read-side metrics for The Book. Not a second SoT."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def _f(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def clv_distribution(
    rows: Sequence[Dict[str, Any]],
    *,
    book_type: Optional[str] = None,
) -> Dict[str, Any]:
    vals: List[float] = []
    for r in rows:
        if book_type and str(r.get("type")).lower() != book_type.lower():
            continue
        clv = _f(r.get("clv"))
        if clv is None:
            continue
        vals.append(clv)
    n = len(vals)
    return {
        "type": book_type,
        "n": n,
        "avg_clv": (sum(vals) / n) if n else None,
        "positive_n": sum(1 for v in vals if v > 0),
        "negative_n": sum(1 for v in vals if v < 0),
        "zero_n": sum(1 for v in vals if v == 0),
        "values": vals,
    }


def unit_roi(
    rows: Sequence[Dict[str, Any]],
    *,
    include_paper: bool = False,
) -> Dict[str, Any]:
    """Unit ROI for plays only. Default booked-only; paper toggle separate."""
    stake_ok = {"booked", "paper"} if include_paper else {"booked"}
    selected = []
    for r in rows:
        if str(r.get("type")).lower() != "play":
            continue
        if str(r.get("stake_flag")).lower() not in stake_ok:
            continue
        if str(r.get("result")).lower() == "pending":
            continue
        selected.append(r)
    units = sum(float(r.get("units") or 0) for r in selected)
    pnl = sum(float(r.get("pnl_units") or 0) for r in selected)
    return {
        "include_paper": include_paper,
        "n_plays": len(selected),
        "units": units,
        "pnl_units": pnl,
        "roi": (pnl / units) if units else None,
        "note": "leans excluded (units=0); paper never mixed unless include_paper",
    }


def lean_hit_rate(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    leans = [r for r in rows if str(r.get("type")).lower() == "lean"]
    decided = [
        r
        for r in leans
        if str(r.get("result")).lower() in {"win", "loss", "push"}
    ]
    wins = sum(1 for r in decided if str(r.get("result")).lower() == "win")
    losses = sum(1 for r in decided if str(r.get("result")).lower() == "loss")
    pushes = sum(1 for r in decided if str(r.get("result")).lower() == "push")
    denom = wins + losses
    return {
        "n_leans": len(leans),
        "n_decided": len(decided),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate": (wins / denom) if denom else None,
    }


def calibration_by_kei_edge(
    rows: Sequence[Dict[str, Any]],
    *,
    buckets: Sequence[tuple[float, float]] = (
        (0.0, 2.5),
        (2.5, 4.0),
        (4.0, 6.0),
        (6.0, 99.0),
    ),
) -> List[Dict[str, Any]]:
    """KEI |edge| bucket vs cover rate on settled non-void rows."""
    out: List[Dict[str, Any]] = []
    for lo, hi in buckets:
        bucket_rows = []
        for r in rows:
            if str(r.get("result")).lower() not in {"win", "loss", "push"}:
                continue
            kei = r.get("kei_at_post") if isinstance(r.get("kei_at_post"), dict) else {}
            edge = _f(kei.get("edge_pts"))
            if edge is None:
                continue
            mag = abs(edge)
            if lo <= mag < hi:
                bucket_rows.append(r)
        wins = sum(1 for r in bucket_rows if str(r.get("result")).lower() == "win")
        losses = sum(1 for r in bucket_rows if str(r.get("result")).lower() == "loss")
        denom = wins + losses
        out.append(
            {
                "edge_abs_lo": lo,
                "edge_abs_hi": hi,
                "n": len(bucket_rows),
                "wins": wins,
                "losses": losses,
                "cover_rate": (wins / denom) if denom else None,
            }
        )
    return out


def live_exposure(
    rows: Sequence[Dict[str, Any]],
    *,
    week_or_slate: Optional[str] = None,
) -> Dict[str, Any]:
    pending_plays = []
    for r in rows:
        if str(r.get("type")).lower() != "play":
            continue
        if str(r.get("result")).lower() != "pending":
            continue
        if week_or_slate and str(r.get("week_or_slate")) != str(week_or_slate):
            continue
        pending_plays.append(r)
    return {
        "week_or_slate": week_or_slate,
        "pending_play_count": len(pending_plays),
        "pending_play_units": sum(float(r.get("units") or 0) for r in pending_plays),
    }
