"""Matchup-architecture holdout (E1–E5). Research only.

Frozen splits are pre-registered and must not be changed after seeing scores:

* Train-0 = 2022 W1–14 (fit window, not used to pick a ship)
* Val-0   = 2023 W1–14 (first out-of-time)
* Val-1   = 2024 W1–14 (decision / untouched holdout)

2025 remains sealed. 2026 is confirm-only and is not in any loss.
Production ``MATCHUP_RESPONSE`` stays 1.40. No coefficient is written.
Market close is a diagnostic, not the objective.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from src.services.cfb_season_engine import priors as P
from src.services.cfb_season_engine.priors import (
    overlay_matchup_response,
    overlay_score_components,
)
from src.services.cfb_season_engine.qb_feature_contract import (
    QB_FEATURE_CONTRACT_VERSION,
)
from src.services.cfb_season_engine.team_features import (
    CFB_EDGE_BOARD_PUBLIC_ENABLED,
)
from src.services.cfb_warehouse.frozen_140_scoring import (
    LEGAL_SEASONS,
    SPLITS,
    FrozenScoringError,
    assert_frozen_priors,
    load_legal_scoring_bundle,
    refuse_sealed_or_confirm,
    score_joined_rows,
    summarize_scored,
)

# Pre-registered. Do not edit after the first scored run.
PROTOCOL_SPLITS = {
    "train_0": {"seasons": (2022,), "weeks": "1-14", "role": "registered_train_not_a_fit_target"},
    "val_0": {"seasons": (2023,), "weeks": "1-14", "role": "first_out_of_time"},
    "val_1": {"seasons": (2024,), "weeks": "1-14", "role": "untouched_holdout"},
}
assert PROTOCOL_SPLITS["train_0"]["seasons"] == SPLITS["train_0"]["seasons"]
assert PROTOCOL_SPLITS["val_0"]["seasons"] == SPLITS["val_0"]["seasons"]
assert PROTOCOL_SPLITS["val_1"]["seasons"] == SPLITS["val_1"]["seasons"]

# E2 includes 1.00 as the control. 1.40 is the production baseline, not a candidate.
E2_GRID = (1.00, 1.15, 1.25)
FROZEN_BASELINE = 1.40

EXPERIMENTS: Tuple[Dict[str, Any], ...] = (
    {
        "id": "baseline_140",
        "family": "baseline",
        "label": "production MATCHUP_RESPONSE=1.40",
        "response": 1.40,
        "overlay": {},
    },
    {
        "id": "E1_response_1.00",
        "family": "E1",
        "label": "MATCHUP_RESPONSE=1.00 (linear ratio, composed indexes)",
        "response": 1.00,
        "overlay": {},
    },
    {
        "id": "E2_response_1.15",
        "family": "E2",
        "label": "MATCHUP_RESPONSE=1.15",
        "response": 1.15,
        "overlay": {},
    },
    {
        "id": "E2_response_1.25",
        "family": "E2",
        "label": "MATCHUP_RESPONSE=1.25",
        "response": 1.25,
        "overlay": {},
    },
    {
        "id": "E0_identity_matchup",
        "family": "E0",
        "label": "identity matchup (ratio→1; diagnosis neutralization)",
        "response": None,
        "overlay": {"matchup_mode": "identity"},
    },
    {
        "id": "E3_raw_efficiency",
        "family": "E3",
        "label": "matchup from raw off_eff/def_eff, still **1.40",
        "response": 1.40,
        "overlay": {"matchup_mode": "raw_efficiency"},
    },
    {
        "id": "E3_raw_efficiency_r1",
        "family": "E3",
        "label": "matchup from raw off_eff/def_eff, **1.00",
        "response": 1.00,
        "overlay": {"matchup_mode": "raw_efficiency"},
    },
    {
        "id": "E4_possessions_ppp",
        "family": "E4",
        "label": "possessions × linear PPP on composed ratio",
        "response": None,
        "overlay": {"matchup_mode": "possessions_ppp"},
    },
    {
        "id": "E5_zero_adders",
        "family": "E5",
        "label": "zero HFA / coaching / special teams (totals adders off)",
        "response": None,
        "overlay": {
            "zero_hfa": True,
            "zero_coaching": True,
            "zero_special_teams": True,
        },
    },
)


def _favorite_card(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    close_n = 0
    close_hit = 0
    actual_n = 0
    actual_hit = 0
    flips_vs_close = 0
    for raw in rows:
        model = float(raw["model_spread_home"])
        close = float(raw["close_spread_home"])
        actual = float(raw["actual_margin"])
        if abs(model) > 1e-9 and abs(close) > 1e-9:
            close_n += 1
            agree = (model < 0) == (close < 0)
            if agree:
                close_hit += 1
            else:
                flips_vs_close += 1
        if abs(model) > 1e-9 and abs(actual) > 1e-9:
            actual_n += 1
            if (model < 0) == (actual > 0):
                actual_hit += 1
    return {
        "favorite_agree_vs_close_n": close_n,
        "favorite_agree_vs_close": (close_hit / close_n) if close_n else None,
        "favorite_flips_vs_close": flips_vs_close,
        "favorite_agree_vs_actual_n": actual_n,
        "favorite_agree_vs_actual": (actual_hit / actual_n) if actual_n else None,
    }


def _split_rows(rows: Sequence[Mapping[str, Any]], name: str) -> List[Mapping[str, Any]]:
    seasons = set(PROTOCOL_SPLITS[name]["seasons"])
    return [r for r in rows if int(r["season"]) in seasons]


def _enrich(summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    out = dict(summary)
    splits = dict(out.get("splits") or {})
    for name in PROTOCOL_SPLITS:
        block = dict(splits.get(name) or {})
        subset = _split_rows(rows, name)
        block["favorite"] = _favorite_card(subset)
        splits[name] = block
    out["splits"] = splits
    by_season = dict(out.get("by_season") or {})
    for season, block in by_season.items():
        subset = [r for r in rows if int(r["season"]) == int(season)]
        row = dict(block)
        row["favorite"] = _favorite_card(subset)
        by_season[season] = row
    out["by_season"] = by_season
    return out


def _card(summary: Mapping[str, Any], split: str) -> Dict[str, Any]:
    block = (summary.get("splits") or {}).get(split) or {}
    fav = block.get("favorite") or {}
    high = (block.get("slices") or {}).get("high_total_tail_ge_68") or {}
    buckets = block.get("projected_total_buckets") or {}
    return {
        "n": block.get("n"),
        "total_mae_vs_actual": block.get("total_vs_actual_mae"),
        "total_rmse_vs_actual": block.get("total_vs_actual_rmse"),
        "total_bias_vs_actual": block.get("total_vs_actual_bias"),
        "total_medae_vs_actual": block.get("total_vs_actual_median_abs"),
        "error_vs_actual_quantiles": block.get("error_vs_actual_quantiles"),
        "total_mae_vs_close": block.get("total_vs_close_mae"),
        "total_bias_vs_close": block.get("total_vs_close_bias"),
        "spread_mae_vs_close": block.get("spread_vs_close_mae"),
        "margin_mae_vs_actual": block.get("margin_vs_actual_mae"),
        "mean_model_total": block.get("mean_model_total"),
        "mean_actual_total": block.get("mean_actual_total"),
        "mean_close_total": block.get("mean_close_total"),
        "favorite_agree_vs_close": fav.get("favorite_agree_vs_close"),
        "favorite_flips_vs_close": fav.get("favorite_flips_vs_close"),
        "favorite_agree_vs_actual": fav.get("favorite_agree_vs_actual"),
        "high_tail_n": high.get("n"),
        "high_tail_bias_vs_actual": high.get("total_vs_actual_bias"),
        "projected_total_buckets": {
            name: {
                "n": brow.get("n"),
                "bias_vs_actual": brow.get("total_vs_actual_bias"),
                "mae_vs_actual": brow.get("total_vs_actual_mae"),
            }
            for name, brow in buckets.items()
        },
    }


def score_experiment(
    spec: Mapping[str, Any],
    bundle: Mapping[str, Any],
    *,
    lake_only: bool,
) -> Dict[str, Any]:
    assert_frozen_priors()
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
        raise FrozenScoringError("production MATCHUP_RESPONSE drifted from 1.40")
    response = spec.get("response")
    overlay = spec.get("overlay") or {}
    with overlay_matchup_response(response):
        with overlay_score_components(overlay):
            if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
                raise FrozenScoringError("overlay mutated MATCHUP_RESPONSE")
            scored, skipped = score_joined_rows(
                bundle["joined"], bundle["universes"], lake_only=lake_only
            )
    if abs(float(P.MATCHUP_RESPONSE) - FROZEN_BASELINE) > 1e-9:
        raise FrozenScoringError("overlay leaked after reset")
    summary = _enrich(summarize_scored(scored), scored)
    return {
        "id": spec["id"],
        "family": spec["family"],
        "label": spec["label"],
        "response_overlay": response,
        "score_overlay": overlay,
        "production_matchup_response_still": P.MATCHUP_RESPONSE,
        "skipped": skipped,
        "n_scored": summary.get("n_scored"),
        "splits": {name: _card(summary, name) for name in PROTOCOL_SPLITS},
        "by_season": {
            season: {
                "n": block.get("n"),
                "total_bias_vs_actual": block.get("total_vs_actual_bias"),
                "total_mae_vs_actual": block.get("total_vs_actual_mae"),
                "favorite_agree_vs_close": (block.get("favorite") or {}).get(
                    "favorite_agree_vs_close"
                ),
            }
            for season, block in (summary.get("by_season") or {}).items()
        },
    }


def _causality(records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_id = {r["id"]: r for r in records}
    base = (by_id.get("baseline_140") or {}).get("splits") or {}
    e1 = (by_id.get("E1_response_1.00") or {}).get("splits") or {}
    e0 = (by_id.get("E0_identity_matchup") or {}).get("splits") or {}
    evidence: List[str] = []
    supported = True
    for split in ("val_1", "val_0", "train_0"):
        b = (base.get(split) or {}).get("total_bias_vs_actual")
        i1 = (e1.get(split) or {}).get("total_bias_vs_actual")
        i0 = (e0.get(split) or {}).get("total_bias_vs_actual")
        if b is None or i1 is None:
            supported = False
            evidence.append(f"{split}: missing baseline or E1")
            continue
        drop_e1 = float(b) - float(i1)
        evidence.append(
            f"{split}: baseline bias {float(b):+.2f} → E1 {float(i1):+.2f} (Δ {drop_e1:+.2f})"
        )
        if drop_e1 < 1.5:
            supported = False
            evidence.append(f"{split}: E1 did not move bias by ≥1.5")
        if i0 is not None:
            evidence.append(
                f"{split}: identity matchup bias {float(i0):+.2f} "
                f"(Δ vs baseline {float(b) - float(i0):+.2f})"
            )
    flips_base = (base.get("val_1") or {}).get("favorite_flips_vs_close")
    flips_e1 = (e1.get("val_1") or {}).get("favorite_flips_vs_close")
    if flips_base is not None and flips_e1 is not None:
        evidence.append(
            f"Val-1 favorite flips vs close: baseline {flips_base} → E1 {flips_e1}"
        )
    return {
        "e1_reduces_holdout_bias": supported,
        "evidence": evidence,
        "note": (
            "Causality here means the nonlinear composed-index matchup term "
            "moves totals bias and favorite identity on untouched 2022–24 data. "
            "It does not earn a production coefficient."
        ),
    }


def decide(records: Sequence[Mapping[str, Any]], *, lake_mounted: bool) -> Dict[str, Any]:
    if not lake_mounted:
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "ship": False,
            "why": ["legal Odds-API lake not mounted; cannot score frozen splits"],
        }
    if not records:
        return {
            "decision": "INSUFFICIENT EVIDENCE",
            "ship": False,
            "why": ["no experiments scored"],
        }
    causality = _causality(records)
    return {
        "decision": (
            "CAUSALITY_SUPPORTED_DO_NOT_SHIP"
            if causality["e1_reduces_holdout_bias"]
            else "INSUFFICIENT_CAUSALITY_DO_NOT_SHIP"
        ),
        "ship": False,
        "recommended_coefficient": None,
        "causality": causality,
        "why": [
            "n=47 W2 DK snapshot is diagnosis only and was not in this loss",
            "E2 is a grid, not an argmin. Do not pick 1.15 or 1.25 from Val-1 MAE",
            "Market MAE is diagnostic. Do not optimize to reproduce the book",
            "Production MATCHUP_RESPONSE remains 1.40",
            "Public board / #532 stay dark",
            *causality["evidence"],
        ],
    }


def run_matchup_architecture_holdout(
    *,
    cache_dir=None,
    lake_only: bool = True,
) -> Dict[str, Any]:
    assert_frozen_priors()
    refuse_sealed_or_confirm(LEGAL_SEASONS)
    if QB_FEATURE_CONTRACT_VERSION != "cfb-qb-feature-v1":
        raise FrozenScoringError("qb feature contract drifted")
    if CFB_EDGE_BOARD_PUBLIC_ENABLED:
        raise FrozenScoringError("public board kill switch must stay off")

    bundle = load_legal_scoring_bundle(cache_dir=cache_dir, lake_only=lake_only)
    lake_mounted = all(
        (bundle.get("lake_locate") or {}).get(str(season), {}).get("mounted")
        for season in LEGAL_SEASONS
    )
    records: List[Dict[str, Any]] = []
    if lake_mounted:
        for spec in EXPERIMENTS:
            records.append(score_experiment(spec, bundle, lake_only=lake_only))
    gate = decide(records, lake_mounted=lake_mounted)
    return {
        "role": "architecture_holdout",
        "do_not_tune": True,
        "do_not_subtract_10": True,
        "kill_switch": "OFF",
        "merge_532": False,
        "used_2026_for_fitting": False,
        "opened_2025": False,
        "wrote_production_coefficient": False,
        "qb_feature_contract_version": QB_FEATURE_CONTRACT_VERSION,
        "matchup_response_frozen": P.MATCHUP_RESPONSE,
        "engine_version": P.ENGINE_VERSION,
        "protocol_splits": PROTOCOL_SPLITS,
        "e2_grid": list(E2_GRID),
        "objective": (
            "actual MAE / bias / favorite identity / tails / projected-total "
            "buckets / year stability. Close is diagnostic only."
        ),
        "lake_only": lake_only,
        "lake_mounted": lake_mounted,
        "lake_locate": bundle.get("lake_locate"),
        "experiments": records,
        "decision": gate,
        "reconstruction_limits": [
            "v1 universe: Layer A QB + prior-year efficiency + league-avg roster/units.",
            "Live 2026 real-roster path is wider-ratio than this reconstruction.",
            "E4 possessions=12.6×pace is a scaffold, not a fitted drive model.",
            "E3 uses packaged off_eff/def_eff, not EPA/success/explosiveness PBP.",
            "2025 sealed. 2026 W2 n=47 is not in this loss.",
        ],
    }
