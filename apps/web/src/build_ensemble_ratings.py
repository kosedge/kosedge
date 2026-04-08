"""
Build full_ensemble_ratings.parquet: one row per (year, team_norm) with KenPom, Torvik, Evan.
Stronger team normalization for matching odds (st -> state, uconn -> connecticut).
Run from apps/web: python src/build_ensemble_ratings.py
"""
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_RATINGS, FULL_ENSEMBLE_RATINGS_PATH, ensure_dirs

ensure_dirs()


def normalize_team(col_expr: pl.Expr) -> pl.Expr:
    """Match odds team names: lowercase, strip, st->state, uconn->connecticut, remove dots."""
    return (
        col_expr.str.to_lowercase()
        .str.replace_all(r"\.", "")
        .str.replace_all(" st", " state")
        .str.replace_all("uconn", "connecticut")
        .str.strip_chars()
    )


def load_kenpom() -> pl.DataFrame:
    p = RAW_RATINGS / "kenpom_ratings_2016-2026.csv"
    if not p.exists():
        return pl.DataFrame()
    df = pl.read_csv(p)
    if "teamname" not in df.columns or "season" not in df.columns:
        return pl.DataFrame()
    sel = [
        pl.col("season").cast(pl.Int32).alias("year"),
        normalize_team(pl.col("teamname")).alias("team_norm"),
        pl.col("adjem").alias("adjem") if "adjem" in df.columns else pl.lit(None).alias("adjem"),
        pl.col("sos").alias("sos") if "sos" in df.columns else pl.lit(None).alias("sos"),
    ]
    # Optional: tempo/eff for totals (KenPom uses AdjOE, AdjDE, AdjT or AdjTempo)
    kp_oe = "AdjOE" if "AdjOE" in df.columns else ("adjoe" if "adjoe" in df.columns else None)
    kp_de = "AdjDE" if "AdjDE" in df.columns else ("adjde" if "adjde" in df.columns else None)
    kp_t = "AdjT" if "AdjT" in df.columns else ("AdjTempo" if "AdjTempo" in df.columns else ("adjt" if "adjt" in df.columns else None))
    if kp_oe:
        sel.append(pl.col(kp_oe).cast(pl.Float64).alias("adjoe_kp"))
    else:
        sel.append(pl.lit(None).cast(pl.Float64).alias("adjoe_kp"))
    if kp_de:
        sel.append(pl.col(kp_de).cast(pl.Float64).alias("adjde_kp"))
    else:
        sel.append(pl.lit(None).cast(pl.Float64).alias("adjde_kp"))
    if kp_t:
        sel.append(pl.col(kp_t).cast(pl.Float64).alias("adjt_kp"))
    else:
        sel.append(pl.lit(None).cast(pl.Float64).alias("adjt_kp"))
    df = df.select(sel)
    return df.unique(subset=["year", "team_norm"])


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
        sel = [
            pl.lit(year).alias("year"),
            normalize_team(pl.col("team")).alias("team_norm"),
        ]
        for col, name in [("adjoe", "adjoe"), ("adjde", "adjde"), ("barthag", "barthag"), ("adjt", "adjt")]:
            if col in df.columns:
                sel.append(pl.col(col).cast(pl.Float64).alias(name))
            else:
                sel.append(pl.lit(None).cast(pl.Float64).alias(name))
        if "adjoe" in df.columns and "adjde" in df.columns:
            sel.append((pl.col("adjoe") - pl.col("adjde")).alias("net_torvik"))
        else:
            sel.append(pl.lit(None).cast(pl.Float64).alias("net_torvik"))
        df = df.select(sel)
        out.append(df)
    if not out:
        return pl.DataFrame()
    return pl.concat(out).unique(subset=["year", "team_norm"])


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
            pl.lit(year).alias("year"),
            normalize_team(pl.col("team")).alias("team_norm"),
            pl.col("bpr").alias("bpr") if "bpr" in df.columns else pl.lit(None).alias("bpr"),
            pl.col("obpr").alias("obpr") if "obpr" in df.columns else pl.lit(None).alias("obpr"),
            pl.col("dbpr").alias("dbpr") if "dbpr" in df.columns else pl.lit(None).alias("dbpr"),
        )
        out.append(df)
    if not out:
        return pl.DataFrame()
    return pl.concat(out).unique(subset=["year", "team_norm"])


def load_haslametrics() -> pl.DataFrame:
    """Optional: offense - defense per team-year. Returns empty if files missing or unparseable."""
    out = []
    for year in range(2016, 2027):
        off_path = RAW_RATINGS / f"haslametrics_offense_{year}.csv"
        def_path = RAW_RATINGS / f"haslametrics_defense_{year}.csv"
        if not off_path.exists() or not def_path.exists():
            continue
        try:
            off = pl.read_csv(off_path, truncate_ragged_lines=True, infer_schema_length=100)
            def_ = pl.read_csv(def_path, truncate_ragged_lines=True, infer_schema_length=100)
            # Find team column (first string or name containing team/school)
            team_col = None
            for c in off.columns:
                if c and str(c).lower() in ("team", "school", "name", "teamname"):
                    team_col = c
                    break
            if team_col is None and len(off.columns) >= 1:
                team_col = off.columns[0]
            if team_col is None:
                continue
            # Find numeric rating column
            num_cols = [c for c in off.columns if off[c].dtype in (pl.Float64, pl.Int64) and c != "year"]
            if not num_cols:
                continue
            off_rating = num_cols[0]
            off = off.select(
                pl.col(team_col).alias("team_raw"),
                pl.col(off_rating).alias("off"),
            ).with_columns(normalize_team(pl.col("team_raw")).alias("team_norm")).select(pl.lit(year).alias("year"), pl.col("team_norm"), pl.col("off"))
            num_cols_d = [c for c in def_.columns if def_[c].dtype in (pl.Float64, pl.Int64) and c != "year"]
            if not num_cols_d:
                continue
            def_ = def_.select(pl.col(def_.columns[0]).alias("team_raw"), pl.col(num_cols_d[0]).alias("def_")).with_columns(normalize_team(pl.col("team_raw")).alias("team_norm")).select(pl.col("team_norm"), pl.col("def_"))
            combined = off.join(def_, on="team_norm", how="inner").with_columns((pl.col("off") - pl.col("def_")).alias("haslam_net")).select(pl.lit(year).alias("year"), pl.col("team_norm"), pl.col("haslam_net"))
            out.append(combined)
        except Exception:
            continue
    if not out:
        return pl.DataFrame()
    return pl.concat(out).unique(subset=["year", "team_norm"])


def load_dratings() -> pl.DataFrame:
    """Optional: D-Ratings rating per team-year. Returns empty if files missing or unparseable."""
    out = []
    for f in sorted(RAW_RATINGS.glob("dratings_ratings_*.csv")):
        try:
            year = int(f.stem.split("_")[-1])
        except (IndexError, ValueError):
            continue
        try:
            df = pl.read_csv(f, truncate_ragged_lines=True)
            if len(df.columns) < 2:
                continue
            team_col = df.columns[0]
            rating_col = None
            for c in df.columns[1:]:
                if df[c].dtype in (pl.Float64, pl.Int64):
                    rating_col = c
                    break
            if rating_col is None:
                continue
            df = df.select(
                pl.lit(year).alias("year"),
                normalize_team(pl.col(team_col).cast(pl.Utf8)).alias("team_norm"),
                pl.col(rating_col).cast(pl.Float64).alias("dratings_rating"),
            )
            out.append(df)
        except Exception:
            continue
    if not out:
        return pl.DataFrame()
    return pl.concat(out).unique(subset=["year", "team_norm"])


def map_dratings_to_kenpom(dratings: pl.DataFrame, kp: pl.DataFrame) -> pl.DataFrame:
    """Map D-Ratings (long names like 'michigan wolverines') to KenPom team_norm (e.g. 'michigan').
    Uses longest-prefix match so 'north carolina tar heels' -> 'north carolina' not 'north'."""
    kp_teams = (
        kp.select(["year", "team_norm"])
        .unique()
        .rename({"team_norm": "kp_norm"})
        .with_columns(pl.col("kp_norm").str.len_chars().alias("_len"))
    )
    expanded = dratings.join(kp_teams, on="year", how="left")
    matched = expanded.filter(
        (pl.col("team_norm") == pl.col("kp_norm"))
        | (pl.col("team_norm").str.starts_with(pl.col("kp_norm") + " "))
    )
    # Longest kp_norm wins per (year, dratings team_norm), then one row per (year, kp_norm)
    matched = (
        matched.sort("_len", descending=True)
        .unique(subset=["year", "kp_norm"], keep="first")
        .select(["year", pl.col("kp_norm").alias("team_norm"), "dratings_rating"])
    )
    return matched


def main() -> None:
    kp = load_kenpom()
    if kp.is_empty():
        print("No KenPom data; need kenpom_ratings_2016-2026.csv")
        return

    # Start from KenPom, join Torvik then Evan (one row per team-year, all source columns)
    full = kp
    tv = load_torvik()
    if not tv.is_empty():
        full = full.join(
            tv.select(["year", "team_norm", "adjoe", "adjde", "net_torvik", "barthag", "adjt"]),
            on=["year", "team_norm"],
            how="left",
        )
    else:
        full = full.with_columns(
            pl.lit(None).alias("adjoe"),
            pl.lit(None).alias("adjde"),
            pl.lit(None).alias("net_torvik"),
            pl.lit(None).alias("barthag"),
            pl.lit(None).alias("adjt"),
        )
    # Fill tempo/eff from KenPom when Torvik is null (so totals can vary)
    if "adjoe_kp" in full.columns:
        full = full.with_columns(
            pl.coalesce(pl.col("adjoe"), pl.col("adjoe_kp")).alias("adjoe"),
            pl.coalesce(pl.col("adjde"), pl.col("adjde_kp")).alias("adjde"),
            pl.coalesce(pl.col("adjt"), pl.col("adjt_kp")).alias("adjt"),
        ).drop(["adjoe_kp", "adjde_kp", "adjt_kp"])
    ev = load_evanmiya()
    if not ev.is_empty():
        full = full.join(
            ev.select(["year", "team_norm", "bpr", "obpr", "dbpr"]),
            on=["year", "team_norm"],
            how="left",
        )
    else:
        full = full.with_columns(
            pl.lit(None).alias("bpr"),
            pl.lit(None).alias("obpr"),
            pl.lit(None).alias("dbpr"),
        )

    haslam = load_haslametrics()
    if not haslam.is_empty():
        full = full.join(haslam.select(["year", "team_norm", "haslam_net"]), on=["year", "team_norm"], how="left")
        print(f"Joined Haslametrics: {full['haslam_net'].drop_nulls().len()} non-null")
    else:
        full = full.with_columns(pl.lit(None).alias("haslam_net"))

    dratings = load_dratings()
    if not dratings.is_empty():
        dratings_mapped = map_dratings_to_kenpom(dratings, kp)
        full = full.join(dratings_mapped.select(["year", "team_norm", "dratings_rating"]), on=["year", "team_norm"], how="left")
        print(f"Joined D-Ratings: {full['dratings_rating'].drop_nulls().len()} non-null")
    else:
        full = full.with_columns(pl.lit(None).alias("dratings_rating"))

    full.write_parquet(FULL_ENSEMBLE_RATINGS_PATH)
    print(f"Wrote {FULL_ENSEMBLE_RATINGS_PATH} with {len(full)} rows (team-year, KenPom + Torvik + Evan).")


if __name__ == "__main__":
    main()
