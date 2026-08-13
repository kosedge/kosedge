"""cfbfastR / SportsDataverse PBP ingest — download once, store locally.

Maps ``load_cfb_pbp(seasons)`` onto HD parquet. Production model-service must
not live-query CFBD. Opponent-adj EPA mart is a later pass; this writes the
season files and a core column subset (EPA / success / state).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Sequence

from src.services.cfb_warehouse.paths import clean_dir, pbp_raw_dir
from src.services.cfb_warehouse.sdv import fetch_sdv_file

PBP_SEASONS = tuple(range(2014, 2026))
PBP_TAG = "espn_cfb_pbp"

# Brief field list → actual SportsDataverse column names (2020+ schema).
PBP_CORE_COLUMNS = (
    "season",
    "week",
    "game_id",
    "id",
    "drive.id",
    "pos_team",
    "def_pos_team",
    "homeTeamAbbrev",
    "awayTeamAbbrev",
    "homeTeamName",
    "awayTeamName",
    "down",
    "distance",
    "start.yardsToEndzone",
    "statYardage",
    "type.text",
    "EPA",
    "EP_start",
    "EP_end",
    "EPA_success",
    "rz_play",
    "stuffed_run",
    "pos_score_diff",
    "start.TimeSecsRem",
    "under_2",
    "wpa",
    "wp_before",
    "wp_after",
    "scrimmage_play",
    "pass",
    "rush",
)


def ingest_pbp(
    *,
    seasons: Sequence[int] = PBP_SEASONS,
    prefer_hd: bool = True,
) -> Dict[str, Any]:
    raw = pbp_raw_dir(prefer_hd=prefer_hd)
    clean = clean_dir(prefer_hd=prefer_hd) / "pbp"
    raw.mkdir(parents=True, exist_ok=True)
    clean.mkdir(parents=True, exist_ok=True)

    import pandas as pd

    by_season: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    total_plays = 0
    total_games = 0

    for season in seasons:
        filename = f"play_by_play_{int(season)}.parquet"
        try:
            src = fetch_sdv_file(PBP_TAG, filename, cache_dir=raw)
            df = pd.read_parquet(src)
        except Exception as exc:  # noqa: BLE001
            errors[str(season)] = str(exc)[:240]
            by_season[str(season)] = {"status": "fetch_failed", "error": str(exc)[:240]}
            continue
        keep = [c for c in PBP_CORE_COLUMNS if c in df.columns]
        core = df.loc[:, keep].copy()
        dest = clean / f"pbp_{int(season)}_core.parquet"
        core.to_parquet(dest, index=False)
        n_games = int(df["game_id"].nunique()) if "game_id" in df.columns else 0
        total_plays += int(len(df))
        total_games += n_games
        by_season[str(season)] = {
            "status": "ok",
            "plays": int(len(df)),
            "games": n_games,
            "raw_cols": int(len(df.columns)),
            "core_cols": len(keep),
            "raw_path": str(src),
            "core_path": str(dest),
            "bytes": int(src.stat().st_size),
        }

    readme = clean / "README.md"
    readme.write_text(
        "# CFB PBP (cfbfastR / SportsDataverse)\n\n"
        "Full season parquet lives in `raw/cfb/pbp/play_by_play_{year}.parquet` "
        "(download-once). Core EPA/success/state columns are copied here as "
        "`pbp_{year}_core.parquet`.\n\n"
        "Do not live-query CFBD/cfbfastR from model-service. Opponent-adj mart "
        "is a later pass — these files are the input.\n",
        encoding="utf-8",
    )
    inventory = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "sportsdataverse espn_cfb_pbp (load_cfb_pbp)",
        "seasons": list(seasons),
        "plays": total_plays,
        "games": total_games,
        "by_season": by_season,
        "errors": errors,
        "core_columns": list(PBP_CORE_COLUMNS),
        "raw_dir": str(raw),
        "clean_dir": str(clean),
    }
    (clean / "inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )
    return inventory
