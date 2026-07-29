#!/usr/bin/env python3
"""2026 NFL paper track under locked selective-publish thresholds.

Scores upcoming / unsettled 2026 boards with owned projections + odds.
When finals exist, also grades ATS / movement-CLV on PLAY tags.

Policy: spread_play_v2_cap7 (2.5 ≤ |edge| < 7.0); total PLAY [2.5, 3.0).
DB-first — no Odds API.

Writes:
  data/ops/nfl-paper-track-2026.json
  data/ops/nfl-paper-track-2026.md
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from sqlalchemy import create_engine, text  # noqa: E402

from src.services.nfl_side_total_publish_policy import (  # noqa: E402
    POLICY_VERSION,
    SPREAD_PLAY_MAX,
    SPREAD_PLAY_MIN,
    TOTAL_PLAY_MAX,
    TOTAL_PLAY_MIN,
    candidate_tag,
)

OUT_JSON = ROOT / "data" / "ops" / "nfl-paper-track-2026.json"
OUT_MD = ROOT / "data" / "ops" / "nfl-paper-track-2026.md"
WIN_PROFIT = 100.0 / 110.0


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _f(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    engine = create_engine(_db_url())
    with engine.connect() as conn:
        games = conn.execute(
            text(
                """
                SELECT
                  g.id AS game_uuid,
                  g.external_id,
                  g.game_date,
                  g.start_time,
                  s.season_year,
                  ht.abbr AS home_team,
                  at.abbr AS away_team,
                  sch.week,
                  sch.spread_line,
                  sch.total_line,
                  sch.home_score,
                  sch.away_score
                FROM games g
                JOIN seasons s ON s.id = g.season_id
                JOIN leagues l ON l.id = s.league_id
                JOIN teams ht ON ht.id = g.home_team_id
                JOIN teams at ON at.id = g.away_team_id
                JOIN nfl_dp_schedules sch
                  ON sch.game_id = g.external_id
                 AND sch.season = 2026
                WHERE l.code = 'nfl'
                  AND s.season_year = 2026
                ORDER BY g.game_date NULLS LAST, g.start_time NULLS LAST
                """
            )
        ).mappings().all()

        proj = {
            str(r["game_id"]): dict(r)
            for r in conn.execute(
                text(
                    """
                    SELECT DISTINCT ON (mp.game_id)
                      mp.game_id, mp.spread_home, mp.total_mean, mp.model_version,
                      COALESCE(
                        (mp.projection->'audit'->>'pipeline_run_at')::timestamptz,
                        mp.created_at
                      ) AS effective_at
                    FROM nfl_market_projections mp
                    JOIN games g ON g.id = mp.game_id
                    JOIN seasons s ON s.id = g.season_id
                    WHERE s.season_year = 2026
                      AND mp.spread_home IS NOT NULL
                    ORDER BY mp.game_id,
                      CASE WHEN mp.projection->'audit'->>'pipeline_run_at' IS NOT NULL THEN 0 ELSE 1 END,
                      COALESCE(
                        (mp.projection->'audit'->>'pipeline_run_at')::timestamptz,
                        mp.created_at
                      ) DESC
                    """
                )
            ).mappings().all()
        }

        oc = {
            str(r["game_id"]): dict(r)
            for r in conn.execute(
                text(
                    """
                    SELECT
                      o.game_id,
                      (ARRAY_AGG(o.spread_home ORDER BY o.captured_at ASC)
                        FILTER (WHERE o.spread_home IS NOT NULL))[1] AS open_spread,
                      (ARRAY_AGG(o.spread_home ORDER BY o.captured_at DESC)
                        FILTER (WHERE o.spread_home IS NOT NULL))[1] AS close_spread,
                      (ARRAY_AGG(o.total_points ORDER BY o.captured_at ASC)
                        FILTER (WHERE o.total_points IS NOT NULL))[1] AS open_total,
                      (ARRAY_AGG(o.total_points ORDER BY o.captured_at DESC)
                        FILTER (WHERE o.total_points IS NOT NULL))[1] AS close_total,
                      COUNT(*) FILTER (WHERE o.spread_home IS NOT NULL)::int AS n_snaps_spread
                    FROM odds_snapshots o
                    JOIN games g ON g.id = o.game_id
                    JOIN seasons s ON s.id = g.season_id
                    WHERE s.season_year = 2026
                    GROUP BY o.game_id
                    """
                )
            ).mappings().all()
        }

    paper_rows: List[Dict[str, Any]] = []
    settled_play: List[Dict[str, Any]] = []

    for g in games:
        gid = str(g["game_uuid"])
        p = proj.get(gid)
        if not p:
            continue
        model_s = _f(p.get("spread_home"))
        model_t = _f(p.get("total_mean"))
        if model_s is None:
            continue
        o = oc.get(gid) or {}
        close_s = _f(o.get("close_spread"))
        open_s = _f(o.get("open_spread"))
        nflverse_s = _f(g.get("spread_line"))
        if close_s is None and nflverse_s is not None:
            close_s = -nflverse_s
        if close_s is None:
            # Paper without a market line — skip edge tagging
            continue
        abs_spread = abs(model_s - close_s)
        tag_s = candidate_tag("spread", abs_spread)
        close_t = _f(o.get("close_total"))
        if close_t is None:
            close_t = _f(g.get("total_line"))
        tag_t = "PASS"
        abs_total = None
        if model_t is not None and close_t is not None:
            abs_total = abs(model_t - close_t)
            tag_t = candidate_tag("total", abs_total)

        row = {
            "game_id": gid,
            "external_id": g.get("external_id"),
            "game_date": str(g.get("game_date") or ""),
            "week": g.get("week"),
            "home_team": g.get("home_team"),
            "away_team": g.get("away_team"),
            "model_spread_home": model_s,
            "market_spread_home": close_s,
            "abs_edge_spread": round(abs_spread, 3),
            "spread_tag": tag_s,
            "model_total": model_t,
            "market_total": close_t,
            "abs_edge_total": round(abs_total, 3) if abs_total is not None else None,
            "total_tag": tag_t,
            "settled": g.get("home_score") is not None and g.get("away_score") is not None,
            "n_snaps_spread": int(o.get("n_snaps_spread") or 0),
        }
        paper_rows.append(row)

        if row["settled"] and tag_s == "PLAY":
            hm = float(g["home_score"]) - float(g["away_score"])
            lean_home = (model_s - close_s) < 0
            diff = hm + close_s
            if lean_home:
                won = True if diff > 1e-9 else False if diff < -1e-9 else None
            else:
                won = True if diff < -1e-9 else False if diff > 1e-9 else None
            clv = None
            if open_s is not None and int(o.get("n_snaps_spread") or 0) >= 2:
                clv = (open_s - close_s) if lean_home else (close_s - open_s)
            settled_play.append({"won": won, "clv": clv, **row})

    spread_play = [r for r in paper_rows if r["spread_tag"] == "PLAY"]
    total_play = [r for r in paper_rows if r["total_tag"] == "PLAY"]
    unsettled_play = [r for r in spread_play if not r["settled"]]

    decided = [r for r in settled_play if r.get("won") is not None]
    clv_move = [
        float(r["clv"])
        for r in settled_play
        if r.get("clv") is not None and abs(float(r["clv"])) > 1e-9
    ]
    settled_summary = {
        "n": len(decided),
        "hit_rate": (sum(1 for r in decided if r["won"]) / len(decided)) if decided else None,
        "roi": (
            sum((WIN_PROFIT if r["won"] else -1.0) for r in decided) / len(decided)
            if decided
            else None
        ),
        "n_clv_move": len(clv_move),
        "clv_positive_rate": (
            sum(1 for x in clv_move if x > 0) / len(clv_move) if clv_move else None
        ),
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy_version": POLICY_VERSION,
        "thresholds": {
            "spread_play": f"{SPREAD_PLAY_MIN} <= |edge| < {SPREAD_PLAY_MAX}",
            "total_play": f"{TOTAL_PLAY_MIN} <= |edge| < {TOTAL_PLAY_MAX}",
        },
        "inventory": {
            "games_2026": len(games),
            "games_with_projection_and_line": len(paper_rows),
            "spread_play_paper": len(spread_play),
            "total_play_paper": len(total_play),
            "unsettled_spread_play": len(unsettled_play),
            "settled_spread_play": len(settled_play),
            "games_with_owned_oc": sum(1 for r in paper_rows if r["n_snaps_spread"] >= 2),
        },
        "settled_play_grading": settled_summary,
        "paper_spread_plays": [
            {
                "date": r["game_date"],
                "matchup": f"{r['away_team']}@{r['home_team']}",
                "abs_edge": r["abs_edge_spread"],
                "model": r["model_spread_home"],
                "market": r["market_spread_home"],
                "settled": r["settled"],
            }
            for r in sorted(spread_play, key=lambda x: (x["game_date"], x["home_team"]))
        ][:80],
        "notes": [
            "Universe = seasons.season_year=2026 AND nfl_dp_schedules.season=2026 "
            "(excludes late-2025 playoff games that sit on calendar-2026 season rows).",
            "Paper track only until finals settle — do not claim ATS from unsettled rows.",
            "Re-run weekly (or after each slate) to accumulate live confirmation sample.",
            "PASS default remains; these tags mirror publish policy for research/paper.",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n")

    md = [
        "# NFL 2026 paper track",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Policy: `{POLICY_VERSION}`",
        "",
        "## Inventory",
        "",
        "```json",
        json.dumps(report["inventory"], indent=2),
        "```",
        "",
        "## Settled PLAY grading (if any)",
        "",
        "```json",
        json.dumps(settled_summary, indent=2),
        "```",
        "",
        f"Open paper spread PLAY tags: **{len(unsettled_play)}** "
        f"(of {len(spread_play)} total tagged).",
        "",
        "Re-run: `DATABASE_URL=... .venv/bin/python scripts/nfl/paper_track_2026.py`",
        "",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps({"inventory": report["inventory"], "settled": settled_summary}, indent=2))
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
