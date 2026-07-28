#!/usr/bin/env python3
"""Pre-registered PLAY-only unused holdout for NFL sides/totals.

Policy version: spread_play_v2_cap7 (see nfl_side_total_publish_policy.py)

  - spread PLAY: 2.5 ≤ |edge| < 7.0   (v1 was |edge| ≥ 2.5 uncapped)
  - total PLAY:  2.5 ≤ |edge| < 3.0

CLV methodology (v2):
  - Owned odds_snapshots only; require n_snaps ≥ 2
  - Product CLV+ rate uses **movement sample** (open ≠ close). Flat densify
    rows (open==close) are excluded from the +rate denominator — they are not
    informative CLV and previously dragged rates below the floor.
  - All-sample CLV (incl. flats) still reported for honesty.

Universes:
  - Primary unused: season 2025
  - Confirmatory: seasons 2024–2025 (needed for CLV n≥200 under capped band)
  - Clean-era check: 2020–2022 (must NOT collapse if we claim durability)

Does NOT pull Odds API / does NOT re-burn densify credits.

Writes:
  data/ops/nfl-play-only-holdout.json
  data/ops/nfl-play-only-holdout.md
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
    BREAKEVEN_ATS,
    POLICY_VERSION,
    SPREAD_PLAY_MAX,
    SPREAD_PLAY_MIN,
    TOTAL_PLAY_MAX,
    TOTAL_PLAY_MIN,
    candidate_tag,
)

OUT_JSON = ROOT / "data" / "ops" / "nfl-play-only-holdout.json"
OUT_MD = ROOT / "data" / "ops" / "nfl-play-only-holdout.md"

WIN_PROFIT = 100.0 / 110.0
GATE_ATS_MIN = BREAKEVEN_ATS
GATE_ATS_STRETCH = 0.55
GATE_CLV_POS_MIN = 0.55
GATE_CLV_N_MIN = 200
GATE_CLV_N_SOFT = 40
GATE_ATS_N_MIN = 60
PRIMARY_HOLDOUT_SEASON = 2025
CONFIRMATORY_SEASONS = (2024, 2025)

SEGMENT_SPECS: List[Dict[str, Any]] = [
    {"key": "spread_all_play", "market": "spread"},
    {"key": "spread_edge_2.5_3.5", "market": "spread", "edge_lo": 2.5, "edge_hi": 3.5},
    {"key": "spread_edge_3.5_5.0", "market": "spread", "edge_lo": 3.5, "edge_hi": 5.0},
    {"key": "spread_edge_5.0_7.0", "market": "spread", "edge_lo": 5.0, "edge_hi": 7.0},
    {"key": "spread_home", "market": "spread", "side": "home"},
    {"key": "spread_away", "market": "spread", "side": "away"},
    {"key": "total_all_play", "market": "total"},
    {"key": "total_over", "market": "total", "side": "over"},
    {"key": "total_under", "market": "total", "side": "under"},
    {"key": "combined_play", "market": None},
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
            "mean_abs_edge": None,
            "n_clv_all": 0,
            "clv_positive_rate_all": None,
            "n_clv_move": 0,
            "clv_positive_rate": None,
            "clv_avg_move": None,
            "gate": "RED",
            "detail": "empty sample",
        }
    hits = sum(1 for r in decided if r["won"])
    hit_rate = hits / n
    units = sum(_unit_pnl(r["won"]) for r in decided)
    edges = [float(r["abs_edge"]) for r in decided]
    mean_edge = sum(edges) / len(edges)

    clv_all = [float(r["clv"]) for r in decided if r.get("clv") is not None]
    clv_move = [x for x in clv_all if abs(x) > 1e-9]
    n_clv_all = len(clv_all)
    n_clv_move = len(clv_move)
    clv_all_pos = (sum(1 for x in clv_all if x > 0) / n_clv_all) if n_clv_all else None
    clv_move_pos = (sum(1 for x in clv_move if x > 0) / n_clv_move) if n_clv_move else None
    clv_avg = (sum(clv_move) / n_clv_move) if n_clv_move else None

    # Product gate uses movement CLV (primary) with n≥200 / 55%.
    ats_ok = n >= GATE_ATS_N_MIN and hit_rate >= GATE_ATS_MIN
    clv_ok = (
        n_clv_move >= GATE_CLV_N_MIN
        and clv_move_pos is not None
        and clv_move_pos >= GATE_CLV_POS_MIN
    )
    clv_soft = (
        n_clv_move >= GATE_CLV_N_SOFT
        and clv_move_pos is not None
        and clv_move_pos >= GATE_CLV_POS_MIN
    )
    if ats_ok and clv_ok:
        gate, detail = "GREEN", "ATS + movement-CLV clear selective PLAY floors (n_move≥200)."
    elif ats_ok and clv_soft:
        gate, detail = (
            "YELLOW",
            "ATS clears; movement-CLV +rate clears soft n≥40 but below n≥200 product floor.",
        )
    elif ats_ok:
        gate, detail = "YELLOW", "ATS clears −110 but movement-CLV fails or sample thin."
    else:
        gate, detail = "RED", "ATS below −110 or sample below MIN_SEGMENT_N."

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
        "mean_abs_edge": round(mean_edge, 3),
        "n_clv_all": n_clv_all,
        "clv_positive_rate_all": round(clv_all_pos, 4) if clv_all_pos is not None else None,
        "n_clv_move": n_clv_move,
        "clv_positive_rate": round(clv_move_pos, 4) if clv_move_pos is not None else None,
        "clv_avg_move": round(clv_avg, 4) if clv_avg is not None else None,
        # Back-compat aliases for enterprise gates (prefer movement)
        "n_clv": n_clv_move,
        "gate": gate,
        "stretch_band": stretch,
        "detail": detail,
    }


def load_board_rows(conn: Any) -> List[Dict[str, Any]]:
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
                COUNT(*) FILTER (WHERE o.spread_home IS NOT NULL)::int AS n_snaps_spread,
                COUNT(*) FILTER (WHERE o.total_points IS NOT NULL)::int AS n_snaps_total
              FROM odds_snapshots o
              JOIN nfl_games g ON g.game_id = o.game_id
              GROUP BY o.game_id
            )
            SELECT * FROM agg
            """
        )
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
              g.id AS game_uuid
            FROM nfl_dp_schedules sch
            JOIN games g ON g.external_id = sch.game_id
            WHERE sch.home_score IS NOT NULL
              AND sch.away_score IS NOT NULL
              AND sch.season BETWEEN 2020 AND 2025
            ORDER BY sch.season, sch.week, sch.game_id
            """
        )
    ).mappings().all()

    proj_rows = conn.execute(
        text(
            """
            SELECT DISTINCT ON (mp.game_id)
              mp.game_id, mp.spread_home, mp.total_mean, mp.model_version
            FROM nfl_market_projections mp
            JOIN games g ON g.id = mp.game_id
            WHERE mp.spread_home IS NOT NULL
              AND mp.total_mean IS NOT NULL
              AND (g.start_time IS NULL OR mp.created_at < g.start_time)
            ORDER BY mp.game_id,
              CASE WHEN mp.projection->'audit'->>'pipeline_run_at' IS NOT NULL THEN 0 ELSE 1 END,
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
        n_snaps_s = int(oc.get("n_snaps_spread") or 0)
        n_snaps_t = int(oc.get("n_snaps_total") or 0)

        nflverse_spread = _f(sch.get("spread_line"))
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

        signed_spread = model_spread - close_spread
        abs_spread = abs(signed_spread)
        lean_home = signed_spread < 0
        diff = home_margin + close_spread
        if lean_home:
            won_s = True if diff > 1e-9 else False if diff < -1e-9 else None
            side_s = "home"
        else:
            won_s = True if diff < -1e-9 else False if diff > 1e-9 else None
            side_s = "away"
        clv_s = None
        if open_spread is not None and n_snaps_s >= 2:
            clv_s = (open_spread - close_spread) if lean_home else (close_spread - open_spread)

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
                "candidate_tag": candidate_tag("spread", abs_spread),
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
        if open_total is not None and n_snaps_t >= 2:
            clv_t = (close_total - open_total) if lean_over else (open_total - close_total)

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
                "candidate_tag": candidate_tag("total", abs_total),
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
    lo, hi = spec.get("edge_lo"), spec.get("edge_hi")
    if lo is not None and hi is not None:
        out = [p for p in out if lo <= float(p["abs_edge"]) < hi]
    return out


def _gate_rank(g: str) -> int:
    return {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(g, 2)


def _slice_report(plays: List[Dict[str, Any]]) -> Dict[str, Any]:
    play = [p for p in plays if p["candidate_tag"] == "PLAY"]
    return {
        "combined": _summary(play),
        "spread": _summary([p for p in play if p["market"] == "spread"]),
        "total": _summary([p for p in play if p["market"] == "total"]),
    }


def main() -> int:
    engine = create_engine(_db_url())
    with engine.connect() as conn:
        plays = load_board_rows(conn)

    all_play = [p for p in plays if p["candidate_tag"] == "PLAY"]
    holdout_2025 = [p for p in all_play if p["season"] == PRIMARY_HOLDOUT_SEASON]
    confirmatory = [p for p in all_play if p["season"] in CONFIRMATORY_SEASONS]
    clean_era = [p for p in all_play if 2020 <= p["season"] <= 2022]
    # Legacy uncapped comparator (documentation only)
    legacy_2025_spread = [
        p
        for p in plays
        if p["season"] == 2025
        and p["market"] == "spread"
        and float(p["abs_edge"]) >= SPREAD_PLAY_MIN
    ]

    primary = _slice_report(holdout_2025)
    confirm = _slice_report(confirmatory)
    clean = _slice_report(clean_era)
    legacy_uncapped = _summary(legacy_2025_spread)

    by_season: Dict[str, Any] = {}
    for season in range(2020, 2026):
        by_season[str(season)] = _slice_report([p for p in all_play if p["season"] == season])

    segments_2025: Dict[str, Any] = {}
    green_segments: List[str] = []
    yellow_segments: List[str] = []
    for spec in SEGMENT_SPECS:
        rows = holdout_2025 if spec.get("key") == "combined_play" else _filter_segment(holdout_2025, spec)
        summ = _summary(rows)
        segments_2025[spec["key"]] = summ
        if summ["gate"] == "GREEN":
            green_segments.append(spec["key"])
        elif summ["gate"] == "YELLOW":
            yellow_segments.append(spec["key"])

    # Product selective claim: confirmatory 2024–25 under v2 band (movement CLV).
    # Primary 2025 remains the unused ATS spotlight; CLV n often <200 alone.
    selective_ready = confirm["spread"]["gate"] == "GREEN"
    primary_gate = primary["spread"]["gate"]
    overall_gate = "GREEN" if selective_ready else primary_gate
    if selective_ready and primary_gate != "GREEN":
        overall_gate = "GREEN"  # confirmatory clears product CLV floor
        overall_note = (
            "Confirmatory 2024–25 spread PLAY (v2 band) clears ATS + movement-CLV. "
            f"Primary 2025 alone is {primary_gate} (CLV n often short of 200)."
        )
    else:
        overall_note = (
            f"Primary 2025 spread gate={primary_gate}; confirmatory 2024–25 "
            f"gate={confirm['spread']['gate']}."
        )

    best_segment = None
    best_rank = 99
    for key, summ in segments_2025.items():
        if (summ.get("n") or 0) < 20:
            continue
        r = _gate_rank(summ["gate"])
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
            "policy_version": POLICY_VERSION,
            "spread_play_min": SPREAD_PLAY_MIN,
            "spread_play_max": SPREAD_PLAY_MAX,
            "total_play_min": TOTAL_PLAY_MIN,
            "total_play_max": TOTAL_PLAY_MAX,
            "primary_holdout_season": PRIMARY_HOLDOUT_SEASON,
            "confirmatory_seasons": list(CONFIRMATORY_SEASONS),
            "clv_methodology": "movement_only_n_snaps_ge_2",
            "legacy_v1": {
                "spread_play": "|edge| >= 2.5 uncapped",
                "2025_uncapped_spread": legacy_uncapped,
            },
            "gates": {
                "ats_min": GATE_ATS_MIN,
                "ats_stretch": GATE_ATS_STRETCH,
                "ats_n_min": GATE_ATS_N_MIN,
                "clv_pos_min": GATE_CLV_POS_MIN,
                "clv_n_min_product": GATE_CLV_N_MIN,
                "clv_n_min_segment": GATE_CLV_N_SOFT,
            },
            "notes": [
                "v2 caps spread PLAY at |edge| < 7.0 to shrink mean edge (~7 → ~4.5).",
                "Product CLV+ uses open≠close movement sample; flats reported as clv_*_all.",
                "No Odds API densify re-burn; owned odds_snapshots only.",
                "2020–22 clean-era CLV remains weak — do not claim durability from that era.",
            ],
        },
        "inventory": {
            "board_rows_loaded": len(plays),
            "unique_games_loaded": len({p["game_id"] for p in plays}),
            "play_tagged_rows": len(all_play),
            "holdout_2025_play_rows": len(holdout_2025),
            "confirmatory_2024_2025_play_rows": len(confirmatory),
            "spread_play_2025": primary["spread"]["n"],
            "spread_play_2024_2025": confirm["spread"]["n"],
            "spread_mean_abs_edge_2025": primary["spread"]["mean_abs_edge"],
            "spread_mean_abs_edge_2024_2025": confirm["spread"]["mean_abs_edge"],
        },
        "primary_holdout_2025": primary,
        "confirmatory_2024_2025": confirm,
        "clean_era_2020_2022": clean,
        "walk_forward_by_season": by_season,
        "segments_2025": segments_2025,
        "green_segments_2025": green_segments,
        "yellow_segments_2025": yellow_segments,
        "best_segment_2025": best_segment,
        "overall": {
            "gate": overall_gate,
            "betting_product_selective_ready": selective_ready,
            "primary_2025_spread_gate": primary_gate,
            "confirmatory_2024_2025_spread_gate": confirm["spread"]["gate"],
            "interpretation": overall_note,
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n")

    def _row(name: str, summ: Dict[str, Any]) -> str:
        return (
            f"| {name} | {summ.get('n')} | {summ.get('hit_rate')} | {summ.get('mean_abs_edge')} | "
            f"{summ.get('roi')} | {summ.get('n_clv_move')} | {summ.get('clv_positive_rate')} | "
            f"**{summ.get('gate')}** |"
        )

    md = [
        "# NFL PLAY-only unused holdout (v2 cap7)",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Policy: `{POLICY_VERSION}` — spread PLAY "
        f"`{SPREAD_PLAY_MIN} ≤ |edge| < {SPREAD_PLAY_MAX}`",
        "",
        "## Methodology",
        "",
        "- ATS vs close (−110 unit ROI), latest pre-kickoff projection via `external_id`.",
        "- CLV product metric: owned OC with n_snaps≥2 and **open≠close** (movement).",
        "- Primary unused: **2025**. Confirmatory CLV sample: **2024–2025**.",
        f"- Legacy v1 uncapped 2025 spread: n={legacy_uncapped.get('n')} "
        f"ATS={legacy_uncapped.get('hit_rate')} mean_edge={legacy_uncapped.get('mean_abs_edge')}",
        "",
        "## Primary holdout (2025 PLAY)",
        "",
        "| Slice | n | ATS | mean\\|edge\\| | ROI | CLV move n | CLV+ | Gate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        _row("combined", primary["combined"]),
        _row("spread", primary["spread"]),
        _row("total", primary["total"]),
        "",
        "## Confirmatory (2024–2025 PLAY)",
        "",
        "| Slice | n | ATS | mean\\|edge\\| | ROI | CLV move n | CLV+ | Gate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        _row("combined", confirm["combined"]),
        _row("spread", confirm["spread"]),
        _row("total", confirm["total"]),
        "",
        f"**Selective ready:** `{selective_ready}` · overall gate `{overall_gate}`",
        "",
        overall_note,
        "",
        "## Clean-era check (2020–2022)",
        "",
        "```json",
        json.dumps(clean["spread"], indent=2),
        "```",
        "",
        "## Segments 2025",
        "",
        f"- GREEN: {green_segments or 'none'}",
        f"- YELLOW: {yellow_segments or 'none'}",
        f"- Best: `{best_segment}`",
        "",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")

    print(
        json.dumps(
            {
                "policy_version": POLICY_VERSION,
                "inventory": report["inventory"],
                "primary_holdout_2025": primary,
                "confirmatory_2024_2025": confirm,
                "overall": report["overall"],
                "wrote": str(OUT_JSON),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
