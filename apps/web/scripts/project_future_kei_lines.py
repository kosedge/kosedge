"""
Fetch upcoming NCAAM games from The Odds API, join full_ensemble_ratings,
project ensemble spread and total (same model as merge_games_ensemble), write
data/processed/kei_lines_ncaam.json for the KEI Lines page.

Requires: ODDS_API_KEY, full_ensemble_ratings.parquet, ensemble_weights.json (optional).
Run from apps/web: python scripts/project_future_kei_lines.py
"""
import json
import os
import sys
from pathlib import Path

import polars as pl
import requests

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import (
    FULL_ENSEMBLE_RATINGS_PATH,
    PROCESSED,
    ENSEMBLE_WEIGHTS_PATH,
)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
NCAAB_SPORT = "basketball_ncaab"

# Must match merge_games_ensemble for join to ratings
ODDS_TO_RATINGS_ALIASES = {
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


def _load_dotenv() -> None:
    if os.environ.get("ODDS_API_KEY"):
        return
    for name in (".env.local", ".env"):
        p = _WEB / name
        if not p.is_file():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line and line.split("=", 1)[0].strip() == "ODDS_API_KEY":
                    _, _, value = line.partition("=")
                    value = value.strip().strip('"').strip("'")
                    if value:
                        os.environ["ODDS_API_KEY"] = value
                    return


def _normalize_team(s: str) -> str:
    s = (s or "").lower().replace(".", "").replace(" st", " state").replace("uconn", "connecticut").strip()
    return ODDS_TO_RATINGS_ALIASES.get(s, s)


def _odds_team_to_short(full: str) -> str:
    parts = (full or "").split()
    if len(parts) >= 3:
        short = " ".join(parts[:2])
    else:
        short = parts[0] if parts else ""
    return _normalize_team(short)


def _game_season(commence_iso: str) -> int:
    if not commence_iso or len(commence_iso) < 10:
        return 2025
    y = int(commence_iso[:4])
    m = int(commence_iso[5:7])
    return (y + 1) if m >= 11 else y


def fetch_upcoming_events(api_key: str) -> list[dict]:
    url = f"{ODDS_API_BASE}/sports/{NCAAB_SPORT}/odds"
    params = {"regions": "us", "markets": "spreads,totals", "oddsFormat": "american", "apiKey": api_key}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    events = r.json()
    return events if isinstance(events, list) else []


def main() -> None:
    _load_dotenv()
    api_key = (os.environ.get("ODDS_API_KEY") or "").strip()
    if not api_key:
        print("Set ODDS_API_KEY in environment or apps/web/.env.local")
        return

    if not FULL_ENSEMBLE_RATINGS_PATH.exists():
        print(f"Missing {FULL_ENSEMBLE_RATINGS_PATH}. Run build_ensemble_ratings.py first.")
        return

    events = fetch_upcoming_events(api_key)
    now_iso = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    future = [e for e in events if (e.get("commence_time") or "") > now_iso]
    if not future:
        print("No upcoming NCAAM events from Odds API (or all in the past).")
        PROCESSED.mkdir(parents=True, exist_ok=True)
        out_path = PROCESSED / "kei_lines_ncaam.json"
        with open(out_path, "w") as f:
            json.dump({"games": []}, f, indent=2)
        print(f"Wrote {out_path} with 0 games.")
        return

    rows = []
    for e in future:
        rows.append({
            "event_id": e.get("id"),
            "home_team": e.get("home_team", ""),
            "away_team": e.get("away_team", ""),
            "commence_time": e.get("commence_time"),
            "home_team_norm": _odds_team_to_short(e.get("home_team", "")),
            "away_team_norm": _odds_team_to_short(e.get("away_team", "")),
            "season": _game_season(e.get("commence_time", "")),
        })
    odds = pl.DataFrame(rows)

    ratings = pl.read_parquet(FULL_ENSEMBLE_RATINGS_PATH)
    if "year" not in ratings.columns:
        print("full_ensemble_ratings must have a 'year' column.")
        return
    latest_year = int(ratings["year"].max())
    ratings = ratings.filter(pl.col("year") == latest_year).with_columns(pl.lit(latest_year).alias("season"))

    def _safe_col(name: str, alias: str | None = None) -> pl.Expr:
        if name in ratings.columns:
            return pl.col(name).alias(alias or name)
        return pl.lit(None).cast(pl.Float64).alias(alias or name)

    home_ratings = ratings.select([
        pl.col("team_norm").alias("home_team_norm"),
        pl.col("season"),
        _safe_col("adjem"),
        _safe_col("adjoe"),
        _safe_col("adjde"),
        _safe_col("net_torvik"),
        _safe_col("barthag"),
        _safe_col("adjt"),
        _safe_col("bpr"),
        _safe_col("haslam_net"),
    ])
    away_ratings = ratings.select([
        pl.col("team_norm").alias("away_team_norm"),
        pl.col("season"),
        _safe_col("adjem", "adjem_away"),
        _safe_col("adjoe", "adjoe_away"),
        _safe_col("adjde", "adjde_away"),
        _safe_col("net_torvik", "net_torvik_away"),
        _safe_col("barthag", "barthag_away"),
        _safe_col("adjt", "adjt_away"),
        _safe_col("bpr", "bpr_away"),
        _safe_col("haslam_net", "haslam_net_away"),
    ])

    merged = odds.join(home_ratings, on=["home_team_norm", "season"], how="left")
    merged = merged.join(away_ratings, on=["away_team_norm", "season"], how="left")

    # Torvik net diff
    merged = merged.with_columns(
        (pl.col("net_torvik").fill_null(0) - pl.col("net_torvik_away").fill_null(0)).alias("torvik_net_diff")
    )
    # Clip diffs to avoid 30–40 pt blowups from missing/NaN ratings (one team has rating, other NaN)
    SPREAD_DIFF_CLIP = 30.0
    adjem_diff = (pl.col("adjem").fill_null(0) - pl.col("adjem_away").fill_null(0)).clip(-SPREAD_DIFF_CLIP, SPREAD_DIFF_CLIP)
    torvik_diff = pl.col("torvik_net_diff").fill_null(0).clip(-SPREAD_DIFF_CLIP, SPREAD_DIFF_CLIP)
    bpr_diff = (pl.col("bpr").fill_null(0) - pl.col("bpr_away").fill_null(0)).clip(-SPREAD_DIFF_CLIP, SPREAD_DIFF_CLIP)
    # barthag is 0–1; *20 → 0–20 pts; clip the scaled diff to be safe
    barthag_diff = ((pl.col("barthag").fill_null(0) - pl.col("barthag_away").fill_null(0)) * 20).clip(-SPREAD_DIFF_CLIP, SPREAD_DIFF_CLIP)
    haslam_diff = (
        (pl.col("haslam_net").fill_null(0) - pl.col("haslam_net_away").fill_null(0)).clip(-SPREAD_DIFF_CLIP, SPREAD_DIFF_CLIP)
        if "haslam_net" in merged.columns and "haslam_net_away" in merged.columns
        else pl.lit(0.0)
    )

    w_adjem, w_torvik, w_barthag, w_bpr, w_haslam, home_court = 0.40, 0.30, 0.15, 0.10, 0.05, 3.75
    if ENSEMBLE_WEIGHTS_PATH.exists():
        try:
            with open(ENSEMBLE_WEIGHTS_PATH) as f:
                w = json.load(f)
            w_adjem = w.get("adjem", w_adjem)
            w_torvik = w.get("torvik", w_torvik)
            w_barthag = w.get("barthag", w_barthag)
            w_bpr = w.get("bpr", w_bpr)
            w_haslam = w.get("haslam", w_haslam)
            home_court = w.get("home_court", home_court)
        except Exception:
            pass

    raw_spread = (
        w_adjem * adjem_diff
        + w_torvik * torvik_diff
        + w_barthag * barthag_diff
        + w_bpr * bpr_diff
        + w_haslam * haslam_diff
        + home_court
    )
    # Cap final spread to sane range (e.g. 1–20 pts typical; allow -28 to +28)
    merged = merged.with_columns(raw_spread.clip(-28.0, 28.0).alias("ensemble_spread"))

    if all(c in merged.columns for c in ("adjt", "adjt_away", "adjoe", "adjde", "adjoe_away", "adjde_away")):
        pace = (pl.col("adjt").fill_null(70) + pl.col("adjt_away").fill_null(70)) / 2.0
        pts = (
            pl.col("adjoe").fill_null(100) + pl.col("adjde_away").fill_null(100)
            + pl.col("adjoe_away").fill_null(100) + pl.col("adjde").fill_null(100)
        )
        merged = merged.with_columns((pace / 100.0 * pts / 2.0).alias("ensemble_total"))
    else:
        merged = merged.with_columns(pl.lit(None).cast(pl.Float64).alias("ensemble_total"))

    merged = merged.sort("commence_time")

    games = []
    for r in merged.iter_rows(named=True):
        games.append({
            "id": r.get("event_id"),
            "homeTeam": r.get("home_team") or "",
            "awayTeam": r.get("away_team") or "",
            "commenceTime": r.get("commence_time"),
            "projSpreadHome": round(r["ensemble_spread"], 2) if r.get("ensemble_spread") is not None else None,
            "projTotal": round(r["ensemble_total"], 2) if r.get("ensemble_total") is not None else None,
        })

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED / "kei_lines_ncaam.json"
    with open(out_path, "w") as f:
        json.dump({"games": games}, f, indent=2)
    print(f"Wrote {out_path} with {len(games)} upcoming games (ratings year={latest_year}).")


if __name__ == "__main__":
    main()
