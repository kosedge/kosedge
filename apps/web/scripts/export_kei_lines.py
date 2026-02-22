"""
Export KEI lines (projected spread + O/U) for the web app.
Reads merged_games_with_odds_and_ratings.parquet, writes data/processed/kei_lines_ncaam.json.
Run from apps/web: python scripts/export_kei_lines.py
"""
import json
import sys
from pathlib import Path

import polars as pl

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import MERGED_GAMES_PATH, PROCESSED

PROCESSED.mkdir(parents=True, exist_ok=True)


def export_ncaam() -> None:
    if not MERGED_GAMES_PATH.exists():
        print(f"Missing {MERGED_GAMES_PATH}. Run merge_games_ensemble.py first.")
        return

    df = pl.read_parquet(MERGED_GAMES_PATH)
    # Prefer display names; fallback to norm
    home_col = "home_team" if "home_team" in df.columns else "home_team_norm"
    away_col = "away_team" if "away_team" in df.columns else "away_team_norm"
    if home_col not in df.columns:
        home_col = "home_team_norm"
    if away_col not in df.columns:
        away_col = "away_team_norm"

    required = [home_col, away_col, "ensemble_spread"]
    if not all(c in df.columns for c in required):
        print(f"Missing columns. Have: {df.columns}. Need: {required}")
        return

    rows = df.unique(subset=["event_id"], keep="first").sort("commence_time", descending=True)
    games = []
    for r in rows.iter_rows(named=True):
        home = r.get(home_col) or r.get("home_team_norm") or ""
        away = r.get(away_col) or r.get("away_team_norm") or ""
        if isinstance(home, str):
            home = home.strip()
        if isinstance(away, str):
            away = away.strip()
        games.append({
            "id": r.get("event_id"),
            "homeTeam": home,
            "awayTeam": away,
            "commenceTime": r.get("commence_time"),
            "projSpreadHome": round(r["ensemble_spread"], 2) if r.get("ensemble_spread") is not None else None,
            "projTotal": round(r["ensemble_total"], 2) if r.get("ensemble_total") is not None else None,
        })

    out_path = PROCESSED / "kei_lines_ncaam.json"
    with open(out_path, "w") as f:
        json.dump({"games": games}, f, indent=2)
    print(f"Wrote {out_path} with {len(games)} games.")


if __name__ == "__main__":
    export_ncaam()
