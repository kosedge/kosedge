#!/usr/bin/env python3
"""NFL Spread Validation Lab runner — Protocol v1.0 (FROZEN).

Reads owned ops artifacts only. Does not invent odds, rematerialize boards,
or flip live PLAY/LEAN/PASS tags. Missing series → N/A—DATA GAP.

Pipeline stages (protocol §11):
  prediction → timestamped market → outcome → error → calibration →
  edge bucket → CLV → regime → threshold evaluation → grades → influence

Usage:
  python3 scripts/lab/nfl_spread_validation_v1.py

Writes:
  data/ops/lab/nfl-spread-scorecard-v1.json
  docs/lab/NFL_SPREAD_SCORECARD_v1.md
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]

PROTOCOL_VERSION = "nfl-spread-validation-protocol-v1.0"
PROTOCOL_DOC = "docs/lab/NFL_SPREAD_VALIDATION_PROTOCOL_v1.md"
COS_SIGN = "Chief of Staff — 2026-09-04 — Protocol v1.0"

# Frozen criteria (protocol §2–§9) — do not retune after seeing results.
BREAKEVEN_ATS = 0.5238
ATS_STRETCH = 0.55
MIN_N_OVERALL = 200
MIN_N_BUCKET = 40
MIN_N_PLAY_ATS = 60
MIN_N_CLV_GREEN = 200
MIN_N_CLV_SOFT = 40
CLV_POS_MIN = 0.55
CLV_POS_RED = 0.50
CLV_N_RED = 100
BIAS_GREEN_MAX = 2.0
BIAS_RED_MIN = 3.0
MAE_YELLOW_TOL = 0.15  # within 15% of market benchmark
MARGIN_MAE_YELLOW = 10.5
MARGIN_MAE_SECONDARY = 9.5

BUCKETS = [
    ("noise", 0.0, 1.1),
    ("lean_band", 1.1, 2.5),
    ("play_low", 2.5, 3.5),
    ("play_mid", 3.5, 5.0),
    ("play_high", 5.0, 7.0),
    ("mega_edge", 7.0, None),
]

# Artifact paths (prefer existing gate/holdout JSON — no new scrapes).
HOLDOUT_PATH = ROOT / "data" / "ops" / "nfl-play-only-holdout.json"
GRADING_CANDIDATES = [
    ROOT / "data" / "ops" / "nfl-kav-grading-after.json",
    ROOT / "data" / "ops" / "nfl-odds-open-close-grading.json",
    ROOT / "data" / "ops" / "nfl-kav-grading-before.json",
]
SUPERVISED_CANDIDATES = [
    ROOT / "data" / "ops" / "nfl-kav-supervised-retrain-v3.json",
]
ENTERPRISE_GATES_PATH = ROOT / "data" / "ops" / "nfl-enterprise-gates-latest.json"
VEGAS_PATH = ROOT / "data" / "ops" / "nfl-vegas-benchmark-report.json"

OUT_JSON = ROOT / "data" / "ops" / "lab" / "nfl-spread-scorecard-v1.json"
OUT_MD = ROOT / "docs" / "lab" / "NFL_SPREAD_SCORECARD_v1.md"

DATA_GAP = "N/A—DATA GAP"
GRADE_GAP = "N/A—DATA_GAP"


def _load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _load_first(paths: List[Path]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    for p in paths:
        d = _load(p)
        if d is not None:
            return d, str(p.relative_to(ROOT))
    return None, None


def _wilson_ci(hits: int, n: int, z: float = 1.96) -> Optional[Tuple[float, float]]:
    if n <= 0:
        return None
    p = hits / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - margin), min(1.0, center + margin))


def _pct(x: Optional[float]) -> str:
    if x is None:
        return DATA_GAP
    return f"{100.0 * x:.2f}%"


def _num(x: Optional[float], digits: int = 4) -> str:
    if x is None:
        return DATA_GAP
    return f"{x:.{digits}f}"


def _grade_predictive(
    *,
    n: int,
    model_mae: Optional[float],
    market_mae: Optional[float],
    margin_mae: Optional[float],
    signed_bias: Optional[float],
    close_missing_rate: Optional[float],
) -> Tuple[str, str]:
    """Apply protocol §8.1. Missing close series → DATA GAP."""
    if close_missing_rate is not None and close_missing_rate >= 0.20:
        return GRADE_GAP, "Closing lines/finals missing for ≥20% of intended slate."
    if model_mae is None or market_mae is None or n < 100:
        if model_mae is None or market_mae is None:
            return GRADE_GAP, "Model or market spread MAE series unavailable."
        return "YELLOW", f"Thin sample n={n} (<100 for RED/GREEN MAE gates)."

    ratio = model_mae / market_mae if market_mae > 0 else None
    within_15 = ratio is not None and ratio <= (1.0 + MAE_YELLOW_TOL)
    beats_market = model_mae <= market_mae
    margin_ok_yellow = margin_mae is not None and margin_mae <= MARGIN_MAE_YELLOW
    margin_bad = margin_mae is not None and margin_mae > MARGIN_MAE_YELLOW

    # Bias series missing → cannot clear GREEN conjunct; do not invent.
    if signed_bias is not None and abs(signed_bias) > BIAS_RED_MIN and n >= 100:
        return "RED", f"Systematic bias |mean error|={abs(signed_bias):.3f} > {BIAS_RED_MIN}."

    worse_15 = ratio is not None and ratio > (1.0 + MAE_YELLOW_TOL)
    if n >= 100 and worse_15 and margin_bad:
        return (
            "RED",
            f"Model MAE worse than market by >15% ({model_mae:.4f} vs {market_mae:.4f}) "
            f"and margin MAE {margin_mae:.4f} > {MARGIN_MAE_YELLOW}.",
        )

    bias_ok = signed_bias is not None and abs(signed_bias) <= BIAS_GREEN_MAX
    if n >= MIN_N_OVERALL and beats_market and bias_ok:
        return (
            "GREEN",
            f"n={n}; model MAE {model_mae:.4f} ≤ market {market_mae:.4f}; "
            f"|bias|={abs(signed_bias):.3f} ≤ {BIAS_GREEN_MAX}.",
        )

    if n >= 100 and (within_15 or margin_ok_yellow):
        bias_note = (
            f"signed bias series = {DATA_GAP} (blocks GREEN conjunct)"
            if signed_bias is None
            else f"|bias|={abs(signed_bias):.3f}"
        )
        return (
            "YELLOW",
            f"n={n}; MAE market-relative ok (model {model_mae:.4f} / market {market_mae:.4f}); "
            f"margin MAE={_num(margin_mae)}; {bias_note}.",
        )

    return "YELLOW", f"n={n}; MAE/margin inconclusive — caution."


def _grade_market_edge(play: Dict[str, Any]) -> Tuple[str, str]:
    """Apply protocol §8.2 to play_band_all slice."""
    if not play or play.get("n") is None:
        return GRADE_GAP, "play_band_all ATS/CLV outcomes missing."

    n = int(play.get("n") or 0)
    ats = play.get("hit_rate")
    roi = play.get("roi")
    n_clv = int(play.get("n_clv_move") or play.get("n_clv") or 0)
    clv_pos = play.get("clv_positive_rate")

    if ats is None or n == 0:
        return GRADE_GAP, "Outcomes missing for play_band_all."

    # RED bars
    if n >= MIN_N_PLAY_ATS and float(ats) < BREAKEVEN_ATS:
        return "RED", f"play_band_all ATS {ats:.4f} < {BREAKEVEN_ATS} at n={n}."
    if n >= MIN_N_PLAY_ATS and roi is not None and float(roi) < 0:
        return "RED", f"play_band_all ROI {roi:.4f} < 0 at n={n}."
    if (
        n_clv >= CLV_N_RED
        and clv_pos is not None
        and float(clv_pos) < CLV_POS_RED
    ):
        return "RED", f"CLV+ {clv_pos:.4f} < {CLV_POS_RED} at n_clv_move={n_clv}."

    # GREEN bars
    ats_ok = n >= MIN_N_PLAY_ATS and float(ats) >= BREAKEVEN_ATS
    roi_ok = roi is not None and float(roi) > 0
    clv_green = (
        n_clv >= MIN_N_CLV_GREEN
        and clv_pos is not None
        and float(clv_pos) >= CLV_POS_MIN
    )
    if ats_ok and roi_ok and clv_green:
        return (
            "GREEN",
            f"play_band_all ATS {ats:.4f} n={n}; ROI {roi:.4f}; "
            f"CLV+ {clv_pos:.4f} n_clv_move={n_clv} (≥{MIN_N_CLV_GREEN}).",
        )

    # Without CLV series, cannot be GREEN (protocol honesty).
    if clv_pos is None and n_clv == 0:
        if ats_ok:
            return (
                GRADE_GAP,
                f"ATS reportable (ATS={ats:.4f} n={n}) but CLV series absent — "
                f"Market Edge Evidence cannot be GREEN.",
            )
        return GRADE_GAP, "CLV series absent and ATS insufficient."

    # YELLOW: ATS clears but CLV soft/fails floor or n_clv in [40,200)
    if ats_ok and (
        not clv_green
        or (MIN_N_CLV_SOFT <= n_clv < MIN_N_CLV_GREEN)
        or (clv_pos is not None and float(clv_pos) < CLV_POS_MIN)
    ):
        return (
            "YELLOW",
            f"ATS clears (ATS={ats:.4f} n={n}, ROI={_num(roi)}) but CLV soft/fails "
            f"(CLV+={_num(clv_pos)} n_clv_move={n_clv}; GREEN needs ≥{MIN_N_CLV_GREEN} @ ≥{CLV_POS_MIN}).",
        )

    return "YELLOW", f"ATS/CLV inconclusive (ATS={ats} n={n}, CLV+={clv_pos} n_clv={n_clv})."


def _grade_evidence_quality(
    *,
    overall_n: int,
    play_n: int,
    n_clv_move: int,
    contradicting_regimes: int,
    clv_expected: bool,
    inventory_ok: bool,
) -> Tuple[str, str]:
    """Apply protocol §8.3."""
    if not inventory_ok:
        return GRADE_GAP, "Cannot establish coverage denominators (broken inventory)."

    coverage = (n_clv_move / play_n) if play_n > 0 else None

    if overall_n < 100 or (clv_expected and coverage is not None and coverage < 0.40):
        return (
            "RED",
            f"Thin n={overall_n} or CLV coverage {_pct(coverage)} < 40%.",
        )
    if contradicting_regimes >= 2:
        return "RED", f"{contradicting_regimes} contradicting regimes with n≥40."

    if (
        overall_n >= MIN_N_OVERALL
        and coverage is not None
        and coverage >= 0.70
        and contradicting_regimes <= 1
    ):
        return (
            "GREEN",
            f"overall_n={overall_n}; play_band n={play_n}; CLV coverage {_pct(coverage)}; "
            f"contradicting regimes={contradicting_regimes}.",
        )

    return (
        "YELLOW",
        f"overall_n={overall_n}; CLV coverage {_pct(coverage)}; "
        f"contradicting regimes={contradicting_regimes} "
        f"(soft CLV n or thin overall).",
    )


def _subscriber_influence(
    pq: str, me: str, eq: str
) -> Tuple[str, str]:
    """Protocol §9 — recommendation only, not a product flip."""
    pillars = {pq, me, eq}
    if GRADE_GAP in pillars and me in (GRADE_GAP, "RED"):
        return (
            "INSUFFICIENT_EVIDENCE",
            "Pillar DATA GAP blocks Market Edge Evidence / influence claim.",
        )
    if me == GRADE_GAP or (eq == "RED" and (pq == GRADE_GAP or me == GRADE_GAP)):
        return "INSUFFICIENT_EVIDENCE", "Evidence blocked by DATA GAP or thin RED Evidence Quality."
    if me == "RED" or pq == "RED":
        return "NO", "Market Edge Evidence RED or Predictive Quality RED at adequate n."
    if me == "GREEN" and eq == "GREEN" and pq in ("GREEN", "YELLOW"):
        return (
            "YES",
            "Predictive ≥ YELLOW; Market Edge GREEN; Evidence Quality GREEN "
            "(scoped to confirmatory PLAY-band evidence — not a live tag flip).",
        )
    if me in ("GREEN", "YELLOW") and eq in ("GREEN", "YELLOW") and "RED" not in pillars:
        return (
            "LIMITED",
            "Market Edge GREEN/YELLOW with Evidence ≥ YELLOW — scope to confirmatory "
            "PLAY-band only; not full-slate product-ready.",
        )
    if me == GRADE_GAP or eq == "RED":
        return "INSUFFICIENT_EVIDENCE", "CLV/coverage gap or Evidence Quality RED (thin n)."
    return "INSUFFICIENT_EVIDENCE", "Does not clear YES/LIMITED/NO bars cleanly."


def _slice_summary(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not row:
        return {"status": DATA_GAP}
    n = int(row.get("n") or 0)
    hits = int(row.get("hits") or 0) if row.get("hits") is not None else None
    ats = row.get("hit_rate")
    if hits is None and ats is not None and n:
        hits = int(round(float(ats) * n))
    ci = _wilson_ci(hits, n) if hits is not None and n else None
    return {
        "n": n,
        "hits": hits,
        "hit_rate": ats,
        "roi": row.get("roi"),
        "units": row.get("units"),
        "mean_abs_edge": row.get("mean_abs_edge"),
        "n_clv_all": row.get("n_clv_all"),
        "clv_positive_rate_all": row.get("clv_positive_rate_all"),
        "n_clv_move": row.get("n_clv_move") or row.get("n_clv"),
        "clv_positive_rate": row.get("clv_positive_rate"),
        "clv_avg_move": row.get("clv_avg_move"),
        "wilson_95": {"low": ci[0], "high": ci[1]} if ci else None,
        "prior_art_gate": row.get("gate"),
        "detail": row.get("detail"),
    }


def _map_bucket_from_segment(key: str) -> Optional[str]:
    mapping = {
        "spread_edge_2.5_3.5": "play_low",
        "spread_edge_3.5_5.0": "play_mid",
        "spread_edge_5.0_7.0": "play_high",
    }
    return mapping.get(key)


def run() -> Dict[str, Any]:
    stages: List[Dict[str, Any]] = []
    data_gaps: List[str] = []
    sources: List[str] = []

    holdout = _load(HOLDOUT_PATH)
    if holdout:
        sources.append(str(HOLDOUT_PATH.relative_to(ROOT)))
    else:
        data_gaps.append(f"Missing holdout artifact: {HOLDOUT_PATH.name}")

    grading, grading_path = _load_first(GRADING_CANDIDATES)
    if grading_path:
        sources.append(grading_path)
    else:
        data_gaps.append("Missing grading artifact (MAE / full-slate ATS).")

    supervised, supervised_path = _load_first(SUPERVISED_CANDIDATES)
    if supervised_path:
        sources.append(supervised_path)

    enterprise = _load(ENTERPRISE_GATES_PATH)
    if enterprise:
        sources.append(str(ENTERPRISE_GATES_PATH.relative_to(ROOT)))

    vegas = _load(VEGAS_PATH)
    if vegas:
        sources.append(str(VEGAS_PATH.relative_to(ROOT)))

    # --- Stage 1–4: prediction / market / outcome / error (from artifacts) ---
    stages.append(
        {
            "stage": "prediction",
            "status": "ok" if grading else DATA_GAP,
            "note": "Model/KEI spreads absorbed from grading + PLAY holdout projections (owned DB snapshot).",
        }
    )
    stages.append(
        {
            "stage": "timestamped_market",
            "status": "ok" if holdout else DATA_GAP,
            "note": "Open/close via owned odds_snapshots (movement_only_n_snaps_ge_2); no Odds API re-burn.",
        }
    )
    stages.append(
        {
            "stage": "outcome",
            "status": "ok" if holdout else DATA_GAP,
            "note": "ATS vs closing home spread; pushes excluded from denominators (prior art).",
        }
    )

    model = (grading or {}).get("model") or {}
    market_close = (grading or {}).get("market_close") or {}
    coverage = (grading or {}).get("coverage") or {}
    metrics = (supervised or {}).get("metrics") or {}

    model_mae = model.get("spread_mae")
    market_mae = market_close.get("spread_mae")
    n_all = int(model.get("n_spread") or 0)
    full_slate_ats = model.get("ats_hit_rate")
    # Signed spread bias not present in grading artifacts.
    signed_bias = None
    data_gaps.append(
        "Signed mean spread error (bias) not present in grading artifacts → "
        f"Predictive GREEN bias conjunct = {DATA_GAP}."
    )

    margin_mae = metrics.get("test_margin_mae")
    brier = metrics.get("test_brier")
    if margin_mae is None:
        data_gaps.append("Supervised margin MAE missing (secondary Predictive metric).")

    # Close missing rate: owned OC join vs schedule games when available.
    sched = coverage.get("schedule_games_2020_2025")
    owned = coverage.get("owned_open_close_games")
    close_missing_rate = None
    if sched and owned is not None and sched > 0:
        # Owned OC can exceed schedule count (extra densify); missing rate vs schedule
        # when rows_with model projection is the grading universe.
        proj_n = coverage.get("rows_with_model_projection") or n_all
        # Grading used closes for all n_spread; treat missing as 0 if n_spread filled.
        close_missing_rate = 0.0 if n_all >= 0.8 * (proj_n or n_all or 1) else None

    stages.append(
        {
            "stage": "error",
            "status": "partial" if signed_bias is None else "ok",
            "model_spread_mae": model_mae,
            "market_spread_mae": market_mae,
            "margin_mae": margin_mae,
            "signed_bias": DATA_GAP,
        }
    )

    # --- Stage 5: calibration ---
    stages.append(
        {
            "stage": "calibration",
            "status": "ok" if model_mae is not None else DATA_GAP,
            "model_spread_mae": model_mae,
            "market_spread_mae": market_mae,
            "brier": brier,
            "margin_mae": margin_mae,
            "vegas_2025_holdout_spread_mae": (
                ((vegas or {}).get("results_2025_holdout") or {}).get("spread_mae")
            ),
        }
    )

    # --- Stage 6–7: edge buckets + CLV from holdout ---
    primary = ((holdout or {}).get("primary_holdout_2025") or {}).get("spread") or {}
    confirmatory = ((holdout or {}).get("confirmatory_2024_2025") or {}).get("spread") or {}
    clean_era = ((holdout or {}).get("clean_era_2020_2022") or {}).get("spread") or {}
    segments = (holdout or {}).get("segments_2025") or {}
    walk = (holdout or {}).get("walk_forward_by_season") or {}

    buckets_out: Dict[str, Any] = {}
    for bid, lo, hi in BUCKETS:
        buckets_out[bid] = {
            "abs_edge_min": lo,
            "abs_edge_max_exclusive": hi,
            "primary_2025": DATA_GAP,
            "note": "noise/lean/mega not segmented in play-only holdout artifact",
        }

    for seg_key, row in segments.items():
        bid = _map_bucket_from_segment(seg_key)
        if bid:
            buckets_out[bid]["primary_2025"] = _slice_summary(row)
            buckets_out[bid]["note"] = "From segments_2025 (PLAY holdout prior art)."

    # lean_band / noise / mega_edge not in PLAY-only holdout segments
    for bid in ("noise", "lean_band", "mega_edge"):
        data_gaps.append(
            f"Bucket `{bid}` ATS/CLV not in nfl-play-only-holdout segments → {DATA_GAP}."
        )

    play_band_primary = _slice_summary(primary)
    play_band_confirm = _slice_summary(confirmatory)

    stages.append(
        {
            "stage": "edge_bucket",
            "status": "ok",
            "play_band_all_primary_2025": play_band_primary,
            "play_band_all_confirmatory_2024_2025": play_band_confirm,
            "buckets": buckets_out,
        }
    )

    clv_status = "ok" if confirmatory.get("n_clv_move") else DATA_GAP
    stages.append(
        {
            "stage": "clv",
            "methodology": "movement_only_n_snaps_ge_2",
            "status": clv_status,
            "primary_2025": {
                "n_clv_move": primary.get("n_clv_move"),
                "clv_positive_rate": primary.get("clv_positive_rate"),
                "clv_avg_move": primary.get("clv_avg_move"),
            },
            "confirmatory_2024_2025": {
                "n_clv_move": confirmatory.get("n_clv_move"),
                "clv_positive_rate": confirmatory.get("clv_positive_rate"),
                "clv_avg_move": confirmatory.get("clv_avg_move"),
            },
            "clv_pred_ts_to_close": DATA_GAP,
        }
    )
    data_gaps.append(
        f"Secondary CLV `clv_pred_ts_to_close` (prediction-timestamp→close) not in artifacts → {DATA_GAP}."
    )

    # --- Stage 8: regimes ---
    regimes: Dict[str, Any] = {}
    contradicting = 0
    overall_dir_ats = confirmatory.get("hit_rate") or primary.get("hit_rate")

    home = segments.get("spread_home")
    away = segments.get("spread_away")
    for name, row in (("home_side", home), ("away_side", away)):
        if not row:
            regimes[name] = DATA_GAP
            continue
        summary = _slice_summary(row)
        regimes[name] = summary
        n = int(row.get("n") or 0)
        ats = row.get("hit_rate")
        if (
            n >= MIN_N_BUCKET
            and ats is not None
            and overall_dir_ats is not None
            and float(overall_dir_ats) >= BREAKEVEN_ATS
            and float(ats) < BREAKEVEN_ATS
        ):
            contradicting += 1

    # Edge-bucket regimes (play_low/mid/high) — diagnostic
    for bid in ("play_low", "play_mid", "play_high"):
        row = buckets_out[bid].get("primary_2025")
        if isinstance(row, dict) and row.get("n"):
            regimes[f"edge_{bid}"] = row
            n = int(row.get("n") or 0)
            ats = row.get("hit_rate")
            if (
                n >= MIN_N_BUCKET
                and ats is not None
                and overall_dir_ats is not None
                and float(overall_dir_ats) >= BREAKEVEN_ATS
                and float(ats) < BREAKEVEN_ATS
            ):
                contradicting += 1
        else:
            regimes[f"edge_{bid}"] = DATA_GAP

    for missing_regime in (
        "favorite",
        "dog",
        "week_W1_W4",
        "week_W5_W12",
        "week_W13_W18",
        "postseason",
        "outdoor",
        "dome",
    ):
        regimes[missing_regime] = DATA_GAP
        data_gaps.append(f"Regime `{missing_regime}` field coverage <80% / absent → {DATA_GAP}.")

    stages.append(
        {
            "stage": "regime",
            "status": "partial",
            "contradicting_regimes_n40": contradicting,
            "regimes": regimes,
        }
    )

    # --- Stage 9–11: thresholds / grades / influence ---
    # Market Edge uses confirmatory window for CLV n≥200 (protocol §3/§7 + enterprise prior art).
    pq_grade, pq_detail = _grade_predictive(
        n=n_all,
        model_mae=float(model_mae) if model_mae is not None else None,
        market_mae=float(market_mae) if market_mae is not None else None,
        margin_mae=float(margin_mae) if margin_mae is not None else None,
        signed_bias=signed_bias,
        close_missing_rate=close_missing_rate,
    )

    me_grade, me_detail = _grade_market_edge(confirmatory)
    me_primary_grade, me_primary_detail = _grade_market_edge(primary)

    play_n = int(confirmatory.get("n") or 0)
    n_clv_move = int(confirmatory.get("n_clv_move") or 0)
    eq_grade, eq_detail = _grade_evidence_quality(
        overall_n=max(n_all, play_n),
        play_n=play_n,
        n_clv_move=n_clv_move,
        contradicting_regimes=contradicting,
        clv_expected=True,
        inventory_ok=bool(holdout and grading),
    )

    # Protocol: ≥2 contradicting regimes force Market Edge ≤ YELLOW
    if contradicting >= 2 and me_grade == "GREEN":
        me_grade = "YELLOW"
        me_detail += " Demoted ≤YELLOW: ≥2 contradicting regimes (n≥40)."

    influence, influence_detail = _subscriber_influence(pq_grade, me_grade, eq_grade)

    stages.append(
        {
            "stage": "threshold_evaluation",
            "protocol_version": PROTOCOL_VERSION,
            "frozen": True,
            "bars_applied": {
                "ats_breakeven": BREAKEVEN_ATS,
                "clv_pos_min": CLV_POS_MIN,
                "clv_n_green": MIN_N_CLV_GREEN,
                "play_ats_n_min": MIN_N_PLAY_ATS,
            },
        }
    )
    stages.append(
        {
            "stage": "grades",
            "predictive_quality": pq_grade,
            "market_edge_evidence": me_grade,
            "evidence_quality": eq_grade,
        }
    )
    stages.append(
        {
            "stage": "influence",
            "subscriber_influence": influence,
            "note": "Evidence recommendation for CoS→Ryan only — NO live PLAY/LEAN/PASS flip.",
        }
    )

    # Comparators
    comparators = {
        "kosedge_alone": {
            "rule": "Bet model side when |edge| in play_band_all (2.5≤|edge|<7.0)",
            "window": "confirmatory_2024_2025",
            "metrics": play_band_confirm,
            "status": "ok",
        },
        "market_alone": {
            "rule": "Always home favorite at close (pick'em excluded)",
            "status": DATA_GAP,
            "note": "Home-favorite baseline ATS not present in owned ops JSON — do not invent.",
        },
        "kosedge_plus_market": {
            "rule": "kosedge_alone ∩ open→close move not strictly against model side",
            "status": DATA_GAP,
            "note": "Filtered momentum-agreement slice not precomputed in holdout artifact.",
        },
    }
    data_gaps.append(f"Comparator market_alone → {DATA_GAP}.")
    data_gaps.append(f"Comparator kosedge_plus_market → {DATA_GAP}.")

    # Full-slate context (not selective claim)
    all_sides_context = {
        "n": n_all,
        "ats_hit_rate": full_slate_ats,
        "note": "Full-slate ATS is context only; selective claim uses play_band_all.",
        "enterprise_full_slate_gate": "RED"
        if full_slate_ats is not None and float(full_slate_ats) < BREAKEVEN_ATS
        else None,
    }

    walk_forward = {}
    for season, block in sorted(walk.items()):
        sp = (block or {}).get("spread") or {}
        walk_forward[season] = _slice_summary(sp)

    # Deduplicate data_gaps while preserving order
    seen = set()
    gaps_unique = []
    for g in data_gaps:
        if g not in seen:
            seen.add(g)
            gaps_unique.append(g)

    payload: Dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "status": "results_filled",
        "cos_sign_off": COS_SIGN,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "sport": "NFL",
            "market": "spread",
            "excluded": ["CBB", "totals", "props", "ml_only"],
        },
        "hard_locks": [
            "no_live_play_lean_pass_flip",
            "no_rebuild_without_defect_and_cos_gate",
            "no_invent_missing_odds",
            "no_post_hoc_bucket_changes",
            "red_equals_honest_failure_success",
            "cbb_excluded",
        ],
        "data_sources": sources,
        "citations": [
            "docs/NFL_ENTERPRISE_GATES.md",
            "data/ops/nfl-play-only-holdout.json",
            "apps/web/lib/nfl-spread-play-lock.ts",
            "NFL_SPREAD_PLAY_LOCKED.md",
            "scripts/nfl/evaluate_enterprise_gates.py",
            "services/model-service/src/services/nfl_enterprise_gates.py",
            PROTOCOL_DOC,
        ],
        "pipeline_stages": stages,
        "grades": {
            "predictive_quality": pq_grade,
            "market_edge_evidence": me_grade,
            "evidence_quality": eq_grade,
        },
        "grade_details": {
            "predictive_quality": pq_detail,
            "market_edge_evidence": me_detail,
            "market_edge_primary_2025_alone": {
                "grade": me_primary_grade,
                "detail": me_primary_detail,
            },
            "evidence_quality": eq_detail,
        },
        "subscriber_influence": influence.replace("_", " ")
        if influence == "INSUFFICIENT_EVIDENCE"
        else influence,
        "subscriber_influence_code": influence,
        "subscriber_influence_detail": influence_detail,
        "results": {
            "windows": {
                "primary_unused_holdout": "2025",
                "confirmatory": "2024-2025",
                "clean_era_check": "2020-2022",
            },
            "all_sides_context": all_sides_context,
            "play_band_all": {
                "primary_2025": play_band_primary,
                "confirmatory_2024_2025": play_band_confirm,
                "clean_era_2020_2022": _slice_summary(clean_era),
            },
            "buckets": buckets_out,
            "regimes": regimes,
            "comparators": comparators,
            "predictive_metrics": {
                "model_spread_mae": model_mae,
                "market_spread_mae": market_mae,
                "n_spread": n_all,
                "margin_mae_supervised": margin_mae,
                "brier_supervised": brier,
                "signed_bias": DATA_GAP,
                "mae_gate": "market_relative_only",
            },
            "walk_forward_by_season": walk_forward,
            "enterprise_gates_echo": {
                "overall": ((enterprise or {}).get("report") or {}).get("overall"),
                "selective_play_ready": ((enterprise or {}).get("report") or {}).get(
                    "selective_play_ready"
                ),
                "betting_product_ready": ((enterprise or {}).get("report") or {}).get(
                    "betting_product_ready"
                ),
            },
        },
        "data_gaps": gaps_unique,
        "min_n": {
            "overall": MIN_N_OVERALL,
            "per_bucket": MIN_N_BUCKET,
            "clv_green": MIN_N_CLV_GREEN,
            "ci_level": 0.95,
        },
        "discrepancy_buckets": [
            {
                "id": bid,
                "abs_edge_min": lo,
                "abs_edge_max_exclusive": hi,
            }
            for bid, lo, hi in BUCKETS
        ],
        "rerun": "python3 scripts/lab/nfl_spread_validation_v1.py",
    }

    # Normalize subscriber_influence for schema enum
    if payload["subscriber_influence"] == "INSUFFICIENT EVIDENCE":
        payload["subscriber_influence"] = "INSUFFICIENT_EVIDENCE"

    return payload


def _md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def write_markdown(payload: Dict[str, Any]) -> str:
    g = payload["grades"]
    r = payload["results"]
    pb = r["play_band_all"]["confirmatory_2024_2025"]
    pp = r["play_band_all"]["primary_2025"]
    pred = r["predictive_metrics"]
    lines = [
        "# NFL Spread Scorecard v1.0",
        "",
        f"**Protocol:** `{PROTOCOL_VERSION}` (FROZEN)  ",
        f"**Status:** `results_filled`  ",
        f"**CoS sign-off:** {COS_SIGN}  ",
        f"**Generated:** {payload['generated_at']}  ",
        f"**Lab:** Kos Edge #3 Model Validation Lab  ",
        f"**Machine JSON:** [`data/ops/lab/nfl-spread-scorecard-v1.json`](../../data/ops/lab/nfl-spread-scorecard-v1.json)",
        "",
        "> Evidence report only. **No** live PLAY / LEAN / PASS flip recommendations.  ",
        "> RED = successful honest failure detection when criteria say so.",
        "",
        "## Executive grades",
        "",
        "| Pillar | Grade | Detail |",
        "| --- | --- | --- |",
        f"| Predictive Quality | **{g['predictive_quality']}** | {_md_escape(payload['grade_details']['predictive_quality'])} |",
        f"| Market Edge Evidence | **{g['market_edge_evidence']}** | {_md_escape(payload['grade_details']['market_edge_evidence'])} |",
        f"| Evidence Quality | **{g['evidence_quality']}** | {_md_escape(payload['grade_details']['evidence_quality'])} |",
        "",
        f"**Subscriber Influence (recommendation to CoS → Ryan):** "
        f"**{payload['subscriber_influence_code'].replace('_', ' ')}**  ",
        f"{payload['subscriber_influence_detail']}",
        "",
        "Primary-2025-alone Market Edge (context): "
        f"`{payload['grade_details']['market_edge_primary_2025_alone']['grade']}` — "
        f"{payload['grade_details']['market_edge_primary_2025_alone']['detail']}",
        "",
        "## Data sources (owned artifacts only)",
        "",
    ]
    for s in payload["data_sources"]:
        lines.append(f"- `{s}`")
    lines.extend(
        [
            "",
            "Citations (prior art, not Lab discovery):",
            "",
        ]
    )
    for c in payload["citations"]:
        lines.append(f"- `{c}`")

    lines.extend(
        [
            "",
            "## Predictive Quality",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Model spread MAE vs close | {_num(pred.get('model_spread_mae'))} |",
            f"| Market spread MAE vs close | {_num(pred.get('market_spread_mae'))} |",
            f"| n (all_sides) | {pred.get('n_spread')} |",
            f"| Supervised margin MAE (secondary) | {_num(pred.get('margin_mae_supervised'))} |",
            f"| Supervised Brier (secondary) | {_num(pred.get('brier_supervised'))} |",
            f"| Signed bias (mean error) | {DATA_GAP} |",
            f"| GREEN gate | market-relative only (no absolute-pt OR) |",
            "",
            "## Market Edge Evidence — `play_band_all` (2.5 ≤ \\|edge\\| < 7.0)",
            "",
            "| Window | n | ATS | ROI (−110) | n_clv_move | CLV+ | mean CLV move |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    def row_line(label: str, sl: Dict[str, Any]) -> str:
        if sl.get("status") == DATA_GAP or sl.get("n") is None:
            return f"| {label} | {DATA_GAP} | {DATA_GAP} | {DATA_GAP} | {DATA_GAP} | {DATA_GAP} | {DATA_GAP} |"
        return (
            f"| {label} | {sl.get('n')} | {_num(sl.get('hit_rate'))} | {_num(sl.get('roi'))} | "
            f"{sl.get('n_clv_move')} | {_num(sl.get('clv_positive_rate'))} | {_num(sl.get('clv_avg_move'))} |"
        )

    lines.append(row_line("Primary unused 2025", pp))
    lines.append(row_line("Confirmatory 2024–2025", pb))
    lines.append(row_line("Clean-era 2020–2022", r["play_band_all"]["clean_era_2020_2022"]))

    lines.extend(
        [
            "",
            "Full-slate ATS (context only, not selective claim): "
            f"n={r['all_sides_context'].get('n')}, "
            f"ATS={_num(r['all_sides_context'].get('ats_hit_rate'))} "
            f"(enterprise full-slate gate echo: "
            f"{r['all_sides_context'].get('enterprise_full_slate_gate')}).",
            "",
            "### Edge buckets (primary 2025 segments)",
            "",
            "| Bucket | \\|edge\\| | n | ATS | ROI | n_clv_move | CLV+ |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for bid, lo, hi in BUCKETS:
        band = f"[{lo}, {hi})" if hi is not None else f"[{lo}, ∞)"
        cell = r["buckets"][bid].get("primary_2025")
        if not isinstance(cell, dict) or cell.get("n") is None:
            lines.append(f"| `{bid}` | {band} | {DATA_GAP} | {DATA_GAP} | {DATA_GAP} | {DATA_GAP} | {DATA_GAP} |")
        else:
            lines.append(
                f"| `{bid}` | {band} | {cell.get('n')} | {_num(cell.get('hit_rate'))} | "
                f"{_num(cell.get('roi'))} | {cell.get('n_clv_move')} | {_num(cell.get('clv_positive_rate'))} |"
            )

    lines.extend(
        [
            "",
            "## Regimes",
            "",
            "| Regime | Status / metrics |",
            "| --- | --- |",
        ]
    )
    for name, val in r["regimes"].items():
        if val == DATA_GAP or not isinstance(val, dict):
            lines.append(f"| `{name}` | {DATA_GAP} |")
        else:
            lines.append(
                f"| `{name}` | n={val.get('n')}, ATS={_num(val.get('hit_rate'))}, "
                f"CLV+={_num(val.get('clv_positive_rate'))} (n_move={val.get('n_clv_move')}) |"
            )

    lines.extend(
        [
            "",
            "## Comparators",
            "",
            "| Comparator | Status | Notes |",
            "| --- | --- | --- |",
        ]
    )
    for cid, c in r["comparators"].items():
        if c.get("status") == DATA_GAP:
            lines.append(f"| `{cid}` | {DATA_GAP} | {_md_escape(c.get('note') or '')} |")
        else:
            m = c.get("metrics") or {}
            lines.append(
                f"| `{cid}` | ok | n={m.get('n')}, ATS={_num(m.get('hit_rate'))}, "
                f"ROI={_num(m.get('roi'))}, CLV+={_num(m.get('clv_positive_rate'))} |"
            )

    lines.extend(
        [
            "",
            "## Walk-forward by season (`play_band` spread)",
            "",
            "| Season | n | ATS | ROI | n_clv_move | CLV+ |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for season, sl in r["walk_forward_by_season"].items():
        lines.append(
            f"| {season} | {sl.get('n')} | {_num(sl.get('hit_rate'))} | {_num(sl.get('roi'))} | "
            f"{sl.get('n_clv_move')} | {_num(sl.get('clv_positive_rate'))} |"
        )

    lines.extend(
        [
            "",
            "## DATA GAPs (honest)",
            "",
        ]
    )
    for gap in payload["data_gaps"]:
        lines.append(f"- {gap}")

    lines.extend(
        [
            "",
            "## Hard locks honored",
            "",
            "- No rematerialize / no live tag flip / no invented odds / no p-hacking",
            "- CBB excluded",
            "- Criteria frozen at Protocol v1.0 — buckets/min-N/G-Y-R not retuned after results",
            "- RED is a successful Lab outcome when criteria detect failure",
            "",
            "## Re-run",
            "",
            "```bash",
            payload["rerun"],
            "```",
            "",
            "Requires the cited ops JSON artifacts under `data/ops/` (no DB required for this Lab pass).",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = run()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    md = write_markdown(payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md)
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    print(
        "Grades:",
        payload["grades"],
        "Influence:",
        payload["subscriber_influence_code"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
