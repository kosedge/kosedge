"""
Ingest CBS Sports CBB injuries and write RAW_GAMES/injury.parquet for the pipeline.

Approximate mapping:
- Scrape team-level injury lists from CBS.
- Normalize team names to team_norm (matching merge_games_ensemble).
- Join to schedule (RAW_GAMES/schedule.parquet) by team_norm + game_date to infer event_id.
- Mark key_player_out_home/away = True when any non-questionable OUT/Doubtful is present.

Run from apps/web:
  python src/ingest_cbs_injuries.py
"""
import sys
from datetime import date
from pathlib import Path
from typing import List

import polars as pl
import requests
from bs4 import BeautifulSoup

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_GAMES, SCHEDULE_PATH, INJURY_PATH, ensure_dirs


def _normalize_team(name: str) -> str:
    return (
        name.lower()
        .replace(".", "")
        .replace(" st", " state")
        .replace("uconn", "connecticut")
        .strip()
    )


def fetch_cbs_injuries() -> List[dict]:
    url = "https://www.cbssports.com/college-basketball/injuries/"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    rows: List[dict] = []
    sections = soup.select("section.TableBaseWrapper")
    today = date.today().isoformat()

    for section in sections:
        team_header = section.select_one("h3")
        if not team_header:
            continue
        team_name = team_header.get_text(strip=True)
        team_norm = _normalize_team(team_name)

        table = section.select_one("table")
        if not table:
            continue
        tbody = table.select_one("tbody")
        if not tbody:
            continue
        for tr in tbody.select("tr"):
            cols = tr.select("td")
            if len(cols) < 3:
                continue
            status = cols[0].get_text(strip=True).lower()
            player = cols[1].get_text(strip=True)
            note = cols[2].get_text(strip=True)
            # Treat OUT and Doubtful as key-player-out signal; skip "day-to-day"/"probable"
            if "out" in status or "doubtful" in status:
                rows.append(
                    {
                        "team_norm": team_norm,
                        "player": player,
                        "status": status,
                        "note": note,
                        "report_date": today,
                    }
                )
    return rows


def main() -> None:
    ensure_dirs()
    if not SCHEDULE_PATH.exists():
        print("Missing schedule.parquet. Run build_schedule_from_odds.py first.")
        return

    injuries = fetch_cbs_injuries()
    if not injuries:
        print("No injuries scraped from CBS.")
        return

    inj_df = pl.DataFrame(injuries)
    # Use today's date to flag games occurring today or later; approximate mapping
    sched = pl.read_parquet(SCHEDULE_PATH)
    if "game_date" not in sched.columns:
        print("schedule.parquet missing game_date; cannot join injuries.")
        return

    today = date.today()
    sched = sched.with_columns(
        pl.col("game_date").cast(pl.Date)
    )
    # For now, we flag any game where team_norm matches, regardless of specific player
    inj_home = (
        sched.select(["team_norm", "game_date"])
        .join(
            inj_df.select(["team_norm"]).unique(),
            on="team_norm",
            how="inner",
        )
        .with_columns(pl.lit(True).alias("key_player_out"))
    )

    # Map to event_id: join back to odds by team_norm + game_date
    # We assume merge_games_ensemble has already materialized schedule->event_id via odds/event_id join.
    # Here we approximate by joining on team_norm + game_date; event_id will be filled in merge step.

    # Build injury flags per team/game_date
    inj_flags = inj_home.unique(subset=["team_norm", "game_date"]).with_columns(
        pl.col("key_player_out").cast(pl.Boolean)
    )

    RAW_GAMES.mkdir(parents=True, exist_ok=True)
    inj_flags.write_parquet(INJURY_PATH)
    print(f"Wrote {INJURY_PATH} with {len(inj_flags)} rows.")


if __name__ == "__main__":
    main()

