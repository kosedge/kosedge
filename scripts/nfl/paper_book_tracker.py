#!/usr/bin/env python3
"""Locked paper book for selective NFL PLAY — no peeking, fixed thresholds.

Logs every spread/total/ML candidate that clears publish policy against
owned open/close when available. Does not retune bands.

Usage:
  DATABASE_URL=postgresql://ryankos:postgres@127.0.0.1:5432/kosedge \\
    PYTHONPATH=services/model-service:. \\
    .venv/bin/python scripts/nfl/paper_book_tracker.py --season 2025
"""

from __future__ import annotations

import argparse
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

from src.services.nfl_moneyline_publish_policy import publish_moneyline_tag  # noqa: E402
from src.services.nfl_side_total_publish_policy import (  # noqa: E402
    POLICY_VERSION,
    publish_tag,
)


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    # Docker hostnames are useless on the host — rewrite to loopback.
    if "@postgres:" in url:
        return url.replace("@postgres:", "@127.0.0.1:")
    return url


def _f(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fetch_rows(conn: Any, season: int) -> List[Dict[str, Any]]:
    """Join latest pre-kick projections to owned OC + schedule scores."""
    oc_rows = conn.execute(
        text(
            """
            WITH nfl_games AS (
              SELECT g.id AS game_id
              FROM games g
              JOIN seasons s ON s.id = g.season_id
              JOIN leagues l ON l.id = s.league_id
              WHERE lower(l.code) IN ('nfl', 'americanfootball_nfl')
                AND s.season_year = :season
            ),
            agg AS (
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
                (ARRAY_AGG(o.price_home ORDER BY o.captured_at DESC)
                  FILTER (WHERE o.price_home IS NOT NULL))[1] AS close_home_ml,
                (ARRAY_AGG(o.price_away ORDER BY o.captured_at DESC)
                  FILTER (WHERE o.price_away IS NOT NULL))[1] AS close_away_ml,
                COUNT(*) FILTER (WHERE o.spread_home IS NOT NULL)::int AS n_snaps_spread
              FROM odds_snapshots o
              JOIN nfl_games g ON g.game_id = o.game_id
              GROUP BY o.game_id
            )
            SELECT * FROM agg
            """
        ),
        {"season": season},
    ).mappings().all()
    oc_by = {str(r["game_id"]): dict(r) for r in oc_rows}

    sched = conn.execute(
        text(
            """
            SELECT
              sch.season, sch.week,
              sch.home_team, sch.away_team,
              sch.spread_line, sch.total_line,
              sch.home_score, sch.away_score,
              g.id AS game_uuid,
              g.start_time
            FROM nfl_dp_schedules sch
            JOIN games g ON g.external_id = sch.game_id
            WHERE sch.season = :season
            ORDER BY sch.week NULLS LAST, sch.game_id
            """
        ),
        {"season": season},
    ).mappings().all()

    proj_rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (mp.game_id)
              mp.game_id, mp.spread_home, mp.total_mean, mp.home_win_prob,
              mp.away_win_prob, mp.model_version
            FROM nfl_market_projections mp
            JOIN games g ON g.id = mp.game_id
            JOIN seasons s ON s.id = g.season_id
            WHERE s.season_year = :season
              AND mp.spread_home IS NOT NULL
              AND (g.start_time IS NULL OR mp.created_at < g.start_time)
            ORDER BY mp.game_id,
              CASE WHEN mp.projection->'audit'->>'pipeline_run_at' IS NOT NULL
                   THEN 0 ELSE 1 END,
              COALESCE(
                (mp.projection->'audit'->>'pipeline_run_at')::timestamptz,
                mp.created_at
              ) DESC
            """
        ),
        {"season": season},
    ).mappings().all()
    proj_by = {str(r["game_id"]): dict(r) for r in proj_rows}

    out: List[Dict[str, Any]] = []
    for sch in sched:
        gid = str(sch["game_uuid"]) if sch.get("game_uuid") else None
        if not gid:
            continue
        proj = proj_by.get(gid)
        if not proj:
            continue
        oc = oc_by.get(gid) or {}
        close_spread = _f(oc.get("close_spread"))
        close_total = _f(oc.get("close_total"))
        nflverse_spread = _f(sch.get("spread_line"))
        nflverse_total = _f(sch.get("total_line"))
        # nflverse spread_line is away-centric; convert to home line.
        if close_spread is None and nflverse_spread is not None:
            close_spread = -nflverse_spread
        if close_total is None and nflverse_total is not None:
            close_total = nflverse_total
        out.append(
            {
                "game_id": gid,
                "season": int(sch["season"]),
                "week": int(sch["week"] or 0),
                "home_team": sch.get("home_team"),
                "away_team": sch.get("away_team"),
                "model_spread": _f(proj.get("spread_home")),
                "model_total": _f(proj.get("total_mean")),
                "home_win_prob": _f(proj.get("home_win_prob")),
                "away_win_prob": _f(proj.get("away_win_prob")),
                "open_spread": _f(oc.get("open_spread")),
                "close_spread": close_spread,
                "open_total": _f(oc.get("open_total")),
                "close_total": close_total,
                "close_home_ml": _f(oc.get("close_home_ml")),
                "close_away_ml": _f(oc.get("close_away_ml")),
                "n_snaps_spread": int(oc.get("n_snaps_spread") or 0),
                "home_score": sch.get("home_score"),
                "away_score": sch.get("away_score"),
            }
        )
    return out


def _ats_hit(
    lean_home: bool, home_score: Any, away_score: Any, close_spread: Any
) -> Optional[bool]:
    if home_score is None or away_score is None or close_spread is None:
        return None
    margin = float(home_score) - float(away_score)
    cover_margin = margin + float(close_spread)
    if abs(cover_margin) < 1e-9:
        return None  # push
    home_covers = cover_margin > 0
    return home_covers if lean_home else (not home_covers)


def build_paper_book(season: int, gate: str = "YELLOW") -> Dict[str, Any]:
    plays: List[Dict[str, Any]] = []
    notes: List[str] = []
    rows: List[Dict[str, Any]] = []
    try:
        engine = create_engine(_db_url())
        with engine.connect() as conn:
            rows = _fetch_rows(conn, season)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"db_failed:{exc}")

    for row in rows:
        ms = row.get("model_spread")
        cs = row.get("close_spread")
        mt = row.get("model_total")
        ct = row.get("close_total")
        if ms is not None and cs is not None:
            edge = float(ms) - float(cs)
            pub = publish_tag(
                market="spread", abs_edge=abs(edge), product_gate_status=gate
            )
            if pub.get("tag") == "PLAY":
                lean_home = edge < 0  # model more home-favored than market
                hit = _ats_hit(
                    lean_home,
                    row.get("home_score"),
                    row.get("away_score"),
                    cs,
                )
                clv = None
                if (
                    row.get("open_spread") is not None
                    and int(row.get("n_snaps_spread") or 0) >= 2
                ):
                    # Positive CLV = line moved toward our side.
                    clv = (
                        float(row["open_spread"]) - float(cs)
                        if lean_home
                        else float(cs) - float(row["open_spread"])
                    )
                model_wp = (
                    row.get("home_win_prob") if lean_home else row.get("away_win_prob")
                )
                offered = (
                    row.get("close_home_ml") if lean_home else row.get("close_away_ml")
                )
                ml_pub = publish_moneyline_tag(
                    spread_tag="PLAY",
                    spread_stake_eligible=bool(pub.get("stake_eligible")),
                    model_win_prob=model_wp,
                    offered_american=offered,
                    product_gate_status=gate,
                )
                plays.append(
                    {
                        "game_id": row.get("game_id"),
                        "week": row.get("week"),
                        "market": "spread",
                        "side": "home" if lean_home else "away",
                        "matchup": f"{row.get('away_team')}@{row.get('home_team')}",
                        "edge": round(edge, 3),
                        "model": float(ms),
                        "close": float(cs),
                        "open": (
                            float(row["open_spread"])
                            if row.get("open_spread") is not None
                            else None
                        ),
                        "clv_move": round(clv, 3) if clv is not None else None,
                        "ats_hit": hit,
                        "ml_tag": ml_pub.get("tag"),
                        "ml_reason": ml_pub.get("reason"),
                        "ml_ev": ml_pub.get("ev"),
                    }
                )
        if mt is not None and ct is not None:
            t_edge = float(mt) - float(ct)
            t_pub = publish_tag(
                market="total", abs_edge=abs(t_edge), product_gate_status=gate
            )
            if t_pub.get("tag") == "PLAY":
                plays.append(
                    {
                        "game_id": row.get("game_id"),
                        "week": row.get("week"),
                        "market": "total",
                        "side": "over" if t_edge > 0 else "under",
                        "matchup": f"{row.get('away_team')}@{row.get('home_team')}",
                        "edge": round(t_edge, 3),
                        "model": float(mt),
                        "close": float(ct),
                        "open": (
                            float(row["open_total"])
                            if row.get("open_total") is not None
                            else None
                        ),
                    }
                )

    spread_plays = [p for p in plays if p["market"] == "spread"]
    graded = [p for p in spread_plays if p.get("ats_hit") is not None]
    hits = sum(1 for p in graded if p["ats_hit"])
    clv_pos = [p for p in spread_plays if p.get("clv_move") is not None]
    ml_plays = [p for p in spread_plays if p.get("ml_tag") == "PLAY"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "season": season,
        "policy_version": POLICY_VERSION,
        "product_gate": gate,
        "locked": True,
        "notes": notes,
        "n_board_rows": len(rows),
        "n_plays": len(plays),
        "n_spread_plays": len(spread_plays),
        "n_ml_plays": len(ml_plays),
        "n_graded_spread": len(graded),
        "spread_ats": (hits / len(graded)) if graded else None,
        "n_clv": len(clv_pos),
        "clv_positive_rate": (
            sum(1 for p in clv_pos if (p.get("clv_move") or 0) > 0) / len(clv_pos)
            if clv_pos
            else None
        ),
        "plays": plays,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2025)
    ap.add_argument("--gate", default=os.getenv("NFL_PRODUCT_GATE_STATUS", "YELLOW"))
    ap.add_argument(
        "--out", type=Path, default=ROOT / "data/ops/nfl-paper-book-latest.json"
    )
    args = ap.parse_args()
    book = build_paper_book(args.season, gate=args.gate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(book, indent=2), encoding="utf-8")
    md = args.out.with_suffix(".md")
    md.write_text(
        "\n".join(
            [
                f"# NFL paper book ({book['season']})",
                "",
                f"- Generated: `{book['generated_at']}`",
                f"- Policy: `{book['policy_version']}` (locked)",
                f"- Gate: {book['product_gate']}",
                f"- Board rows: {book['n_board_rows']}",
                f"- Plays: {book['n_plays']} (spread {book['n_spread_plays']}, ML {book['n_ml_plays']})",
                f"- Graded ATS: {book['spread_ats']}",
                f"- CLV+ rate: {book['clv_positive_rate']} (n={book['n_clv']})",
                f"- Notes: {book['notes'] or 'none'}",
                "",
                "Thresholds are frozen. Do not retune from this log.",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({k: book[k] for k in book if k != "plays"}, indent=2))


if __name__ == "__main__":
    main()
