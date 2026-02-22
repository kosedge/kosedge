"""
Single source of truth for data paths. All pipeline scripts should import from here.

Assumes this file lives in apps/web (WEB_ROOT). Run all Python pipeline scripts
from apps/web:  python src/build_ratings.py   or   python scripts/fetch_historical_ncaab_odds.py

For tests, set env DATA_DIR to a temp path so the pipeline uses fixture data.
"""
import os
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parent
_DATA_DIR_ENV = os.environ.get("DATA_DIR")
DATA_DIR = Path(_DATA_DIR_ENV) if _DATA_DIR_ENV else (WEB_ROOT / "data")
RAW = DATA_DIR / "raw"
PROCESSED = DATA_DIR / "processed"

# Raw subdirs (ratings = KenPom/Torvik/Evan/Haslametrics/D-Ratings; games = ESPN/Sports-Ref; odds = historical + fallback JSON)
RAW_RATINGS = RAW / "ratings"
RAW_GAMES = RAW / "games"
RAW_ODDS = RAW / "odds"
ODDS_OPEN = RAW_ODDS / "open"
ODDS_CLOSE = RAW_ODDS / "close"

# Processed outputs
FULL_RATINGS_PATH = PROCESSED / "full_ratings.parquet"
FULL_ENSEMBLE_RATINGS_PATH = PROCESSED / "full_ensemble_ratings.parquet"
ODDS_PARQUET_PATH = PROCESSED / "ncaab_historical_odds_open_close.parquet"
ACTUAL_MARGINS_PATH = PROCESSED / "actual_margins.parquet"
GAMES_WITH_EDGES_PATH = PROCESSED / "games_with_edges.parquet"
MERGED_GAMES_PATH = PROCESSED / "merged_games_with_odds_and_ratings.parquet"
FLAT_BETTING_PICKS_PATH = PROCESSED / "flat_betting_picks.csv"
KEI_BACKTEST_RESULTS_PATH = PROCESSED / "kei_backtest_results.json"
MARGIN_MODEL_PATH = PROCESSED / "margin_model.json"
ENSEMBLE_WEIGHTS_PATH = PROCESSED / "ensemble_weights.json"

# As-of-date ratings (one row per as_of_date + team; join to games by nearest prior date)
RATINGS_ARCHIVE_DIR = RAW_RATINGS / "archive"
KENPOM_ARCHIVE_PATH = PROCESSED / "kenpom_archive.parquet"
TORVIK_ARCHIVE_PATH = PROCESSED / "torvik_archive.parquet"
# Weekly rolling snapshots (one parquet per date: kenpom_YYYY-MM-DD.parquet)
KENPOM_SNAPSHOTS_DIR = PROCESSED / "kenpom_snapshots"
TORVIK_SNAPSHOTS_DIR = PROCESSED / "torvik_snapshots"
# Schedule for rest/travel: team, game_date, is_home, opponent_norm, venue_id (optional)
SCHEDULE_PATH = RAW_GAMES / "schedule.parquet"
# Injury/availability (event_id or team+date, key_player_out)
INJURY_PATH = RAW_GAMES / "injury.parquet"


def ensure_dirs() -> None:
    """Create data dirs if missing. Call from scripts that write output."""
    for d in (
        RAW_RATINGS, RAW_GAMES, RAW_ODDS, ODDS_OPEN, ODDS_CLOSE, PROCESSED, RATINGS_ARCHIVE_DIR,
        KENPOM_SNAPSHOTS_DIR, TORVIK_SNAPSHOTS_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
