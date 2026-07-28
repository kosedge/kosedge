#!/usr/bin/env python3
"""Pre-registered PLAY-only unused holdout for NFL sides/totals.

Evaluates ATS / CLV / ROI ONLY on games that would have been tagged PLAY
under the locked selective-publish thresholds:

  - spread PLAY: |edge| ≥ 2.5
  - total PLAY:  2.5 ≤ |edge| < 3.0

Primary unused universe: season_year = 2025 (KAV re-sim boards).
Secondary: walk-forward seasons + prior-season evidence (labeled).

If the full PLAY universe fails product floors, shrinks into pre-declared
segments (market, edge band, side, home/road) and reports any GREEN slice.

Does NOT pull Odds API. Uses owned odds_snapshots open/close + nflverse close.

Writes:
  data/ops/nfl-play-only-holdout.json
  data/ops/nfl-play-only-holdout.md
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

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge"
)

from sqlalchemy import create_engine, text  # noqa: E402

from src.services.nfl_side_total_publish_policy import (  # noqa: E402
    BREAKEVEN_ATS,
    SPREAD_PLAY_MIN,
    TOTAL_PLAY_MAX,
    TOTAL_PLAY_MIN,
    candidate_tag,
)

OUT_JSON = ROOT / "data" / "ops" / "nfl-play-only-holdout.json"
OUT_MD = ROOT / "data" / "ops" / "nfl-play-only-holdout.md"

WIN_PROFIT = 100.0 / 110.0
# Product floors for selective PLAY claim (aspirational CLV n≥200)
GATE_ATS_MIN = BREAKEVEN_ATS
GATE_ATS_STRETCH = 0.55
GATE_CLV_POS_MIN = 0.55
GATE_CLV_N_MIN = 200
GATE_CLV_N_SOFT = 40  # segment confirmatory floor
GATE_ATS_N_MIN = 60
PRIMARY_HOLDOUT_SEASON = 2025

# Pre-registered shrink ladder (do not invent post-hoc after seeing results
# beyond this declared list).
SEGMENT_SPECS: List[Dict[str, Any]] = [
    {"key": "spread_all_play", "market": "spread", "edge_lo": SPREAD_PLAY_MIN, "edge_hi": 100.0},
    {"key": "spread_edge_2.5_3.5", "market": "spread", "edge_lo": 2.5, "edge_hi": 3.5},
    {"key": "spread_edge_3.5_5.0", "market": "spread", "edge_lo": 3.5, "edge_hi": 5.0},
    {"key": "spread_edge_5.0_plus", "market": "spread", "edge_lo": 5.0, "edge_hi": 100.0},
    {"key": "spread_home", "market": "spread", "side": "home"},
    {"key": "spread_away", "market": "spread", "side": "away"},
    {"key": "total_all_play", "market": "total", "edge_lo": TOTAL_PLAY_MIN, "edge_hi": TOTAL_PLAY_MAX},
    {"key": "total_over", "market": "total", "side": "over"},
    {"key": "total_under", "market": "total", "side": "under"},
    {"key": "combined_play", "market": None},  # all PLAY tags
]


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


def _unit_pnl(won: Optional[bool]) -> float:
    if won is None:
        return 0.0
    return WIN_PROFIT if won else -1.0


def _summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    decided = [r for r in rows if r.get("won") is not None]
    n = len(decided)
    if n == 0:
        return {
            "n": 0,
            "hit_rate": None,
            "roi": None,
            "units": 0.0,
            "beats_minus_110": False,
            "n_clv": 0,
            "clv_positive_rate": None,
            "clv_avg": None,
            "gate": "RED",
            "detail": "empty sample",
        }
    hits = sum(1 for r in decided if r["won"])
    hit_rate = hits / n
    units = sum(_unit_pnl(r["won"]) for r in decided)
    clv_vals = [float(r["clv"]) for r in decided if r.get("clv") is not None]
    n_clv = len(clv_vals)
    clv_pos = (sum(1 for x in clv_vals if x > 0) / n_clv) if n_clv else None
    clv_avg = (sum(clv_vals) / n_clv) if n_clv else None

    ats_ok = n >= GATE_ATS_N_MIN and hit_rate >= GATE_ATS_MIN
    clv_ok_hard = (
        n_clv >= GATE_CLV_N_MIN
        and clv_pos is not None
        and clv_pos >= GATE_CLV_POS_MIN
    )
    clv_ok_soft = (
        n_clv >= GATE_CLV_N_SOFT
        and clv_pos is not None
        and clv_pos >= GATE_CLV_POS_MIN
    )
    if ats_ok and clv_ok_hard:
        gate = "GREEN"
        detail = "ATS + CLV (n≥200) clear selective PLAY floors."
    elif ats_ok and (n_clv < GATE_CLV_N_SOFT or clv_ok_soft):
        gate = "YELLOW" if n_clv < GATE_CLV_N_MIN else ("GREEN" if clv_ok_hard else "YELLOW")
        if n_clv < GATE_CLV_N_SOFT:
            detail = "ATS clears; CLV sample thin — cautious selective claim only."
        elif clv_ok_soft and not clv_ok_hard:
            detail = "ATS clears; CLV +rate clears soft n≥40 but below n≥200 product floor."
        else:
            detail = "ATS clears; CLV +rate below floor."
            gate = "YELLOW" if hit_rate >= GATE_ATS_STRETCH else "RED"
    elif ats_ok:
        gate = "YELLOW" if hit_rate >= GATE_ATS_STRETCH else "RED"
        detail = "ATS clears −110 but CLV fails or missing."
    else:
        gate = "RED"
        detail = "ATS below −110 or sample below MIN_SEGMENT_N."

    # Stretch toward 55–60%
    stretch = None
    if hit_rate >= 0.60:
        stretch = "60pct+"
    elif hit_rate >= GATE_ATS_STRETCH:
        stretch = "55pct+"
    elif hit_rate >= GATE_ATS_MIN:
        stretch = "breakeven+"

    return {
        "n": n,
        "hits": hits,
        "hit_rate": round(hit_rate, 4),
        "roi": round(units / n, 4),
        "units": round(units, 3),
        "beats_minus_110": bool(hit_rate >= GATE_ATS_MIN),
        "n_clv": n_clv,
        "clv_positive_rate": round(clv_pos, 4) if clv_pos is not None else None,
        "clv_avg": round(clv_avg, 4) if clv_avg is not None else None,
        "gate": gate,
        "stretch_band": stretch,
        "detail": detail,
    }


def load_board_rows(conn: Any) -> List[Dict[str, Any]]:
    """One projection per settled schedule game (external_id join) + owned OC."""
    oc_rows = conn.execute(
        text(
            """
            WITH nfl_games AS (
              SELECT g.id AS game_id
              FROM games g
              JOIN seasons s ON s.id = g.season_id
              JOIN leagues l ON l.id = s.league_id
              WHERE lower(l.code) IN ('nfl', 'americanfootball_nfl')
            ),
            ranked AS (
              SELECT
                o.game_id,
                FIRST_VALUE(o.spread_home) OVER w AS open_spread,
                FIRST_VALUE(o.total_points) OVER w AS open_total,
                LAST_VALUE(o.spread_home) OVER w AS close_spread,
                LAST_VALUE(o.total_points) OVER w AS close_total,
                ROW_NUMBER() OVER (PARTITION BY o.game_id ORDER BY o.captured_at) AS rn
              FROM odds_snapshots o
              JOIN nfl_games g ON g.game_id = o.game_id
              WHERE o.spread_home IS NOT NULL OR o.total_points IS NOT NULL
              WINDOW w AS (
                PARTITION BY o.game_id
                ORDER BY o.captured_at
                ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
              )
            )
            SELECT game_id, open_spread, close_spread, open_total, close_total
            FROM ranked
            WHERE rn = 1
            """
        )
    ).mappings().all()
    oc_by = {str(r["game_id"]): dict(r) for r in oc_rows}

    # Join schedule → games via nflverse external_id (avoids duplicate abbr matches).
    sched = conn.execute(
        text(
            """
            SELECT
              sch.season, sch.week,
              sch.home_team, sch.away_team,
              sch.spread_line, sch.total_line,
              sch.home_score, sch.away_score,
              sch.game_id AS dp_game_id,
              g.id AS game_uuid,
              g.start_time
            FROM nfl_dp_schedules sch
            JOIN games g ON g.external_id = sch.game_id
            WHERE sch.home_score IS NOT NULL
              AND sch.away_score IS NOT NULL
              AND sch.season BETWEEN 2020 AND 2025
            ORDER BY sch.season, sch.week, sch.game_id
            """
        )
    ).mappings().all()

    # Prefer latest KAV/pipeline re-sim row that is still pre-kickoff when possible.
    # Rank: has pipeline_run_at DESC, then effective_at DESC. Only rows with
    # created_at < kickoff (or missing kickoff) to reduce post-game leakage.
    proj_rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (mp.game_id)
              mp.game_id,
              mp.spread_home,
              mp.total_mean,
              mp.model_version,
              mp.projection,
              mp.created_at,
              COALESCE(
                (mp.projection->'audit'->>'pipeline_run_at')::timestamptz,
                mp.created_at
              ) AS effective_at
            FROM nfl_market_projections mp
            JOIN games g ON g.id = mp.game_id
            WHERE mp.spread_home IS NOT NULL
              AND mp.total_mean IS NOT NULL
              AND (
                g.start_time IS NULL
                OR mp.created_at < g.start_time
              )
            ORDER BY mp.game_id,
              CASE
                WHEN mp.projection->'audit'->>'pipeline_run_at' IS NOT NULL THEN 0
                ELSE 1
              END,
              COALESCE(
                (mp.projection->'audit'->>'pipeline_run_at')::timestamptz,
                mp.created_at
              ) DESC
            """
        )
    ).mappings().all()
    proj_by = {str(r["game_id"]): dict(r) for r in proj_rows}

    plays: List[Dict[str, Any]] = []
    for sch in sched:
        gid = str(sch["game_uuid"]) if sch.get("game_uuid") else None
        if not gid:
            continue
        proj = proj_by.get(gid)
        if not proj:
            continue
        model_spread = _f(proj.get("spread_home"))
        model_total = _f(proj.get("total_mean"))
        if model_spread is None or model_total is None:
            continue

        oc = oc_by.get(gid) or {}
        close_spread = _f(oc.get("close_spread"))
        open_spread = _f(oc.get("open_spread"))
        close_total = _f(oc.get("close_total"))
        open_total = _f(oc.get("open_total"))

        nflverse_spread = _f(sch.get("spread_line"))  # + home favored
        nflverse_total = _f(sch.get("total_line"))
        if close_spread is None and nflverse_spread is not None:
            close_spread = -nflverse_spread
        if close_total is None and nflverse_total is not None:
            close_total = nflverse_total
        if close_spread is None or close_total is None:
            continue

        home_margin = float(sch["home_score"]) - float(sch["away_score"])
        actual_total = float(sch["home_score"]) + float(sch["away_score"])
        season = int(sch["season"])
        week = int(sch["week"] or 0)

        # Spread PLAY candidate vs close
        signed_spread = model_spread - close_spread
        abs_spread = abs(signed_spread)
        lean_home = signed_spread < 0  # model more home-favored (more negative)
        if lean_home:
            diff = home_margin + close_spread
            won_s = True if diff > 1e-9 else False if diff < -1e-9 else None
            side_s = "home"
        else:
            diff = (-home_margin) + (-close_spread)
            won_s = True if diff > 1e-9 else False if diff < -1e-9 else None
            side_s = "away"
        clv_s = None
        if open_spread is not None:
            # CLV for recommended side: positive when close moves toward our side
            if lean_home:
                clv_s = open_spread - close_spread
            else:
                clv_s = close_spread - open_spread

        tag_s = candidate_tag("spread", abs_spread)
        plays.append(
            {
                "market": "spread",
                "season": season,
                "week": week,
                "game_id": gid,
                "abs_edge": abs_spread,
                "side": side_s,
                "won": won_s,
                "clv": clv_s,
                "candidate_tag": tag_s,
                "home_road": "home" if side_s == "home" else "away",
            }
        )

        signed_total = model_total - close_total
        abs_total = abs(signed_total)
        lean_over = signed_total > 0
        if lean_over:
            diff_t = actual_total - close_total
            won_t = True if diff_t > 1e-9 else False if diff_t < -1e-9 else None
            side_t = "over"
        else:
            diff_t = close_total - actual_total
            won_t = True if diff_t > 1e-9 else False if diff_t < -1e-9 else None
            side_t = "under"
        clv_t = None
        if open_total is not None:
            clv_t = (close_total - open_total) if lean_over else (open_total - close_total)

        tag_t = candidate_tag("total", abs_total)
        plays.append(
            {
                "market": "total",
                "season": season,
                "week": week,
                "game_id": gid,
                "abs_edge": abs_total,
                "side": side_t,
                "won": won_t,
                "clv": clv_t,
                "candidate_tag": tag_t,
                "home_road": None,
            }
        )
    return plays


def _filter_segment(plays: List[Dict[str, Any]], spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = [p for p in plays if p.get("candidate_tag") == "PLAY"]
    market = spec.get("market")
    if market:
        out = [p for p in out if p["market"] == market]
    side = spec.get("side")
    if side:
        out = [p for p in out if p.get("side") == side]
    lo = spec.get("edge_lo")
    hi = spec.get("edge_hi")
    if lo is not None and hi is not None:
        out = [p for p in out if lo <= float(p["abs_edge"]) < hi]
    return out


def _gate_rank(g: str) -> int:
    return {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(g, 2)


def main() -> int:
    engine = create_engine(_db_url())
    with engine.connect() as conn:
        plays = load_board_rows(conn)

    all_play = [p for p in plays if p["candidate_tag"] == "PLAY"]
    holdout_2025 = [p for p in all_play if p["season"] == PRIMARY_HOLDOUT_SEASON]
    prior = [p for p in all_play if 2020 <= p["season"] <= 2024]

    # Walk-forward: evaluate each season as holdout using locked (pre-registered) tags
    by_season: Dict[str, Any] = {}
    for season in range(2020, 2026):
        season_plays = [p for p in all_play if p["season"] == season]
        by_season[str(season)] = {
            "combined": _summary(season_plays),
            "spread": _summary([p for p in season_plays if p["market"] == "spread"]),
            "total": _summary([p for p in season_plays if p["market"] == "total"]),
        }

    # Segment shrink on primary holdout
    segments_2025: Dict[str, Any] = {}
    green_segments: List[str] = []
    yellow_segments: List[str] = []
    for spec in SEGMENT_SPECS:
        rows = _filter_segment(holdout_2025, spec)
        # For edge/side specs without market already filtering PLAY, keep PLAY only
        if spec.get("key") == "combined_play":
            rows = holdout_2025
        summ = _summary(rows)
        segments_2025[spec["key"]] = summ
        if summ["gate"] == "GREEN":
            green_segments.append(spec["key"])
        elif summ["gate"] == "YELLOW":
            yellow_segments.append(spec["key"])

    primary = {
        "combined": _summary(holdout_2025),
        "spread": _summary([p for p in holdout_2025 if p["market"] == "spread"]),
        "total": _summary([p for p in holdout_2025 if p["market"] == "total"]),
    }
    prior_evidence = {
        "combined": _summary(prior),
        "spread": _summary([p for p in prior if p["market"] == "spread"]),
        "total": _summary([p for p in prior if p["market"] == "total"]),
    }

    # Overall selective-product gate from primary unused holdout
    overall_gate = primary["combined"]["gate"]
    # Prefer a GREEN segment if combined fails
    if overall_gate != "GREEN" and green_segments:
        overall_gate = "YELLOW"  # segment GREEN exists but full PLAY universe not GREEN
    betting_product_selective_ready = (
        primary["combined"]["gate"] == "GREEN"
        or (
            primary["spread"]["gate"] == "GREEN"
            and primary["spread"]["n"] >= GATE_ATS_N_MIN
        )
    )

    best_segment = None
    best_rank = 99
    for key, summ in segments_2025.items():
        r = _gate_rank(summ["gate"])
        n = summ.get("n") or 0
        if n < 20:
            continue
        if r < best_rank or (
            r == best_rank
            and best_segment
            and (summ.get("hit_rate") or 0) > (segments_2025[best_segment].get("hit_rate") or 0)
        ):
            best_rank = r
            best_segment = key

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_url_host": os.environ["DATABASE_URL"].split("@")[-1],
        "pre_registered": {
            "spread_play_min": SPREAD_PLAY_MIN,
            "total_play_min": TOTAL_PLAY_MIN,
            "total_play_max": TOTAL_PLAY_MAX,
            "primary_holdout_season": PRIMARY_HOLDOUT_SEASON,
            "gates": {
                "ats_min": GATE_ATS_MIN,
                "ats_stretch": GATE_ATS_STRETCH,
                "ats_n_min": GATE_ATS_N_MIN,
                "clv_pos_min": GATE_CLV_POS_MIN,
                "clv_n_min_product": GATE_CLV_N_MIN,
                "clv_n_min_segment": GATE_CLV_N_SOFT,
            },
            "notes": [
                "Thresholds match nfl_side_total_publish_policy (locked).",
                "Primary unused board holdout = 2025 settled KAV projections vs close.",
                "Threshold selection originally used 2023–25 bucket study — 2025 overlap "
                "is disclosed; walk-forward by_season shows each year under locked tags.",
                "CLV from owned odds_snapshots open→close sided by model edge; no Odds API.",
            ],
        },
        "inventory": {
            "board_rows_loaded": len(plays),
            "unique_games_loaded": len({p["game_id"] for p in plays}),
            "play_tagged_rows": len(all_play),
            "holdout_2025_play_rows": len(holdout_2025),
            "holdout_2025_unique_games": len({p["game_id"] for p in holdout_2025}),
            "prior_2020_2024_play_rows": len(prior),
            "spread_play_2025": sum(
                1 for p in holdout_2025 if p["market"] == "spread" and p.get("won") is not None
            ),
            "total_play_2025": sum(
                1 for p in holdout_2025 if p["market"] == "total" and p.get("won") is not None
            ),
            "spread_abs_edge_mean_2025_play": (
                round(
                    sum(p["abs_edge"] for p in holdout_2025 if p["market"] == "spread")
                    / max(1, sum(1 for p in holdout_2025 if p["market"] == "spread")),
                    3,
                )
            ),
        },
        "primary_holdout_2025": primary,
        "prior_2020_2024_evidence": prior_evidence,
        "walk_forward_by_season": by_season,
        "segments_2025": segments_2025,
        "green_segments_2025": green_segments,
        "yellow_segments_2025": yellow_segments,
        "best_segment_2025": best_segment,
        "overall": {
            "gate": overall_gate,
            "betting_product_selective_ready": betting_product_selective_ready,
            "interpretation": (
                "Selective PLAY holdout clears product floors."
                if betting_product_selective_ready
                else (
                    f"Full PLAY universe gate={primary['combined']['gate']}; "
                    f"best shrink segment={best_segment} "
                    f"({segments_2025.get(best_segment, {}).get('gate')}). "
                    "Do NOT claim ~60% or subscription GREEN unless a pre-registered "
                    "segment clears ATS+CLV with adequate n."
                )
            ),
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n")

    md = [
        "# NFL PLAY-only unused holdout",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Pre-registered policy",
        "",
        f"- Spread PLAY: `|edge| ≥ {SPREAD_PLAY_MIN}`",
        f"- Total PLAY: `{TOTAL_PLAY_MIN} ≤ |edge| < {TOTAL_PLAY_MAX}`",
        f"- Primary holdout season: **{PRIMARY_HOLDOUT_SEASON}**",
        f"- Floors: ATS ≥ {GATE_ATS_MIN:.4f} (stretch {GATE_ATS_STRETCH}), "
        f"CLV+ ≥ {GATE_CLV_POS_MIN} with n≥{GATE_CLV_N_MIN} (segment soft n≥{GATE_CLV_N_SOFT})",
        "",
        "## Primary holdout (2025 PLAY)",
        "",
        f"| Slice | n | ATS | ROI | CLV n | CLV+ | Gate |",
        f"| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for name, summ in primary.items():
        md.append(
            f"| {name} | {summ['n']} | {summ['hit_rate']} | {summ['roi']} | "
            f"{summ['n_clv']} | {summ['clv_positive_rate']} | **{summ['gate']}** |"
        )
    md += [
        "",
        f"**Overall selective gate:** `{overall_gate}` · "
        f"betting_product_selective_ready=`{betting_product_selective_ready}`",
        "",
        f"Best shrink segment: `{best_segment}` → "
        f"`{json.dumps(segments_2025.get(best_segment), indent=2) if best_segment else None}`",
        "",
        "## GREEN / YELLOW segments (2025)",
        "",
        f"- GREEN: {green_segments or 'none'}",
        f"- YELLOW: {yellow_segments or 'none'}",
        "",
        "## Prior evidence (2020–2024 PLAY, not unused)",
        "",
        "```json",
        json.dumps(prior_evidence, indent=2),
        "```",
        "",
        "## Walk-forward by season (locked tags)",
        "",
        "```json",
        json.dumps(by_season, indent=2),
        "```",
        "",
        "## Honesty",
        "",
        report["overall"]["interpretation"],
        "",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")

    print(json.dumps({
        "inventory": report["inventory"],
        "primary_holdout_2025": primary,
        "overall": report["overall"],
        "best_segment_2025": best_segment,
        "green_segments_2025": green_segments,
        "yellow_segments_2025": yellow_segments,
        "wrote": str(OUT_JSON),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
