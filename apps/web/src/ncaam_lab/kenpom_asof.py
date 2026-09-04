"""KenPom feed attach — as-of ≤ tip (backward), leakage-audited.

KenPom is a feed only, never SoT. Prefer weekly snapshots under
apps/web/data/processed/kenpom_snapshots/.
"""

from __future__ import annotations

import warnings
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

import polars as pl


def load_kenpom_snapshot_archive(snapshot_dir: Path) -> Optional[pl.DataFrame]:
    """Concat kenpom_YYYY-MM-DD.parquet → archive with as_of_date + team_norm + metrics."""
    if not snapshot_dir.exists():
        return None
    files = sorted(snapshot_dir.glob("kenpom_*.parquet"))
    if not files:
        return None
    frames: List[pl.DataFrame] = []
    for fp in files:
        try:
            date_str = fp.stem.replace("kenpom_", "")
            df = pl.read_parquet(fp)
            if "snapshot_date" in df.columns:
                df = df.with_columns(
                    pl.col("snapshot_date").cast(pl.Utf8).str.to_date(strict=False).alias("as_of_date")
                )
            else:
                df = df.with_columns(pl.lit(date_str).str.to_date(strict=False).alias("as_of_date"))
            # Normalize tempo column name for Lab fair_total
            if "adjt" not in df.columns and "adjtempo" in df.columns:
                df = df.with_columns(pl.col("adjtempo").alias("adjt"))
            if "team_norm" not in df.columns:
                continue
            keep = ["team_norm", "as_of_date", "adjem"]
            for c in ("adjoe", "adjde", "adjt", "season"):
                if c in df.columns:
                    keep.append(c)
            frames.append(df.select(keep))
        except Exception:
            continue
    if not frames:
        return None
    return pl.concat(frames, how="diagonal_relaxed").unique().sort("team_norm", "as_of_date")


def attach_kenpom_asof(
    games: pl.DataFrame,
    archive: pl.DataFrame,
    *,
    home_key: str = "home_ratings_norm",
    away_key: str = "away_ratings_norm",
    tip_col: str = "tip_date",
) -> pl.DataFrame:
    """Backward asof join KenPom metrics for home/away. No look-ahead."""
    if tip_col not in games.columns:
        raise ValueError(f"games missing {tip_col}")
    for key in (home_key, away_key):
        if key not in games.columns:
            raise ValueError(f"games missing {key}")

    need = ["team_norm", "as_of_date", "adjem"]
    for c in need:
        if c not in archive.columns:
            raise ValueError(f"kenpom archive missing {c}")

    metric_cols = [c for c in ("adjem", "adjoe", "adjde", "adjt") if c in archive.columns]
    arch = archive.sort("team_norm", "as_of_date")

    home_sel = arch.select(
        [pl.col("team_norm"), pl.col("as_of_date")]
        + [pl.col(c).alias(f"{c}_home") for c in metric_cols]
    )
    away_sel = arch.select(
        [pl.col("team_norm"), pl.col("as_of_date")]
        + [pl.col(c).alias(f"{c}_away") for c in metric_cols]
    )

    g = games.sort(home_key, tip_col)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*[Ss]ortedness.*", category=UserWarning)
        g = g.join_asof(
            home_sel.sort("team_norm", "as_of_date"),
            left_on=tip_col,
            right_on="as_of_date",
            by_left=home_key,
            by_right="team_norm",
            strategy="backward",
        )
        if "as_of_date" in g.columns:
            g = g.rename({"as_of_date": "kenpom_as_of_home"})
        g = g.sort(away_key, tip_col)
        g = g.join_asof(
            away_sel.sort("team_norm", "as_of_date"),
            left_on=tip_col,
            right_on="as_of_date",
            by_left=away_key,
            by_right="team_norm",
            strategy="backward",
        )
        if "as_of_date" in g.columns:
            g = g.rename({"as_of_date": "kenpom_as_of_away"})

    return g


def assert_no_kenpom_leakage(games: pl.DataFrame) -> Tuple[bool, int]:
    """Return (ok, n_violations). Violation = kenpom_as_of > tip_date."""
    violations = 0
    if "tip_date" not in games.columns:
        return False, -1
    for side in ("kenpom_as_of_home", "kenpom_as_of_away"):
        if side not in games.columns:
            continue
        for tip, asof in zip(games["tip_date"].to_list(), games[side].to_list()):
            if tip is None or asof is None:
                continue
            tip_d = tip if isinstance(tip, date) else date.fromisoformat(str(tip)[:10])
            asof_d = asof if isinstance(asof, date) else date.fromisoformat(str(asof)[:10])
            if asof_d > tip_d:
                violations += 1
    return violations == 0, violations
