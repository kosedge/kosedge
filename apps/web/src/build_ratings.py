"""
Build full_ratings.parquet from KenPom, Torvik, and Evan Miya CSVs.
One row per team per season with normalized team name and key metrics.
Run from apps/web: python src/build_ratings.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_RATINGS, PROCESSED, FULL_RATINGS_PATH, ensure_dirs

ensure_dirs()


def _norm(s: pl.Expr) -> pl.Expr:
    return s.str.to_lowercase().str.strip_chars()


def load_kenpom() -> pl.DataFrame:
    p = RAW_RATINGS / "kenpom_ratings_2016-2026.csv"
    if not p.exists():
        return pl.DataFrame()
    df = pl.read_csv(p)
    if "teamname" not in df.columns or "season" not in df.columns:
        return pl.DataFrame()
    col_lower = {c.lower(): c for c in df.columns}
    adjem_col = col_lower.get("adjem")
    sos_col = col_lower.get("sos")
    df = df.with_columns(
        _norm(pl.col("teamname")).alias("team_norm")
    )
    df = df.select(
        pl.col("season").alias("season"),
        pl.col("team_norm"),
        pl.col(adjem_col).alias("adjem") if adjem_col else pl.lit(None).alias("adjem"),
        pl.col(sos_col).alias("sos_kenpom") if sos_col else pl.lit(None).alias("sos_kenpom"),
    )
    return df.unique(subset=["season", "team_norm"])


def load_torvik() -> pl.DataFrame:
    out = []
    for f in sorted(RAW_RATINGS.glob("barttorvik_*.csv")):
        try:
            year = int(f.stem.split("_")[1])
        except (IndexError, ValueError):
            continue
        df = pl.read_csv(f, truncate_ragged_lines=True)
        if "team" not in df.columns:
            continue
        df = df.select(
            pl.lit(year).alias("season"),
            _norm(pl.col("team")).alias("team_norm"),
            pl.col("adjoe").alias("adjoe") if "adjoe" in df.columns else pl.lit(None).alias("adjoe"),
            pl.col("adjde").alias("adjde") if "adjde" in df.columns else pl.lit(None).alias("adjde"),
            pl.col("barthag").alias("barthag") if "barthag" in df.columns else pl.lit(None).alias("barthag"),
            pl.col("sos").alias("sos_torvik") if "sos" in df.columns else pl.lit(None).alias("sos_torvik"),
        )
        out.append(df)
    if not out:
        return pl.DataFrame()
    return pl.concat(out).unique(subset=["season", "team_norm"])


def load_evanmiya() -> pl.DataFrame:
    out = []
    for f in sorted(RAW_RATINGS.glob("evanmiya_team_ratings_*.csv")):
        try:
            year = int(f.stem.split("_")[-1])
        except (IndexError, ValueError):
            continue
        df = pl.read_csv(f, truncate_ragged_lines=True)
        if "team" not in df.columns:
            continue
        df = df.select(
            pl.lit(year).alias("season"),
            _norm(pl.col("team")).alias("team_norm"),
            pl.col("bpr").alias("bpr") if "bpr" in df.columns else pl.lit(None).alias("bpr"),
        )
        out.append(df)
    if not out:
        return pl.DataFrame()
    return pl.concat(out).unique(subset=["season", "team_norm"])


def main() -> None:
    kp = load_kenpom()
    tv = load_torvik()
    ev = load_evanmiya()

    if kp.is_empty():
        print("No KenPom data found; need kenpom_ratings_2016-2026.csv in data/raw/ratings/")
        return

    full = kp
    if not tv.is_empty():
        full = full.join(
            tv.select(["season", "team_norm", "adjoe", "adjde", "barthag", "sos_torvik"]),
            on=["season", "team_norm"],
            how="left",
        )
    else:
        full = full.with_columns(
            pl.lit(None).alias("adjoe"),
            pl.lit(None).alias("adjde"),
            pl.lit(None).alias("barthag"),
            pl.lit(None).alias("sos_torvik"),
        )
    if not ev.is_empty():
        full = full.join(
            ev.select(["season", "team_norm", "bpr"]),
            on=["season", "team_norm"],
            how="left",
        )
    else:
        full = full.with_columns(pl.lit(None).alias("bpr"))

    full = full.with_columns(
        pl.coalesce(pl.col("sos_kenpom"), pl.col("sos_torvik")).alias("sos")
    ).drop(["sos_kenpom", "sos_torvik"])

    full.write_parquet(FULL_RATINGS_PATH)
    print(f"Wrote {FULL_RATINGS_PATH} with {len(full)} rows (team-season).")


if __name__ == "__main__":
    main()
