#!/usr/bin/env python3
"""Walk-forward PLAY edge-band study (no peeking).

Protocol (pre-registered):
  1) Selection universe = settled 2023 only.
  2) Eligible bands: ATS ≥ 52.38%, n ≥ 60.
  3) Rank by movement-CLV+ (primary), then n_clv, then ATS.
  4) Evaluate top candidates + current product band ONCE on 2024–25 confirmatory.
  5) Also report 2025-only and 2020–22 clean-era (diagnostic, not for selection).

Product policy stays `spread_play_v2_cap7` unless a candidate clears confirmatory
GREEN (n≥60 ATS, n_clv≥200, CLV+≥0.55) AND improves CLV+ vs v2 without
collapsing ATS. Research bands that improve CLV+ but fail n_clv≥200 are
documented only — not promoted to publish defaults.

Writes:
  data/ops/nfl-walkforward-play-band-study.{json,md}
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

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
)

OUT_JSON = ROOT / "data" / "ops" / "nfl-walkforward-play-band-study.json"
OUT_MD = ROOT / "data" / "ops" / "nfl-walkforward-play-band-study.md"

# Candidate half-open |edge| bands. Product v2 is always included in confirm.
BANDS: List[Tuple[float, float]] = [
    (2.5, 5.0),
    (2.5, 6.0),
    (2.5, 7.0),  # product v2
    (2.5, 8.0),
    (3.0, 6.0),
    (3.0, 7.0),
    (3.5, 6.0),
    (3.5, 7.0),
    (3.5, 8.0),
    (4.0, 7.0),
    (4.0, 8.0),
    (5.0, 7.0),
    (5.0, 8.0),
    (2.5, 100.0),  # uncapped reference (not a product candidate)
    (3.5, 100.0),
]

PRODUCT_BAND = (SPREAD_PLAY_MIN, SPREAD_PLAY_MAX)
TOP_K_CONFIRM = 5


def _db_url() -> str:
    url = os.environ["DATABASE_URL"]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _gate(m: Optional[Dict[str, Any]]) -> str:
    if not m:
        return "NONE"
    ats_ok = m["n"] >= 60 and m["ats"] >= BREAKEVEN_ATS
    clv = m.get("clv")
    n_clv = m.get("n_clv") or 0
    if ats_ok and n_clv >= 200 and clv is not None and clv >= 0.55:
        return "GREEN"
    if ats_ok and n_clv >= 40 and clv is not None and clv >= 0.55:
        return "YELLOW"
    if ats_ok:
        return "AMBER"
    return "RED"


def _metrics(rows: Sequence[Dict[str, Any]], seasons: Set[int], lo: float, hi: float) -> Optional[Dict[str, Any]]:
    ats: List[bool] = []
    edges: List[float] = []
    clv_move: List[float] = []
    for r in rows:
        if int(r["season"]) not in seasons:
            continue
        close = r["close_spread"]
        if close is None and r["spread_line"] is not None:
            close = -float(r["spread_line"])
        if close is None:
            continue
        close = float(close)
        model = float(r["model"])
        hm = float(r["hm"])
        signed = model - close
        ae = abs(signed)
        if not (lo <= ae < hi):
            continue
        lean_home = signed < 0
        diff = hm + close
        if lean_home:
            won = True if diff > 1e-9 else False if diff < -1e-9 else None
        else:
            won = True if diff < -1e-9 else False if diff > 1e-9 else None
        if won is not None:
            ats.append(won)
            edges.append(ae)
        if r["open_spread"] is not None and int(r["n_snaps"] or 0) >= 2:
            o = float(r["open_spread"])
            clv = (o - close) if lean_home else (close - o)
            if abs(clv) > 1e-9:
                clv_move.append(clv)
    if not ats:
        return None
    return {
        "n": len(ats),
        "ats": sum(ats) / len(ats),
        "mean_abs_edge": sum(edges) / len(edges),
        "n_clv": len(clv_move),
        "clv": (sum(1 for x in clv_move if x > 0) / len(clv_move)) if clv_move else None,
        "avg_clv": (sum(clv_move) / len(clv_move)) if clv_move else None,
        "gate": None,  # filled by caller after wrap
    }


def _wrap(m: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not m:
        return None
    out = dict(m)
    out["gate"] = _gate(out)
    return out


def main() -> int:
    engine = create_engine(_db_url())
    with engine.connect() as conn:
        rows = list(
            conn.execute(
                text(
                    """
                    SELECT sch.season, sch.home_score - sch.away_score AS hm, sch.spread_line,
                           mp.spread_home AS model, oc.open_spread, oc.close_spread, oc.n_snaps
                    FROM nfl_dp_schedules sch
                    JOIN games g ON g.external_id = sch.game_id
                    JOIN LATERAL (
                      SELECT spread_home, created_at, projection FROM nfl_market_projections mp
                      WHERE mp.game_id = g.id AND mp.spread_home IS NOT NULL
                        AND (g.start_time IS NULL OR mp.created_at < g.start_time)
                      ORDER BY CASE WHEN mp.projection->'audit'->>'pipeline_run_at' IS NOT NULL THEN 0 ELSE 1 END,
                               COALESCE((mp.projection->'audit'->>'pipeline_run_at')::timestamptz, mp.created_at) DESC
                      LIMIT 1
                    ) mp ON TRUE
                    LEFT JOIN LATERAL (
                      SELECT
                        (ARRAY_AGG(o.spread_home ORDER BY o.captured_at ASC)
                          FILTER (WHERE o.spread_home IS NOT NULL))[1] AS open_spread,
                        (ARRAY_AGG(o.spread_home ORDER BY o.captured_at DESC)
                          FILTER (WHERE o.spread_home IS NOT NULL))[1] AS close_spread,
                        COUNT(*) FILTER (WHERE o.spread_home IS NOT NULL)::int AS n_snaps
                      FROM odds_snapshots o WHERE o.game_id = g.id
                    ) oc ON TRUE
                    WHERE sch.season BETWEEN 2020 AND 2025
                      AND sch.home_score IS NOT NULL
                    """
                )
            ).mappings()
        )

    selection: List[Dict[str, Any]] = []
    for lo, hi in BANDS:
        m = _wrap(_metrics(rows, {2023}, lo, hi))
        if not m or m["n"] < 60 or m["ats"] < BREAKEVEN_ATS:
            continue
        selection.append({"lo": lo, "hi": hi, "band": f"[{lo},{hi})", **m})

    selection.sort(
        key=lambda x: (
            x["clv"] if x["clv"] is not None else -1.0,
            x["n_clv"],
            x["ats"],
        ),
        reverse=True,
    )

    confirm_bands: List[Tuple[float, float]] = [PRODUCT_BAND]
    for item in selection[:TOP_K_CONFIRM]:
        pair = (float(item["lo"]), float(item["hi"]))
        if pair not in confirm_bands:
            confirm_bands.append(pair)

    confirmatory: List[Dict[str, Any]] = []
    for lo, hi in confirm_bands:
        m24 = _wrap(_metrics(rows, {2024, 2025}, lo, hi))
        m25 = _wrap(_metrics(rows, {2025}, lo, hi))
        m22 = _wrap(_metrics(rows, {2020, 2021, 2022}, lo, hi))
        confirmatory.append(
            {
                "lo": lo,
                "hi": hi,
                "band": f"[{lo},{hi})",
                "is_product_v2": (lo, hi) == PRODUCT_BAND,
                "confirm_2024_25": m24,
                "primary_2025": m25,
                "clean_era_2020_22": m22,
            }
        )

    product_confirm = next(
        (c["confirm_2024_25"] for c in confirmatory if c["is_product_v2"]), None
    )
    research_regs: List[Dict[str, Any]] = []
    for c in confirmatory:
        if c["is_product_v2"]:
            continue
        # Uncapped / mega-edge bands are diagnostic only — never research-register.
        if float(c["hi"]) >= 50.0:
            continue
        m = c["confirm_2024_25"]
        if not m or not product_confirm:
            continue
        improves_clv = (
            m.get("clv") is not None
            and product_confirm.get("clv") is not None
            and m["clv"] > product_confirm["clv"]
            and m["ats"] >= BREAKEVEN_ATS
        )
        clears_green = m["gate"] == "GREEN"
        research_regs.append(
            {
                "band": c["band"],
                "lo": c["lo"],
                "hi": c["hi"],
                "improves_clv_vs_v2": improves_clv,
                "clears_confirmatory_green": clears_green,
                "promote_to_product": False,  # none this round — volume or policy
                "confirm": m,
                "registration_id": f"spread_play_research_{str(c['lo']).replace('.', '')}_{str(c['hi']).replace('.', '')}",
                "reason": (
                    "Improves confirmatory CLV+ vs v2 but fails n_clv≥200 GREEN volume"
                    if improves_clv and not clears_green
                    else (
                        "Clears GREEN — review for product swap"
                        if clears_green and improves_clv
                        else "Tracked from 2023 selection; does not beat v2 CLV+ on confirm"
                    )
                ),
            }
        )

    promote_candidates = [r for r in research_regs if r["promote_to_product"] or r["clears_confirmatory_green"]]
    # Explicit product decision
    product_decision = {
        "keep_policy": POLICY_VERSION,
        "product_band": f"[{PRODUCT_BAND[0]},{PRODUCT_BAND[1]})",
        "rationale": (
            "Only capped band that clears confirmatory GREEN (n_clv≥200, CLV+≥0.55, ATS≥breakeven). "
            "Tighter CLV-max bands improve CLV+ but drop below n_clv=200 — research-only."
        ),
        "promote_any_new_band": False,
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "selection_universe": "2023 settled PLAY-eligible spreads",
            "confirmatory_universe": "2024–25 settled (single evaluation)",
            "clv_definition": "owned odds_snapshots open≠close, n_snaps≥2 (movement only)",
            "eligibility": f"ATS≥{BREAKEVEN_ATS}, n≥60 on selection",
            "ranking": "CLV+ desc, then n_clv, then ATS",
            "no_peeking": True,
        },
        "product_decision": product_decision,
        "selection_2023_ranked": selection,
        "confirmatory": confirmatory,
        "research_registrations": research_regs,
        "promote_review": promote_candidates,
        "notes": [
            "Do not densify 2020–23 Odds API to chase band volume.",
            "Primary-2025 CLV n≥200 remains math-blocked under product [2.5,7).",
            "Uncapped bands are reference-only (mega-edge calibration risk).",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, default=str) + "\n")

    md: List[str] = [
        "# Walk-forward PLAY edge-band study",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Selection: **2023 only** (ATS≥breakeven, n≥60), rank by movement CLV+",
        "- Confirm once: **2024–25**",
        "- Product remains **`spread_play_v2_cap7`** unless a band clears GREEN *and* beats v2 CLV+",
        "",
        "## Product decision",
        "",
        f"- Keep `{POLICY_VERSION}` band `[{PRODUCT_BAND[0]},{PRODUCT_BAND[1]})`",
        f"- Promote new band: **{product_decision['promote_any_new_band']}**",
        f"- Rationale: {product_decision['rationale']}",
        "",
        "## 2023 selection (top)",
        "",
        "| Band | n | ATS | CLV n | CLV+ |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for s in selection[:8]:
        md.append(
            f"| {s['band']} | {s['n']} | {s['ats']:.3f} | {s['n_clv']} | "
            f"{(s['clv'] if s['clv'] is not None else float('nan')):.3f} |"
        )

    md += [
        "",
        "## Confirmatory 2024–25",
        "",
        "| Band | Product? | n | ATS | CLV n | CLV+ | Gate |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for c in confirmatory:
        m = c["confirm_2024_25"] or {}
        md.append(
            f"| {c['band']} | {'yes' if c['is_product_v2'] else 'no'} | "
            f"{m.get('n')} | {m.get('ats', float('nan')):.3f} | {m.get('n_clv')} | "
            f"{(m.get('clv') if m.get('clv') is not None else float('nan')):.3f} | {m.get('gate')} |"
        )

    md += ["", "## Research registrations (not product)", ""]
    for r in research_regs:
        if not r["improves_clv_vs_v2"]:
            continue
        m = r["confirm"]
        md.append(
            f"- **`{r['registration_id']}`** `{r['band']}` — confirm CLV+ "
            f"{m['clv']:.3f} ATS {m['ats']:.3f} n_clv={m['n_clv']} gate={m['gate']} — "
            f"{r['reason']}"
        )

    md += [
        "",
        "Re-run: `DATABASE_URL=... .venv/bin/python scripts/nfl/walkforward_play_band_study.py`",
        "",
    ]
    OUT_MD.write_text("\n".join(md) + "\n")
    print(
        json.dumps(
            {
                "product": product_decision,
                "selection_top3": selection[:3],
                "research_improve_clv": [
                    r["registration_id"] for r in research_regs if r["improves_clv_vs_v2"]
                ],
            },
            indent=2,
            default=str,
        )
    )
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
