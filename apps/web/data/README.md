# Data layout (pipeline)

All paths are defined in **`pipeline_paths.py`** at the app root. Run all Python pipeline scripts from **`apps/web`**.

## Directory structure

```
data/
├── raw/
│   ├── ratings/     # KenPom, Torvik, Evan Miya, Haslametrics, D-Ratings (CSVs)
│   ├── games/       # ESPN & Sports-Reference game results (CSVs)
│   └── odds/        # Historical odds JSON
│       ├── open/    # YYYY-MM-DD.json (12:00 UTC snapshot)
│       ├── close/   # YYYY-MM-DD.json (22:00 UTC snapshot)
│       └── *.json   # Optional fallback / extra API response files
└── processed/       # Parquet & model outputs
```

## Run order (from `apps/web`)

**One command (recommended):**
```bash
python run_pipeline.py              # full pipeline
python run_pipeline.py --skip-odds  # use existing odds parquet
python run_pipeline.py --check-env  # print ODDS_API_KEY / KENPOM_API_KEY status
```

**Step by step:**
```bash
# 1. Build ratings
python src/build_ratings.py
python src/build_ensemble_ratings.py

# 2. Odds (fetch then process)
python scripts/fetch_historical_ncaab_odds.py --start 2024-11-01 --end 2025-02-15
python src/process_odds.py

# 3. Join / merge
python src/join_and_backtest.py
python src/merge_games_ensemble.py

# 4. (Optional) Game results → actual margins → backtest
python scrape_cbb_results.py
python scrape_cbb_results_espn.py
python src/build_actual_margins.py
# Then re-run merge_games_ensemble.py

# 5. (Optional) Train margin model
python src/train_margin_model.py
```

## Key outputs

| File | Produced by |
|------|-------------|
| `full_ratings.parquet` | build_ratings.py |
| `full_ensemble_ratings.parquet` | build_ensemble_ratings.py |
| `ncaab_historical_odds_open_close.parquet` | process_odds.py |
| `actual_margins.parquet` | build_actual_margins.py |
| `games_with_edges.parquet` | join_and_backtest.py |
| `merged_games_with_odds_and_ratings.parquet` | merge_games_ensemble.py |
| `flat_betting_picks.csv` | flat_betting_backtest.py |
| `margin_model.json` | train_margin_model.py |

## Ingest / scrape targets

- **Ratings:** `data/raw/ratings/` — ingest_kenpom.py, ingest_dratings.py, ingest_haslametrics.py
- **Games:** `data/raw/games/` — scrape_cbb_results.py, scrape_cbb_results_espn.py
- **Odds:** `data/raw/odds/open/` and `close/` — fetch_historical_ncaab_odds.py

## Fetch latest ratings (Haslametrics, D-Ratings)

From `apps/web` with deps installed (`pip install -r requirements-pipeline.txt` or `pip install requests beautifulsoup4`):

```bash
python src/ingest_dratings.py   # current season → dratings_ratings_2026.csv
python src/ingest_haslametrics.py   # offense/defense/fingerprint/performance by year
```

D-Ratings: current season via `ingest_dratings.py` → `dratings_ratings_2026.csv`. **Historical seasons (2020–2025):** run from **`apps/web`** (not repo root):

```bash
cd apps/web
pip install -r requirements-dratings-historical.txt
python -m playwright install chromium
python scripts/ingest_dratings_historical.py
```

Writes `data/raw/ratings/dratings_ratings_2020.csv` … `dratings_ratings_2025.csv`. Haslametrics is per-year. Fallback: `python scripts/write_dratings_from_fetch.py` (stdlib only, partial 2026).
