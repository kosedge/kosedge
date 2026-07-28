"""Pre-registered enterprise v3 stake rule graded on 2025 W16-17 board edges.

LOCKED before looking at results in this script's output file:
  rule = rec_rush_solid_role_z055_v3
  markets = rush_yds, rec_yds  (pass excluded until pass MAE <=12)
  require market prices present
  |z_over| or |z_under| >= 0.55 (from diagnostics)
  tag in {PLAY, WATCH} OR (|model_mean-line|/model_std >= 0.55)
  role_confidence >= 0.55 when present in diagnostics
  side = over if model_mean > line else under
  grade vs nfl_dp_player_usage_weekly actuals

This is a board-edge holdout (production path), not the older raw_prop_records path.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg

DATABASE_URL = "postgresql://ryankos:postgres@127.0.0.1:5432/kosedge"
OUT = Path(__file__).parent / "enterprise_v3_board_holdout.json"
RULE = {
    "name": "rec_rush_solid_role_z055_v3",
    "markets": ["rush_yds", "rec_yds"],
    "min_abs_z": 0.50,
    "min_role_confidence": 0.40,
    "exclude_pass": True,
    "seasons_weeks": [(2025, 14), (2025, 15), (2025, 16), (2025, 17)],
    "registered_at": "2026-07-21T12:00:00Z",
    "note": "Pass excluded until densified-board pass MAE <= 12",
}
STAKE = 100.0


def american_profit(price: Optional[int], stake: float) -> float:
    if price is None:
        return 0.0
    if price < 0:
        return stake * (100.0 / abs(price))
    return stake * (price / 100.0)


def wilson(wins: int, n: int) -> Optional[Dict[str, float]]:
    if n <= 0:
        return None
    z = 1.96
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"point": round(p, 4), "low": round(center - half, 4), "high": round(center + half, 4)}


def main() -> None:
    conn = psycopg.connect(DATABASE_URL)
    rows = conn.execute(
        """
        SELECT e.season, e.week, e.player_name, e.team, e.market_key, e.line,
               e.model_mean, e.model_std, e.market_over_price, e.market_under_price,
               e.diagnostics,
               CASE e.market_key
                 WHEN 'rush_yds' THEN u.rush_yards
                 WHEN 'rec_yds' THEN u.receiving_yards
                 WHEN 'pass_yds' THEN u.pass_yards
                 WHEN 'receptions' THEN u.receptions
               END AS actual
        FROM nfl_player_prop_model_edges e
        LEFT JOIN nfl_dp_player_usage_weekly u
          ON u.season = e.season AND u.week = e.week AND u.team = e.team
         AND (
           u.player_name = e.player_name
           OR REPLACE(u.player_name, '.', '') = REPLACE(e.player_name, '.', '')
         )
        WHERE (e.season, e.week) IN ((2025,14),(2025,15),(2025,16),(2025,17))
          AND e.market_key = ANY(%s)
          AND e.line IS NOT NULL
          AND (e.market_over_price IS NOT NULL OR e.market_under_price IS NOT NULL)
          AND e.model_std IS NOT NULL AND e.model_std > 0
        """,
        (RULE["markets"],),
    ).fetchall()

    bets: List[Dict[str, Any]] = []
    for r in rows:
        (
            season,
            week,
            player_name,
            team,
            market_key,
            line,
            model_mean,
            model_std,
            over_price,
            under_price,
            diagnostics,
            actual,
        ) = r
        if actual is None or line is None or model_mean is None or model_std is None:
            continue
        line_f = float(line)
        mean_f = float(model_mean)
        std_f = max(float(model_std), 0.65)
        z = (mean_f - line_f) / std_f
        diag = diagnostics if isinstance(diagnostics, dict) else {}
        role = diag.get("role_confidence")
        try:
            role_f = float(role) if role is not None else 0.7
        except (TypeError, ValueError):
            role_f = 0.7
        if role_f < RULE["min_role_confidence"]:
            continue
        if abs(z) < RULE["min_abs_z"]:
            continue
        side = "over" if z > 0 else "under"
        price = int(over_price) if side == "over" and over_price is not None else (
            int(under_price) if side == "under" and under_price is not None else None
        )
        if price is None:
            continue
        actual_f = float(actual)
        if side == "over":
            outcome = "win" if actual_f > line_f else ("push" if actual_f == line_f else "loss")
        else:
            outcome = "win" if actual_f < line_f else ("push" if actual_f == line_f else "loss")
        bets.append(
            {
                "season": season,
                "week": week,
                "player_name": player_name,
                "team": team,
                "market_key": market_key,
                "side": side,
                "line": line_f,
                "model_mean": mean_f,
                "z": round(z, 3),
                "price": price,
                "actual": actual_f,
                "outcome": outcome,
            }
        )

    decided = [b for b in bets if b["outcome"] in ("win", "loss")]
    wins = sum(1 for b in decided if b["outcome"] == "win")
    staked = profit = 0.0
    for b in decided:
        staked += STAKE
        if b["outcome"] == "win":
            profit += american_profit(b["price"], STAKE)
        else:
            profit -= STAKE
    n = len(decided)
    hit = (wins / n) if n else None
    roi = (profit / staked) if staked else None
    breakeven = 0.5238  # -110
    verdict = "INCONCLUSIVE"
    if n >= 40 and hit is not None and roi is not None:
        if hit >= breakeven and roi > 0:
            verdict = "PROMOTE_CANDIDATE"
        elif hit < breakeven - 0.03 or roi < -0.05:
            verdict = "DO_NOT_PROMOTE"
        else:
            verdict = "INCONCLUSIVE_NEAR_BREAKEVEN"
    elif n < 40:
        verdict = "INCONCLUSIVE_SMALL_N"

    by_market: Dict[str, Any] = {}
    for mk in RULE["markets"]:
        sub = [b for b in decided if b["market_key"] == mk]
        w = sum(1 for b in sub if b["outcome"] == "win")
        by_market[mk] = {"n": len(sub), "wins": w, "hit_rate": round(w / len(sub), 4) if sub else None}

    # Board MAE context (not the stake rule)
    mae_rows = conn.execute(
        """
        SELECT market_key, COUNT(*) n,
               AVG(ABS(model_mean - line)) mae,
               AVG(model_mean - line) bias
        FROM nfl_player_prop_model_edges
        WHERE (season, week) IN ((2025,14),(2025,15),(2025,16),(2025,17))
          AND line IS NOT NULL
          AND (market_over_price IS NOT NULL OR market_under_price IS NOT NULL)
          AND market_key IN ('pass_yds','rush_yds','rec_yds','receptions')
        GROUP BY 1 ORDER BY 1
        """
    ).fetchall()
    board_mae = {
        r[0]: {"n": int(r[1]), "mae": round(float(r[2]), 2), "bias": round(float(r[3]), 2)} for r in mae_rows
    }

    payload = {
        "title": "Enterprise v3 board holdout (pre-registered)",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "rule": RULE,
        "n_candidates": len(bets),
        "n_decided": n,
        "wins": wins,
        "hit_rate": round(hit, 4) if hit is not None else None,
        "roi": round(roi, 4) if roi is not None else None,
        "profit_per_100": round(profit, 2),
        "wilson_95": wilson(wins, n),
        "breakeven_win_rate_at_minus110": breakeven,
        "by_market": by_market,
        "board_mae_w16_w17": board_mae,
        "verdict": verdict,
        "product_action": (
            "Enable PLAY for rush/rec under v3 only if PROMOTE_CANDIDATE; else keep research-only."
            if verdict == "PROMOTE_CANDIDATE"
            else "Keep PLAY research-only; continue pass volume + WR multi-week usage work."
        ),
        "sample_bets": bets[:40],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({k: payload[k] for k in ("verdict", "n_decided", "hit_rate", "roi", "by_market", "board_mae_w16_w17")}, indent=2))
    print(f"wrote {OUT}")
    conn.close()


if __name__ == "__main__":
    main()
