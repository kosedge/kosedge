"""Go/no-go enterprise gates for NFL sides/totals as a betting product.

Prints GREEN / YELLOW / RED with honest interpretation. Does not promote
failed retunes. Props stay research-only unless a separate holdout clears.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

# -110 American breakeven
BREAKEVEN_ATS = 0.5238

# Product-level floors (subscription / betting-product claim)
GATE_ATS_HIT_MIN = BREAKEVEN_ATS
GATE_ATS_N_MIN = 200
GATE_CLV_POS_RATE_MIN = 0.55
GATE_CLV_N_MIN = 200  # "hundreds+" target
GATE_MODEL_MAE_LE_MARKET = True  # model MAE must be ≤ market close MAE
GATE_HOLDOUT_MARGIN_MAE_MAX = 9.5  # chronological supervised holdout
GATE_HOLDOUT_TOTAL_MAE_MAX = 10.5
GATE_HOLDOUT_BRIER_MAX = 0.22

# Selective PLAY unused-holdout floors (subscription claim on PLAY slice only)
GATE_PLAY_ATS_HIT_MIN = BREAKEVEN_ATS
GATE_PLAY_ATS_STRETCH = 0.55
GATE_PLAY_ATS_N_MIN = 60
GATE_PLAY_CLV_POS_RATE_MIN = 0.55
GATE_PLAY_CLV_N_MIN = 200  # product; soft confirmatory n=40 lives in publish policy


@dataclass
class GateCheck:
    name: str
    status: str  # GREEN | YELLOW | RED
    value: Any
    threshold: Any
    detail: str


@dataclass
class GateReport:
    overall: str
    betting_product_ready: bool
    selective_play_ready: bool = False
    checks: List[GateCheck] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "betting_product_ready": self.betting_product_ready,
            "selective_play_ready": self.selective_play_ready,
            "checks": [asdict(c) for c in self.checks],
            "notes": list(self.notes),
        }


def _status_rank(s: str) -> int:
    return {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(s.upper(), 2)


def _worst(*statuses: str) -> str:
    return max(statuses, key=_status_rank)


def _play_holdout_slice(play_holdout: Dict[str, Any], market: str = "spread") -> Dict[str, Any]:
    """Prefer confirmatory 2024–25 (CLV n), fall back to primary 2025."""
    confirm = play_holdout.get("confirmatory_2024_2025") or {}
    primary = play_holdout.get("primary_holdout_2025") or {}
    # Use confirmatory when it has a spread slice; gates still surface primary in value.
    src = confirm if confirm.get(market) or confirm.get("combined") else primary
    return src.get(market) or src.get("combined") or {}


def evaluate_enterprise_gates(
    *,
    grading: Optional[Dict[str, Any]] = None,
    supervised: Optional[Dict[str, Any]] = None,
    play_holdout: Optional[Dict[str, Any]] = None,
    props_stake_eligible: bool = False,
) -> GateReport:
    """Evaluate product gates from grading + supervised + PLAY-only holdout."""
    checks: List[GateCheck] = []
    notes: List[str] = []
    grading = grading or {}
    supervised = supervised or {}
    play_holdout = play_holdout or {}
    model = grading.get("model") or {}
    market = grading.get("market_close") or {}
    coverage = grading.get("coverage") or {}

    # --- ATS ---
    ats = model.get("ats_hit_rate")
    n_spread = int(model.get("n_spread") or 0)
    if ats is None or n_spread < GATE_ATS_N_MIN:
        checks.append(
            GateCheck(
                "ats_vs_minus_110",
                "RED" if ats is None else "YELLOW",
                {"hit_rate": ats, "n": n_spread},
                {"min_hit": GATE_ATS_HIT_MIN, "min_n": GATE_ATS_N_MIN},
                "Insufficient ATS sample or missing hit rate for full-slate claim.",
            )
        )
    elif float(ats) >= GATE_ATS_HIT_MIN:
        checks.append(
            GateCheck(
                "ats_vs_minus_110",
                "GREEN",
                {"hit_rate": float(ats), "n": n_spread},
                {"min_hit": GATE_ATS_HIT_MIN, "min_n": GATE_ATS_N_MIN},
                "Full-slate ATS clears −110 breakeven.",
            )
        )
    else:
        checks.append(
            GateCheck(
                "ats_vs_minus_110",
                "RED",
                {"hit_rate": float(ats), "n": n_spread},
                {"min_hit": GATE_ATS_HIT_MIN, "min_n": GATE_ATS_N_MIN},
                "Full-slate ATS below −110 breakeven — selective segments only.",
            )
        )

    # --- CLV ---
    clv_rate = model.get("clv_spread_positive_rate")
    n_clv = int(model.get("n_clv_spread") or 0)
    if n_clv < GATE_CLV_N_MIN:
        checks.append(
            GateCheck(
                "clv_spread_sample",
                "YELLOW" if n_clv >= 100 else "RED",
                {"n_clv_spread": n_clv, "positive_rate": clv_rate},
                {"min_n": GATE_CLV_N_MIN, "min_pos_rate": GATE_CLV_POS_RATE_MIN},
                "Owned open/close CLV sample below hundreds+ target.",
            )
        )
    elif clv_rate is not None and float(clv_rate) >= GATE_CLV_POS_RATE_MIN:
        checks.append(
            GateCheck(
                "clv_spread_sample",
                "GREEN",
                {"n_clv_spread": n_clv, "positive_rate": float(clv_rate)},
                {"min_n": GATE_CLV_N_MIN, "min_pos_rate": GATE_CLV_POS_RATE_MIN},
                "CLV +rate and sample clear product bar.",
            )
        )
    else:
        checks.append(
            GateCheck(
                "clv_spread_sample",
                "RED",
                {"n_clv_spread": n_clv, "positive_rate": clv_rate},
                {"min_n": GATE_CLV_N_MIN, "min_pos_rate": GATE_CLV_POS_RATE_MIN},
                "CLV +rate below floor despite adequate sample.",
            )
        )

    # --- MAE vs close ---
    m_spread = model.get("spread_mae")
    k_spread = market.get("spread_mae")
    m_total = model.get("total_mae")
    k_total = market.get("total_mae")
    if None in (m_spread, k_spread, m_total, k_total):
        checks.append(
            GateCheck(
                "mae_vs_market_close",
                "YELLOW",
                {"model_spread": m_spread, "market_spread": k_spread,
                 "model_total": m_total, "market_total": k_total},
                "model_mae <= market_mae",
                "Missing MAE comparison inputs.",
            )
        )
    else:
        spread_ok = float(m_spread) <= float(k_spread)
        total_ok = float(m_total) <= float(k_total)
        if spread_ok and total_ok:
            status = "GREEN"
            detail = "Model beats market close MAE on spread and total."
        elif spread_ok or total_ok:
            status = "YELLOW"
            detail = "Model beats market on one of spread/total MAE only."
        else:
            status = "RED"
            detail = "Model worse than market close MAE on both markets."
        checks.append(
            GateCheck(
                "mae_vs_market_close",
                status,
                {
                    "model_spread_mae": float(m_spread),
                    "market_spread_mae": float(k_spread),
                    "model_total_mae": float(m_total),
                    "market_total_mae": float(k_total),
                },
                "model_mae <= market_mae",
                detail,
            )
        )

    # --- Supervised chronological holdout ---
    metrics = supervised.get("metrics") or supervised
    test_brier = metrics.get("test_brier")
    test_margin = metrics.get("test_margin_mae")
    test_total = metrics.get("test_total_mae")
    schema = supervised.get("schema_version")
    has_kav = "diff_kav_net_5g" in (supervised.get("feature_keys") or [])
    if test_brier is None or test_margin is None or test_total is None:
        checks.append(
            GateCheck(
                "supervised_holdout",
                "YELLOW",
                {"schema_version": schema, "has_kav": has_kav},
                {
                    "max_brier": GATE_HOLDOUT_BRIER_MAX,
                    "max_margin_mae": GATE_HOLDOUT_MARGIN_MAE_MAX,
                    "max_total_mae": GATE_HOLDOUT_TOTAL_MAE_MAX,
                },
                "Supervised holdout metrics missing.",
            )
        )
    else:
        ok = (
            float(test_brier) <= GATE_HOLDOUT_BRIER_MAX
            and float(test_margin) <= GATE_HOLDOUT_MARGIN_MAE_MAX
            and float(test_total) <= GATE_HOLDOUT_TOTAL_MAE_MAX
            and (schema is None or int(schema) >= 3)
        )
        checks.append(
            GateCheck(
                "supervised_holdout",
                "GREEN" if ok else "RED",
                {
                    "test_brier": float(test_brier),
                    "test_margin_mae": float(test_margin),
                    "test_total_mae": float(test_total),
                    "schema_version": schema,
                    "has_kav_feature": has_kav,
                    "test_rows": metrics.get("test_rows"),
                },
                {
                    "max_brier": GATE_HOLDOUT_BRIER_MAX,
                    "max_margin_mae": GATE_HOLDOUT_MARGIN_MAE_MAX,
                    "max_total_mae": GATE_HOLDOUT_TOTAL_MAE_MAX,
                    "min_schema": 3,
                },
                "Chronological holdout within floors."
                if ok
                else "Holdout metrics miss floors or schema < v3.",
            )
        )

    # --- Coverage / densify ---
    owned_oc = int(coverage.get("owned_open_close_games") or 0)
    if owned_oc >= 800:
        cov_status = "GREEN"
    elif owned_oc >= 400:
        cov_status = "YELLOW"
    else:
        cov_status = "RED"
    checks.append(
        GateCheck(
            "owned_open_close_coverage",
            cov_status,
            {"owned_open_close_games": owned_oc},
            {"green_min": 800, "yellow_min": 400},
            "Owned open/close game coverage for CLV densify track.",
        )
    )

    # --- Props ---
    checks.append(
        GateCheck(
            "props_stake_policy",
            "GREEN" if not props_stake_eligible else "RED",
            {"props_stake_eligible": props_stake_eligible},
            {"expected": False},
            "Props must remain research-only / stake-off until holdout clears.",
        )
    )

    # --- PLAY-only unused holdout (primary subscription claim axis) ---
    spread_play = _play_holdout_slice(play_holdout, "spread")
    primary_spread = (play_holdout.get("primary_holdout_2025") or {}).get("spread") or {}
    combined_play = _play_holdout_slice(play_holdout, "combined")
    play_ats = spread_play.get("hit_rate")
    play_n = int(spread_play.get("n") or 0)
    # Prefer movement-CLV fields from v2 holdout artifact.
    play_clv_n = int(
        spread_play.get("n_clv_move")
        or spread_play.get("n_clv")
        or 0
    )
    play_clv_rate = spread_play.get("clv_positive_rate")
    play_overall = (play_holdout.get("overall") or {}).get("gate")
    if not play_holdout or play_ats is None:
        checks.append(
            GateCheck(
                "play_only_holdout",
                "RED",
                {"artifact_present": bool(play_holdout)},
                {
                    "ats_min": GATE_PLAY_ATS_HIT_MIN,
                    "ats_n_min": GATE_PLAY_ATS_N_MIN,
                    "clv_pos_min": GATE_PLAY_CLV_POS_RATE_MIN,
                    "clv_n_min": GATE_PLAY_CLV_N_MIN,
                },
                "PLAY-only holdout artifact missing — run scripts/nfl/play_only_holdout.py.",
            )
        )
    else:
        ats_ok = play_n >= GATE_PLAY_ATS_N_MIN and float(play_ats) >= GATE_PLAY_ATS_HIT_MIN
        clv_ok = (
            play_clv_n >= GATE_PLAY_CLV_N_MIN
            and play_clv_rate is not None
            and float(play_clv_rate) >= GATE_PLAY_CLV_POS_RATE_MIN
        )
        if ats_ok and clv_ok:
            play_status = "GREEN"
            play_detail = (
                "Confirmatory spread PLAY (v2 band, movement-CLV) clears ATS + CLV product floors."
            )
        elif ats_ok and play_clv_n >= 40 and play_clv_rate is not None and float(play_clv_rate) >= GATE_PLAY_CLV_POS_RATE_MIN:
            play_status = "YELLOW"
            play_detail = (
                "Spread PLAY ATS clears; movement-CLV +rate clears soft n but below n≥200."
            )
        elif ats_ok:
            play_status = "YELLOW"
            play_detail = (
                "Spread PLAY ATS clears −110, but movement-CLV fails or sample thin. "
                "Do NOT claim subscription GREEN / ~60% until CLV clears."
            )
        else:
            play_status = "RED"
            play_detail = "Spread PLAY holdout fails ATS floor or sample."
        if (
            ats_ok
            and play_ats is not None
            and float(play_ats) >= GATE_PLAY_ATS_STRETCH
            and not clv_ok
        ):
            notes.append(
                "PLAY ATS looks strong but movement-CLV does not clear n≥200 @ 55% — "
                "do not market 60%."
            )
        checks.append(
            GateCheck(
                "play_only_holdout",
                play_status,
                {
                    "spread_play_confirmatory": spread_play,
                    "spread_play_primary_2025": primary_spread,
                    "combined_play_gate": combined_play.get("gate"),
                    "artifact_overall_gate": play_overall,
                    "mean_abs_edge": spread_play.get("mean_abs_edge"),
                    "green_segments": play_holdout.get("green_segments_2025") or [],
                    "best_segment": play_holdout.get("best_segment_2025"),
                    "policy_version": (play_holdout.get("pre_registered") or {}).get(
                        "policy_version"
                    ),
                },
                {
                    "ats_min": GATE_PLAY_ATS_HIT_MIN,
                    "ats_stretch": GATE_PLAY_ATS_STRETCH,
                    "ats_n_min": GATE_PLAY_ATS_N_MIN,
                    "clv_pos_min": GATE_PLAY_CLV_POS_RATE_MIN,
                    "clv_n_min": GATE_PLAY_CLV_N_MIN,
                    "clv_methodology": "movement_only",
                },
                play_detail,
            )
        )

    overall = "GREEN"
    for c in checks:
        overall = _worst(overall, c.status)

    # Full-slate betting-product claim still requires full-slate ATS+CLV green.
    # Selective subscription claim additionally requires PLAY-only holdout GREEN.
    critical = {c.name: c.status for c in checks}
    betting_ready = (
        overall == "GREEN"
        and critical.get("ats_vs_minus_110") == "GREEN"
        and critical.get("clv_spread_sample") == "GREEN"
        and critical.get("play_only_holdout") == "GREEN"
        and critical.get("mae_vs_market_close") in {"GREEN", "YELLOW"}
        and critical.get("supervised_holdout") == "GREEN"
        and not props_stake_eligible
    )
    selective_ready = (
        critical.get("play_only_holdout") == "GREEN"
        and critical.get("supervised_holdout") == "GREEN"
        and critical.get("mae_vs_market_close") in {"GREEN", "YELLOW"}
        and not props_stake_eligible
    )

    if not betting_ready:
        notes.append(
            "Do NOT claim betting-product ready. Ship selective PASS-default "
            "publish gates and keep improving ATS/CLV samples."
        )
    if selective_ready and not betting_ready:
        notes.append(
            "Selective PLAY holdout GREEN — chargeable wedge is PLAY-tagged sides only, "
            "not full-slate."
        )
    if critical.get("ats_vs_minus_110") == "RED":
        notes.append(
            "Full-slate ATS failed — publish PLAY only on segments that clear "
            "nfl_side_total_publish_policy evidence."
        )
    if critical.get("play_only_holdout") in {"RED", "YELLOW"}:
        notes.append(
            "PLAY-only unused holdout not GREEN — keep NFL_PRODUCT_GATE_STATUS "
            "conservative; PASS default remains mandatory."
        )

    return GateReport(
        overall=overall if betting_ready or overall != "GREEN" else "YELLOW",
        betting_product_ready=betting_ready,
        selective_play_ready=selective_ready,
        checks=checks,
        notes=notes,
    )
