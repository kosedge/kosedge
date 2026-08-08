#!/usr/bin/env python3
"""Rebuild packaged EPA prior artifact for NFL season-engine offline mode.

Source order:
  1. Local postgres ``nfl_dp_team_situational_weekly`` (source=nflverse)
  2. ``DATABASE_URL`` / ``LAUNCH_RESEARCH_DATABASE_URL`` if local empty

Writes:
  services/model-service/src/services/nfl_season_engine/data/nfl_team_epa_priors_<season>.json

Conversion uses ``tasks._epa_to_strength_indices`` so units match Edge Board.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
MS = ROOT / "services" / "model-service"
sys.path.insert(0, str(MS))

OUT_DIR = MS / "src" / "services" / "nfl_season_engine" / "data"


def _connect(dsn: str):
    try:
        import psycopg

        return psycopg.connect(dsn)
    except Exception:
        import psycopg2

        return psycopg2.connect(dsn)


def _candidate_dsns(explicit: Optional[str]) -> List[str]:
    out: List[str] = []
    if explicit:
        out.append(explicit)
    out.append("postgresql://ryankos:postgres@127.0.0.1:5432/kosedge")
    for key in ("LAUNCH_RESEARCH_DATABASE_URL", "DATABASE_URL"):
        raw = (os.getenv(key) or "").strip()
        if not raw:
            continue
        raw = raw.replace("postgresql+psycopg://", "postgresql://").replace(
            "postgresql+psycopg2://", "postgresql://"
        )
        if raw not in out:
            out.append(raw)
    return out


def _fetch_season_avgs(conn: Any, prior_season: int) -> List[Tuple]:
    sql = """
        SELECT
          team,
          COUNT(*)::int AS n_weeks,
          COALESCE(SUM(offensive_plays), 0)::int AS offensive_plays,
          COALESCE(SUM(defensive_plays), 0)::int AS defensive_plays,
          CASE WHEN COALESCE(SUM(offensive_plays),0) > 0
            THEN SUM(epa_per_play_offense * offensive_plays) / NULLIF(SUM(offensive_plays), 0)
            ELSE AVG(epa_per_play_offense) END AS off_epa,
          CASE WHEN COALESCE(SUM(defensive_plays),0) > 0
            THEN SUM(epa_per_play_defense_allowed * defensive_plays)
                 / NULLIF(SUM(defensive_plays), 0)
            ELSE AVG(epa_per_play_defense_allowed) END AS def_epa_allowed,
          AVG(pressure_rate_generated) AS pressure_generated,
          AVG(pressure_rate_allowed) AS pressure_allowed
        FROM nfl_dp_team_situational_weekly
        WHERE season = %s AND source = 'nflverse'
        GROUP BY team
        ORDER BY team
    """
    cur = conn.cursor()
    cur.execute(sql, (int(prior_season),))
    rows = cur.fetchall()
    cur.close()
    return list(rows)


def _epa_to_strength_indices(
    *,
    off_epa: float,
    def_epa_allowed: float,
    pressure_generated: float = 0.0,
    pressure_allowed: float = 0.0,
) -> Dict[str, float]:
    """Mirror ``tasks._epa_to_strength_indices`` (avoid importing FastAPI app)."""
    pressure_delta = float(pressure_generated) - float(pressure_allowed)
    offense_index = max(
        0.82, min(1.22, 1.0 + (float(off_epa) * 0.75) + (pressure_delta * 0.18))
    )
    defense_index = max(
        0.82, min(1.24, 1.0 + ((-float(def_epa_allowed)) * 0.90) + (pressure_delta * 0.14))
    )
    return {
        "offense_index": round(offense_index, 6),
        "defense_index": round(defense_index, 6),
    }


def build(season: int, prior_season: int, dsn: Optional[str]) -> Path:
    rows: List[Tuple] = []
    used_dsn = ""
    last_err: Optional[Exception] = None
    for candidate in _candidate_dsns(dsn):
        try:
            with _connect(candidate) as conn:
                rows = _fetch_season_avgs(conn, prior_season)
            if rows:
                used_dsn = candidate.split("@")[-1] if "@" in candidate else candidate
                break
        except Exception as exc:  # pragma: no cover - ops path
            last_err = exc
            continue
    if not rows:
        raise SystemExit(
            f"No situational weekly rows for season={prior_season}. last_err={last_err}"
        )

    teams: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        team = str(r[0] or "").strip().upper()
        if team == "LAR":
            team = "LA"
        off_epa = float(r[4] or 0.0)
        def_epa = float(r[5] or 0.0)
        pg = float(r[6] or 0.0)
        pa = float(r[7] or 0.0)
        indices = _epa_to_strength_indices(
            off_epa=off_epa,
            def_epa_allowed=def_epa,
            pressure_generated=pg,
            pressure_allowed=pa,
        )
        teams[team] = {
            "off_epa_per_play": round(off_epa, 6),
            "def_epa_allowed_per_play": round(def_epa, 6),
            "pressure_rate_generated": round(pg, 6),
            "pressure_rate_allowed": round(pa, 6),
            "offense_index": float(indices["offense_index"]),
            "defense_index": float(indices["defense_index"]),
            "n_weeks": int(r[1]),
            "offensive_plays": int(r[2]),
            "defensive_plays": int(r[3]),
        }

    if len(teams) != 32:
        raise SystemExit(f"Expected 32 teams, got {len(teams)}: {sorted(teams)}")

    payload = {
        "season": int(season),
        "prior_season": int(prior_season),
        "source": "packaged_epa_prior",
        "source_table": "nfl_dp_team_situational_weekly",
        "source_filter": "source=nflverse",
        "source_host": used_dsn,
        "as_of": date.today().isoformat(),
        "method": "play_weighted_season_avg_epa_to_strength_indices",
        "conversion": "tasks._epa_to_strength_indices (pressure from seasonal avg rates)",
        "notes": (
            f"{season} launch priors = {prior_season} season play-weighted EPA averages "
            "from nfl_dp_team_situational_weekly. Units match live simulate_nfl_game "
            "via _epa_to_strength_indices. LAR normalized to LA."
        ),
        "team_count": len(teams),
        "teams": teams,
    }
    out = OUT_DIR / f"nfl_team_epa_priors_{season}.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--prior-season", type=int, default=None)
    parser.add_argument("--dsn", default="")
    args = parser.parse_args()
    prior = int(args.prior_season) if args.prior_season else int(args.season) - 1
    path = build(args.season, prior, args.dsn or None)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
