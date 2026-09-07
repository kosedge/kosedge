"""PIT KenPom snapshot audit (metadata only; no scores or error metrics).

Archive-date / capture-time semantics (locked):
  - `snapshot_date` is taken from the filename `kenpom_YYYY-MM-DD.parquet`.
  - That filename date IS the archive as-of date used for PIT selection
    (`archive_date_semantics = filename_date_is_as_of`).
  - `captured_at` may be null ONLY under that explicit policy. Snapshots that
    set `require_captured_at=True` (or lack the policy flag) with null
    `captured_at` are ineligible.
  - Game-level PIT_ELIGIBLE further requires both bridged team_norms present
    in the selected snapshot with non-null AdjEM and AdjT.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import polars as pl

from ncaam_lab.holdout_2425.constants import KENPOM_SNAPSHOT_DIR, WINDOW_END, WINDOW_START
from ncaam_lab.holdout_2425.io_util import sha256_file

_WEB_SRC = Path(__file__).resolve().parents[2]
if str(_WEB_SRC) not in sys.path:
    sys.path.insert(0, str(_WEB_SRC))

from ncaam_identity import to_ratings_norm  # noqa: E402

# Locked policy: filename date is the archive as-of; null captured_at allowed
# only because of this explicit declaration (not silent acceptance).
ARCHIVE_DATE_SEMANTICS = "filename_date_is_as_of"
NULL_CAPTURED_AT_POLICY = "allowed_when_filename_date_is_as_of"


def inventory_snapshots(
    snapshot_dir: Path = KENPOM_SNAPSHOT_DIR,
    *,
    window_start: date = WINDOW_START,
    window_end: date = WINDOW_END,
    require_captured_at: bool = False,
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
                    "archive_date_semantics": ARCHIVE_DATE_SEMANTICS,
                    "null_captured_at_policy": NULL_CAPTURED_AT_POLICY,
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

        # captured_at: prefer column if present; else null under explicit policy.
        captured_at: Optional[str] = None
        if "captured_at" in cols:
            caps = [
                str(v)
                for v in df.select(pl.col("captured_at").cast(pl.Utf8))
                .unique()
                .to_series()
                .to_list()
                if v is not None and str(v).strip()
            ]
            if caps:
                captured_at = sorted(caps)[0]
        captured_at_ok = True
        captured_reason = None
        if captured_at is None:
            if require_captured_at:
                captured_at_ok = False
                captured_reason = "captured_at_required_but_null"
            elif ARCHIVE_DATE_SEMANTICS != "filename_date_is_as_of":
                captured_at_ok = False
                captured_reason = "null_captured_at_without_filename_asof_policy"
            # else: null allowed under NULL_CAPTURED_AT_POLICY

        eligible = bool(
            asof_ok
            and captured_at_ok
            and has_adjem
            and has_adjt
            and has_team
            and adjem_c >= 0.99
            and adjt_c >= 0.99
            and n_dup == 0
        )
        quarantine = None
        if not eligible:
            if not asof_ok:
                quarantine = "asof_mismatch"
            elif not captured_at_ok:
                quarantine = captured_reason
            else:
                quarantine = "incomplete_or_duplicate_or_missing_cols"
        out.append(
            {
                "filename": fp.name,
                "path": fp.as_posix(),
                "sha256": sha256_file(fp),
                "snapshot_date": snap_date.isoformat(),
                "source_as_of": snap_date.isoformat(),
                "archive_date": snap_date.isoformat(),
                "archive_date_semantics": ARCHIVE_DATE_SEMANTICS,
                "null_captured_at_policy": NULL_CAPTURED_AT_POLICY,
                "captured_at": captured_at,
                "schema_columns": sorted(cols),
                "row_count": df.height,
                "unique_team_count": int(df["team_norm"].n_unique()) if has_team else 0,
                "duplicate_team_groups": n_dup,
                "adjem_completeness": round(adjem_c, 6),
                "adjt_completeness": round(adjt_c, 6),
                "b7_team_norm_present": has_team,
                "asof_provenance_ok": asof_ok,
                "eligible": eligible,
                "quarantine_reason": quarantine,
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


def _adjt_col(cols: set[str]) -> Optional[str]:
    if "adjtempo" in cols:
        return "adjtempo"
    if "adjt" in cols:
        return "adjt"
    return None


def _team_rating_ok(df: pl.DataFrame, team_norm: str) -> Tuple[bool, Dict[str, Any]]:
    """Both AdjEM and AdjT must be present/non-null for the bridged team_norm."""
    cols = set(df.columns)
    adjt = _adjt_col(cols)
    if "team_norm" not in cols or "adjem" not in cols or adjt is None:
        return False, {"reason": "snapshot_missing_rating_columns"}
    hit = df.filter(pl.col("team_norm") == team_norm)
    if hit.height == 0:
        return False, {"reason": "team_not_in_snapshot", "team_norm": team_norm}
    row = hit.row(0, named=True)
    adjem = row.get("adjem")
    adjt_v = row.get(adjt)
    if adjem is None or adjt_v is None:
        return False, {
            "reason": "missing_adjem_or_adjt",
            "team_norm": team_norm,
            "adjem": adjem,
            "adjt": adjt_v,
        }
    return True, {"team_norm": team_norm, "adjem": float(adjem), "adjt": float(adjt_v)}


def _load_snapshot_frame(sel: Dict[str, Any]) -> Optional[pl.DataFrame]:
    path = sel.get("path")
    if not path:
        return None
    fp = Path(str(path))
    if not fp.exists():
        return None
    return pl.read_parquet(fp)


def build_game_eligibility(
    games: List[Dict[str, Any]],
    snapshots: List[Dict[str, Any]],
    *,
    require_both_teams_ratings: bool = True,
) -> Dict[str, Any]:
    """Declare PIT_ELIGIBLE only when snapshot is eligible AND (by default)
    both bridged teams are present with AdjEM + AdjT.
    """
    rows: List[Dict[str, Any]] = []
    n_ok = n_miss = 0
    frame_cache: Dict[str, pl.DataFrame] = {}

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

        home_id = str(g.get("home") or "")
        away_id = str(g.get("away") or "")
        home_bridge = to_ratings_norm(home_id) if home_id else ""
        away_bridge = to_ratings_norm(away_id) if away_id else ""

        team_gate_ok = True
        team_gate_detail: Dict[str, Any] = {
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_ratings_norm": home_bridge,
            "away_ratings_norm": away_bridge,
        }
        if require_both_teams_ratings:
            if not home_bridge or not away_bridge:
                team_gate_ok = False
                team_gate_detail["reason"] = "missing_bridged_team_id"
            else:
                key = str(sel.get("filename") or sel.get("path"))
                if key not in frame_cache:
                    frame = _load_snapshot_frame(sel)
                    if frame is None:
                        team_gate_ok = False
                        team_gate_detail["reason"] = "snapshot_frame_unreadable"
                    else:
                        frame_cache[key] = frame
                if team_gate_ok:
                    df = frame_cache[key]
                    home_ok, home_meta = _team_rating_ok(df, home_bridge)
                    away_ok, away_meta = _team_rating_ok(df, away_bridge)
                    team_gate_detail["home"] = home_meta
                    team_gate_detail["away"] = away_meta
                    if not (home_ok and away_ok):
                        team_gate_ok = False
                        team_gate_detail["reason"] = "bridged_team_or_ratings_missing"

        if not team_gate_ok:
            rows.append(
                {
                    "source_event_id": g.get("espn_game_id"),
                    "event_id": g.get("espn_game_id"),
                    "tip_date": tip.isoformat(),
                    "home_team_id": home_id,
                    "away_team_id": away_id,
                    "eligibility_status": "PIT_TEAMS_OR_RATINGS_MISSING",
                    "selected_snapshot_id": sel["filename"],
                    "selected_snapshot_sha256": sel["sha256"],
                    "selected_snapshot_as_of": sel["snapshot_date"],
                    "team_gate": team_gate_detail,
                }
            )
            n_miss += 1
            continue

        rows.append(
            {
                "source_event_id": g.get("espn_game_id"),
                "event_id": g.get("espn_game_id"),
                "tip_date": tip.isoformat(),
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_ratings_norm": home_bridge,
                "away_ratings_norm": away_bridge,
                "eligibility_status": "PIT_ELIGIBLE",
                "selected_snapshot_id": sel["filename"],
                "selected_snapshot_sha256": sel["sha256"],
                "selected_snapshot_as_of": sel["snapshot_date"],
                "archive_date_semantics": sel.get("archive_date_semantics"),
                "captured_at": sel.get("captured_at"),
                "team_gate": team_gate_detail,
            }
        )
        n_ok += 1
    return {
        "n_games": len(games),
        "n_pit_eligible": n_ok,
        "n_missing_or_invalid": n_miss,
        "n_snapshots_inventoried": len(snapshots),
        "n_snapshots_eligible": sum(1 for s in snapshots if s.get("eligible")),
        "archive_date_semantics": ARCHIVE_DATE_SEMANTICS,
        "null_captured_at_policy": NULL_CAPTURED_AT_POLICY,
        "require_both_teams_ratings": require_both_teams_ratings,
        "rows": rows,
        "scores_omitted": True,
        "forbidden_methods_not_used": [
            "current_ratings",
            "end_of_season_backfilled",
            "later_snapshot_for_earlier_event",
            "interpolation_from_future",
            "annual_csv_as_pit",
            "reconstructed_from_later_games",
            "null_captured_at_without_policy",
        ],
    }
