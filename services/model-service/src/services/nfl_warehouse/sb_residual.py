"""Super Bowl outright residual vs season-engine playoff/title rates.

Light-touch: compare owned historical SB winner prices to model title
probability. Do not train a new futures model unless mean abs residual
exceeds ``RESIDUAL_TRAIN_THRESHOLD``.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

RESIDUAL_TRAIN_THRESHOLD = 0.08


def _american_to_implied(price: float) -> float:
    p = float(price)
    if p > 0:
        return 100.0 / (p + 100.0)
    return abs(p) / (abs(p) + 100.0)


def sb_residuals(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Each row: team, market_price (American), model_title_prob (0-1)."""
    residuals = []
    for row in rows:
        try:
            market = _american_to_implied(float(row["market_price"]))
            model = float(row["model_title_prob"])
        except (KeyError, TypeError, ValueError):
            continue
        residuals.append(
            {
                "team": row.get("team"),
                "market_prob": market,
                "model_prob": model,
                "residual": model - market,
            }
        )
    if not residuals:
        return {
            "n": 0,
            "mae": None,
            "train_new_futures_model": False,
            "reason": "no_comparable_rows",
        }
    vig_sum = sum(float(r["market_prob"]) for r in residuals)
    if vig_sum > 0:
        for row in residuals:
            row["market_prob_devig"] = float(row["market_prob"]) / vig_sum
            row["residual_devig"] = float(row["model_prob"]) - float(row["market_prob_devig"])
    mae = sum(abs(r["residual"]) for r in residuals) / len(residuals)
    mae_devig = (
        sum(abs(r["residual_devig"]) for r in residuals) / len(residuals)
        if residuals and "residual_devig" in residuals[0]
        else None
    )
    return {
        "n": len(residuals),
        "mae": round(mae, 4),
        "mae_devig": None if mae_devig is None else round(mae_devig, 4),
        "mean_residual": round(sum(r["residual"] for r in residuals) / len(residuals), 4),
        "train_new_futures_model": (mae_devig if mae_devig is not None else mae) >= RESIDUAL_TRAIN_THRESHOLD,
        "threshold": RESIDUAL_TRAIN_THRESHOLD,
        "rows": residuals,
        "note": "Season engine stays primary. Train a futures model only if mae >= threshold.",
    }
