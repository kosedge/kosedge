"""Schedule SoT D — Lab game set from Odds Path A ∩ B7 resolve ∩ cut window.

Join keys: Odds API event_id + commence_time + B7 team_id.
Fail-closed: unresolved / omit aliases drop the event.
espn_game_id reserved empty for future Schedule SoT A crosswalk.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import polars as pl

from ncaam_identity import resolve_team_id, to_ratings_norm
from ncaam_lab.protocol import (
    CUT_WINDOWS,
    OPEN_TIMESTAMP_MAX_DRIFT_DAYS,
    SCHEDULE_SOT,
    SPORT_KEY,
    classify_tip,
)


def _parse_tip(commence: str) -> Optional[date]:
    if not commence:
        return None
    try:
        return date.fromisoformat(str(commence)[:10])
    except ValueError:
        return None


def open_snapshot_honest_dates(
    open_dir: Path,
    max_drift_days: int = OPEN_TIMESTAMP_MAX_DRIFT_DAYS,
) -> Set[str]:
    """Return YYYY-MM-DD stems whose Odds API timestamp is within max_drift of filename.

    Market Edge honesty filter: exclude days with |api_ts − filename| > 7d.
    """
    import json

    honest: Set[str] = set()
    if not open_dir.exists():
        return honest
    for fp in open_dir.glob("*.json"):
        try:
            payload = json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ts = payload.get("timestamp") if isinstance(payload, dict) else None
        if not ts:
            continue
        try:
            api_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            file_dt = datetime.strptime(fp.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        drift_days = abs((api_dt - file_dt).total_seconds()) / 86400.0
        if drift_days <= max_drift_days:
            honest.add(fp.stem)
    return honest


def build_lab_game_set(
    odds: pl.DataFrame,
    *,
    cut: str = "train_a",
    tip_start: Optional[date] = None,
    tip_end: Optional[date] = None,
    open_dir: Optional[Path] = None,
) -> pl.DataFrame:
    """Build fail-closed Lab rows for a cut window (default Train-A).

    Requires odds columns: event_id, home_team, away_team, commence_time,
    open_spread_home, close_spread_home, open_total, close_total (book grain OK).
    """
    required = {"event_id", "home_team", "away_team", "commence_time"}
    missing = required - set(odds.columns)
    if missing:
        raise ValueError(f"odds parquet missing columns: {sorted(missing)}")

    if tip_start is None or tip_end is None:
        if cut not in CUT_WINDOWS:
            raise ValueError(f"unknown cut window: {cut}")
        window = CUT_WINDOWS[cut]
        tip_start, tip_end = window.start, window.end

    # Consensus close (B1) + optional open mean across books
    agg_exprs = []
    if "close_spread_home" in odds.columns:
        agg_exprs.append(pl.col("close_spread_home").mean().alias("b1_consensus_close_spread"))
    else:
        agg_exprs.append(pl.lit(None).cast(pl.Float64).alias("b1_consensus_close_spread"))
    if "close_total" in odds.columns:
        agg_exprs.append(pl.col("close_total").mean().alias("b1_consensus_close_total"))
    else:
        agg_exprs.append(pl.lit(None).cast(pl.Float64).alias("b1_consensus_close_total"))
    if "open_spread_home" in odds.columns:
        agg_exprs.append(pl.col("open_spread_home").mean().alias("open_consensus_spread_raw"))
    else:
        agg_exprs.append(pl.lit(None).cast(pl.Float64).alias("open_consensus_spread_raw"))
    if "open_total" in odds.columns:
        agg_exprs.append(pl.col("open_total").mean().alias("open_consensus_total_raw"))
    else:
        agg_exprs.append(pl.lit(None).cast(pl.Float64).alias("open_consensus_total_raw"))

    consensus = odds.group_by("event_id").agg(agg_exprs)
    events = odds.unique(subset="event_id", keep="first").select(
        ["event_id", "home_team", "away_team", "commence_time"]
    )
    events = events.join(consensus, on="event_id", how="left")

    # Tip + B7 identity (fail-closed)
    home_ids: List[Optional[str]] = []
    away_ids: List[Optional[str]] = []
    home_ratings: List[Optional[str]] = []
    away_ratings: List[Optional[str]] = []
    tips: List[Optional[date]] = []
    cut_labels: List[Optional[str]] = []
    omit_reasons: List[Optional[str]] = []

    for row in events.iter_rows(named=True):
        tip = _parse_tip(row["commence_time"])
        tips.append(tip)
        hid = resolve_team_id(row["home_team"] or "", source="odds")
        aid = resolve_team_id(row["away_team"] or "", source="odds")
        home_ids.append(hid)
        away_ids.append(aid)
        home_ratings.append(to_ratings_norm(hid) if hid else None)
        away_ratings.append(to_ratings_norm(aid) if aid else None)
        if tip is None:
            cut_labels.append(None)
            omit_reasons.append("bad_commence")
            continue
        label = classify_tip(tip)
        cut_labels.append(label)
        if hid is None or aid is None:
            omit_reasons.append("b7_unresolved")
        elif tip < tip_start or tip > tip_end:
            omit_reasons.append("outside_cut")
        elif label is None:
            omit_reasons.append("excluded_or_outside_universe")
        else:
            omit_reasons.append(None)

    events = events.with_columns(
        [
            pl.Series("tip_date", tips),
            pl.Series("home_team_id", home_ids),
            pl.Series("away_team_id", away_ids),
            pl.Series("home_ratings_norm", home_ratings),
            pl.Series("away_ratings_norm", away_ratings),
            pl.Series("cut_window", cut_labels),
            pl.Series("omit_reason", omit_reasons),
        ]
    )

    # Fail-closed keep set for requested cut
    kept = events.filter(pl.col("omit_reason").is_null())
    if cut in ("train_a", "test_a", "universe_path_a"):
        kept = kept.filter(pl.col("cut_window") == cut)

    honest_dates = open_snapshot_honest_dates(open_dir) if open_dir else set()
    # Open honesty keyed by tip calendar day (Path A filename = tip slate day convention).
    # When tip day not in honest set, null out open consensus for Market Edge.
    tip_strs = [
        d.isoformat() if d is not None else None for d in kept["tip_date"].to_list()
    ]
    honest_flags = [(t in honest_dates) if t else False for t in tip_strs]
    kept = kept.with_columns(
        [
            pl.Series("open_snapshot_honest", honest_flags),
            pl.lit(None).cast(pl.Utf8).alias("espn_game_id"),  # future SoT A crosswalk
            pl.lit(SCHEDULE_SOT).alias("schedule_sot"),
            pl.lit(SPORT_KEY).alias("sport"),
        ]
    )
    kept = kept.with_columns(
        [
            pl.when(pl.col("open_snapshot_honest"))
            .then(pl.col("open_consensus_spread_raw"))
            .otherwise(None)
            .alias("open_consensus_spread"),
            pl.when(pl.col("open_snapshot_honest"))
            .then(pl.col("open_consensus_total_raw"))
            .otherwise(None)
            .alias("open_consensus_total"),
        ]
    ).drop(["open_consensus_spread_raw", "open_consensus_total_raw"])

    return kept.sort(["tip_date", "event_id"])


def omit_summary(events_with_reasons: pl.DataFrame) -> Dict[str, Any]:
    if "omit_reason" not in events_with_reasons.columns:
        return {"kept": len(events_with_reasons), "omitted": {}}
    omitted = events_with_reasons.filter(pl.col("omit_reason").is_not_null())
    counts: Dict[str, int] = {}
    for reason in omitted["omit_reason"].to_list():
        counts[str(reason)] = counts.get(str(reason), 0) + 1
    kept = events_with_reasons.filter(pl.col("omit_reason").is_null())
    return {"kept": len(kept), "omitted": counts, "total_events": len(events_with_reasons)}
