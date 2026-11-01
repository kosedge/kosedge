"""t5115u metric-specific EVAL/DEV cohort pins + identity resolution.

Does not score. Does not claim a one-run. Full freeze 892 is not an EVAL
accuracy cohort. Primary EVAL = 2022–23 REG only. DEV 2020–21 stays
separately labeled. CERT=0.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

from .q2 import T5107U_DEV_SEASONS, T5107U_EVAL_SEASONS


class MetricCohortRefuse(ValueError):
    """Fail-closed metric-cohort / identity pin."""

LABEL = "RESEARCH_CONSUMED_RETRO"
CERT_CANDIDATE = 0
EVAL_METRIC_SPLIT = "EVAL"
DEV_METRIC_SPLIT = "DEV"
# 2020 REG is 16 games × 16 weeks over weeks 1–17. Week 18 on games.csv
# 4fe1cdd7 is the Wild Card round (Jan 9–11 2021), not extra REG games.
WILDCARD_2020_W18 = (
    "2020_18_BAL_TEN",
    "2020_18_CHI_NO",
    "2020_18_CLE_PIT",
    "2020_18_IND_BUF",
    "2020_18_LA_SEA",
    "2020_18_TB_WAS",
)
# Declared REG universe = owned PBP REG counts (INPUT_BINDINGS n_reg_games).
DECLARED_REG_UNIVERSE = {2020: 256, 2021: 272, 2022: 271, 2023: 272}
PIN_WEEK_1_18 = {2020: 262, 2021: 272, 2022: 271, 2023: 272}


def cohort_sha256(game_ids: Sequence[str]) -> str:
    return hashlib.sha256(
        json.dumps({"game_ids": list(game_ids)}, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _season(row: Mapping[str, Any]) -> int:
    return int(row.get("season") or 0)


def split_forecasts(forecasts: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    eval_rows = [dict(r) for r in forecasts if _season(r) in T5107U_EVAL_SEASONS]
    dev_rows = [dict(r) for r in forecasts if _season(r) in T5107U_DEV_SEASONS]
    other = [
        dict(r)
        for r in forecasts
        if _season(r) not in T5107U_DEV_SEASONS + T5107U_EVAL_SEASONS
    ]
    if other:
        raise MetricCohortRefuse(
            f"forecast seasons outside DEV/EVAL window: {sorted({_season(r) for r in other})}"
        )
    return {"EVAL": eval_rows, "DEV": dev_rows}


def pin_metric_cohorts(forecasts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Bind EVAL=2022–23 and DEV=2020–21 from the freeze. Never default to all 892."""
    split = split_forecasts(forecasts)
    eval_ids = [str(r["game_id"]) for r in split["EVAL"]]
    dev_ids = [str(r["game_id"]) for r in split["DEV"]]
    if not eval_ids:
        raise MetricCohortRefuse("EVAL metric cohort empty — refuse")
    if len(eval_ids) != len(set(eval_ids)) or len(dev_ids) != len(set(dev_ids)):
        raise MetricCohortRefuse("duplicate game_id in metric cohort")
    wildcard = [gid for gid in dev_ids if gid in WILDCARD_2020_W18]
    eval_by_season = dict(Counter(_season(r) for r in split["EVAL"]))
    dev_by_season = dict(Counter(_season(r) for r in split["DEV"]))
    return {
        "schema_version": "nfl-t5115u-metric-cohorts-v1",
        "label": LABEL,
        "cert_candidate": CERT_CANDIDATE,
        "full_freeze_n": len(forecasts),
        "full_freeze_is_eval_accuracy_cohort": False,
        "eval": {
            "metric_split": EVAL_METRIC_SPLIT,
            "seasons": list(T5107U_EVAL_SEASONS),
            "season_type": "REG",
            "game_ids": eval_ids,
            "n": len(eval_ids),
            "n_by_season": eval_by_season,
            "cohort_sha256": cohort_sha256(eval_ids),
            "pooled_dev": False,
        },
        "dev": {
            "metric_split": DEV_METRIC_SPLIT,
            "seasons": list(T5107U_DEV_SEASONS),
            "game_ids": dev_ids,
            "n": len(dev_ids),
            "n_by_season": dev_by_season,
            "cohort_sha256": cohort_sha256(dev_ids),
            "n_2020_wildcard_w18_in_freeze": len(wildcard),
            "wildcard_2020_w18_game_ids": wildcard,
            "not_pooled_into_eval": True,
        },
        "notes": [
            "Primary EVAL accuracy = 2022–23 REG only.",
            "DEV 2020–21 retained separately; never pooled into EVAL metrics.",
            "2020 W18 Wild Card identities stay in the freeze DEV list, labeled, and are outside the declared 256 REG universe.",
        ],
    }


def refuse_pooled_or_default_eval(
    forecasts: Sequence[Mapping[str, Any]],
    eligible_cohorts: Mapping[str, Any] | None,
) -> None:
    """Fail-closed: mixed freeze cannot default to every frozen game."""
    seasons = {_season(r) for r in forecasts}
    has_dev = bool(seasons & set(T5107U_DEV_SEASONS))
    has_eval = bool(seasons & set(T5107U_EVAL_SEASONS))
    if has_dev and has_eval and eligible_cohorts is None:
        raise MetricCohortRefuse(
            "metric-specific eligible cohort required — refuse default to full freeze (DEV+EVAL)"
        )
    if eligible_cohorts is None:
        return
    allow = list((eligible_cohorts.get("margin_cohort") or {}).get("game_ids") or [])
    if not allow and eligible_cohorts.get("metric_split") == EVAL_METRIC_SPLIT:
        allow = list(eligible_cohorts.get("game_ids") or [])
    by_id = {str(r["game_id"]): r for r in forecasts}
    allow_seasons = {_season(by_id[gid]) for gid in allow if gid in by_id}
    if (allow_seasons & set(T5107U_DEV_SEASONS)) and (allow_seasons & set(T5107U_EVAL_SEASONS)):
        raise MetricCohortRefuse("refusing pooled DEV+EVAL accuracy cohort")
    if eligible_cohorts.get("metric_split") == EVAL_METRIC_SPLIT and (
        allow_seasons & set(T5107U_DEV_SEASONS)
    ):
        raise MetricCohortRefuse("EVAL metric cohort may not include DEV 2020–21 games")


def declared_reg_hold_table(
    *,
    recon_excluded_n: Mapping[int, int],
    recon_partial_n: Mapping[int, int],
) -> dict[str, Any]:
    """G5 30% HOLD on declared PBP REG universe (not the week≤18 pin filter)."""
    from .evaluator import PER_SEASON_EXCLUSION_HOLD, season_exclusion_hold

    seasons = []
    any_hold = False
    for season, declared in DECLARED_REG_UNIVERSE.items():
        excluded = int(recon_excluded_n.get(season, 0)) + int(recon_partial_n.get(season, 0))
        row = season_exclusion_hold(declared, excluded)
        row["season"] = season
        row["declared_source"] = "owned_pbp_reg"
        row["pin_week_1_18"] = PIN_WEEK_1_18[season]
        row["pin_minus_declared"] = PIN_WEEK_1_18[season] - declared
        seasons.append(row)
        any_hold = any_hold or bool(row["hold"])
    return {
        "hold_threshold": PER_SEASON_EXCLUSION_HOLD,
        "any_season_hold": any_hold,
        "seasons": seasons,
        "quote_eligibility": "REQUIRED_BEFORE_METRICS_NOT_APPLIED_t5115u",
        "notes": [
            "Declared n is owned PBP REG, not games.csv week≤18.",
            "2020 pin 262 − declared 256 = 6 Wild Card rows preserved, not extra REG games.",
            "Owned-quote eligibility must still run before metrics; HOLD is reapplied after that filter.",
        ],
    }
