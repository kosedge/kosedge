"""Fix the 2026 preseason team-strength prior.

Root cause (confirmed via direct DB inspection): the placeholder seeded into
nfl_dp_team_situational_weekly for season 2026 (repeated identically across
all 18 weeks, since no real 2026 games have been played) was each team's
*last trailing-5-game snapshot from the end of 2025* -- not their full 2025
season average. That's the single noisiest, most recency-biased number
available. For Cleveland specifically: the carried-forward snapshot was
-0.125 offensive EPA/play, but their real full-2025 average was -0.196 (2nd
worst in the league) -- a materially worse number got silently replaced by
a better-looking small-sample tail.

This script does NOT change the model architecture (heuristic sim +
supervised ML overlay). It fixes the INPUT the same validated model uses for
the preseason cold-start period, in two steps:

  1. Recency-bias fix: replace the last-5-game snapshot with each team's
     full 2025 season average EPA/play (offense and defense).
  2. Market anchor: blend in real 2026/27 Super Bowl futures odds (The Odds
     API, americanfootball_nfl_super_bowl_winner) as a second, independent
     signal -- the market prices in real offseason information (coaching
     changes, injuries, roster moves, holdouts) that a stats-only carry-
     forward cannot see. Vig-removed SB win probabilities are converted to
     a percentile-rank-based EPA-equivalent adjustment and blended 50/50
     with the season-average signal.

Once real 2026 games are played, this correction becomes moot -- the
existing walk-forward rolling-window materializer takes over with real,
week-varying data, exactly as validated in this session's backtests.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

import numpy as np  # noqa: E402
import requests  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
SEASON = 2026

# Full-name -> nflverse abbreviation (same map used elsewhere this session).
FULL_NAME_TO_ABBR = {
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


def american_to_implied_prob(price: int) -> float:
    if price > 0:
        return 100.0 / (price + 100.0)
    return abs(price) / (abs(price) + 100.0)


def fetch_market_sb_probs() -> dict[str, float]:
    """Returns {abbr: vig-removed implied SB win probability}."""
    resp = requests.get(
        "https://api.the-odds-api.com/v4/sports/americanfootball_nfl_super_bowl_winner/odds",
        params={"apiKey": ODDS_API_KEY, "regions": "us", "markets": "outrights", "oddsFormat": "american"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise RuntimeError("No Super Bowl futures data returned")

    # Average implied prob across all books that have outrights, then
    # remove the vig (normalize so probabilities sum to 1).
    raw_by_team: dict[str, list[float]] = {}
    for event in data:
        for book in event.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") != "outrights":
                    continue
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name")
                    abbr = FULL_NAME_TO_ABBR.get(name)
                    if not abbr:
                        continue
                    price = outcome.get("price")
                    if price is None:
                        continue
                    raw_by_team.setdefault(abbr, []).append(american_to_implied_prob(price))

    avg_by_team = {abbr: float(np.mean(probs)) for abbr, probs in raw_by_team.items()}
    total = sum(avg_by_team.values())
    normalized = {abbr: p / total for abbr, p in avg_by_team.items()}
    return normalized


def main() -> None:
    if not ODDS_API_KEY:
        raise SystemExit("ODDS_API_KEY not set")

    print("Fetching real 2026/27 Super Bowl futures odds...")
    market_sb_probs = fetch_market_sb_probs()
    print(f"Got {len(market_sb_probs)} teams' market SB probabilities.")

    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()

    rows = session.execute(
        text(
            """
            SELECT team,
              AVG(epa_per_play_offense)::numeric AS off_epa,
              AVG(epa_per_play_defense_allowed)::numeric AS def_epa,
              AVG(pressure_rate_allowed)::numeric AS pressure_allowed,
              AVG(pressure_rate_generated)::numeric AS pressure_generated,
              AVG(pass_rate)::numeric AS pass_rate,
              AVG(early_down_pass_rate)::numeric AS early_down_pass_rate,
              AVG(red_zone_td_rate)::numeric AS red_zone_td_rate,
              AVG(success_rate_offense)::numeric AS success_rate_offense,
              AVG(success_rate_defense_allowed)::numeric AS success_rate_defense_allowed
            FROM nfl_dp_team_situational_weekly
            WHERE season = 2025
            GROUP BY team
            """
        )
    ).fetchall()
    season_avg = {r.team: dict(r._mapping) for r in rows}
    print(f"Computed full-2025-season averages for {len(season_avg)} teams.")

    missing_market = set(season_avg.keys()) - set(market_sb_probs.keys())
    if missing_market:
        print(f"WARNING: no market data for {missing_market}, using season-average only for these teams.")

    # Market percentile -> EPA-equivalent adjustment. Rank teams by market
    # SB probability, map percentile [0,1] linearly onto the same offensive
    # EPA range actually observed in the 2025 season data, then blend with
    # the real stats-based average. This treats the market as an
    # independent, offseason-aware signal of the same underlying quantity.
    teams_by_market_rank = sorted(market_sb_probs.keys(), key=lambda t: market_sb_probs[t])
    n = len(teams_by_market_rank)
    percentile_by_team = {t: i / max(1, n - 1) for i, t in enumerate(teams_by_market_rank)}

    off_epa_values = [float(v["off_epa"]) for v in season_avg.values() if v["off_epa"] is not None]
    off_epa_lo, off_epa_hi = min(off_epa_values), max(off_epa_values)
    def_epa_values = [float(v["def_epa"]) for v in season_avg.values() if v["def_epa"] is not None]
    def_epa_lo, def_epa_hi = min(def_epa_values), max(def_epa_values)

    BLEND_WEIGHT_MARKET = 0.5  # 50/50 between real full-season stats and market sentiment

    updates = []
    for team, stats in season_avg.items():
        stats_off_epa = float(stats["off_epa"]) if stats["off_epa"] is not None else 0.0
        stats_def_epa = float(stats["def_epa"]) if stats["def_epa"] is not None else 0.0
        if team in percentile_by_team:
            pct = percentile_by_team[team]
            # SB futures reflect *overall* team quality, not offense
            # specifically -- apply the same market signal to both sides so
            # a team the market rates as simply bad doesn't get propped up
            # by an unadjusted defense number (this was under-correcting
            # exactly that case: a bad-offense/good-defense team).
            market_off_epa_equiv = off_epa_lo + pct * (off_epa_hi - off_epa_lo)
            # Lower (more negative) def_epa_allowed = better defense, so
            # invert: high percentile (good team) -> lower def_epa_allowed.
            market_def_epa_equiv = def_epa_hi - pct * (def_epa_hi - def_epa_lo)
            blended_off_epa = (1 - BLEND_WEIGHT_MARKET) * stats_off_epa + BLEND_WEIGHT_MARKET * market_off_epa_equiv
            blended_def_epa = (1 - BLEND_WEIGHT_MARKET) * stats_def_epa + BLEND_WEIGHT_MARKET * market_def_epa_equiv
        else:
            blended_off_epa = stats_off_epa
            blended_def_epa = stats_def_epa
        updates.append(
            {
                "team": team,
                "season": SEASON,
                "off_epa": round(blended_off_epa, 6),
                "def_epa": round(blended_def_epa, 6),
                "pressure_allowed": stats["pressure_allowed"],
                "pressure_generated": stats["pressure_generated"],
                "pass_rate": stats["pass_rate"],
                "early_down_pass_rate": stats["early_down_pass_rate"],
                "red_zone_td_rate": stats["red_zone_td_rate"],
                "success_rate_offense": stats["success_rate_offense"],
                "success_rate_defense_allowed": stats["success_rate_defense_allowed"],
                "market_sb_prob": market_sb_probs.get(team),
                "market_percentile": percentile_by_team.get(team),
            }
        )

    print("\nTeam corrections (old placeholder off_epa -> new blended off_epa):")
    old_rows = session.execute(
        text("SELECT team, epa_per_play_offense FROM nfl_dp_team_situational_weekly WHERE season=2026 AND week=1")
    ).fetchall()
    old_by_team = {r.team: float(r.epa_per_play_offense) for r in old_rows}
    for u in sorted(updates, key=lambda x: x["off_epa"]):
        old = old_by_team.get(u["team"])
        old_str = f"{old:+.4f}" if old is not None else "  n/a "
        mkt = f"sb_prob={u['market_sb_prob']:.4f}" if u["market_sb_prob"] is not None else "no market data"
        print(f"  {u['team']:<4} old={old_str}  new={u['off_epa']:+.4f}  ({mkt})")

    print(f"\nUpdating nfl_dp_team_situational_weekly for season {SEASON}, all 18 weeks, {len(updates)} teams...")
    for u in updates:
        session.execute(
            text(
                """
                UPDATE nfl_dp_team_situational_weekly
                SET epa_per_play_offense = :off_epa,
                    epa_per_play_defense_allowed = :def_epa,
                    pressure_rate_allowed = :pressure_allowed,
                    pressure_rate_generated = :pressure_generated,
                    pass_rate = :pass_rate,
                    early_down_pass_rate = :early_down_pass_rate,
                    red_zone_td_rate = :red_zone_td_rate,
                    success_rate_offense = :success_rate_offense,
                    success_rate_defense_allowed = :success_rate_defense_allowed,
                    updated_at = NOW()
                WHERE season = :season AND team = :team
                """
            ),
            u,
        )
    session.commit()
    print("Done. Re-run materialize_matchup_features_from_usage / _load_team_strength_priors consumers to pick this up.")
    session.close()


if __name__ == "__main__":
    main()
