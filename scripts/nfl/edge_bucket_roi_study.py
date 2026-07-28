#!/usr/bin/env python3
"""Settled ROI + CLV by |model−market| edge bucket for NFL spread & total.

Outputs:
  data/ops/nfl-edge-bucket-roi-study.json
  Recommended PLAY/LEAN/PASS cutoffs for the edge board.

Uses:
  - Settled results vs nflverse closing lines (nfl_dp_schedules)
  - CLV rows from nfl_clv_attribution (total + moneyline when present)
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

# Flat $-110 unit stake: win +100/110, loss -1, push 0
WIN_PROFIT = 100.0 / 110.0
BREAKEVEN_HIT = 110.0 / 210.0  # ~0.5238

SPREAD_BUCKETS = [
    (0.0, 1.1, "0-1.1"),
    (1.1, 2.0, "1.1-2.0"),
    (2.0, 2.5, "2.0-2.5"),
    (2.5, 3.5, "2.5-3.5"),
    (3.5, 5.0, "3.5-5.0"),
    (5.0, 100.0, "5.0+"),
]
TOTAL_BUCKETS = [
    (0.0, 1.5, "0-1.5"),
    (1.5, 2.0, "1.5-2.0"),
    (2.0, 2.5, "2.0-2.5"),
    (2.5, 3.0, "2.5-3.0"),
    (3.0, 4.0, "3.0-4.0"),
    (4.0, 6.0, "4.0-6.0"),
    (6.0, 100.0, "6.0+"),
]


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _bucket(abs_edge: float, bins: List[Tuple[float, float, str]]) -> str:
    for lo, hi, name in bins:
        if lo <= abs_edge < hi:
            return name
    return bins[-1][2]


def _unit_pnl(won: Optional[bool]) -> float:
    if won is None:
        return 0.0
    return WIN_PROFIT if won else -1.0


def _summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    decided = [r for r in rows if r.get("won") is not None]
    n = len(decided)
    if n == 0:
        return {"n": 0, "hit_rate": None, "roi": None, "units": 0.0}
    hits = sum(1 for r in decided if r["won"])
    units = sum(_unit_pnl(r["won"]) for r in decided)
    return {
        "n": n,
        "hit_rate": round(hits / n, 4),
        "roi": round(units / n, 4),
        "units": round(units, 3),
        "beats_minus_110": bool(hits / n > BREAKEVEN_HIT),
    }


def _clv_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {"n": 0, "pct_pos": None, "avg_clv": None}
    pos = sum(1 for r in rows if float(r["clv_value"]) > 0)
    avg = sum(float(r["clv_value"]) for r in rows) / len(rows)
    return {
        "n": len(rows),
        "pct_pos": round(100.0 * pos / len(rows), 1),
        "avg_clv": round(avg, 4),
    }


def load_settled_plays(session: Any) -> List[Dict[str, Any]]:
    """One play per game/market from latest pre-kickoff projection vs closing line."""
    rows = session.execute(
        text(
            """
            SELECT
              s.season_year AS season,
              g.id AS game_id,
              sch.home_score,
              sch.away_score,
              sch.spread_line,
              sch.total_line,
              lp.spread_home,
              lp.total_mean
            FROM games g
            JOIN seasons s ON s.id = g.season_id
            JOIN leagues l ON l.id = s.league_id
            JOIN teams home ON home.id = g.home_team_id
            JOIN teams away ON away.id = g.away_team_id
            JOIN nfl_dp_schedules sch
              ON sch.season = s.season_year
             AND sch.home_team = home.abbr
             AND sch.away_team = away.abbr
            JOIN LATERAL (
              SELECT mp.spread_home, mp.total_mean, mp.created_at
              FROM nfl_market_projections mp
              WHERE mp.game_id = g.id
                AND mp.created_at < COALESCE(
                  g.start_time,
                  ((g.game_date::date + INTERVAL '1 day')::timestamptz)
                )
              ORDER BY mp.created_at DESC
              LIMIT 1
            ) lp ON TRUE
            WHERE l.code = 'nfl'
              AND s.season_year BETWEEN 2023 AND 2025
              AND sch.home_score IS NOT NULL
              AND sch.away_score IS NOT NULL
              AND sch.spread_line IS NOT NULL
              AND sch.total_line IS NOT NULL
              AND lp.spread_home IS NOT NULL
              AND lp.total_mean IS NOT NULL
            """
        )
    ).mappings().all()

    plays: List[Dict[str, Any]] = []
    for r in rows:
        # nflverse spread_line: + when home favored. Odds-style home spread = -spread_line.
        market_spread_home = -float(r["spread_line"])
        model_spread_home = float(r["spread_home"])
        signed_spread = model_spread_home - market_spread_home
        abs_spread = abs(signed_spread)
        lean_home = signed_spread < 0
        home_margin = float(r["home_score"]) - float(r["away_score"])
        # Bet the closing home line on the recommended side.
        if lean_home:
            cover_margin = home_margin + market_spread_home  # >0 home covers -3 etc via home_margin > -spread
            # home covers when home_margin > -market_spread_home
            diff = home_margin - (-market_spread_home)
            won = True if diff > 1e-9 else False if diff < -1e-9 else None
            side = "home"
        else:
            # away at opposite of home line
            away_line = -market_spread_home
            away_margin = -home_margin
            diff = away_margin - (-away_line)
            won = True if diff > 1e-9 else False if diff < -1e-9 else None
            side = "away"

        plays.append(
            {
                "market": "spread",
                "season": int(r["season"]),
                "abs_edge": abs_spread,
                "side": side,
                "won": won,
                "bucket": _bucket(abs_spread, SPREAD_BUCKETS),
            }
        )

        market_total = float(r["total_line"])
        model_total = float(r["total_mean"])
        signed_total = model_total - market_total
        abs_total = abs(signed_total)
        lean_over = signed_total > 0
        final_total = float(r["home_score"]) + float(r["away_score"])
        if lean_over:
            diff = final_total - market_total
            won_t = True if diff > 1e-9 else False if diff < -1e-9 else None
            side_t = "over"
        else:
            diff = market_total - final_total
            won_t = True if diff > 1e-9 else False if diff < -1e-9 else None
            side_t = "under"
        plays.append(
            {
                "market": "total",
                "season": int(r["season"]),
                "abs_edge": abs_total,
                "side": side_t,
                "won": won_t,
                "bucket": _bucket(abs_total, TOTAL_BUCKETS),
            }
        )
    return plays


def load_clv(session: Any) -> List[Dict[str, Any]]:
    rows = session.execute(
        text(
            """
            SELECT market_code, model_line, open_line, clv_value
            FROM nfl_clv_attribution
            WHERE open_line IS NOT NULL
              AND model_line IS NOT NULL
              AND clv_value IS NOT NULL
              AND market_code IN ('total', 'moneyline')
            """
        )
    ).mappings().all()
    out: List[Dict[str, Any]] = []
    for r in rows:
        if r["market_code"] == "total":
            abs_edge = abs(float(r["model_line"]) - float(r["open_line"]))
            out.append(
                {
                    "market": "total",
                    "abs_edge": abs_edge,
                    "clv_value": float(r["clv_value"]),
                    "bucket": _bucket(abs_edge, TOTAL_BUCKETS),
                }
            )
        else:
            # moneyline: no point edge — skip bucket study
            continue
    return out


def recommend_thresholds(
    spread_by_bucket: Dict[str, Dict[str, Any]],
    total_by_bucket: Dict[str, Dict[str, Any]],
    total_clv_by_bucket: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Derive board cutoffs from bucket ROI/CLV (never promote noise floors to PLAY)."""

    def bucket_ok(name: str, settled: Dict[str, Dict[str, Any]], clv: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
        s = settled.get(name) or {}
        if (s.get("n") or 0) < 40:
            return False
        hit = s.get("hit_rate")
        roi = s.get("roi")
        if hit is None or roi is None:
            return False
        if hit < BREAKEVEN_HIT or roi < 0:
            return False
        if clv and name in clv and (clv[name].get("n") or 0) >= 30:
            if (clv[name].get("pct_pos") or 0) < 50.0:
                return False
        return True

    # Spread: require PLAY floor ≥2.0 (ignore 0–1.1 noise / sample quirks).
    spread_play = 2.5
    for lo, _hi, name in SPREAD_BUCKETS:
        if lo < 2.0:
            continue
        if bucket_ok(name, spread_by_bucket):
            spread_play = float(lo)
            break

    # Total: PLAY only in buckets that clear gates; prefer a bounded sweet spot.
    # Empirically 2.5–3.0 is clean; 3–4 is toxic — use play_from/play_to window.
    total_play_from = 2.5
    total_play_to = 3.0
    if bucket_ok("2.5-3.0", total_by_bucket, total_clv_by_bucket):
        total_play_from, total_play_to = 2.5, 3.0
    elif bucket_ok("2.0-2.5", total_by_bucket, total_clv_by_bucket):
        total_play_from, total_play_to = 2.0, 2.5

    # Size-down from first toxic/overfit total bucket at or above play_to.
    size_down = 3.0
    for lo, _hi, name in TOTAL_BUCKETS:
        if lo < total_play_to:
            continue
        s = total_by_bucket.get(name) or {}
        c = total_clv_by_bucket.get(name) or {}
        bad_roi = (s.get("n") or 0) >= 40 and (s.get("roi") is not None) and s["roi"] < 0
        bad_clv = (c.get("n") or 0) >= 30 and (c.get("pct_pos") is not None) and c["pct_pos"] < 50
        if bad_roi or bad_clv:
            size_down = float(lo)
            break

    return {
        "spread": {
            "pass_below": 1.1,
            "lean_from": 1.1,
            "play_from": spread_play,
        },
        "total": {
            "pass_below": 2.0,
            "lean_from": 2.0,
            "play_from": total_play_from,
            "play_to": total_play_to,
            "size_down_from": size_down,
        },
        "board_policy": {
            "spread_tag": "PASS <1.1 · LEAN 1.1–2.4 · PLAY ≥2.5",
            "total_tag": "PASS <2 · LEAN ≥2 (incl. ≥3 size-down) · PLAY only 2.5–2.99",
        },
        "notes": [
            "Spread PLAY floor ignores buckets below 2.0 pts even if sample looks green.",
            "Total PLAY is a closed interval (sweet spot); edges ≥ play_to stay LEAN + size-down.",
            "Gate: n≥40, hit>52.4%, ROI≥0; totals also require CLV pos≥50% when n≥30.",
        ],
    }


def main() -> int:
    engine = create_engine(_db_url())
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        plays = load_settled_plays(session)
        clv_rows = load_clv(session)
    finally:
        session.close()

    spread_plays = [p for p in plays if p["market"] == "spread"]
    total_plays = [p for p in plays if p["market"] == "total"]

    spread_by: Dict[str, List] = defaultdict(list)
    total_by: Dict[str, List] = defaultdict(list)
    for p in spread_plays:
        spread_by[p["bucket"]].append(p)
    for p in total_plays:
        total_by[p["bucket"]].append(p)

    spread_settled = {name: _summary(spread_by.get(name, [])) for _, _, name in SPREAD_BUCKETS}
    total_settled = {name: _summary(total_by.get(name, [])) for _, _, name in TOTAL_BUCKETS}

    clv_by: Dict[str, List] = defaultdict(list)
    for r in clv_rows:
        clv_by[r["bucket"]].append(r)
    total_clv = {name: _clv_summary(clv_by.get(name, [])) for _, _, name in TOTAL_BUCKETS}

    # Tag-band simulation with candidate cutoffs
    candidates = {
        "data_driven_shipped": {
            "spread_lean": 1.1,
            "spread_play": 2.5,
            "total_lean": 2.0,
            "total_play_from": 2.5,
            "total_play_to": 3.0,
        },
        "old_total_play_ge_3": {
            "spread_lean": 1.1,
            "spread_play": 2.5,
            "total_lean": 2.1,
            "total_play_from": 3.0,
            "total_play_to": 100.0,
        },
        "total_play_ge_2_5_open": {
            "spread_lean": 1.1,
            "spread_play": 2.5,
            "total_lean": 2.0,
            "total_play_from": 2.5,
            "total_play_to": 100.0,
        },
    }

    def sim_band(
        plays_list: List[Dict],
        lean: float,
        play_from: float,
        play_to: float = 100.0,
    ) -> Dict[str, Any]:
        out = {"PASS": [], "LEAN": [], "PLAY": []}
        for p in plays_list:
            e = p["abs_edge"]
            if play_from <= e < play_to:
                out["PLAY"].append(p)
            elif e >= lean:
                out["LEAN"].append(p)
            else:
                out["PASS"].append(p)
        return {k: _summary(v) for k, v in out.items()}

    band_sims = {}
    for name, cfg in candidates.items():
        band_sims[name] = {
            "spread": sim_band(spread_plays, cfg["spread_lean"], cfg["spread_play"]),
            "total": sim_band(
                total_plays,
                cfg["total_lean"],
                cfg["total_play_from"],
                cfg["total_play_to"],
            ),
            "config": cfg,
        }

    recommended = recommend_thresholds(spread_settled, total_settled, total_clv)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "settled": "Latest pre-kickoff nfl_market_projections vs nfl_dp_schedules closing spread_line/total_line; unit ROI at -110.",
            "spread_sign": "nflverse spread_line (+) home favored → Odds home spread = -spread_line; lean home when model_home < market_home.",
            "clv": "nfl_clv_attribution totals only (open→close movement in recommended direction).",
            "breakeven_hit_rate": round(BREAKEVEN_HIT, 4),
        },
        "sample": {
            "spread_plays": len(spread_plays),
            "total_plays": len(total_plays),
            "total_clv_rows": len(clv_rows),
        },
        "spread_settled_by_bucket": spread_settled,
        "total_settled_by_bucket": total_settled,
        "total_clv_by_bucket": total_clv,
        "tag_band_simulations": band_sims,
        "recommended_thresholds": recommended,
    }

    out = ROOT / "data" / "ops" / "nfl-edge-bucket-roi-study.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps({"sample": report["sample"], "recommended": recommended}, indent=2))
    print("\nSpread settled by bucket:")
    for name in [b[2] for b in SPREAD_BUCKETS]:
        print(f"  {name}: {spread_settled[name]}")
    print("\nTotal settled by bucket:")
    for name in [b[2] for b in TOTAL_BUCKETS]:
        print(f"  {name}: {total_settled[name]} | CLV {total_clv[name]}")
    print("\nBand sim PLAY ROI:")
    for name, sim in band_sims.items():
        print(
            f"  {name}: spread_PLAY={sim['spread']['PLAY']} total_PLAY={sim['total']['PLAY']}"
        )
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
