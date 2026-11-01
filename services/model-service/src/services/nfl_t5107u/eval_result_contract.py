"""Inherited EVAL result contract — vs IF **and** market.

DEV437 is IF-only + market NOT_READY. That diagnostic does not complete
this contract. The EVAL scoring path must emit, for **both** IF and market:

- achieved MAE / RMSE / bias
- per-season tables
- game-cluster and season-week-cluster CIs on signed paired loss diffs

Schema/tests only. No live EVAL EXEC. CERT=0. DRAFT≠merge.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .evaluator import BOOT_B, BOOT_SEED

SCHEMA = "nfl-t5129u-eval-result-contract-v1"

EVAL_RESULT_CONTRACT_KEYS = (
    "n",
    "n_by_season",
    "mae_challenger",
    "mae_if",
    "mae_market",
    "rmse_challenger",
    "rmse_if",
    "rmse_market",
    "bias_challenger",
    "bias_if",
    "bias_market",
    "delta_mae_vs_if",
    "delta_mae_vs_market",
    "mean_signed_diff_vs_if",
    "mean_signed_diff_vs_market",
    "per_season",
    "bootstrap_game",
    "bootstrap_season_week",
    "bootstrap_game_vs_market",
    "bootstrap_season_week_vs_market",
)

PER_SEASON_CONTRACT_KEYS = (
    "n",
    "mae_challenger",
    "mae_if",
    "mae_market",
    "rmse_challenger",
    "rmse_if",
    "rmse_market",
    "bias_challenger",
    "bias_if",
    "bias_market",
    "mean_signed_diff_vs_if",
    "mean_signed_diff_vs_market",
)

BOOTSTRAP_KEYS = (
    "bootstrap_game",
    "bootstrap_season_week",
    "bootstrap_game_vs_market",
    "bootstrap_season_week_vs_market",
)


class EvalResultContractRefuse(ValueError):
    """EVAL result missing IF+market contract fields. Not a retune. Not EXEC."""


def _present(value: Any) -> bool:
    return value is not None


def _check_bootstrap(name: str, body: Any) -> None:
    if not isinstance(body, Mapping):
        raise EvalResultContractRefuse(f"{name} missing from EVAL result")
    ci = body.get("ci95")
    if not isinstance(ci, (list, tuple)) or len(ci) != 2:
        raise EvalResultContractRefuse(f"{name} requires ci95 [lo, hi]")
    if body.get("B") != BOOT_B:
        raise EvalResultContractRefuse(f"{name} bootstrap B is frozen at {BOOT_B}")
    if body.get("seed") != BOOT_SEED:
        raise EvalResultContractRefuse(f"{name} bootstrap seed is frozen at {BOOT_SEED}")
    if "point" not in body:
        raise EvalResultContractRefuse(f"{name} requires point (MEAN signed paired loss diff)")


def validate_eval_result_contract(scored: Mapping[str, Any]) -> None:
    """Require vs-IF **and** vs-market. DEV437 / IF-only does not pass."""
    if not isinstance(scored, Mapping):
        raise EvalResultContractRefuse("EVAL result is not a mapping")
    missing = [k for k in EVAL_RESULT_CONTRACT_KEYS if k not in scored]
    if missing:
        raise EvalResultContractRefuse(
            f"EVAL result contract incomplete (need IF and market): {missing}"
        )
    for key in (
        "mae_if",
        "mae_market",
        "rmse_if",
        "rmse_market",
        "bias_if",
        "bias_market",
        "mean_signed_diff_vs_if",
        "mean_signed_diff_vs_market",
    ):
        if not _present(scored.get(key)):
            raise EvalResultContractRefuse(
                f"EVAL result missing {key} — DEV437 / IF-only does not complete this contract"
            )
    seasons = scored.get("per_season")
    if not isinstance(seasons, Mapping) or not seasons:
        raise EvalResultContractRefuse("EVAL result requires per-season tables vs IF and market")
    n_by = scored.get("n_by_season")
    if not isinstance(n_by, Mapping) or not n_by:
        raise EvalResultContractRefuse("EVAL result requires n_by_season")
    for season, row in seasons.items():
        if not isinstance(row, Mapping):
            raise EvalResultContractRefuse(f"per_season[{season}] is not a table")
        gap = [k for k in PER_SEASON_CONTRACT_KEYS if k not in row or not _present(row.get(k))]
        if gap:
            raise EvalResultContractRefuse(
                f"per_season[{season}] missing IF+market fields: {gap}"
            )
    for name in BOOTSTRAP_KEYS:
        _check_bootstrap(name, scored.get(name))


def apply_eval_result_contract(scored: dict[str, Any]) -> dict[str, Any]:
    """Validate then stamp. Mutates ``scored`` in place."""
    validate_eval_result_contract(scored)
    scored["eval_result_contract"] = SCHEMA
    scored["eval_result_sides"] = ["if", "market"]
    return scored


def refuse_incomplete_market_before_claim(
    *,
    eligible_cohorts: Mapping[str, Any] | None,
    market_points: Sequence[Mapping[str, Any]] | None,
) -> None:
    """IF-only / partial market must not claim (look burn). Pre-claim, pre-loader."""
    allow = list(((eligible_cohorts or {}).get("margin_cohort") or {}).get("game_ids") or [])
    if not allow:
        raise EvalResultContractRefuse(
            "eligible margin cohort required for market-completeness gate"
        )
    market_by = {str(p.get("game_id")): p for p in (market_points or [])}
    missing = [
        gid for gid in allow if (market_by.get(gid) or {}).get("market_margin") is None
    ]
    if missing:
        raise EvalResultContractRefuse(
            "market incomplete for eligible cohort — refuse before claim "
            f"(missing {len(missing)} of {len(allow)})"
        )
