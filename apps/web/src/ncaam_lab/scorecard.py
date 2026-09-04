"""NCAAM Fair Lab first scorecard — Phase E / protocol v1.0.

Frozen gates registered BEFORE fill. No peek-tune after Test-A.
RED = successful honest failure detection when criteria say so.

Baselines:
  B1 — close consensus (Path A) as market-implied home margin = -close
  B2 — KenPom AdjEM + HCA fair_spread_home (predicted home margin)

Predictive: MAE/RMSE of B2 and B1 vs actual_margin (same-space home margin).
Market Edge: full-slate bet B2 side vs close; CLV only where open_snapshot_honest.
No Edge>4 shopping for primary grades.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import polars as pl

from ncaam_lab.protocol import PROTOCOL_DOC, PROTOCOL_VERSION, protocol_manifest
from ncaam_lab.results_attach import attach_lab_outcomes

# ---------------------------------------------------------------------------
# Frozen grade gates (registered pre-fill — do not retune after Test-A)
# Adapted from NFL Lab §8 with AMBER (not YELLOW) for NCAAM CoS vocabulary.
# Primary window = Test-A OOS. Train-A is diagnostic context only.
# ---------------------------------------------------------------------------

BREAKEVEN_ATS = 0.5238
MIN_N_PRED_GREEN = 100
MIN_N_PRED_AMBER = 50
MIN_N_PRED_RED = 50
MAE_AMBER_TOL = 0.15  # within 15% of B1 market MAE
BIAS_GREEN_MAX = 2.0
BIAS_RED_MIN = 3.0
MARGIN_MAE_AMBER = 12.0  # CBB margins wider than NFL; secondary only

MIN_N_ATS = 60
MIN_N_CLV_GREEN = 100  # CBB Path A thinner than NFL; still require CLV for GREEN
MIN_N_CLV_SOFT = 40
CLV_POS_MIN = 0.55
CLV_POS_RED = 0.50
CLV_N_RED = 80

MIN_N_EVIDENCE_GREEN = 100
MIN_N_EVIDENCE_AMBER = 50
OUTCOME_COV_GREEN = 0.40
OUTCOME_COV_AMBER = 0.20
OPEN_HONEST_COV_GREEN = 0.70

DATA_GAP = "N/A—DATA GAP"
SCORECARD_VERSION = "ncaam-fair-lab-scorecard-v1.0"
SCORECARD_DOC = "docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1.md"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _web_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _mae(errs: List[float]) -> Optional[float]:
    if not errs:
        return None
    return float(sum(abs(e) for e in errs) / len(errs))


def _rmse(errs: List[float]) -> Optional[float]:
    if not errs:
        return None
    return float(math.sqrt(sum(e * e for e in errs) / len(errs)))


def _mean(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    return float(sum(xs) / len(xs))


def load_actual_margins(path: Optional[Path] = None) -> pl.DataFrame:
    """Owned actual_margins only — secondary event_id overlay (no Odds densify)."""
    p = path or (_web_root() / "data" / "processed" / "actual_margins.parquet")
    if not p.exists():
        return pl.DataFrame({"event_id": [], "actual_margin": []})
    df = pl.read_parquet(p)
    cols = [c for c in ("event_id", "actual_margin") if c in df.columns]
    return df.select(cols).unique(subset=["event_id"], keep="first")


def attach_outcomes(
    lab: pl.DataFrame,
    actuals: Optional[pl.DataFrame] = None,
    *,
    densify: bool = True,
) -> pl.DataFrame:
    """Attach actual_margin. Default densify uses Schedule SoT packs (repo only).

    densify=False keeps the historical thin event_id→actual_margins join (v1 freeze baseline).
    """
    if densify:
        out, _receipt = attach_lab_outcomes(lab, event_actuals=actuals)
        return out
    if actuals is None or actuals.is_empty() or "event_id" not in actuals.columns:
        return lab.with_columns(pl.lit(None).cast(pl.Float64).alias("actual_margin"))
    return lab.join(actuals.select(["event_id", "actual_margin"]), on="event_id", how="left")


def score_cut(lab: pl.DataFrame, *, cut: str) -> Dict[str, Any]:
    """Score one cut window vs B1 + B2. Does not mutate protocol knobs."""
    n_lab = len(lab)
    continuity = {}
    if "continuity_state" in lab.columns and n_lab:
        for state in lab["continuity_state"].to_list():
            continuity[str(state)] = continuity.get(str(state), 0) + 1
    settled_forbidden = int(continuity.get("SETTLED", 0))

    with_actual = lab.filter(pl.col("actual_margin").is_not_null()) if "actual_margin" in lab.columns else lab.head(0)
    n_actual = len(with_actual)
    outcome_cov = (n_actual / n_lab) if n_lab else 0.0

    # Same-space home-margin errors
    # B2 fair_spread_home = predicted home margin
    # B1 implied margin = -close_spread (betting convention → margin)
    b2_errs: List[float] = []
    b1_errs: List[float] = []
    for row in with_actual.iter_rows(named=True):
        am = float(row["actual_margin"])
        fair = row.get("fair_spread_home")
        close = row.get("b1_consensus_close_spread")
        if fair is not None:
            b2_errs.append(am - float(fair))
        if close is not None:
            b1_implied = -float(close)
            b1_errs.append(am - b1_implied)

    b2_mae = _mae(b2_errs)
    b2_rmse = _rmse(b2_errs)
    b2_bias = _mean(b2_errs)
    b1_mae = _mae(b1_errs)
    b1_rmse = _rmse(b1_errs)
    b1_bias = _mean(b1_errs)

    predictive = {
        "n_lab_games": n_lab,
        "n_with_actual": n_actual,
        "outcome_coverage": round(outcome_cov, 4),
        "b2_margin_mae": None if b2_mae is None else round(b2_mae, 4),
        "b2_margin_rmse": None if b2_rmse is None else round(b2_rmse, 4),
        "b2_signed_bias": None if b2_bias is None else round(b2_bias, 4),
        "b1_margin_mae": None if b1_mae is None else round(b1_mae, 4),
        "b1_margin_rmse": None if b1_rmse is None else round(b1_rmse, 4),
        "b1_signed_bias": None if b1_bias is None else round(b1_bias, 4),
        "market_relative": {
            "b2_mae_le_b1": (
                None
                if b2_mae is None or b1_mae is None
                else bool(b2_mae <= b1_mae)
            ),
            "b2_vs_b1_ratio": (
                None
                if b2_mae is None or b1_mae is None or b1_mae == 0
                else round(b2_mae / b1_mae, 4)
            ),
        },
        "convention": {
            "b2": "fair_spread_home = predicted home margin (AdjEM diff + HCA)",
            "b1": "implied home margin = -b1_consensus_close_spread",
            "error": "actual_margin - predicted_or_implied_margin",
        },
    }

    # Market Edge — full slate (no Edge>4 shopping). Honest open only for CLV.
    honest = with_actual.filter(pl.col("open_snapshot_honest") == True) if n_actual and "open_snapshot_honest" in with_actual.columns else with_actual.head(0)  # noqa: E712
    n_honest_open = 0
    ats_n = 0
    ats_wins = 0
    units = 0.0  # −110: win +1, lose −1.1
    clv_moves: List[float] = []
    clv_pos = 0

    for row in with_actual.iter_rows(named=True):
        fair = row.get("fair_spread_home")
        close = row.get("b1_consensus_close_spread")
        am = row.get("actual_margin")
        if fair is None or close is None or am is None:
            continue
        fair_f = float(fair)
        close_f = float(close)
        am_f = float(am)
        # Honest margin-space edge vs close for side choice when open missing:
        # prefer open when honest; else close (ATS still grades vs close).
        open_raw = row.get("open_consensus_spread")
        honest_flag = bool(row.get("open_snapshot_honest"))
        if honest_flag and open_raw is not None:
            n_honest_open += 1
            open_f = float(open_raw)
            edge = fair_f - (-open_f)  # fair margin − open implied margin
            line_for_side = open_f
        else:
            edge = fair_f - (-close_f)
            line_for_side = close_f
            open_f = None

        bet_home = edge > 0
        # Push exclusion: exact zero cover vs close
        cover_home_raw = am_f + close_f
        if abs(cover_home_raw) < 1e-9:
            continue  # push
        home_cover = cover_home_raw > 0
        won = home_cover if bet_home else (not home_cover)
        ats_n += 1
        if won:
            ats_wins += 1
            units += 1.0
        else:
            units -= 1.1

        if open_f is not None:
            # Home bettor CLV pts = open_spread − close_spread (betting convention)
            clv_home = open_f - close_f
            clv = clv_home if bet_home else -clv_home
            if abs(open_f - close_f) > 1e-9:
                clv_moves.append(clv)
                if clv > 0:
                    clv_pos += 1

    ats = (ats_wins / ats_n) if ats_n else None
    roi = (units / ats_n) if ats_n else None
    n_clv = len(clv_moves)
    clv_plus = (clv_pos / n_clv) if n_clv else None
    mean_clv = _mean(clv_moves)

    # Open honesty coverage among scored actuals
    open_honest_cov = (n_honest_open / n_actual) if n_actual else 0.0

    market_edge = {
        "primary_filter": "full_slate_no_edge_gt4_shopping",
        "n_ats": ats_n,
        "ats": None if ats is None else round(ats, 4),
        "ats_wins": ats_wins,
        "roi_minus110": None if roi is None else round(roi, 4),
        "units_minus110": round(units, 4),
        "n_open_honest_with_actual": n_honest_open,
        "open_honest_coverage_on_actuals": round(open_honest_cov, 4),
        "n_clv_move": n_clv,
        "clv_positive_rate": None if clv_plus is None else round(clv_plus, 4),
        "mean_clv_move": None if mean_clv is None else round(mean_clv, 4),
        "side_rule": "bet home iff (fair_margin - open_or_close_implied_margin) > 0",
        "clv_rule": "home CLV = open_spread - close_spread; away = negate; pushes on zero line move excluded from n_clv_move",
    }

    evidence = {
        "n_lab_games": n_lab,
        "n_with_fair_spread": int(lab["fair_spread_home"].is_not_null().sum())
        if n_lab and "fair_spread_home" in lab.columns
        else 0,
        "n_with_actual": n_actual,
        "outcome_coverage": round(outcome_cov, 4),
        "continuity_counts": continuity,
        "settled_forbidden_count": settled_forbidden,
        "open_snapshot_honest_n": int(lab["open_snapshot_honest"].sum())
        if n_lab and "open_snapshot_honest" in lab.columns
        else 0,
        "schedule_sot": "D",
        "espn_schedule_sot_a_note": (
            "PR 477 ESPN Schedule SoT A package exists (slate_complete=false); "
            "Lab joins remain Odds event_id + B7 fail-closed for this scorecard"
        ),
    }

    return {
        "cut": cut,
        "predictive": predictive,
        "market_edge": market_edge,
        "evidence": evidence,
    }


def grade_predictive(pred: Dict[str, Any]) -> Tuple[str, str]:
    n = int(pred.get("n_with_actual") or 0)
    b2 = pred.get("b2_margin_mae")
    b1 = pred.get("b1_margin_mae")
    bias = pred.get("b2_signed_bias")
    cov = float(pred.get("outcome_coverage") or 0)

    if n < MIN_N_PRED_AMBER or b2 is None or b1 is None:
        if cov < OUTCOME_COV_AMBER or n == 0:
            return DATA_GAP, f"n_with_actual={n}; outcome coverage too thin for Predictive grade"
        return DATA_GAP, f"n_with_actual={n} < {MIN_N_PRED_AMBER} or MAE missing"

    ratio = (b2 / b1) if b1 else None
    bias_abs = abs(bias) if bias is not None else None

    if (
        n >= MIN_N_PRED_GREEN
        and b2 <= b1
        and (bias_abs is None or bias_abs <= BIAS_GREEN_MAX)
    ):
        return "GREEN", (
            f"n={n}; B2 MAE {b2:.4f} ≤ B1 MAE {b1:.4f}; "
            f"bias={bias if bias is not None else DATA_GAP}"
        )

    worse_by_15 = ratio is not None and ratio > (1.0 + MAE_AMBER_TOL)
    if n >= MIN_N_PRED_RED and worse_by_15 and (b2 > MARGIN_MAE_AMBER or (bias_abs is not None and bias_abs > BIAS_RED_MIN)):
        return "RED", (
            f"n={n}; B2 MAE {b2:.4f} worse than B1 {b1:.4f} by >15% "
            f"(ratio={ratio:.4f}); bias={bias}"
        )
    if n >= MIN_N_PRED_RED and bias_abs is not None and bias_abs > BIAS_RED_MIN and worse_by_15:
        return "RED", f"n={n}; systematic bias |{bias}| > {BIAS_RED_MIN} with MAE worse than market"

    ratio_s = f"{ratio:.4f}" if ratio is not None else "n/a"

    # AMBER band
    within_15 = ratio is not None and ratio <= (1.0 + MAE_AMBER_TOL)
    if n >= MIN_N_PRED_AMBER and (within_15 or b2 <= MARGIN_MAE_AMBER):
        return "AMBER", (
            f"n={n}; B2 MAE {b2:.4f} vs B1 {b1:.4f} (ratio={ratio_s}); "
            f"clears soft AMBER, not market-relative GREEN"
        )

    if n >= MIN_N_PRED_RED and worse_by_15:
        return "RED", f"n={n}; B2 MAE {b2:.4f} > B1 {b1:.4f} by >15% (ratio={ratio_s})"

    return "AMBER", f"n={n}; thin / mixed Predictive signal (B2={b2}, B1={b1})"


def grade_market_edge(me: Dict[str, Any]) -> Tuple[str, str]:
    n = int(me.get("n_ats") or 0)
    ats = me.get("ats")
    roi = me.get("roi_minus110")
    n_clv = int(me.get("n_clv_move") or 0)
    clv_plus = me.get("clv_positive_rate")

    if n == 0 or ats is None:
        return DATA_GAP, "no ATS sample (actuals or pushes missing)"

    if n >= MIN_N_ATS and ats >= BREAKEVEN_ATS and roi is not None and roi > 0 and clv_plus is not None and clv_plus >= CLV_POS_MIN and n_clv >= MIN_N_CLV_GREEN:
        return "GREEN", (
            f"full_slate ATS={ats:.4f} n={n}; ROI={roi:.4f}; "
            f"CLV+={clv_plus:.4f} n_clv={n_clv}"
        )

    if n >= MIN_N_ATS and (ats < BREAKEVEN_ATS or (roi is not None and roi < 0)):
        detail = f"full_slate ATS={ats:.4f} n={n}; ROI={roi}"
        if clv_plus is not None and n_clv >= CLV_N_RED and clv_plus < CLV_POS_RED:
            detail += f"; CLV+={clv_plus:.4f} n_clv={n_clv}"
        return "RED", detail

    if n >= MIN_N_ATS and clv_plus is not None and n_clv >= CLV_N_RED and clv_plus < CLV_POS_RED:
        return "RED", f"CLV+={clv_plus:.4f} < {CLV_POS_RED} at n_clv={n_clv}; ATS={ats}"

    if n >= MIN_N_ATS and ats >= BREAKEVEN_ATS:
        return "AMBER", (
            f"ATS clears ({ats:.4f} n={n}) but CLV/ROI soft "
            f"(CLV+={clv_plus} n_clv={n_clv}; ROI={roi}) — no Edge>4 shopping"
        )

    if n < MIN_N_ATS:
        return "AMBER", f"thin ATS n={n} < {MIN_N_ATS}; ATS={ats}; ROI={roi}"

    return "AMBER", f"mixed Market Edge; ATS={ats} n={n}; ROI={roi}; CLV+={clv_plus}"


def grade_evidence(
    ev: Dict[str, Any],
    *,
    leakage_ok: bool,
    leakage_violations: int,
    manifests: Dict[str, Any],
) -> Tuple[str, str]:
    n_actual = int(ev.get("n_with_actual") or 0)
    cov = float(ev.get("outcome_coverage") or 0)
    settled = int(ev.get("settled_forbidden_count") or 0)

    if not leakage_ok or leakage_violations > 0:
        return "RED", f"KenPom leakage violations={leakage_violations} (must be 0)"
    if settled > 0:
        return "RED", f"SETTLED continuity tags present ({settled}) — forbidden under protocol"

    if n_actual < MIN_N_EVIDENCE_AMBER or cov < OUTCOME_COV_AMBER:
        return "RED", (
            f"outcome coverage too thin for claimed scorecard "
            f"(n_actual={n_actual}, cov={cov:.2%})"
        )

    if n_actual >= MIN_N_EVIDENCE_GREEN and cov >= OUTCOME_COV_GREEN and leakage_violations == 0:
        return "GREEN", (
            f"n_actual={n_actual}; outcome_cov={cov:.2%}; leakage=0; "
            f"continuity PRIOR/UNKNOWN only; SoT D locked"
        )

    return "AMBER", (
        f"n_actual={n_actual}; outcome_cov={cov:.2%} "
        f"(below GREEN floor {OUTCOME_COV_GREEN:.0%}); leakage=0; SoT D"
    )


def influence_decision(grades: Dict[str, str]) -> Tuple[str, str]:
    pq = grades.get("predictive_quality")
    me = grades.get("market_edge_evidence")
    eq = grades.get("evidence_quality")

    if DATA_GAP in (pq, me, eq) or eq == "RED":
        return "INSUFFICIENT EVIDENCE", (
            "Evidence Quality RED or DATA GAP blocks influence claim; "
            "numbers reported honestly — no product flip"
        )
    if me == "RED" or pq == "RED":
        return "NO", "Predictive or Market Edge RED at adequate n — do not influence subscribers"
    if me == "GREEN" and eq == "GREEN" and pq in ("GREEN", "AMBER"):
        return "YES", "All pillars clear — still research-only; CoS→Ryan required for any product use"
    if me in ("GREEN", "AMBER") and eq == "AMBER":
        return "LIMITED", "Scope to Lab research windows only; no Edge Board / PLAY influence"
    return "INSUFFICIENT EVIDENCE", "Mixed / soft pillars — no influence claim"


def build_scorecard(
    *,
    out_dir: Optional[Path] = None,
    actuals_path: Optional[Path] = None,
    densify_results: bool = True,
) -> Dict[str, Any]:
    root = _repo_root()
    out_dir = out_dir or (root / "data" / "ops" / "lab" / "ncaam")
    actuals = load_actual_margins(actuals_path)

    cuts: Dict[str, Any] = {}
    leakage_ok = True
    leakage_violations = 0
    manifests: Dict[str, Any] = {}
    densify_receipts: Dict[str, Any] = {}

    for cut in ("train_a", "test_a"):
        latest = out_dir / f"ncaam-fair-lab-{cut}-latest.parquet"
        if not latest.exists():
            cuts[cut] = {"error": f"missing {latest.name} — run materialize first"}
            continue
        lab = pl.read_parquet(latest)
        if densify_results:
            lab, densify_receipts[cut] = attach_lab_outcomes(lab, event_actuals=actuals)
        else:
            lab = attach_outcomes(lab, actuals, densify=False)
        # Prefer stamped manifest if present
        man_candidates = sorted(out_dir.glob(f"ncaam-fair-lab-{cut}-*.manifest.json"))
        man = {}
        if man_candidates:
            man = json.loads(man_candidates[-1].read_text(encoding="utf-8"))
            manifests[cut] = {
                "path": str(man_candidates[-1].relative_to(root)),
                "n_lab_games": man.get("n_lab_games"),
                "n_with_fair_spread": man.get("n_with_fair_spread"),
                "n_missing_kenpom": man.get("n_missing_kenpom"),
                "kenpom_leakage_ok": man.get("kenpom_leakage_ok"),
                "kenpom_leakage_violations": man.get("kenpom_leakage_violations"),
                "n_continuity_prior": man.get("n_continuity_prior"),
                "n_continuity_unknown": man.get("n_continuity_unknown"),
                "n_open_snapshot_honest": man.get("n_open_snapshot_honest"),
            }
            if man.get("kenpom_leakage_ok") is False:
                leakage_ok = False
            leakage_violations += int(man.get("kenpom_leakage_violations") or 0)
        scored = score_cut(lab, cut=cut)
        scored["manifest"] = manifests.get(cut)
        if cut in densify_receipts:
            scored["results_attach"] = {
                "n_with_actual": densify_receipts[cut].get("n_with_actual"),
                "outcome_coverage": densify_receipts[cut].get("outcome_coverage"),
                "n_with_actual_pack": densify_receipts[cut].get("n_with_actual_pack"),
                "n_with_actual_event_id_fill": densify_receipts[cut].get(
                    "n_with_actual_event_id_fill"
                ),
                "sources": densify_receipts[cut].get("sources"),
            }
        cuts[cut] = scored

    # Primary grades from Test-A OOS only
    primary = cuts.get("test_a") or {}
    if "error" in primary or not primary.get("predictive"):
        grades = {
            "predictive_quality": DATA_GAP,
            "market_edge_evidence": DATA_GAP,
            "evidence_quality": DATA_GAP,
        }
        grade_detail = {"predictive_quality": "Test-A missing", "market_edge_evidence": "Test-A missing", "evidence_quality": "Test-A missing"}
    else:
        g_pred, d_pred = grade_predictive(primary["predictive"])
        g_me, d_me = grade_market_edge(primary["market_edge"])
        g_ev, d_ev = grade_evidence(
            primary["evidence"],
            leakage_ok=leakage_ok,
            leakage_violations=leakage_violations,
            manifests=manifests,
        )
        grades = {
            "predictive_quality": g_pred,
            "market_edge_evidence": g_me,
            "evidence_quality": g_ev,
        }
        grade_detail = {
            "predictive_quality": d_pred,
            "market_edge_evidence": d_me,
            "evidence_quality": d_ev,
        }

    influence, influence_detail = influence_decision(grades)
    generated = datetime.now(timezone.utc).isoformat()

    card: Dict[str, Any] = {
        "scorecard_version": SCORECARD_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_doc": PROTOCOL_DOC,
        "scorecard_doc": SCORECARD_DOC,
        "status": "results_filled",
        "generated_at": generated,
        "sport": "ncaam",
        "schedule_sot_lab": "D",
        "baselines": {
            "B1": "close_consensus_path_a",
            "B2": "kenpom_adjem_plus_hca_prior_unknown_honesty",
        },
        "primary_window": "test_a",
        "diagnostic_window": "train_a",
        "hard_locks": [
            "no_peek_tune_after_test_a",
            "no_edge_gt4_shopping",
            "no_edge_board_populate",
            "no_play_lean_conf",
            "kenpom_feed_not_sot",
            "continuity_prior_unknown_only",
            "path_a_only",
            "lab_joins_remain_sot_d",
            "red_equals_honest_failure_success",
        ],
        "frozen_gates": {
            "breakeven_ats": BREAKEVEN_ATS,
            "min_n_pred_green": MIN_N_PRED_GREEN,
            "min_n_pred_amber": MIN_N_PRED_AMBER,
            "mae_amber_tol": MAE_AMBER_TOL,
            "min_n_ats": MIN_N_ATS,
            "min_n_clv_green": MIN_N_CLV_GREEN,
            "clv_pos_min": CLV_POS_MIN,
            "outcome_cov_green": OUTCOME_COV_GREEN,
            "note": "Gates locked pre-fill; AMBER vocabulary per CoS #14 DAY GO",
        },
        "grades": grades,
        "grade_detail": grade_detail,
        "subscriber_influence": influence,
        "subscriber_influence_detail": influence_detail,
        "leakage_receipt": {
            "kenpom_leakage_ok": leakage_ok,
            "kenpom_leakage_violations": leakage_violations,
            "settled_forbidden_total": sum(
                int((cuts.get(c) or {}).get("evidence", {}).get("settled_forbidden_count") or 0)
                for c in ("train_a", "test_a")
            ),
        },
        "cuts": cuts,
        "inputs": {
            "actual_margins": str(
                (actuals_path or (_web_root() / "data" / "processed" / "actual_margins.parquet"))
            ),
            "n_actual_events_owned": len(actuals) if not actuals.is_empty() else 0,
            "results_densify": densify_results,
            "results_attach_receipts": densify_receipts,
            "actuals_caveat": (
                "Primary actuals from Schedule SoT packs (tip_date + B7 team_id, fail-closed). "
                "Secondary fill from owned actual_margins.parquet / results.csv by event_id. "
                "No Odds densify. Sparse espn_cbb_games_*.csv alone are insufficient for Lab coverage."
                if densify_results
                else (
                    "Thin path: owned actual_margins.parquet by event_id only "
                    "(historical v1 freeze baseline ~406 events)."
                )
            ),
        },
        "protocol": protocol_manifest(),
        "product_side_effects": "none",
    }
    return card


def write_scorecard_artifacts(
    card: Dict[str, Any],
    *,
    out_dir: Optional[Path] = None,
    overwrite_frozen_v1: bool = False,
) -> Dict[str, str]:
    """Write scorecard artifacts.

    Frozen v1 JSON/MD are NOT overwritten unless overwrite_frozen_v1=True.
    Densified runs should use the coverage receipt script instead of retuning v1.
    """
    root = _repo_root()
    out_dir = out_dir or (root / "data" / "ops" / "lab" / "ncaam")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamped = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    densified = bool((card.get("inputs") or {}).get("results_densify"))
    if densified and not overwrite_frozen_v1:
        # Keep v1 frozen — write stamped research preview only
        preview_json = out_dir / f"ncaam-fair-lab-scorecard-densify-preview-{stamped}.json"
        preview_json.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
        return {
            "preview_json": str(preview_json.relative_to(root)),
            "frozen_v1_untouched": "true",
            "note": "Densified scorecard not written over v1; use coverage receipt + v1.1 later",
        }

    json_path = out_dir / "ncaam-fair-lab-scorecard-v1.json"
    stamped_json = out_dir / f"ncaam-fair-lab-scorecard-v1-{stamped}.json"
    md_ops = out_dir / "ncaam-fair-lab-scorecard-v1.md"
    ops_note = root / "data" / "ops" / "ncaam-lab-first-scorecard-20260904.md"
    docs_md = root / "docs" / "lab" / "NCAAM_FAIR_LAB_SCORECARD_v1.md"

    payload = json.dumps(card, indent=2) + "\n"
    json_path.write_text(payload, encoding="utf-8")
    stamped_json.write_text(payload, encoding="utf-8")

    md = render_scorecard_md(card)
    md_ops.write_text(md, encoding="utf-8")
    docs_md.write_text(md, encoding="utf-8")
    ops_note.write_text(render_ops_note(card), encoding="utf-8")

    # Refresh README pointer
    readme = out_dir / "README.md"
    readme.write_text(
        "# NCAAM Lab fair artifacts\n\n"
        "Protocol twin + Train-A / Test-A fair parquet manifests + first scorecard.\n"
        "See `docs/lab/NCAAM_FAIR_LAB_PROTOCOL_v1.md`,\n"
        "`docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1.md`, and\n"
        "`data/ops/ncaam-lab-first-scorecard-20260904.md`.\n\n"
        "Results densify receipt: `data/ops/ncaam-lab-results-densify-20260904.md`.\n\n"
        "```bash\n"
        "python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut train_a\n"
        "python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut test_a\n"
        "python3 apps/web/scripts/lab_ncaam_fair_scorecard.py --no-densify  # v1 baseline\n"
        "python3 apps/web/scripts/lab_ncaam_results_coverage_receipt.py\n"
        "```\n",
        encoding="utf-8",
    )

    return {
        "json": str(json_path.relative_to(root)),
        "stamped_json": str(stamped_json.relative_to(root)),
        "md_ops": str(md_ops.relative_to(root)),
        "docs_md": str(docs_md.relative_to(root)),
        "ops_note": str(ops_note.relative_to(root)),
    }


def render_scorecard_md(card: Dict[str, Any]) -> str:
    g = card["grades"]
    gd = card["grade_detail"]
    test = card.get("cuts", {}).get("test_a", {})
    train = card.get("cuts", {}).get("train_a", {})
    tp = test.get("predictive", {})
    tm = test.get("market_edge", {})
    te = test.get("evidence", {})
    leak = card.get("leakage_receipt", {})

    def _fmt(v: Any) -> str:
        if v is None:
            return DATA_GAP
        return str(v)

    lines = [
        "# NCAAM Fair Lab Scorecard v1.0",
        "",
        f"**Protocol:** `{card['protocol_version']}` (LOCKED)",
        f"**Scorecard:** `{card['scorecard_version']}`",
        f"**Status:** `{card['status']}`",
        f"**Generated:** {card['generated_at']}",
        f"**Lab:** Kos Edge #14 CBB / NCAAM research fair engine",
        f"**Machine JSON:** [`data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.json`](../../data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.json)",
        "",
        "> Evidence report only. **No** Edge Board / PLAY / LEAN / Conf% / props.",
        "> **RED = successful** honest failure detection when criteria say so.",
        "> No peek-tuning after Test-A. No Edge>4 shopping.",
        "",
        "## Executive grades (Test-A OOS primary)",
        "",
        "| Pillar | Grade | Detail |",
        "| ------ | ----- | ------ |",
        f"| Predictive Quality | **{g['predictive_quality']}** | {gd['predictive_quality']} |",
        f"| Market Edge Evidence | **{g['market_edge_evidence']}** | {gd['market_edge_evidence']} |",
        f"| Evidence Quality | **{g['evidence_quality']}** | {gd['evidence_quality']} |",
        "",
        f"**Subscriber Influence (recommendation to CoS → Ryan):** **{card['subscriber_influence']}**",
        "",
        card["subscriber_influence_detail"],
        "",
        "## Locks held",
        "",
        "- Baselines **B1** close consensus; **B2** KenPom+HCA + PRIOR/UNKNOWN honesty",
        "- Cuts: Train-A 2022-11-07→2023-03-12; Test-A 2023-11-06→2024-01-28; 2025 pocket OUT",
        "- Schedule Lab joins **D** (Odds `event_id` + B7 fail-closed)",
        "- Continuity PRIOR/UNKNOWN only — never fake SETTLED",
        "- Market Edge open honesty: exclude open timestamp drift >7d",
        "- ESPN Schedule SoT A (PR 477) noted; Lab joins **not** switched (`slate_complete=false`)",
        "",
        "## Leakage / continuity receipt",
        "",
        f"- KenPom leakage OK: `{leak.get('kenpom_leakage_ok')}`",
        f"- KenPom leakage violations: `{leak.get('kenpom_leakage_violations')}` (must be 0)",
        f"- SETTLED forbidden count: `{leak.get('settled_forbidden_total')}` (must be 0)",
        "",
        "## Test-A Predictive (B2 vs B1, home-margin space)",
        "",
        "| Metric | Value |",
        "| ------ | ----- |",
        f"| n lab games | {_fmt(tp.get('n_lab_games'))} |",
        f"| n with actual | {_fmt(tp.get('n_with_actual'))} |",
        f"| outcome coverage | {_fmt(tp.get('outcome_coverage'))} |",
        f"| B2 margin MAE | {_fmt(tp.get('b2_margin_mae'))} |",
        f"| B2 margin RMSE | {_fmt(tp.get('b2_margin_rmse'))} |",
        f"| B2 signed bias | {_fmt(tp.get('b2_signed_bias'))} |",
        f"| B1 margin MAE | {_fmt(tp.get('b1_margin_mae'))} |",
        f"| B1 margin RMSE | {_fmt(tp.get('b1_margin_rmse'))} |",
        f"| B2 MAE ≤ B1 | {_fmt((tp.get('market_relative') or {}).get('b2_mae_le_b1'))} |",
        f"| B2/B1 MAE ratio | {_fmt((tp.get('market_relative') or {}).get('b2_vs_b1_ratio'))} |",
        "",
        "## Test-A Market Edge (full slate; honest open CLV)",
        "",
        "| Metric | Value |",
        "| ------ | ----- |",
        f"| filter | `{_fmt(tm.get('primary_filter'))}` |",
        f"| n ATS | {_fmt(tm.get('n_ats'))} |",
        f"| ATS | {_fmt(tm.get('ats'))} |",
        f"| ROI (−110) | {_fmt(tm.get('roi_minus110'))} |",
        f"| n open honest w/ actual | {_fmt(tm.get('n_open_honest_with_actual'))} |",
        f"| n CLV move | {_fmt(tm.get('n_clv_move'))} |",
        f"| CLV+ rate | {_fmt(tm.get('clv_positive_rate'))} |",
        f"| mean CLV move | {_fmt(tm.get('mean_clv_move'))} |",
        "",
        "## Test-A Evidence",
        "",
        f"- Continuity: `{_fmt(te.get('continuity_counts'))}`",
        f"- Open snapshot honest (lab rows): `{_fmt(te.get('open_snapshot_honest_n'))}`",
        f"- {te.get('espn_schedule_sot_a_note')}",
        "",
        "## Train-A diagnostic (context only — not primary grade)",
        "",
    ]
    trp = train.get("predictive", {})
    trm = train.get("market_edge", {})
    lines += [
        "| Metric | Train-A |",
        "| ------ | ------- |",
        f"| n lab / n actual | {_fmt(trp.get('n_lab_games'))} / {_fmt(trp.get('n_with_actual'))} |",
        f"| B2 MAE / B1 MAE | {_fmt(trp.get('b2_margin_mae'))} / {_fmt(trp.get('b1_margin_mae'))} |",
        f"| ATS / ROI | {_fmt(trm.get('ats'))} / {_fmt(trm.get('roi_minus110'))} |",
        f"| CLV+ (n_move) | {_fmt(trm.get('clv_positive_rate'))} ({_fmt(trm.get('n_clv_move'))}) |",
        "",
        "## Hard NOT (held)",
        "",
        "- Edge Board / PLAY / Conf% / props",
        "- Odds densify / invent tips / KenPom-as-SoT / #12 GO-2 / squash",
        "- Retune after seeing Test-A",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_ops_note(card: Dict[str, Any]) -> str:
    g = card["grades"]
    return (
        "# NCAAM Lab — first frozen scorecard (#14 DAY GO)\n\n"
        f"**As of:** {card['generated_at'][:10]}\n"
        f"**Branch base:** `cursor/ncaam-lab-fair-engine-21e8` (PR 476) / scorecard follow-up\n"
        f"**Protocol:** `{card['protocol_version']}`\n"
        f"**Scorecard:** `{card['scorecard_version']}`\n\n"
        "## Grades (Test-A OOS)\n\n"
        f"| Pillar | Grade |\n"
        f"| ------ | ----- |\n"
        f"| Predictive Quality | **{g['predictive_quality']}** |\n"
        f"| Market Edge Evidence | **{g['market_edge_evidence']}** |\n"
        f"| Evidence Quality | **{g['evidence_quality']}** |\n\n"
        f"**Subscriber Influence:** **{card['subscriber_influence']}**\n\n"
        f"{card['subscriber_influence_detail']}\n\n"
        "## Artifacts\n\n"
        "- `data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.json`\n"
        "- `data/ops/lab/ncaam/ncaam-fair-lab-scorecard-v1.md`\n"
        "- `docs/lab/NCAAM_FAIR_LAB_SCORECARD_v1.md`\n"
        "- Fair sets: `ncaam-fair-lab-{train_a,test_a}-latest.parquet`\n\n"
        "## Receipts\n\n"
        f"- Leakage violations: `{card['leakage_receipt']['kenpom_leakage_violations']}`\n"
        f"- SETTLED count: `{card['leakage_receipt']['settled_forbidden_total']}`\n"
        "- Lab joins remain Schedule SoT **D** (ESPN SoT A in PR 477 noted; `slate_complete=false`)\n"
        "- No retune after Test-A; no Edge>4 shopping; no Edge Board writes\n\n"
        "## How to re-run\n\n"
        "```bash\n"
        "python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut train_a\n"
        "python3 apps/web/scripts/lab_ncaam_fair_materialize.py --cut test_a\n"
        "python3 apps/web/scripts/lab_ncaam_fair_scorecard.py\n"
        "```\n"
    )
