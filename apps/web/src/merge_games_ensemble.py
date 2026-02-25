"""
Merge odds + full_ensemble_ratings: join home/away ratings, compute KenPom spread,
Torvik net diff, ensemble spread (40% KenPom, 40% Torvik, 20% Evan), edge flags, optional backtest.
Requires: full_ensemble_ratings.parquet, ncaab_historical_odds_open_close.parquet.
Optional: actual_margins.parquet or data/raw/games/results.csv for backtest.
Run from apps/web: python src/merge_games_ensemble.py
"""
import sys
from pathlib import Path
from typing import Optional

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import (
    FULL_ENSEMBLE_RATINGS_PATH,
    ODDS_PARQUET_PATH,
    ACTUAL_MARGINS_PATH,
    MERGED_GAMES_PATH,
    RAW_GAMES,
    PROCESSED,
    INJURY_PATH,
    KENPOM_ARCHIVE_PATH,
    KENPOM_SNAPSHOTS_DIR,
    TORVIK_SNAPSHOTS_DIR,
    ENSEMBLE_WEIGHTS_PATH,
)


def normalize_team(col_expr: pl.Expr) -> pl.Expr:
    """Must match build_ensemble_ratings."""
    return (
        col_expr.str.to_lowercase()
        .str.replace_all(r"\.", "")
        .str.replace_all(" st", " state")
        .str.replace_all("uconn", "connecticut")
        .str.strip_chars()
    )


ODDS_TO_RATINGS_ALIASES: dict[str, str] = {
    "unc": "north carolina",
    "lsu": "louisiana state",
    "usc": "southern california",
    "ole miss": "mississippi",
    "unlv": "nevada las vegas",
    "vcu": "virginia commonwealth",
    "smu": "southern methodist",
    "tcu": "texas christian",
    "wku": "western kentucky",
    "utsa": "texas san antonio",
    "unm": "new mexico",
}


def odds_team_to_short(col_expr: pl.Expr) -> pl.Expr:
    """Odds use 'Purdue Boilermakers'; ratings use 'purdue'. Derive short name for join."""
    parts = col_expr.str.split(" ")
    short = pl.when(parts.list.len() >= 3).then(parts.list.head(2).list.join(" ")).otherwise(parts.list.get(0))
    normed = normalize_team(short)
    result: pl.Expr = normed
    for odds_val, ratings_val in ODDS_TO_RATINGS_ALIASES.items():
        result = pl.when(result == odds_val).then(pl.lit(ratings_val)).otherwise(result)
    return result


def game_season(commence_expr: pl.Expr) -> pl.Expr:
    date_str = commence_expr.str.slice(0, 10)
    dt = date_str.str.to_datetime(format="%Y-%m-%d")
    year = dt.dt.year()
    month = dt.dt.month()
    return pl.when(month >= 11).then(year + 1).otherwise(year).alias("season")


def _build_archive_from_snapshots(snapshot_dir: Path, prefix: str, date_col: str = "as_of_date") -> Optional[pl.DataFrame]:
    """Load all prefix_YYYY-MM-DD.parquet files, concat into one table with date column for join_asof."""
    if not snapshot_dir.exists():
        return None
    files = sorted(snapshot_dir.glob(f"{prefix}_*.parquet"))
    if not files:
        return None
    out = []
    for f in files:
        try:
            date_str = f.stem.replace(f"{prefix}_", "")
            df = pl.read_parquet(f)
            if "snapshot_date" in df.columns:
                df = df.with_columns(pl.col("snapshot_date").str.to_date(strict=False).alias(date_col))
            else:
                df = df.with_columns(pl.lit(date_str).str.to_date(strict=False).alias(date_col))
            out.append(df)
        except Exception:
            continue
    if not out:
        return None
    combined = pl.concat(out, how="diagonal_relaxed").unique()
    return combined.sort("team_norm", date_col)


def main() -> None:
    if not FULL_ENSEMBLE_RATINGS_PATH.exists():
        print(f"Run build_ensemble_ratings.py first. Missing {FULL_ENSEMBLE_RATINGS_PATH}")
        return
    if not ODDS_PARQUET_PATH.exists():
        print(f"Run process_odds.py first. Missing {ODDS_PARQUET_PATH}")
        return

    ratings = pl.read_parquet(FULL_ENSEMBLE_RATINGS_PATH)
    odds = pl.read_parquet(ODDS_PARQUET_PATH)

    # Consensus close lines (mean across books) — reduces noise vs single book
    consensus = odds.group_by("event_id").agg(
        pl.col("close_spread_home").mean().alias("consensus_close_spread"),
        pl.col("close_total").mean().alias("consensus_close_total"),
    )
    odds_first = odds.unique(subset="event_id", keep="first")
    odds = odds_first.join(consensus, on="event_id")
    print(f"Consensus close (mean across books) for {len(odds):,} unique events.")

    odds = odds.with_columns([
        odds_team_to_short(pl.col("home_team")).alias("home_team_norm"),
        odds_team_to_short(pl.col("away_team")).alias("away_team_norm"),
        game_season(pl.col("commence_time")),
        pl.col("commence_time").str.slice(0, 10).str.to_date(strict=False).alias("game_date"),
    ])

    use_archive = False
    kenpom_snap = _build_archive_from_snapshots(KENPOM_SNAPSHOTS_DIR, "kenpom")
    if kenpom_snap is not None and "team_norm" in kenpom_snap.columns and "adjem" in kenpom_snap.columns:
        try:
            arch = kenpom_snap.sort("team_norm", "as_of_date")
            arch_h = arch.select([
                pl.col("team_norm"), pl.col("as_of_date"),
                pl.col("adjem").alias("adjem_h"), pl.col("adjoe").alias("adjoe_h") if "adjoe" in arch.columns else pl.lit(None).alias("adjoe_h"),
                pl.col("adjde").alias("adjde_h") if "adjde" in arch.columns else pl.lit(None).alias("adjde_h"),
                pl.col("adjt").alias("adjt_h") if "adjt" in arch.columns else pl.lit(None).alias("adjt_h"),
            ])
            arch_a = arch.select([
                pl.col("team_norm"), pl.col("as_of_date"),
                pl.col("adjem").alias("adjem_away"), pl.col("adjoe").alias("adjoe_away") if "adjoe" in arch.columns else pl.lit(None).alias("adjoe_away"),
                pl.col("adjde").alias("adjde_away") if "adjde" in arch.columns else pl.lit(None).alias("adjde_away"),
                pl.col("adjt").alias("adjt_away") if "adjt" in arch.columns else pl.lit(None).alias("adjt_away"),
            ])
            odds = odds.join_asof(
                arch_h,
                left_on="game_date", right_on="as_of_date",
                by_left="home_team_norm", by_right="team_norm", strategy="backward"
            ).join_asof(
                arch_a,
                left_on="game_date", right_on="as_of_date",
                by_left="away_team_norm", by_right="team_norm", strategy="backward"
            )
            odds = odds.rename({"adjem_h": "adjem", "adjoe_h": "adjoe", "adjde_h": "adjde", "adjt_h": "adjt"})
            drop_cols = [c for c in ("as_of_date", "as_of_date_right") if c in odds.columns]
            if drop_cols:
                odds = odds.drop(drop_cols)
            odds = odds.with_columns([
                pl.lit(None).cast(pl.Float64).alias("net_torvik"), pl.lit(None).cast(pl.Float64).alias("net_torvik_away"),
                pl.lit(None).cast(pl.Float64).alias("barthag"), pl.lit(None).cast(pl.Float64).alias("barthag_away"),
                pl.lit(None).cast(pl.Float64).alias("bpr"), pl.lit(None).cast(pl.Float64).alias("bpr_away"),
            ])
            use_archive = True
            print("Using KenPom weekly snapshots (rolling ratings) for ratings.")
        except Exception as e:
            print("KenPom snapshots load failed:", e)

    if not use_archive and KENPOM_ARCHIVE_PATH.exists():
        try:
            arch = pl.read_parquet(KENPOM_ARCHIVE_PATH).sort("team_norm", "as_of_date")
            if "as_of_date" in arch.columns and "team_norm" in arch.columns and "adjem" in arch.columns:
                arch_h = arch.select([
                    pl.col("team_norm"), pl.col("as_of_date"),
                    pl.col("adjem").alias("adjem_h"), pl.col("adjoe").alias("adjoe_h") if "adjoe" in arch.columns else pl.lit(None).alias("adjoe_h"),
                    pl.col("adjde").alias("adjde_h") if "adjde" in arch.columns else pl.lit(None).alias("adjde_h"),
                    pl.col("adjt").alias("adjt_h") if "adjt" in arch.columns else pl.lit(None).alias("adjt_h"),
                ])
                arch_a = arch.select([
                    pl.col("team_norm"), pl.col("as_of_date"),
                    pl.col("adjem").alias("adjem_away"), pl.col("adjoe").alias("adjoe_away") if "adjoe" in arch.columns else pl.lit(None).alias("adjoe_away"),
                    pl.col("adjde").alias("adjde_away") if "adjde" in arch.columns else pl.lit(None).alias("adjde_away"),
                    pl.col("adjt").alias("adjt_away") if "adjt" in arch.columns else pl.lit(None).alias("adjt_away"),
                ])
                odds = odds.join_asof(
                    arch_h,
                    left_on="game_date", right_on="as_of_date",
                    by_left="home_team_norm", by_right="team_norm", strategy="backward"
                ).join_asof(
                    arch_a,
                    left_on="game_date", right_on="as_of_date",
                    by_left="away_team_norm", by_right="team_norm", strategy="backward"
                )
                odds = odds.rename({"adjem_h": "adjem", "adjoe_h": "adjoe", "adjde_h": "adjde", "adjt_h": "adjt"})
                drop_cols = [c for c in ("as_of_date", "as_of_date_right") if c in odds.columns]
                if drop_cols:
                    odds = odds.drop(drop_cols)
                odds = odds.with_columns([
                    pl.lit(None).cast(pl.Float64).alias("net_torvik"), pl.lit(None).cast(pl.Float64).alias("net_torvik_away"),
                    pl.lit(None).cast(pl.Float64).alias("barthag"), pl.lit(None).cast(pl.Float64).alias("barthag_away"),
                    pl.lit(None).cast(pl.Float64).alias("bpr"), pl.lit(None).cast(pl.Float64).alias("bpr_away"),
                ])
                use_archive = True
                print("Using KenPom as-of-date archive for ratings.")
        except Exception as e:
            print("Archive load failed:", e)

    if not use_archive:
        ratings = ratings.with_columns(pl.col("year").alias("season"))
        home_cols = [
            pl.col("team_norm").alias("home_team_norm"),
            pl.col("season"),
            pl.col("adjem"),
            pl.col("sos"),
            pl.col("adjoe"),
            pl.col("adjde"),
            pl.col("net_torvik"),
            pl.col("barthag"),
            pl.col("adjt"),
            pl.col("bpr"),
            pl.col("obpr"),
            pl.col("dbpr"),
        ]
        away_cols = [
            pl.col("team_norm").alias("away_team_norm"),
            pl.col("season"),
            pl.col("adjem").alias("adjem_away"),
            pl.col("sos").alias("sos_away"),
            pl.col("adjoe").alias("adjoe_away"),
            pl.col("adjde").alias("adjde_away"),
            pl.col("net_torvik").alias("net_torvik_away"),
            pl.col("barthag").alias("barthag_away"),
            pl.col("adjt").alias("adjt_away"),
            pl.col("bpr").alias("bpr_away"),
        ]
        if "haslam_net" in ratings.columns:
            home_cols.append(pl.col("haslam_net"))
            away_cols.append(pl.col("haslam_net").alias("haslam_net_away"))
        if "dratings_rating" in ratings.columns:
            home_cols.append(pl.col("dratings_rating"))
            away_cols.append(pl.col("dratings_rating").alias("dratings_rating_away"))
        home_ratings = ratings.select(home_cols)
        away_ratings = ratings.select(away_cols)
        merged = odds.join(home_ratings, on=["home_team_norm", "season"], how="left")
        merged = merged.join(away_ratings, on=["away_team_norm", "season"], how="left")
    else:
        merged = odds

    # Optional: fill Torvik from weekly snapshots when using rolling KenPom
    if use_archive and (torvik_snap := _build_archive_from_snapshots(TORVIK_SNAPSHOTS_DIR, "torvik")) is not None:
        if "team_norm" in torvik_snap.columns and "game_date" in merged.columns:
            try:
                tv = torvik_snap.sort("team_norm", "as_of_date")
                need = ["net_torvik", "barthag"]
                cols = ["team_norm", "as_of_date"] + [c for c in need if c in tv.columns]
                if len(cols) > 2:
                    for c in need:
                        if c in merged.columns:
                            merged = merged.drop(c)
                        if f"{c}_away" in merged.columns:
                            merged = merged.drop(f"{c}_away")
                    tv_h = tv.select(cols).rename({c: f"{c}_h" for c in need if c in tv.columns})
                    tv_a = tv.select(cols).rename({c: f"{c}_away" for c in need if c in tv.columns})
                    merged = merged.join_asof(
                        tv_h,
                        left_on="game_date", right_on="as_of_date",
                        by_left="home_team_norm", by_right="team_norm", strategy="backward",
                    ).join_asof(
                        tv_a,
                        left_on="game_date", right_on="as_of_date",
                        by_left="away_team_norm", by_right="team_norm", strategy="backward",
                    )
                    merged = merged.rename({f"{c}_h": c for c in need if f"{c}_h" in merged.columns})
                    merged = merged.drop([c for c in ("as_of_date", "as_of_date_right") if c in merged.columns])
                    print("Using Torvik weekly snapshots (rolling) for net_torvik/barthag.")
            except Exception as e:
                print("Torvik snapshots join failed:", e)

    # KenPom spread (adjem diff + home court +3)
    merged = merged.with_columns(
        (pl.col("adjem") - pl.col("adjem_away").fill_null(0) + 3.0).alias("kenpom_spread")
    )
    # Torvik net diff (we add home court once in ensemble)
    merged = merged.with_columns(
        (pl.col("net_torvik").fill_null(0) - pl.col("net_torvik_away").fill_null(0)).alias("torvik_net_diff")
    )
    # Ensemble: use estimated weights when present, else default (KenPom/Torvik heavy).
    adjem_diff = pl.col("adjem").fill_null(0) - pl.col("adjem_away").fill_null(0)
    torvik_diff = pl.col("torvik_net_diff").fill_null(0)
    bpr_diff = pl.col("bpr").fill_null(0) - pl.col("bpr_away").fill_null(0)
    barthag_diff = (pl.col("barthag").fill_null(0) - pl.col("barthag_away").fill_null(0)) * 20
    haslam_diff = (pl.col("haslam_net").fill_null(0) - pl.col("haslam_net_away").fill_null(0)) if "haslam_net" in merged.columns else pl.lit(0.0)

    w_adjem, w_torvik, w_barthag, w_bpr, w_haslam, home_court = 0.40, 0.30, 0.15, 0.10, 0.05, 3.75
    if ENSEMBLE_WEIGHTS_PATH.exists():
        try:
            import json
            with open(ENSEMBLE_WEIGHTS_PATH) as f:
                w = json.load(f)
            w_adjem = w.get("adjem", w_adjem)
            w_torvik = w.get("torvik", w_torvik)
            w_barthag = w.get("barthag", w_barthag)
            w_bpr = w.get("bpr", w_bpr)
            w_haslam = w.get("haslam", w_haslam)
            home_court = w.get("home_court", home_court)
            print("Using estimated ensemble weights from", ENSEMBLE_WEIGHTS_PATH.name)
        except Exception as e:
            print("Could not load ensemble weights:", e)
    merged = merged.with_columns(
        (
            w_adjem * adjem_diff
            + w_torvik * torvik_diff
            + w_barthag * barthag_diff
            + w_bpr * bpr_diff
            + w_haslam * haslam_diff
            + home_court
        ).alias("ensemble_spread")
    )

    # Edge: use consensus line. Bet home when model > line; bet away when line > model.
    line_col = "consensus_close_spread"
    merged = merged.with_columns([
        (pl.col("ensemble_spread") - pl.col(line_col)).alias("spread_edge"),
        (pl.col("ensemble_spread") - pl.col(line_col) > 4).alias("edge_home"),
        (pl.col(line_col) - pl.col("ensemble_spread") > 4).alias("edge_away"),
    ])

    # Tempo/matchup: |adjt_home - adjt_away|; optional filter for similar pace (e.g. < 10)
    if "adjt" in merged.columns and "adjt_away" in merged.columns:
        merged = merged.with_columns(
            (pl.col("adjt").fill_null(0) - pl.col("adjt_away").fill_null(0)).abs().alias("tempo_diff")
        )
    else:
        merged = merged.with_columns(pl.lit(None).cast(pl.Float64).alias("tempo_diff"))

    # Ensemble total (KenPom-style: pace/100 * (off+def for both sides))
    if all(c in merged.columns for c in ("adjt", "adjt_away", "adjoe", "adjde", "adjoe_away", "adjde_away")):
        pace = (pl.col("adjt").fill_null(70) + pl.col("adjt_away").fill_null(70)) / 2.0
        pts_per_100 = (pl.col("adjoe").fill_null(100) + pl.col("adjde_away").fill_null(100)
                        + pl.col("adjoe_away").fill_null(100) + pl.col("adjde").fill_null(100))
        merged = merged.with_columns(
            (pace / 100.0 * pts_per_100 / 2.0).alias("ensemble_total")
        )
        merged = merged.with_columns(
            (pl.col("ensemble_total") - pl.col("consensus_close_total")).alias("total_edge")
        )
    else:
        merged = merged.with_columns([
            pl.lit(None).cast(pl.Float64).alias("ensemble_total"),
            pl.lit(None).cast(pl.Float64).alias("total_edge"),
        ])

    # EV: model win prob (logistic in spread edge) vs implied (logistic in line). +EV when model > implied.
    # k ~ 0.15: ~50% at 0, ~73% at 5pt edge
    _k = 0.15
    merged = merged.with_columns(
        (1.0 / (1.0 + (pl.lit(-_k) * pl.col("spread_edge")).exp())).alias("model_win_prob_home")
    )
    merged = merged.with_columns(
        (1.0 / (1.0 + (pl.lit(-_k) * pl.col(line_col)).exp())).alias("implied_prob_home")
    )
    merged = merged.with_columns(
        (pl.col("model_win_prob_home") > pl.col("implied_prob_home")).alias("ev_positive_home")
    )
    merged = merged.with_columns(
        ((1.0 - pl.col("model_win_prob_home")) > (1.0 - pl.col("implied_prob_home"))).alias("ev_positive_away")
    )

    # Rest/travel: join from build_rest_travel.py output when available
    rest_travel_path = PROCESSED / "rest_travel.parquet"
    if rest_travel_path.exists():
        rt = pl.read_parquet(rest_travel_path)
        game_date = pl.col("commence_time").str.slice(0, 10).str.to_date(strict=False)
        merged = merged.with_columns(game_date.alias("game_date"))
        merged = merged.join(
            rt.select(["home_team_norm", "away_team_norm", "game_date", "days_rest_home", "days_rest_away", "travel_miles_away"]),
            on=["home_team_norm", "away_team_norm", "game_date"],
            how="left",
        )
    else:
        merged = merged.with_columns([
            pl.lit(None).cast(pl.Int32).alias("days_rest_home"),
            pl.lit(None).cast(pl.Int32).alias("days_rest_away"),
            pl.lit(None).cast(pl.Float64).alias("travel_miles_away"),
        ])
    # Injury: join from injury.parquet when available (event_id, key_player_out_home, key_player_out_away)
    merged = merged.with_columns([
        pl.lit(None).cast(pl.Boolean).alias("key_player_out_home"),
        pl.lit(None).cast(pl.Boolean).alias("key_player_out_away"),
    ])
    if INJURY_PATH.exists():
        try:
            inj = pl.read_parquet(INJURY_PATH)
            if "event_id" in inj.columns and "key_player_out_home" in inj.columns and "key_player_out_away" in inj.columns:
                merged = merged.drop(["key_player_out_home", "key_player_out_away"]).join(
                    inj.select(["event_id", "key_player_out_home", "key_player_out_away"]),
                    on="event_id", how="left",
                )
        except Exception:
            pass

    # Optional actual margin and total for backtest (prefer results.csv when it has home_pts/away_pts for actual_total)
    actual = None
    results_csv = RAW_GAMES / "results.csv"
    if results_csv.exists():
        df = pl.read_csv(results_csv)
        if "event_id" in df.columns and "home_pts" in df.columns and "away_pts" in df.columns:
            actual = df.with_columns([
                (pl.col("home_pts") - pl.col("away_pts")).alias("actual_margin"),
                (pl.col("home_pts") + pl.col("away_pts")).alias("actual_total"),
            ]).select(["event_id", "actual_margin", "actual_total"])
    if actual is None and ACTUAL_MARGINS_PATH.exists():
        actual = pl.read_parquet(ACTUAL_MARGINS_PATH)
    elif actual is None and results_csv.exists():
        df = pl.read_csv(results_csv)
        if "event_id" in df.columns and "actual_margin" in df.columns:
            actual = df.select(["event_id", "actual_margin"])
            if "actual_total" in df.columns:
                actual = actual.join(df.select(["event_id", "actual_total"]), on="event_id", how="left")

    if actual is not None and "event_id" in actual.columns:
        actual_cols = ["event_id", "actual_margin"] + (["actual_total"] if "actual_total" in actual.columns else [])
        merged = merged.join(actual.select(actual_cols), on="event_id", how="left")
        if "actual_total" not in merged.columns:
            merged = merged.with_columns(pl.lit(None).cast(pl.Float64).alias("actual_total"))
        merged = merged.with_columns(
            (pl.col("actual_margin") + pl.col("consensus_close_spread") > 0).alias("home_cover")
        )
        # Units: if we bet home (edge_home), +1 when home_cover else -1; if we bet away (edge_away), +1 when not home_cover else -1
        merged = merged.with_columns(
            pl.when(pl.col("edge_home"))
            .then(pl.when(pl.col("home_cover")).then(1.0).otherwise(-1.0))
            .when(pl.col("edge_away"))
            .then(pl.when(pl.col("home_cover")).then(-1.0).otherwise(1.0))
            .otherwise(pl.lit(None))
            .alias("units")
        )
        backtest = merged.filter(
            (pl.col("edge_home") | pl.col("edge_away")) & pl.col("actual_margin").is_not_null()
        )
        if not backtest.is_empty():
            backtest = backtest.unique(subset=["event_id"], keep="first")
            summary = backtest.group_by("season").agg([
                pl.col("home_cover").mean().alias("ats_pct"),
                pl.col("units").sum().alias("total_units"),
                pl.len().alias("n_bets"),
            ])
            print("Backtest (edge > 4 pts) by season, one row per game:")
            print(summary)
    else:
        merged = merged.with_columns(pl.lit(None).cast(pl.Float64).alias("actual_margin"))
        print("No actual_margin; run build_actual_margins.py or add data/raw/games/results.csv for backtest.")

    merged.write_parquet(MERGED_GAMES_PATH)
    print(f"Wrote {MERGED_GAMES_PATH} with {len(merged)} rows.")


if __name__ == "__main__":
    main()
