#!/usr/bin/env python3
"""Train-only regulation clock anchor for Q4 trail−3 FG precedence gating."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

TRAIN_SEASONS = frozenset(range(2013, 2024))


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-pbp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--precedence-max-quantile",
        type=float,
        default=0.75,
        help="Quantile of train equalizing-FG game clock for precedence max",
    )
    args = parser.parse_args()

    clocks: list[float] = []
    with args.historical_pbp.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            payload = row.get("payload") if row.get("object_type") == "pbp_play" else None
            if not isinstance(payload, Mapping):
                continue
            season = _number(payload.get("season"))
            if season is None or int(season) not in TRAIN_SEASONS:
                continue
            if payload.get("season_type") != "REG" or payload.get("qtr") != 4:
                continue
            ps = _number(payload.get("posteam_score"))
            ds = _number(payload.get("defteam_score"))
            seconds = _number(payload.get("game_seconds_remaining"))
            if ps is None or ds is None or seconds is None:
                continue
            if (
                payload.get("play_type") == "field_goal"
                and payload.get("field_goal_result") == "made"
                and int(ps - ds) == -3
            ):
                clocks.append(seconds)

    clocks.sort()
    n = len(clocks)
    if not n:
        raise SystemExit("no train equalizing field goals in sample")

    q = min(1.0, max(0.0, args.precedence_max_quantile))
    idx = min(n - 1, int(round(q * (n - 1))))
    payload = {
        "component": "q4_trail3_eq_fg_regulation_clock",
        "equalizing_fg_count": n,
        "mean_clock_seconds": sum(clocks) / n,
        "precedence_max_quantile": q,
        "q4_trail3_fg_range_precedence_max_clock_seconds": clocks[idx],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
