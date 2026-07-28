#!/usr/bin/env python3
"""Build leakage-safe special-teams KAV weekly features from owned PBP.

ST unit EPA (per team-game):
  - field_goal / extra_point / punt: posteam (kicking/punting), EPA as-is
  - kickoff: defteam (kicking side in nflverse), EPA negated into kicking frame

Weekly row for week W is as-of end of W. Pre-game joins must use week W-1.

Also backfills matchup pack columns home/away/diff_st_kav_net_5g with
strict lag (as_of = game.week - 1).

Writes summary: data/ops/nfl-st-kav-build.json
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from sqlalchemy import create_engine, text  # noqa: E402

OUT = ROOT / "data" / "ops" / "nfl-st-kav-build.json"
ST_SCALE = 0.20  # EPA/play → KAV-like pct (ST noisier than offense)


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _rolling_mean(xs: List[float], n: int) -> float | None:
    if not xs:
        return None
    window = xs[-n:]
    return sum(window) / len(window)


def main() -> int:
    engine = create_engine(_db_url())
    with engine.begin() as conn:
        # Ensure schema
        conn.execute(text((ROOT / "infra" / "db" / "042_nfl_st_kav.sql").read_text()))

        # Team-game ST aggregates (one row per team per game)
        rows = conn.execute(
            text(
                """
                WITH st AS (
                  SELECT
                    p.season,
                    p.week,
                    p.game_id,
                    CASE
                      WHEN p.play_type IN ('field_goal', 'extra_point', 'punt') THEN p.posteam
                      WHEN p.play_type = 'kickoff' THEN p.defteam
                      ELSE NULL
                    END AS team,
                    CASE
                      WHEN p.play_type IN ('field_goal', 'extra_point', 'punt') THEN p.epa
                      WHEN p.play_type = 'kickoff' THEN -p.epa
                      ELSE NULL
                    END AS st_epa
                  FROM nfl_dp_play_by_play p
                  WHERE p.season BETWEEN 2013 AND 2025
                    AND p.play_type IN ('field_goal', 'extra_point', 'punt', 'kickoff')
                    AND p.epa IS NOT NULL
                    AND p.posteam IS NOT NULL
                    AND p.defteam IS NOT NULL
                )
                SELECT season, week, game_id, team,
                       COUNT(*)::int AS st_plays,
                       AVG(st_epa) AS raw_st_epa_per_play
                FROM st
                WHERE team IS NOT NULL
                GROUP BY 1, 2, 3, 4
                ORDER BY 1, 2, 3, 4
                """
            )
        ).mappings().all()

        # League mean EPA for scale
        all_epa = [float(r["raw_st_epa_per_play"]) for r in rows if r["raw_st_epa_per_play"] is not None]
        league_mean = sum(all_epa) / len(all_epa) if all_epa else 0.0

        # Series per team within season
        by_season_team: Dict[Tuple[int, str], List[Tuple[int, str, float, int]]] = defaultdict(list)
        for r in rows:
            season = int(r["season"])
            week = int(r["week"])
            team = str(r["team"])
            epa = float(r["raw_st_epa_per_play"])
            plays = int(r["st_plays"])
            kav = (epa - league_mean) / ST_SCALE
            by_season_team[(season, team)].append((week, str(r["game_id"]), kav, plays))

        # Sort each series by week
        for key in by_season_team:
            by_season_team[key].sort(key=lambda x: (x[0], x[1]))

        conn.execute(text("DELETE FROM nfl_dp_team_st_kav_weekly WHERE season BETWEEN 2013 AND 2025"))

        weekly_written = 0
        now = datetime.now(timezone.utc)
        for (season, team), series in by_season_team.items():
            # Distinct weeks present
            weeks = sorted({w for w, _, _, _ in series})
            for as_of in weeks:
                thru = [(w, gid, kav, pl) for w, gid, kav, pl in series if w <= as_of]
                if not thru:
                    continue
                kavs = [k for _, _, k, _ in thru]
                plays = sum(pl for _, _, _, pl in thru)
                raw = None
                # reconstruct raw from kav: kav = (epa - league)/scale => epa = kav*scale + league
                epas = [k * ST_SCALE + league_mean for k in kavs]
                raw = sum(epas) / len(epas)
                ytd = sum(kavs) / len(kavs)
                g5 = _rolling_mean(kavs, 5)
                conn.execute(
                    text(
                        """
                        INSERT INTO nfl_dp_team_st_kav_weekly (
                          season, week, team, games_played, st_plays,
                          raw_st_epa_per_play, st_kav_net, st_kav_net_5g, st_kav_net_ytd,
                          as_of_week, source, updated_at
                        ) VALUES (
                          :season, :week, :team, :games_played, :st_plays,
                          :raw_st, :st_kav_net, :st_kav_net_5g, :st_kav_net_ytd,
                          :as_of_week, 'nflverse_pbp_st', :updated_at
                        )
                        ON CONFLICT (season, week, team) DO UPDATE SET
                          games_played = EXCLUDED.games_played,
                          st_plays = EXCLUDED.st_plays,
                          raw_st_epa_per_play = EXCLUDED.raw_st_epa_per_play,
                          st_kav_net = EXCLUDED.st_kav_net,
                          st_kav_net_5g = EXCLUDED.st_kav_net_5g,
                          st_kav_net_ytd = EXCLUDED.st_kav_net_ytd,
                          as_of_week = EXCLUDED.as_of_week,
                          updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "season": season,
                        "week": as_of,
                        "team": team,
                        "games_played": len(thru),
                        "st_plays": plays,
                        "raw_st": round(raw, 6) if raw is not None else None,
                        "st_kav_net": round(ytd, 6),
                        "st_kav_net_5g": round(g5, 6) if g5 is not None else None,
                        "st_kav_net_ytd": round(ytd, 6),
                        "as_of_week": as_of,
                        "updated_at": now,
                    },
                )
                weekly_written += 1

        # Backfill matchup features with week-1 lag
        # Clear then fill with strict week-1 lag (week 1 stays NULL — no prior-season bleed).
        conn.execute(
            text(
                """
                UPDATE nfl_dp_matchup_features_weekly
                SET home_st_kav_net_5g = NULL,
                    away_st_kav_net_5g = NULL,
                    diff_st_kav_net_5g = NULL
                WHERE season BETWEEN 2013 AND 2025
                """
            )
        )
        matchup_updated = conn.execute(
            text(
                """
                UPDATE nfl_dp_matchup_features_weekly m
                SET
                  home_st_kav_net_5g = h.st_kav_net_5g,
                  away_st_kav_net_5g = a.st_kav_net_5g,
                  diff_st_kav_net_5g = CASE
                    WHEN h.st_kav_net_5g IS NULL OR a.st_kav_net_5g IS NULL THEN NULL
                    ELSE h.st_kav_net_5g - a.st_kav_net_5g
                  END
                FROM nfl_dp_team_st_kav_weekly h,
                     nfl_dp_team_st_kav_weekly a
                WHERE m.week >= 2
                  AND h.season = m.season
                  AND a.season = m.season
                  AND h.team = m.home_team
                  AND a.team = m.away_team
                  AND h.week = m.week - 1
                  AND a.week = m.week - 1
                  AND m.season BETWEEN 2013 AND 2025
                """
            )
        ).rowcount

        cov = conn.execute(
            text(
                """
                SELECT
                  COUNT(*) AS matchup_n,
                  COUNT(diff_st_kav_net_5g) AS with_st,
                  COUNT(*) FILTER (WHERE week = 1) AS week1_n,
                  COUNT(diff_st_kav_net_5g) FILTER (WHERE week = 1) AS week1_with_st
                FROM nfl_dp_matchup_features_weekly
                WHERE season BETWEEN 2020 AND 2025
                """
            )
        ).mappings().first()

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "team_game_rows": len(rows),
        "weekly_rows_written": weekly_written,
        "matchup_rows_updated": int(matchup_updated or 0),
        "league_mean_st_epa": round(league_mean, 6),
        "st_scale": ST_SCALE,
        "coverage_2020_2025": dict(cov) if cov else {},
        "leakage": "matchup join uses week-1 lag (GREATEST(week-1,0)); week 1 typically null ST",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
