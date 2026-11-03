"""Task-bound arithmetic oracle. Fiction pairs only. Not a fitted predictor.

Computes ML / margin / total / spread / total partitions from ONE joint law.
Ties are a third mass. Ties are never away wins.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence, Tuple

from src.services.nfl_joint_contract_v1.constants import (
    EXPECTED_MEANS,
    EXPECTED_ML,
    EXPECTED_SPREAD,
    EXPECTED_TOTAL,
    ORACLE_HOME_SPREAD,
    ORACLE_PAIRS,
    ORACLE_TOTAL,
    ORACLE_WEIGHTS,
)
from src.services.nfl_joint_contract_v1.refuse import JointContractRefuse, RefuseClass

Pair = Tuple[int, int]


def _finite_number(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JointContractRefuse(
            f"{name} is not numeric",
            refuse_class=RefuseClass.NONFINITE,
        )
    number = float(value)
    if math.isnan(number) or not math.isfinite(number):
        raise JointContractRefuse(
            f"{name} must be finite",
            refuse_class=RefuseClass.NONFINITE,
        )
    if nonnegative and number < 0:
        raise JointContractRefuse(
            f"{name} must be finite nonnegative",
            refuse_class=RefuseClass.NONFINITE,
        )
    return number


def _finite_weight(value: Any, name: str) -> float:
    return _finite_number(value, name, nonnegative=True)


def _finite_prob(value: Any, name: str) -> float:
    number = _finite_number(value, name, nonnegative=True)
    if number > 1.0 + 1e-12:
        raise JointContractRefuse(
            f"{name}={number} is not a probability in [0,1]",
            refuse_class=RefuseClass.PARTITION,
        )
    return number


def parse_weights(weights: Sequence[Any]) -> tuple[float, ...]:
    """Exact 98426: finite nonnegative; abs(sum−1)≤1e-12; never renormalize."""
    parsed = tuple(_finite_weight(w, f"weight[{i}]") for i, w in enumerate(weights))
    total = sum(parsed)
    if abs(total - 1.0) > 1e-12:
        raise JointContractRefuse(
            f"weights sum {total} ; abs(sum-1) must be <= 1e-12 (no renormalization)",
            refuse_class=RefuseClass.PARTITION,
        )
    return parsed


def normalize_weights(weights: Sequence[Any]) -> tuple[float, ...]:
    """Compatibility alias. Does not renormalize. Preserves supplied weights."""
    return parse_weights(weights)


def _int_score(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise JointContractRefuse(
            f"{name} must be a nonnegative int",
            refuse_class=RefuseClass.TYPE,
        )
    if value < 0:
        raise JointContractRefuse(
            f"{name} must be nonnegative",
            refuse_class=RefuseClass.TYPE,
        )
    return value


def normalize_weights(weights: Sequence[Any]) -> tuple[float, ...]:
    parsed = tuple(_finite_weight(w, f"weight[{i}]") for i, w in enumerate(weights))
    total = sum(parsed)
    if total <= 0:
        raise JointContractRefuse("weights sum must be > 0", refuse_class=RefuseClass.PARTITION)
    return tuple(w / total for w in parsed)


def law_from_pairs(
    pairs: Sequence[Sequence[Any]] | None = None,
    weights: Sequence[Any] | None = None,
) -> dict[str, Any]:
    raw_pairs = ORACLE_PAIRS if pairs is None else pairs
    raw_weights = ORACLE_WEIGHTS if weights is None else weights
    if len(raw_pairs) != len(raw_weights):
        raise JointContractRefuse(
            "pairs/weights length mismatch",
            refuse_class=RefuseClass.PARTITION,
        )
    outcomes: list[dict[str, Any]] = []
    preserved = parse_weights(raw_weights)
    for idx, row in enumerate(raw_pairs):
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise JointContractRefuse(
                f"outcome[{idx}] must be a paired (H,A)",
                refuse_class=RefuseClass.TYPE,
            )
        home = _int_score(row[0], f"outcome[{idx}].H")
        away = _int_score(row[1], f"outcome[{idx}].A")
        outcomes.append(
            {
                "home": home,
                "away": away,
                "weight": preserved[idx],
                "margin": home - away,
                "total": home + away,
            }
        )
    return {
        "outcomes": outcomes,
        "n": len(outcomes),
        "weight_sum": sum(preserved),
        "weights": list(preserved),
        "pairs": [(row["home"], row["away"]) for row in outcomes],
    }


def _mass(outcomes: Iterable[dict[str, Any]], pred) -> float:
    return sum(float(row["weight"]) for row in outcomes if pred(row))


def partitions_from_law(
    *,
    pairs: Sequence[Sequence[Any]] | None = None,
    weights: Sequence[Any] | None = None,
    home_spread: float = ORACLE_HOME_SPREAD,
    total_line: float = ORACLE_TOTAL,
) -> dict[str, Any]:
    spread_line = _finite_number(home_spread, "home_spread")
    total_line_v = _finite_number(total_line, "total_line")
    law = law_from_pairs(pairs, weights)
    outcomes = law["outcomes"]
    ml = {
        "home_win": _mass(outcomes, lambda r: r["home"] > r["away"]),
        "away_win": _mass(outcomes, lambda r: r["away"] > r["home"]),
        "tie": _mass(outcomes, lambda r: r["home"] == r["away"]),
    }
    if abs((ml["home_win"] + ml["away_win"] + ml["tie"]) - 1.0) > 1e-12:
        raise JointContractRefuse("ML partition does not sum to 1", refuse_class=RefuseClass.PARTITION)
    # Ties are a third mass — never fold into away_win.
    if ml["tie"] <= 0 and any(r["home"] == r["away"] for r in outcomes):
        raise JointContractRefuse("tie mass dropped", refuse_class=RefuseClass.PARTITION)

    mean_margin = sum(r["weight"] * r["margin"] for r in outcomes)
    mean_total = sum(r["weight"] * r["total"] for r in outcomes)

    spread = {
        "line": spread_line,
        "cover": _mass(outcomes, lambda r: (r["margin"] + spread_line) > 0),
        "push": _mass(outcomes, lambda r: (r["margin"] + spread_line) == 0),
        "loss": _mass(outcomes, lambda r: (r["margin"] + spread_line) < 0),
    }
    if abs((spread["cover"] + spread["push"] + spread["loss"]) - 1.0) > 1e-12:
        raise JointContractRefuse(
            "spread partition does not sum to 1",
            refuse_class=RefuseClass.PARTITION,
        )

    totals = {
        "line": total_line_v,
        "over": _mass(outcomes, lambda r: r["total"] > total_line_v),
        "push": _mass(outcomes, lambda r: r["total"] == total_line_v),
        "under": _mass(outcomes, lambda r: r["total"] < total_line_v),
    }
    if abs((totals["over"] + totals["push"] + totals["under"]) - 1.0) > 1e-12:
        raise JointContractRefuse(
            "total partition does not sum to 1",
            refuse_class=RefuseClass.PARTITION,
        )

    return {
        "ml": ml,
        "means": {"margin": mean_margin, "total": mean_total},
        "spread": spread,
        "total": totals,
        "n": law["n"],
        "weight_sum": law["weight_sum"],
        "outcomes": law["outcomes"],
    }


def frozen_oracle_body() -> dict[str, Any]:
    computed = partitions_from_law()
    return {
        "contract_id": "NFL_JOINT_CONTRACT_V1",
        "contract_hash": "4f2c9e2b",
        "kind": "SYNTHETIC_LITERAL_LAW_ORACLE",
        "fitted": False,
        "historical": False,
        "pairs": [list(p) for p in ORACLE_PAIRS],
        "weights": list(ORACLE_WEIGHTS),
        "home_spread": ORACLE_HOME_SPREAD,
        "total_line": ORACLE_TOTAL,
        "expected": {
            "ml": dict(EXPECTED_ML),
            "means": dict(EXPECTED_MEANS),
            "spread": dict(EXPECTED_SPREAD),
            "total": dict(EXPECTED_TOTAL),
        },
        "computed": {
            "ml": computed["ml"],
            "means": computed["means"],
            "spread": {
                "cover": computed["spread"]["cover"],
                "push": computed["spread"]["push"],
                "loss": computed["spread"]["loss"],
            },
            "total": {
                "over": computed["total"]["over"],
                "push": computed["total"]["push"],
                "under": computed["total"]["under"],
            },
        },
        "notes": [
            "Hand-authored fiction. NOT fitted parameters. NOT historical observations.",
            "All spread/total/ML derive from this same joint law.",
            "Tie mass preserved. Ties are not away wins.",
        ],
    }


def assert_computed_matches_expected(computed: dict[str, Any] | None = None) -> None:
    got = computed if computed is not None else partitions_from_law()
    checks = (
        (got["ml"]["home_win"], EXPECTED_ML["home_win"], "ml.home_win"),
        (got["ml"]["away_win"], EXPECTED_ML["away_win"], "ml.away_win"),
        (got["ml"]["tie"], EXPECTED_ML["tie"], "ml.tie"),
        (got["means"]["margin"], EXPECTED_MEANS["margin"], "mean.margin"),
        (got["means"]["total"], EXPECTED_MEANS["total"], "mean.total"),
        (got["spread"]["cover"], EXPECTED_SPREAD["cover"], "spread.cover"),
        (got["spread"]["push"], EXPECTED_SPREAD["push"], "spread.push"),
        (got["spread"]["loss"], EXPECTED_SPREAD["loss"], "spread.loss"),
        (got["total"]["over"], EXPECTED_TOTAL["over"], "total.over"),
        (got["total"]["push"], EXPECTED_TOTAL["push"], "total.push"),
        (got["total"]["under"], EXPECTED_TOTAL["under"], "total.under"),
    )
    for value, expected, name in checks:
        if abs(float(value) - float(expected)) > 1e-12:
            raise JointContractRefuse(
                f"{name} computed {value} != frozen expected {expected}",
                refuse_class=RefuseClass.PARTITION,
            )
