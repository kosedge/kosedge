#!/usr/bin/env python3
"""Read-only CFB spread Tag holdout vs closing line (no product retune).

Reconstructs the live web Tag rule (cfb-trusted-market.ts cfbEdgeTag 4.0 / 2.5)
against SportsDataverse closing-ish spreads using the published KEI path
(apply_bias_guard on hist-cal proxy model spreads).

Does NOT change pack / KEI / thresholds. Totals and NFL out of scope.

Usage:
  PYTHONPATH=services/model-service \\
    python3 scripts/cfb/run_spread_tag_close_holdout.py --seasons 2023,2024,2025
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "model-service"))

from src.services.cfb_season_engine.cfb_kei import (  # noqa: E402
    BIAS_GUARD_VERSION,
    apply_bias_guard,
)
from src.services.cfb_season_engine.historical_calibration import (  # noqa: E402
    run_historical_backtest,
)

# Live web Tag constants (apps/web/lib/cfb-trusted-market.ts) — NOT Python
# week-varying steady thresholds (2.5 / 1.5).
PLAY_EDGE_PTS = 4.0
LEAN_EDGE_PTS = 2.5
ABSURD_VS_KEI_PTS = 12.0
SINGLE_BOOK_ABSURD_PTS = 8.0

# Hist-cal 2026-08-05 used 2023–2024 as primary for knob decisions.
CONTAMINATED_SEASONS = frozenset({2023, 2024})
# Full sample included 2022–2025; 2025 was not the primary decision set.
UNUSED_PRIMARY_SEASONS = frozenset({2025})


def trust_close_as_market(
    *,
    kei: float,
    close_home: float,
    treat_close_as_consensus: bool,
) -> Tuple[bool, Optional[float], str]:
    """Mirror trustCfbMarket for a single home-signed close (no open).

    When treat_close_as_consensus=True (default): SDV resolved close is a
    consensus/closing-ish number, not a lone junk book → bookCount=2, only
    absurd≥12 applies. When False: strict single-book≥8 also applies.
    """
    gap = abs(close_home - kei)
    if gap >= ABSURD_VS_KEI_PTS:
        return False, None, "absurd_vs_kei"
    if not treat_close_as_consensus and gap >= SINGLE_BOOK_ABSURD_PTS:
        return False, None, "single_book_outlier"
    return True, close_home, "close_consensus" if treat_close_as_consensus else "close_single"


def edge_tag(abs_edge: Optional[float]) -> str:
    if abs_edge is None or not math.isfinite(abs_edge):
        return "PASS"
    if abs_edge >= PLAY_EDGE_PTS:
        return "PLAY"
    if abs_edge >= LEAN_EDGE_PTS:
        return "LEAN"
    return "PASS"


def year_label(season: int) -> str:
    if season in UNUSED_PRIMARY_SEASONS:
        return "unused"
    if season in CONTAMINATED_SEASONS:
        return "contaminated"
    return "confirmatory"


def summarize_band(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    graded = [r for r in rows if r.get("ats_hit") is not None]
    wins = sum(1 for r in graded if r["ats_hit"] is True)
    losses = sum(1 for r in graded if r["ats_hit"] is False)
    pushes = n - len(graded)
    # −110 unit stake: win +100/110, lose −1; pushes excluded from ROI denom.
    stake_n = wins + losses
    pnl = wins * (100.0 / 110.0) - losses * 1.0
    roi = (pnl / stake_n) if stake_n else None
    ats = (wins / stake_n) if stake_n else None
    edges = [float(r["abs_edge"]) for r in rows if r.get("abs_edge") is not None]
    mean_abs_edge = (sum(edges) / len(edges)) if edges else None
    return {
        "n": n,
        "n_ats": stake_n,
        "n_push": pushes,
        "ats_hit_rate": round(ats, 4) if ats is not None else None,
        "ats_wins": wins,
        "ats_losses": losses,
        "roi_minus_110": round(roi, 4) if roi is not None else None,
        "pnl_units_minus_110": round(pnl, 4) if stake_n else None,
        "mean_abs_edge": round(mean_abs_edge, 4) if mean_abs_edge is not None else None,
        "clv_plus_rate": None,
        "clv_note": "CLV unavailable — SDV betting has close only (no owned open≠close)",
    }


def play_band_key(abs_edge: float) -> Optional[str]:
    """PLAY sub-band labels for Task 2c split (same Tag join)."""
    if abs_edge < PLAY_EDGE_PTS:
        return None
    if abs_edge < 7.0:
        return "PLAY_4_7"
    return "PLAY_ge_7"


def summarize_play_splits(subset: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """PLAY all + [4,7) + ≥7 + optional [4,10) when n allows."""
    plays = [x for x in subset if x["tag"] == "PLAY"]
    b47 = [x for x in plays if 4.0 <= float(x["abs_edge"]) < 7.0]
    bge7 = [x for x in plays if float(x["abs_edge"]) >= 7.0]
    b410 = [x for x in plays if 4.0 <= float(x["abs_edge"]) < 10.0]
    out: Dict[str, Any] = {
        "PLAY": summarize_band(plays),
        "PLAY_4_7": {
            **summarize_band(b47),
            "band": "[4.0, 7.0)",
        },
        "PLAY_ge_7": {
            **summarize_band(bge7),
            "band": ">=7.0",
        },
        "LEAN": summarize_band([x for x in subset if x["tag"] == "LEAN"]),
    }
    # Optional third slice — always compute; consumers can ignore if thin.
    out["PLAY_4_10"] = {
        **summarize_band(b410),
        "band": "[4.0, 10.0)",
        "optional": True,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="CFB spread Tag vs close holdout")
    ap.add_argument("--seasons", default="2023,2024,2025")
    ap.add_argument(
        "--stamp",
        default=date.today().strftime("%Y%m%d"),
    )
    ap.add_argument(
        "--strict-single-book",
        action="store_true",
        help="Treat close as single book (also apply ≥8 untrusted gate)",
    )
    args = ap.parse_args()
    seasons = [int(x.strip()) for x in args.seasons.split(",") if x.strip()]
    out_dir = ROOT / "data" / "ops" / f"cfb-spread-tag-close-holdout-{args.stamp}"
    cache_dir = out_dir / "cache"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"== hist-cal backtest seasons={seasons} ==")
    payload = run_historical_backtest(seasons=seasons, cache_dir=cache_dir)
    rows_in = payload.get("rows") or []
    if not rows_in:
        # run_historical_backtest pops rows into graded then drops from summary;
        # check return shape.
        print("ERROR: no graded rows returned", list(payload.keys()))
        return 2

    treat_consensus = not args.strict_single_book
    tagged: List[Dict[str, Any]] = []
    trust_counts: Dict[str, int] = defaultdict(int)
    tag_counts: Dict[str, int] = defaultdict(int)

    for r in rows_in:
        model = float(r["model_spread_home"])
        close = float(r["close_spread_home"])
        week = int(r["week"])
        kei, _guard = apply_bias_guard(model, week=week)
        kei = round(float(kei), 2)
        trusted, market, reason = trust_close_as_market(
            kei=kei,
            close_home=close,
            treat_close_as_consensus=treat_consensus,
        )
        trust_counts[reason] += 1
        if not trusted or market is None:
            tag_counts["PASS_untrusted"] += 1
            continue

        # Home-spread edge: market − KEI; positive ⇒ KEI likes home more than close.
        edge = market - kei
        abs_edge = abs(edge)
        tag = edge_tag(abs_edge)
        tag_counts[tag] += 1
        if tag == "PASS":
            continue

        actual_margin = float(r["actual_margin"])
        cover_margin = actual_margin + close
        if abs(cover_margin) < 1e-9:
            ats_hit = None  # push
        else:
            home_covers = cover_margin > 0
            pick_home = edge > 0
            ats_hit = bool(home_covers) if pick_home else (not bool(home_covers))

        tagged.append(
            {
                "game_id": r["game_id"],
                "season": int(r["season"]),
                "week": week,
                "home": r["home"],
                "away": r["away"],
                "year_label": year_label(int(r["season"])),
                "model_spread_home": model,
                "kei_spread_home": kei,
                "close_spread_home": close,
                "trust_reason": reason,
                "edge_home": round(edge, 4),
                "abs_edge": round(abs_edge, 4),
                "tag": tag,
                "play_band": play_band_key(abs_edge) if tag == "PLAY" else None,
                "tag_side": "home" if edge > 0 else "away",
                "ats_hit": ats_hit,
                "actual_margin": actual_margin,
            }
        )

    def _block(pred) -> Dict[str, Any]:
        subset = [x for x in tagged if pred(x)]
        return summarize_play_splits(subset)

    by_label = {
        "unused": _block(lambda x: x["year_label"] == "unused"),
        "contaminated": _block(lambda x: x["year_label"] == "contaminated"),
        "confirmatory": _block(lambda x: x["year_label"] == "confirmatory"),
        "all_seasons_in_run": _block(lambda _x: True),
    }
    by_season: Dict[str, Any] = {}
    for s in seasons:
        by_season[str(s)] = {
            "year_label": year_label(s),
            **_block(lambda x, s=s: int(x["season"]) == s),
        }

    report = {
        "stamp": args.stamp,
        "rule": {
            "source": "apps/web/lib/cfb-trusted-market.ts cfbEdgeTag + trustCfbMarket",
            "play_pts": PLAY_EDGE_PTS,
            "lean_pts": LEAN_EDGE_PTS,
            "absurd_vs_kei": ABSURD_VS_KEI_PTS,
            "single_book_absurd": SINGLE_BOOK_ABSURD_PTS,
            "close_treated_as": "consensus_bookCount2"
            if treat_consensus
            else "single_book",
            "kei_path": f"apply_bias_guard ({BIAS_GUARD_VERSION}) on hist-cal proxy model_spread",
            "market_for_tag": "SDV espn_cfb_betting close (home_team_spread), home-signed",
            "ats_definition": (
                "Tag side vs close: home covers if actual_margin + close_spread > 0; "
                "push when cover_margin≈0 excluded from ATS/ROI"
            ),
            "roi_definition": "unit stake at −110: win +100/110, lose −1",
            "clv_definition": (
                "movement-CLV+: owned open≠close favoring Tag side; "
                "unavailable when only close exists"
            ),
            "play_band_splits": {
                "PLAY_4_7": "[4.0, 7.0) inclusive 4 exclusive 7",
                "PLAY_ge_7": ">=7.0",
                "PLAY_4_10": "[4.0, 10.0) optional third slice",
            },
        },
        "honesty": {
            "reconstruction": (
                "Hist-cal proxy: prior-year cfb_ratings + league-avg roster/QB — "
                "not live 2026 roster/SP+ KEI. Bias guard applied (published path)."
            ),
            "year_split": {
                "unused": sorted(UNUSED_PRIMARY_SEASONS),
                "contaminated_primary_hist_cal_knobs": sorted(CONTAMINATED_SEASONS),
                "note": (
                    "Hist-cal 2026-08-05 primary decisions on 2023–2024; "
                    "bias_guard coefficients also from that residual. "
                    "2025 is unused for knob year-split but still uses that guard."
                ),
            },
            "not_live_tag_at_open": (
                "Tag formed vs close (only available series), not vs open/best at post. "
                "This is KEI-vs-close band grading, not post-time Tag CLV."
            ),
        },
        "load": payload.get("load"),
        "n_games_projected": len(rows_in),
        "trust_reason_counts": dict(trust_counts),
        "tag_counts_including_pass": dict(tag_counts),
        "n_tagged_play_lean": len(tagged),
        "by_year_label": by_label,
        "by_season": by_season,
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # Keep a slim tagged sample for audit (first 30 PLAY + 30 LEAN).
    sample = [x for x in tagged if x["tag"] == "PLAY"][:30] + [
        x for x in tagged if x["tag"] == "LEAN"
    ][:30]
    (out_dir / "tagged_sample.json").write_text(
        json.dumps(sample, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["by_year_label"], indent=2))
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
