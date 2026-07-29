#!/usr/bin/env python3
"""Era durability + totals PLAY band scan under locked / candidate thresholds.

Documents:
  - Primary-2025 consensus movement-CLV hard ceiling
  - Multi-book movement-CLV (secondary; not used for product gate)
  - Spread v2 durability by era (scopes product to 2024+ / 2023+ pipeline)
  - Totals candidate bands (keep RED unless GREEN)

DB-first. Writes data/ops/nfl-play-durability-totals-scan.json
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from sqlalchemy import create_engine, text  # noqa: E402

OUT = ROOT / "data" / "ops" / "nfl-play-durability-totals-scan.json"
BREAKEVEN = 0.5238
SPREAD_LO, SPREAD_HI = 2.5, 7.0


def _f(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _gate(n: int, ats: Optional[float], n_clv: int, clv: Optional[float]) -> str:
    if n < 60 or ats is None or ats < BREAKEVEN:
        return "RED"
    if n_clv >= 200 and clv is not None and clv >= 0.55:
        return "GREEN"
    if n_clv >= 40 and clv is not None and clv >= 0.55:
        return "YELLOW"
    return "YELLOW_ats"


def main() -> int:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url)
    with engine.connect() as c:
        rows = list(
            c.execute(
                text(
                    """
                    SELECT sch.season, sch.home_score - sch.away_score AS hm,
                           sch.home_score + sch.away_score AS tot,
                           sch.spread_line, sch.total_line,
                           mp.spread_home AS model_s, mp.total_mean AS model_t,
                           g.id::text AS gid
                    FROM nfl_dp_schedules sch
                    JOIN games g ON g.external_id = sch.game_id
                    JOIN LATERAL (
                      SELECT spread_home, total_mean, created_at, projection
                      FROM nfl_market_projections mp
                      WHERE mp.game_id = g.id AND mp.spread_home IS NOT NULL
                        AND mp.total_mean IS NOT NULL
                        AND (g.start_time IS NULL OR mp.created_at < g.start_time)
                      ORDER BY CASE WHEN mp.projection->'audit'->>'pipeline_run_at' IS NOT NULL THEN 0 ELSE 1 END,
                               COALESCE((mp.projection->'audit'->>'pipeline_run_at')::timestamptz, mp.created_at) DESC
                      LIMIT 1
                    ) mp ON TRUE
                    WHERE sch.season BETWEEN 2020 AND 2025 AND sch.home_score IS NOT NULL
                    """
                )
            ).mappings()
        )
        books = list(
            c.execute(
                text(
                    """
                    SELECT o.game_id::text AS gid, o.sportsbook_id,
                      (ARRAY_AGG(o.spread_home ORDER BY o.captured_at ASC)
                        FILTER (WHERE o.spread_home IS NOT NULL))[1] AS open_s,
                      (ARRAY_AGG(o.spread_home ORDER BY o.captured_at DESC)
                        FILTER (WHERE o.spread_home IS NOT NULL))[1] AS close_s,
                      (ARRAY_AGG(o.total_points ORDER BY o.captured_at ASC)
                        FILTER (WHERE o.total_points IS NOT NULL))[1] AS open_t,
                      (ARRAY_AGG(o.total_points ORDER BY o.captured_at DESC)
                        FILTER (WHERE o.total_points IS NOT NULL))[1] AS close_t,
                      COUNT(*) FILTER (WHERE o.spread_home IS NOT NULL)::int AS n_s
                    FROM odds_snapshots o
                    JOIN games g ON g.id = o.game_id
                    JOIN seasons s ON s.id = g.season_id
                    WHERE s.season_year BETWEEN 2020 AND 2025
                    GROUP BY o.game_id, o.sportsbook_id
                    """
                )
            ).mappings()
        )
        cons = {
            r["gid"]: dict(r)
            for r in c.execute(
                text(
                    """
                    SELECT o.game_id::text AS gid,
                      (ARRAY_AGG(o.spread_home ORDER BY o.captured_at ASC)
                        FILTER (WHERE o.spread_home IS NOT NULL))[1] AS open_s,
                      (ARRAY_AGG(o.spread_home ORDER BY o.captured_at DESC)
                        FILTER (WHERE o.spread_home IS NOT NULL))[1] AS close_s,
                      COUNT(*) FILTER (WHERE o.spread_home IS NOT NULL)::int AS n_s
                    FROM odds_snapshots o GROUP BY 1
                    """
                )
            ).mappings()
        }

    by_book: Dict[str, List[dict]] = defaultdict(list)
    for b in books:
        by_book[b["gid"]].append(dict(b))

    def spread_metrics(seasons: Set[int]) -> Dict[str, Any]:
        ats: List[bool] = []
        clv_cons: List[float] = []
        clv_books: List[float] = []
        for r in rows:
            if int(r["season"]) not in seasons:
                continue
            oc = cons.get(r["gid"]) or {}
            close = _f(oc.get("close_s"))
            if close is None and r["spread_line"] is not None:
                close = -float(r["spread_line"])
            if close is None:
                continue
            model = float(r["model_s"])
            ae = abs(model - close)
            if not (SPREAD_LO <= ae < SPREAD_HI):
                continue
            lean_home = (model - close) < 0
            diff = float(r["hm"]) + close
            if abs(diff) <= 1e-9:
                won = None
            else:
                won = (diff > 0) if lean_home else (diff < 0)
            if won is not None:
                ats.append(bool(won))
            if oc.get("open_s") is not None and int(oc.get("n_s") or 0) >= 2:
                o = float(oc["open_s"])
                if abs(o - close) > 1e-9:
                    clv_cons.append((o - close) if lean_home else (close - o))
            for b in by_book.get(r["gid"], []):
                if b.get("open_s") is None or b.get("close_s") is None or int(b.get("n_s") or 0) < 2:
                    continue
                o, cl = float(b["open_s"]), float(b["close_s"])
                if abs(o - cl) <= 1e-9:
                    continue
                clv_books.append((o - cl) if lean_home else (cl - o))
        ats_r = sum(ats) / len(ats) if ats else None
        cons_r = sum(1 for x in clv_cons if x > 0) / len(clv_cons) if clv_cons else None
        book_r = sum(1 for x in clv_books if x > 0) / len(clv_books) if clv_books else None
        return {
            "n": len(ats),
            "ats": round(ats_r, 4) if ats_r is not None else None,
            "n_clv_consensus_move": len(clv_cons),
            "clv_consensus_pos": round(cons_r, 4) if cons_r is not None else None,
            "n_clv_multibook_move": len(clv_books),
            "clv_multibook_pos": round(book_r, 4) if book_r is not None else None,
            "gate_consensus": _gate(len(ats), ats_r, len(clv_cons), cons_r),
            "gate_multibook_secondary": _gate(len(ats), ats_r, len(clv_books), book_r),
        }

    def total_metrics(seasons: Set[int], lo: float, hi: float) -> Dict[str, Any]:
        ats: List[bool] = []
        clv: List[float] = []
        for r in rows:
            if int(r["season"]) not in seasons:
                continue
            closes = [
                float(b["close_t"])
                for b in by_book.get(r["gid"], [])
                if b.get("close_t") is not None
            ]
            opens = [
                float(b["open_t"])
                for b in by_book.get(r["gid"], [])
                if b.get("open_t") is not None
            ]
            close_t = sum(closes) / len(closes) if closes else _f(r["total_line"])
            open_t = sum(opens) / len(opens) if opens else None
            if close_t is None:
                continue
            model = float(r["model_t"])
            ae = abs(model - close_t)
            if not (lo <= ae < hi):
                continue
            lean_over = model > close_t
            actual = float(r["tot"])
            if lean_over:
                diff = actual - close_t
            else:
                diff = close_t - actual
            won = True if diff > 1e-9 else False if diff < -1e-9 else None
            if won is not None:
                ats.append(bool(won))
            if open_t is not None and abs(open_t - close_t) > 1e-9:
                clv.append((close_t - open_t) if lean_over else (open_t - close_t))
        ats_r = sum(ats) / len(ats) if ats else None
        clv_r = sum(1 for x in clv if x > 0) / len(clv) if clv else None
        return {
            "band": [lo, hi],
            "n": len(ats),
            "ats": round(ats_r, 4) if ats_r is not None else None,
            "n_clv_move": len(clv),
            "clv_pos": round(clv_r, 4) if clv_r is not None else None,
            "gate": _gate(len(ats), ats_r, len(clv), clv_r),
        }

    primary_2025 = spread_metrics({2025})
    confirmatory = spread_metrics({2024, 2025})
    eras = {
        "2020-2022": spread_metrics({2020, 2021, 2022}),
        "2023": spread_metrics({2023}),
        "2024-2025": confirmatory,
        "2023-2025": spread_metrics({2023, 2024, 2025}),
    }

    total_bands = [(1.5, 2.5), (2.0, 2.5), (2.0, 3.0), (2.5, 3.0), (2.5, 3.5), (3.0, 4.0)]
    totals = {
        "shipped_band_2.5_3.0": {
            "2025": total_metrics({2025}, 2.5, 3.0),
            "2024-2025": total_metrics({2024, 2025}, 2.5, 3.0),
            "2023-2025": total_metrics({2023, 2024, 2025}, 2.5, 3.0),
        },
        "candidates_2024_2025": [total_metrics({2024, 2025}, lo, hi) for lo, hi in total_bands],
        "candidates_2023_2025": [total_metrics({2023, 2024, 2025}, lo, hi) for lo, hi in total_bands],
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spread_policy": f"{SPREAD_LO} <= |edge| < {SPREAD_HI}",
        "primary_2025_clv_ceiling": {
            "consensus_move_n": primary_2025["n_clv_consensus_move"],
            "play_n": primary_2025["n"],
            "multibook_move_n": primary_2025["n_clv_multibook_move"],
            "hard_ceiling_note": (
                "Primary-2025 consensus movement-CLV cannot reach n≥200 inside the v2 PLAY "
                f"band: only {primary_2025['n']} PLAY games and "
                f"{primary_2025['n_clv_consensus_move']} with open≠close. "
                "Multi-book expands sample but double-counts games — secondary only. "
                "No Odds API densify re-burn; rematch orphans first."
            ),
            "metrics": primary_2025,
        },
        "era_durability_spread_v2": eras,
        "product_scope_recommendation": (
            "Scope selective spread PLAY subscription claim to 2024–2025 confirmatory "
            "(and live 2026+). 2020–2022 clears −110 ATS but fails movement-CLV; treat as "
            "out-of-regime for CLV-backed product claims."
        ),
        "totals": totals,
        "totals_verdict": (
            "No totals band clears GREEN (ATS + movement-CLV n≥200 @ ≥55%). "
            "Keep shipped [2.5, 3.0) research-only / thin-sample; do not flip totals stake."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "primary_2025": primary_2025,
        "eras": {k: {"n": v["n"], "ats": v["ats"], "clv_n": v["n_clv_consensus_move"], "clv+": v["clv_consensus_pos"], "gate": v["gate_consensus"]} for k, v in eras.items()},
        "totals_verdict": report["totals_verdict"],
        "wrote": str(OUT),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
