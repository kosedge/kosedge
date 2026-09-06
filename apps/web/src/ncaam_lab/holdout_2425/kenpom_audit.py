"""PIT KenPom snapshot audit (metadata only; no scores or error metrics)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl

from ncaam_lab.holdout_2425.constants import KENPOM_SNAPSHOT_DIR, WINDOW_END, WINDOW_START
from ncaam_lab.holdout_2425.io_util import sha256_file


def inventory_snapshots(
    snapshot_dir: Path = KENPOM_SNAPSHOT_DIR,
    *,
    window_start: date = WINDOW_START,
    window_end: date = WINDOW_END,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not snapshot_dir.exists():
        return out
    min_snap = date(window_start.year, 10, 1)
    for fp in sorted(snapshot_dir.glob("kenpom_*.parquet")):
        date_str = fp.stem.replace("kenpom_", "")
        try:
            snap_date = date.fromisoformat(date_str)
        except ValueError:
            out.append(
                {
                    "filename": fp.name,
                    "path": fp.as_posix(),
                    "sha256": sha256_file(fp),
                    "eligible": False,
                    "quarantine_reason": "invalid_filename_date",
                }
            )
            continue
        if snap_date < min_snap or snap_date > window_end:
            continue
        df = pl.read_parquet(fp)
        cols = set(df.columns)
        has_adjem = "adjem" in cols
        has_adjt = "adjtempo" in cols or "adjt" in cols
        has_team = "team_norm" in cols
        n_dup = 0
        if has_team:
            n_dup = int(df.group_by("team_norm").len().filter(pl.col("len") > 1).height)
        adjem_c = float(df["adjem"].is_not_null().mean()) if has_adjem else 0.0
        adjt_col = "adjtempo" if "adjtempo" in cols else ("adjt" if "adjt" in cols else None)
        adjt_c = float(df[adjt_col].is_not_null().mean()) if adjt_col else 0.0
        asof_ok = True
        for col in ("snapshot_date", "archivedate"):
            if col in cols:
                vals = (
                    df.select(pl.col(col).cast(pl.Utf8).str.slice(0, 10))
                    .unique()
                    .to_series()
                    .to_list()
                )
                if any(v and v != snap_date.isoformat() for v in vals):
                    asof_ok = False
        eligible = bool(
            asof_ok
            and has_adjem
            and has_adjt
            and has_team
            and adjem_c >= 0.99
            and adjt_c >= 0.99
            and n_dup == 0
        )
        out.append(
            {
                "filename": fp.name,
                "path": fp.as_posix(),
                "sha256": sha256_file(fp),
                "snapshot_date": snap_date.isoformat(),
                "source_as_of": snap_date.isoformat(),
                "captured_at": None,
                "schema_columns": sorted(cols),
                "row_count": df.height,
                "unique_team_count": int(df["team_norm"].n_unique()) if has_team else 0,
                "duplicate_team_groups": n_dup,
                "adjem_completeness": round(adjem_c, 6),
                "adjt_completeness": round(adjt_c, 6),
                "b7_team_norm_present": has_team,
                "asof_provenance_ok": asof_ok,
                "eligible": eligible,
                "quarantine_reason": None
                if eligible
                else (
                    "asof_mismatch"
                    if not asof_ok
                    else "incomplete_or_duplicate_or_missing_cols"
                ),
                "earliest_eligible_tip": snap_date.isoformat(),
            }
        )
    eligible_rows = sorted(
        [r for r in out if r.get("eligible")], key=lambda r: r["snapshot_date"]
    )
    for i, r in enumerate(eligible_rows):
        if i + 1 < len(eligible_rows):
            nxt = date.fromisoformat(eligible_rows[i + 1]["snapshot_date"])
            r["latest_tip_for_which_most_recent"] = nxt.isoformat()
        else:
            r["latest_tip_for_which_most_recent"] = window_end.isoformat()
    return out


def select_snapshot_for_tip(
    tip: date, snapshots: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    eligible = [
        s
        for s in snapshots
        if s.get("eligible") and date.fromisoformat(s["snapshot_date"]) <= tip
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda s: s["snapshot_date"])


def build_game_eligibility(
    games: List[Dict[str, Any]], snapshots: List[Dict[str, Any]]
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    n_ok = n_miss = 0
    for g in games:
        tip_s = str(g.get("date") or "")[:10]
        try:
            tip = date.fromisoformat(tip_s)
        except ValueError:
            rows.append(
                {
                    "source_event_id": g.get("espn_game_id"),
                    "event_id": g.get("espn_game_id"),
                    "tip_date": tip_s,
                    "eligibility_status": "INVALID_TIP",
                    "selected_snapshot_id": None,
                    "selected_snapshot_sha256": None,
                }
            )
            n_miss += 1
            continue
        sel = select_snapshot_for_tip(tip, snapshots)
        if sel is None:
            rows.append(
                {
                    "source_event_id": g.get("espn_game_id"),
                    "event_id": g.get("espn_game_id"),
                    "tip_date": tip.isoformat(),
                    "home_team_id": g.get("home"),
                    "away_team_id": g.get("away"),
                    "eligibility_status": "MISSING_PIT_SNAPSHOT",
                    "selected_snapshot_id": None,
                    "selected_snapshot_sha256": None,
                }
            )
            n_miss += 1
            continue
        assert date.fromisoformat(sel["snapshot_date"]) <= tip
        rows.append(
            {
                "source_event_id": g.get("espn_game_id"),
                "event_id": g.get("espn_game_id"),
                "tip_date": tip.isoformat(),
                "home_team_id": g.get("home"),
                "away_team_id": g.get("away"),
                "eligibility_status": "PIT_ELIGIBLE",
                "selected_snapshot_id": sel["filename"],
                "selected_snapshot_sha256": sel["sha256"],
                "selected_snapshot_as_of": sel["snapshot_date"],
            }
        )
        n_ok += 1
    return {
        "n_games": len(games),
        "n_pit_eligible": n_ok,
        "n_missing_or_invalid": n_miss,
        "n_snapshots_inventoried": len(snapshots),
        "n_snapshots_eligible": sum(1 for s in snapshots if s.get("eligible")),
        "rows": rows,
        "scores_omitted": True,
        "forbidden_methods_not_used": [
            "current_ratings",
            "end_of_season_backfilled",
            "later_snapshot_for_earlier_event",
            "interpolation_from_future",
            "annual_csv_as_pit",
            "reconstructed_from_later_games",
        ],
    }
