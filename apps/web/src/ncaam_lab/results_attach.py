"""Lab results densify — attach actual margins from repo artifacts only.

Primary source: ESPN Schedule SoT packs (already B7-mapped + final scores).
Secondary: owned event_id actuals (`actual_margins.parquet`, `results.csv`).

Hard rules:
  - No Odds API pulls / credit burn
  - Fail-closed on B7 identity (missing home/away team_id → omit)
  - Never invent margins; ambiguous (tip_date, home_id, away_id) → omit
  - Lab schedule join remains SoT D (Odds event_id); packs join on tip + team_id
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import polars as pl


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _web_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_schedule_pack_paths() -> List[Path]:
    """Official Schedule SoT A packs covering Lab Train-A / Test-A tip windows."""
    base = (
        _repo_root()
        / "services"
        / "model-service"
        / "src"
        / "services"
        / "ncaam_schedule"
        / "data"
    )
    return [
        base / "ncaam_official_schedule_2022_23.json",
        base / "ncaam_official_schedule_2023_24.json",
    ]


def _parse_tip_date(tipoff: Optional[str], local_date: Optional[str] = None) -> Optional[date]:
    raw = (tipoff or "").strip()
    if raw:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            pass
    if local_date:
        try:
            return date.fromisoformat(str(local_date)[:10])
        except ValueError:
            return None
    return None


def load_schedule_pack_results(
    pack_paths: Optional[Sequence[Path]] = None,
) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Load final scores from Schedule SoT packs; fail-closed on missing B7 ids.

    Returns (results_df, receipt) where results_df columns are:
      tip_date, home_team_id, away_team_id, actual_margin, espn_game_id, source_pack
    Duplicate (tip_date, home_team_id, away_team_id) keys are dropped entirely.
    """
    paths = list(pack_paths) if pack_paths is not None else default_schedule_pack_paths()
    rows: List[Dict[str, Any]] = []
    receipt: Dict[str, Any] = {
        "packs": [],
        "n_scored_rows_raw": 0,
        "n_omitted_missing_b7": 0,
        "n_omitted_missing_score": 0,
        "n_omitted_ambiguous_key": 0,
        "n_unique_keys": 0,
    }

    for path in paths:
        pack_info: Dict[str, Any] = {
            "path": str(path),
            "exists": path.exists(),
            "n_games": 0,
            "n_kept": 0,
            "n_omit_b7": 0,
            "n_omit_score": 0,
        }
        if not path.exists():
            receipt["packs"].append(pack_info)
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pack_info["error"] = "unreadable"
            receipt["packs"].append(pack_info)
            continue

        games = payload.get("games") or []
        pack_info["n_games"] = len(games)
        for g in games:
            hs, aws = g.get("home_score"), g.get("away_score")
            if hs is None or aws is None:
                pack_info["n_omit_score"] += 1
                receipt["n_omitted_missing_score"] += 1
                continue
            hid = g.get("home")
            aid = g.get("away")
            if not hid or not aid:
                pack_info["n_omit_b7"] += 1
                receipt["n_omitted_missing_b7"] += 1
                continue
            tip = _parse_tip_date(g.get("tipoff") or g.get("kickoff"), g.get("date"))
            if tip is None:
                pack_info["n_omit_b7"] += 1
                receipt["n_omitted_missing_b7"] += 1
                continue
            rows.append(
                {
                    "tip_date": tip,
                    "home_team_id": str(hid),
                    "away_team_id": str(aid),
                    "actual_margin": float(hs) - float(aws),
                    "espn_game_id": str(g.get("espn_game_id") or g.get("game_id") or ""),
                    "source_pack": path.name,
                }
            )
            pack_info["n_kept"] += 1

        receipt["packs"].append(pack_info)

    receipt["n_scored_rows_raw"] = len(rows)
    if not rows:
        empty = pl.DataFrame(
            {
                "tip_date": pl.Series([], dtype=pl.Date),
                "home_team_id": pl.Series([], dtype=pl.Utf8),
                "away_team_id": pl.Series([], dtype=pl.Utf8),
                "actual_margin": pl.Series([], dtype=pl.Float64),
                "espn_game_id": pl.Series([], dtype=pl.Utf8),
                "source_pack": pl.Series([], dtype=pl.Utf8),
            }
        )
        return empty, receipt

    df = pl.DataFrame(rows)
    # Fail-closed ambiguity: any duplicate identity key → drop all copies
    counts = df.group_by(["tip_date", "home_team_id", "away_team_id"]).len()
    amb = counts.filter(pl.col("len") > 1).select(["tip_date", "home_team_id", "away_team_id"])
    receipt["n_omitted_ambiguous_key"] = int(amb.height)
    if amb.height:
        df = df.join(amb, on=["tip_date", "home_team_id", "away_team_id"], how="anti")
    df = df.unique(subset=["tip_date", "home_team_id", "away_team_id"], keep="first")
    receipt["n_unique_keys"] = len(df)
    return df, receipt


def load_event_id_actuals(
    actuals_path: Optional[Path] = None,
    results_csv_path: Optional[Path] = None,
) -> pl.DataFrame:
    """Owned event_id → actual_margin overlays (no Odds densify)."""
    web = _web_root()
    actuals_path = actuals_path or (web / "data" / "processed" / "actual_margins.parquet")
    results_csv_path = results_csv_path or (web / "data" / "raw" / "games" / "results.csv")

    frames: List[pl.DataFrame] = []
    if actuals_path.exists():
        am = pl.read_parquet(actuals_path)
        cols = [c for c in ("event_id", "actual_margin") if c in am.columns]
        if len(cols) == 2:
            frames.append(am.select(cols))

    if results_csv_path.exists():
        try:
            rc = pl.read_csv(results_csv_path, truncate_ragged_lines=True, infer_schema_length=5000)
        except Exception:
            rc = pl.DataFrame()
        if {"event_id", "home_pts", "away_pts"}.issubset(set(rc.columns)):
            frames.append(
                rc.select(
                    [
                        pl.col("event_id"),
                        (pl.col("home_pts").cast(pl.Float64) - pl.col("away_pts").cast(pl.Float64)).alias(
                            "actual_margin"
                        ),
                    ]
                )
            )
        elif {"event_id", "actual_margin"}.issubset(set(rc.columns)):
            frames.append(rc.select(["event_id", "actual_margin"]))

    if not frames:
        return pl.DataFrame(
            {
                "event_id": pl.Series([], dtype=pl.Utf8),
                "actual_margin": pl.Series([], dtype=pl.Float64),
            }
        )

    out = pl.concat(frames, how="diagonal_relaxed").filter(
        pl.col("event_id").is_not_null() & pl.col("actual_margin").is_not_null()
    )
    # Prefer first occurrence (actual_margins.parquet before results.csv)
    return out.unique(subset=["event_id"], keep="first")


def attach_lab_outcomes(
    lab: pl.DataFrame,
    *,
    pack_results: Optional[pl.DataFrame] = None,
    event_actuals: Optional[pl.DataFrame] = None,
    pack_paths: Optional[Sequence[Path]] = None,
    actuals_path: Optional[Path] = None,
    results_csv_path: Optional[Path] = None,
) -> Tuple[pl.DataFrame, Dict[str, Any]]:
    """Attach actual_margin to Lab rows. Fail-closed; never invent.

    Join order:
      1) Schedule pack on tip_date + home_team_id + away_team_id (B7)
      2) Fill remaining nulls via owned event_id actuals
    """
    receipt: Dict[str, Any] = {
        "n_lab": len(lab),
        "n_with_actual_pack": 0,
        "n_with_actual_event_id_fill": 0,
        "n_with_actual": 0,
        "outcome_coverage": 0.0,
        "pack_receipt": None,
        "sources": [],
    }

    required = {"tip_date", "home_team_id", "away_team_id", "event_id"}
    missing = required - set(lab.columns)
    if missing:
        raise ValueError(f"lab frame missing columns for results attach: {sorted(missing)}")

    # Drop any pre-existing actual_margin so densify is the SoT for this attach
    base = lab.drop("actual_margin") if "actual_margin" in lab.columns else lab

    if pack_results is None:
        pack_results, pack_receipt = load_schedule_pack_results(pack_paths)
        receipt["pack_receipt"] = pack_receipt
    else:
        receipt["pack_receipt"] = {"provided_rows": len(pack_results)}

    if event_actuals is None:
        event_actuals = load_event_id_actuals(actuals_path, results_csv_path)

    # Ensure tip_date is Date
    tip = base["tip_date"]
    if tip.dtype == pl.Utf8:
        base = base.with_columns(pl.col("tip_date").str.to_date(strict=False).alias("tip_date"))

    pack_cols = ["tip_date", "home_team_id", "away_team_id", "actual_margin"]
    if pack_results.is_empty():
        joined = base.with_columns(pl.lit(None).cast(pl.Float64).alias("actual_margin"))
    else:
        # Only keep rows with both B7 ids on Lab side (Lab already fail-closed, but belt+suspenders)
        pack_clean = pack_results.select(pack_cols).filter(
            pl.col("home_team_id").is_not_null() & pl.col("away_team_id").is_not_null()
        )
        joined = base.join(pack_clean, on=["tip_date", "home_team_id", "away_team_id"], how="left")
        receipt["sources"].append("schedule_sot_packs")

    n_pack = int(joined.filter(pl.col("actual_margin").is_not_null()).height)
    receipt["n_with_actual_pack"] = n_pack

    if not event_actuals.is_empty() and "event_id" in event_actuals.columns:
        fill = event_actuals.select(["event_id", "actual_margin"]).rename(
            {"actual_margin": "actual_margin_event"}
        )
        joined = joined.join(fill, on="event_id", how="left")
        before_fill = joined.filter(pl.col("actual_margin").is_not_null()).height
        joined = joined.with_columns(
            pl.when(pl.col("actual_margin").is_not_null())
            .then(pl.col("actual_margin"))
            .otherwise(pl.col("actual_margin_event"))
            .alias("actual_margin")
        ).drop("actual_margin_event")
        after_fill = joined.filter(pl.col("actual_margin").is_not_null()).height
        receipt["n_with_actual_event_id_fill"] = int(after_fill - before_fill)
        if receipt["n_with_actual_event_id_fill"]:
            receipt["sources"].append("event_id_owned_actuals")
    else:
        receipt["n_with_actual_event_id_fill"] = 0

    n_actual = int(joined.filter(pl.col("actual_margin").is_not_null()).height)
    receipt["n_with_actual"] = n_actual
    receipt["outcome_coverage"] = round((n_actual / len(joined)) if len(joined) else 0.0, 4)
    return joined, receipt


def coverage_vs_event_id_only(
    lab: pl.DataFrame,
    *,
    actuals_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Before baseline: event_id join to owned actual_margins only (historical thin path)."""
    web = _web_root()
    path = actuals_path or (web / "data" / "processed" / "actual_margins.parquet")
    empty = pl.DataFrame(
        {
            "event_id": pl.Series([], dtype=pl.Utf8),
            "actual_margin": pl.Series([], dtype=pl.Float64),
        }
    )
    if path.exists():
        am = pl.read_parquet(path)
        if {"event_id", "actual_margin"}.issubset(set(am.columns)):
            event_actuals = am.select(["event_id", "actual_margin"]).unique(
                subset=["event_id"], keep="first"
            )
        else:
            event_actuals = empty
    else:
        event_actuals = empty

    if event_actuals.is_empty():
        n = 0
    else:
        j = lab.join(event_actuals, on="event_id", how="left")
        n = int(j.filter(pl.col("actual_margin").is_not_null()).height)
    return {
        "n_lab": len(lab),
        "n_with_actual": n,
        "outcome_coverage": round((n / len(lab)) if len(lab) else 0.0, 4),
        "method": "event_id_actual_margins_only",
    }
