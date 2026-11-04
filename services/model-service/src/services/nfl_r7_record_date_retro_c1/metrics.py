"""DESIGN 25194 point-error metrics. CERT=0. Declared constants ≠ calculations."""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse

PRED_KEYS = ("if_margin", "q2_margin", "c_margin")


def _mean(xs: Sequence[float]) -> float:
    if not xs:
        raise RetroRefuse("metric mean empty")
    return sum(xs) / float(len(xs))


def mae_rmse_bias(errors: Sequence[float]) -> dict[str, Any]:
    if not errors:
        return {"n": 0, "mae": None, "rmse": None, "bias": None, "failures": 0}
    abs_e = [abs(x) for x in errors]
    return {
        "n": len(errors),
        "mae": _mean(abs_e),
        "rmse": math.sqrt(_mean([x * x for x in errors])),
        "bias": _mean(list(errors)),
        "failures": 0,
    }


def paired_abs_loss_diff(
    rows: Sequence[Mapping[str, Any]],
    *,
    left: str,
    right: str,
    y: str = "y_margin",
) -> dict[str, Any]:
    """mean(|left-y| - |right-y|). Primary when left=C and right=archived R5 C."""
    diffs: list[float] = []
    failures = 0
    for row in rows:
        if left not in row or right not in row or y not in row:
            failures += 1
            continue
        diffs.append(abs(float(row[left]) - float(row[y])) - abs(float(row[right]) - float(row[y])))
    if not diffs:
        return {"n": 0, "mean": None, "failures": failures}
    return {"n": len(diffs), "mean": _mean(diffs), "failures": failures}


def _subset(rows: Sequence[Mapping[str, Any]], ids: Iterable[str]) -> list[Mapping[str, Any]]:
    want = set(ids)
    return [row for row in rows if str(row["game_id"]) in want]


def _arm_block(rows: Sequence[Mapping[str, Any]], pred: str) -> dict[str, Any]:
    errors = [float(row[pred]) - float(row["y_margin"]) for row in rows]
    return mae_rmse_bias(errors)


def design_25194_metrics(
    scored: Sequence[Mapping[str, Any]],
    *,
    archive: Mapping[str, Any],
) -> dict[str, Any]:
    if not scored:
        raise RetroRefuse("metrics have no scored rows")
    enriched: list[dict[str, Any]] = []
    r5 = dict(archive.get("r5_c") or {})
    market = dict(archive.get("market_point") or {})
    for row in scored:
        item = dict(row)
        gid = str(item["game_id"])
        if gid in r5:
            item["r5_c"] = float(r5[gid])
        if gid in market:
            item["market_point"] = float(market[gid])
        enriched.append(item)

    slices = dict(archive.get("slices") or {"full": [r["game_id"] for r in scored]})
    full = _subset(enriched, slices.get("full") or [r["game_id"] for r in enriched])

    if_q2_c: dict[str, Any] = {}
    per_season: dict[str, Any] = {}
    by_season: dict[int, list[dict[str, Any]]] = {}
    for row in full:
        by_season.setdefault(int(row["season"]), []).append(row)
    for pred in PRED_KEYS:
        if_q2_c[pred] = _arm_block(full, pred)
    for season, rows in sorted(by_season.items()):
        per_season[str(season)] = {pred: _arm_block(rows, pred) for pred in PRED_KEYS}

    paired: dict[str, Any] = {}
    for name, ids in slices.items():
        part = _subset(enriched, ids)
        paired[str(name)] = {
            "c_minus_if": paired_abs_loss_diff(part, left="c_margin", right="if_margin"),
            "c_minus_r5": paired_abs_loss_diff(part, left="c_margin", right="r5_c"),
        }
    same96 = _subset(enriched, slices.get("same96") or [])
    market96 = paired_abs_loss_diff(same96, left="c_margin", right="market_point")

    primary = paired_abs_loss_diff(full, left="c_margin", right="r5_c")
    return {
        "primary": {
            "name": "mean_abs_R7C_minus_abs_R5C",
            "spec": "DESIGN_25194",
            **primary,
        },
        "if_q2_c": if_q2_c,
        "per_season": per_season,
        "paired_abs_loss": paired,
        "c_minus_market_same96": market96,
        "counts": {name: len(_subset(enriched, ids)) for name, ids in slices.items()},
        "failures": {name: (paired[str(name)]["c_minus_r5"]["failures"] if str(name) in paired else 0) for name in slices},
        "scientific_claim": False,
        "declared_not_calculated": False,
    }


def paired_abs_loss_rows(
    scored: Sequence[Mapping[str, Any]],
    *,
    archive: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Per-game primary residuals for bootstrap. |C-y| - |R5-y|."""
    r5 = dict(archive.get("r5_c") or {})
    out: list[dict[str, Any]] = []
    for row in scored:
        gid = str(row["game_id"])
        if gid not in r5:
            continue
        y = float(row["y_margin"])
        stat = abs(float(row["c_margin"]) - y) - abs(float(r5[gid]) - y)
        out.append(
            {
                "game_id": gid,
                "season": int(row["season"]),
                "week": int(row["week"]),
                "paired_abs_loss": stat,
                "signed_c_minus_y": float(row["c_margin"]) - y,
            }
        )
    if not out:
        raise RetroRefuse("paired abs-loss rows empty")
    return out
