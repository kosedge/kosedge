"""Last-12h (mid / dense) residual vs owned close. Not a model feature."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.services.cfb_warehouse.leakage import is_available_before_kickoff

WINDOW = timedelta(hours=12)


def _parse_ts(raw: Any) -> Optional[datetime]:
    text = str(raw or "").replace("Z", "+00:00")
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def last12h_vs_close(
    snaps: Sequence[Mapping[str, Any]],
    *,
    kickoff: Any,
    game_date: Any = None,
    window: Optional[timedelta] = WINDOW,
) -> Dict[str, Any]:
    """Compare last legal mid/dense snap (optional window) to labeled close."""
    legal: List[Mapping[str, Any]] = []
    for row in snaps:
        captured = row.get("captured_at") or row.get("snapshot_ts")
        if not is_available_before_kickoff(
            available_at=captured, kickoff=kickoff, game_date=game_date
        ):
            continue
        legal.append(row)
    close_rows = [r for r in legal if str(r.get("snapshot_kind") or "") == "close"]
    if not close_rows:
        # Lake export is path-labeled (pre7d/3d/1d/mid); last legal snap is the close.
        close_rows = sorted(
            legal, key=lambda r: str(r.get("captured_at") or r.get("snapshot_ts") or "")
        )[-3:]
    late_rows = [
        r
        for r in legal
        if str(r.get("snapshot_kind") or "") in {"mid", "dense"}
    ]
    kick = _parse_ts(kickoff)
    if kick is not None and window is not None:
        late_rows = [
            r
            for r in late_rows
            if (ts := _parse_ts(r.get("captured_at") or r.get("snapshot_ts"))) is not None
            and (kick - ts) <= window
            and ts < kick
        ]

    def _point(rows: Sequence[Mapping[str, Any]], market: str, field: str) -> Optional[float]:
        picked = [r for r in rows if str(r.get("market") or "") == market]
        if not picked:
            return None
        picked = sorted(picked, key=lambda r: str(r.get("captured_at") or r.get("snapshot_ts") or ""))
        try:
            val = picked[-1].get(field)
            if val is None or val != val:
                return None
            return float(val)
        except (TypeError, ValueError):
            return None

    close_sp = _point(close_rows, "spread", "spread_home")
    late_sp = _point(late_rows, "spread", "spread_home")
    close_tot = _point(close_rows, "total", "total_points")
    late_tot = _point(late_rows, "total", "total_points")
    return {
        "close_spread_home": close_sp,
        "late_spread_home": late_sp,
        "spread_residual": (
            None if close_sp is None or late_sp is None else round(float(late_sp) - float(close_sp), 3)
        ),
        "close_total": close_tot,
        "late_total": late_tot,
        "total_residual": (
            None if close_tot is None or late_tot is None else round(float(late_tot) - float(close_tot), 3)
        ),
        "n_late_snaps": len(late_rows),
        "product": False,
    }
