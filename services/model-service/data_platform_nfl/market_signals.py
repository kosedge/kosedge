"""Real market signal fetch for preseason team-strength anchoring.

Ported from the one-off scripts/nfl/fix_2026_preseason_priors.py so the
market-anchor step is part of the permanent, repeatable bootstrap instead of
something that has to be hand-run and hand-copied into next year's script.
"""

from __future__ import annotations

import os
from typing import Dict

import requests

ODDS_API_BASE = "https://api.the-odds-api.com/v4"

FULL_NAME_TO_ABBR: Dict[str, str] = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


def _american_to_implied_prob(price: float) -> float:
    if price > 0:
        return 100.0 / (price + 100.0)
    return abs(price) / (abs(price) + 100.0)


def fetch_market_sb_probabilities(api_key: str | None = None, timeout: float = 30.0) -> Dict[str, float]:
    """Returns {team_abbr: vig-removed implied Super Bowl win probability}.

    The Odds API's SB-winner market always prices "the next Super Bowl" --
    there is no season-specific sport_key -- so this should be called during
    the current offseason for whichever season is about to start.
    """
    key = api_key or os.environ.get("ODDS_API_KEY", "")
    if not key:
        raise RuntimeError("ODDS_API_KEY not set")
    resp = requests.get(
        f"{ODDS_API_BASE}/sports/americanfootball_nfl_super_bowl_winner/odds",
        params={"apiKey": key, "regions": "us", "markets": "outrights", "oddsFormat": "american"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise RuntimeError("No Super Bowl futures data returned from Odds API")

    raw_by_team: Dict[str, list] = {}
    for event in data:
        for book in event.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") != "outrights":
                    continue
                for outcome in market.get("outcomes", []):
                    abbr = FULL_NAME_TO_ABBR.get(outcome.get("name"))
                    price = outcome.get("price")
                    if not abbr or price is None:
                        continue
                    raw_by_team.setdefault(abbr, []).append(_american_to_implied_prob(price))

    avg_by_team = {abbr: sum(probs) / len(probs) for abbr, probs in raw_by_team.items()}
    total = sum(avg_by_team.values()) or 1.0
    return {abbr: p / total for abbr, p in avg_by_team.items()}


def market_probabilities_to_percentile_ranks(probs: Dict[str, float]) -> Dict[str, float]:
    """Rank teams by market probability into [0, 1], 1.0 = market's best team."""
    teams_sorted = sorted(probs.keys(), key=lambda t: probs[t])
    n = len(teams_sorted)
    return {team: i / max(1, n - 1) for i, team in enumerate(teams_sorted)}
