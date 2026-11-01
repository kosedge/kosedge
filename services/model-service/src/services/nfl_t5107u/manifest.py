"""FROZEN_MANIFEST — design / input-source / fit-policy seal (before EVAL)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .if_control import (
    IF_ASOF,
    IF_EFFICIENCY_CONTRACT,
    IF_FRAMEWORK,
    IF_SIMULATOR,
    IF_TIP,
    KNOWN_MISSING_ARTIFACTS,
    REQUIRED_FIELDS,
)
from .q2 import (
    A_Q2,
    B_Q2,
    CONFIG_SHA256,
    FIT_OBJECT_SHA256,
    FIT_POLICY,
    GAMES_SHA256_PREFIX,
    LAMBDA,
    OUTCOMES_SHA256_PREFIX,
    PARAMETER_LABEL,
    PARAMETER_STATUS,
    REGRESS_FRAC,
    T5107U_DEV_SEASONS,
    T5107U_EVAL_SEASONS,
    TRAINING_END_SEASON,
    TRAINING_SEASONS,
    TRANSFER_MAX_TRAINING_SEASON,
    verify_q2_transfer_policy,
)
from .evaluator import (
    BENCHMARK_BOOKS,
    BOOT_B,
    BOOT_SEED,
    CUTOFF_MINUTES,
    MAX_QUOTE_AGE_HOURS,
    MIN_N_REPORT,
    PER_SEASON_EXCLUSION_HOLD,
)
from .builder import CHALLENGER_WEIGHT, LABEL

FROZEN_MANIFEST_SCHEMA = "nfl-t5107u-frozen-manifest-v1"
DEFAULT_PATH = Path("data/ops/nfl-forecast-builder-t5107u/FROZEN_MANIFEST.json")


def build_frozen_manifest(*, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    transfer = verify_q2_transfer_policy(proposed_refit=False)
    payload: dict[str, Any] = {
        "schema_version": FROZEN_MANIFEST_SCHEMA,
        "label": LABEL,
        "cert_candidate": 0,
        "purpose": "seal_design_input_source_fit_policy_before_eval",
        "sealed": True,
        "sealed_before_eval_generation": True,
        "eval_generation": "NOT_RUN",
        "exec_scoring": "REFUSED_PENDING_ALEX_PREFLIGHT_AND_COS_BIND",
        "paper_tip": "7139f8d9eed71b47eabf8827c0593932a38fea9a36686c66df3f6311282628c7",
        "paper_cover": "af08183c674ab51ff87c75f5bc90cc12c69e8f4569a66ce2e9f314021da926f3",
        "authority": "OWNER AMEND+CLEAR t5107u G1–G7",
        "reuse": {
            "t5105u_689": "f33637db75def870bc9b9ca84a73ce754b21cdae",
            "t5105u_690": "cc594b6fb09b8fdb5368e13be72a263e88920e4c",
            "accept": "e68a11cb",
            "pass_ro": "e78176c3",
            "if_consume": "19c6a4607",
            "q2_library": "8155fd194",
            "q2_handoff": "43b5a6223",
        },
        "design": {
            "challenger": "mC = 0.5*mIF + 0.5*mQ2 (home-away points)",
            "challenger_weight": CHALLENGER_WEIGHT,
            "extra_hfa": 0.0,
            "market_blend": 0.0,
            "weight_search": False,
            "control": "IF @ 6ca03716 retained; archived vs reconstructed labeled",
            "silent_if_drop": False,
            "dev_seasons": list(T5107U_DEV_SEASONS),
            "eval_seasons": list(T5107U_EVAL_SEASONS),
            "season_type": "REG",
            "no_2024_25": True,
            "no_stage_c": True,
            "label": LABEL,
        },
        "input_source": {
            "games_csv_prefix": GAMES_SHA256_PREFIX,
            "outcomes_prefix": OUTCOMES_SHA256_PREFIX,
            "asof_rule": IF_ASOF,
            "if_tip": IF_TIP,
            "if_simulator": IF_SIMULATOR,
            "if_framework": IF_FRAMEWORK,
            "if_efficiency_contract": IF_EFFICIENCY_CONTRACT,
            "if_required_fields": list(REQUIRED_FIELDS),
            "prior_game_only": True,
            "target_outcome_in_own_forecast": False,
        },
        "fit_policy": {
            **transfer,
            "a_q2": A_Q2,
            "b_q2": B_Q2,
            "lam": LAMBDA,
            "regress_frac": REGRESS_FRAC,
            "training_seasons": list(TRAINING_SEASONS),
            "training_end_season": TRAINING_END_SEASON,
            "transfer_max_training_season": TRANSFER_MAX_TRAINING_SEASON,
            "parameter_label": PARAMETER_LABEL,
            "parameter_status": PARAMETER_STATUS,
            "fit_object_sha256": FIT_OBJECT_SHA256,
            "config_sha256": CONFIG_SHA256,
            "dev_2020_21_refit": False,
        },
        "market": {
            "cutoff_minutes_before_kickoff": CUTOFF_MINUTES,
            "max_quote_age_hours": MAX_QUOTE_AGE_HOURS,
            "books": sorted(BENCHMARK_BOOKS),
            "de_vig": "multiplicative qH/(qH+qA)",
            "consensus": "median eligible books",
            "p_bind": "refuse unbound probability line/side (t5105u harness)",
            "timezone": "explicit offset or named source_timezone; naive refused",
        },
        "metrics": {
            "primary": "paired_delta_MAE vs market and vs IF",
            "secondary": ["MAE", "RMSE", "bias", "per_season"],
            "win_brier_logloss": "only if genuine probabilities exist",
            "ties": "reported separately; excluded from binary metrics",
            "logloss_clip": "1/8000",
            "bootstrap_B": BOOT_B,
            "bootstrap_seed": BOOT_SEED,
            "min_n": MIN_N_REPORT,
            "n_lt_100": "DESCRIPTIVE_ONLY",
            "per_season_exclusion_hold": PER_SEASON_EXCLUSION_HOLD,
            "ci_cross_zero": "INCONCLUSIVE",
            "enterprise_pass": False,
        },
        "blockers": list(KNOWN_MISSING_ARTIFACTS)
        + [
            {
                "artifact": "outcomes_2023_score_only",
                "detail": "50bda875 extract stops at 2022; 2023 REG in-season Q2 as-of blocked",
            },
        ],
        "notes": [
            "Seal is design/input-source/fit-policy only.",
            "EVAL sequential generation and EXEC scoring are NOT authorized by this seal alone.",
            "Alex preflight GO + CoS one-run bind required before scoring.",
        ],
    }
    if extra:
        payload.update(dict(extra))
    return payload


def sha256_bytes(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def seal_frozen_manifest(path: Path | None = None) -> dict[str, Any]:
    dest = Path(path) if path else DEFAULT_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = build_frozen_manifest()
    payload["sealed_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    digest = sha256_bytes(payload)
    payload["manifest_sha256"] = digest
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    payload["_path"] = str(dest)
    return payload
