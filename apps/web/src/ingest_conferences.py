"""
Ingest team → conference mapping for Division I CBB and write RAW_GAMES/conferences.parquet.

Implementation:
- Fetch a public table of CBB teams and conferences (e.g. from Wikipedia).
- Normalize team names to team_norm (matching merge_games_ensemble).
- Save as RAW_GAMES/conferences.parquet for downstream joins.

Run from apps/web:
  python src/ingest_conferences.py
"""
import sys
from pathlib import Path

import polars as pl
import requests
from bs4 import BeautifulSoup

_WEB = Path(__file__).resolve().parent.parent
if str(_WEB) not in sys.path:
    sys.path.insert(0, str(_WEB))
from pipeline_paths import RAW_GAMES, ensure_dirs


def _normalize(name: str) -> str:
    return (
        name.lower()
        .replace(".", "")
        .replace(" st", " state")
        .replace("uconn", "connecticut")
        .strip()
    )


def fetch_wikipedia_conferences() -> pl.DataFrame:
    url = "https://en.wikipedia.org/wiki/List_of_NCAA_Division_I_men%27s_basketball_programs"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.select("table.wikitable")
    rows = []
    for table in tables:
        tbody = table.select_one("tbody")
        if not tbody:
            continue

        for tr in tbody.select("tr"):
            cols = tr.select("td")
            if len(cols) < 3:
                continue
            school = cols[0].get_text(" ", strip=True)
            conf = cols[2].get_text(" ", strip=True)
            if not school or not conf:
                continue
            rows.append(
                {
                    "team": school,
                    "conference": conf,
                    "team_norm": _normalize(school),
                }
            )

    if not rows:
        raise RuntimeError("No rows parsed from Wikipedia conferences table.")
    return pl.DataFrame(rows).unique(subset=["team_norm"])


def main() -> None:
    ensure_dirs()
    df = fetch_wikipedia_conferences()
    RAW_GAMES.mkdir(parents=True, exist_ok=True)
    out = RAW_GAMES / "conferences.parquet"
    df.write_parquet(out)
    print(f"Wrote {out} with {len(df)} teams.")


if __name__ == "__main__":
    main()

