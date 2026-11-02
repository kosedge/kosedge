"""b41f4b43 contract constants + cell compare from companion rebuild_w7w17.py.

Sourced from #686 @ 43b5a62233 research/q2s_w7w17_t5044u/gate2/rebuild_w7w17.py.
Tolerances are not loosened. Used for schema / approved-input parity only —
this module does not rescore closed 2017 outcomes.
"""

from __future__ import annotations

import math
from typing import Any

CONTRACT_SHA256 = "b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4"
STAGE_B_FULL_SHA256 = "cd9af2858e21fac5247a489051f0cc61b9490cb97ffdec9ac41a31a2d224d810"
STAGE_B_W7W8_SLICE_SHA256 = (
    "3ab291d66a5b5da88daa073413635196e7361ffc9e1e2eafb35c652bedc7c441"
)
TOL_INDEX = 1e-6
TOL_EPA = 1e-9
TOL_REST = 1e-9

CONTRACT_27 = (
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
    "rest_days_home",
    "rest_days_away",
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "home_pass_rate_5g",
    "away_pass_rate_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_def_epa_allowed_5g",
    "matchup_diff_success_rate_5g",
    "matchup_diff_pressure_allowed_5g",
    "matchup_diff_pressure_generated_5g",
    "matchup_diff_red_zone_td_rate_5g",
)
TEXT_FIELDS = {
    "game_id",
    "home_team",
    "away_team",
    "matchup_season",
    "matchup_week",
}
INDEX_FIELDS = {
    "offense_index_home",
    "offense_index_away",
    "defense_index_home",
    "defense_index_away",
}
EPA_FIELDS = {
    "home_off_epa_5g",
    "away_off_epa_5g",
    "home_def_epa_allowed_5g",
    "away_def_epa_allowed_5g",
    "home_success_offense_5g",
    "away_success_offense_5g",
    "home_success_defense_allowed_5g",
    "away_success_defense_allowed_5g",
    "matchup_diff_off_epa_5g",
    "matchup_diff_success_rate_5g",
}
REST_FIELDS = {"rest_days_home", "rest_days_away"}
EXACT_NUMERIC_FIELDS = (
    set(CONTRACT_27) - TEXT_FIELDS - INDEX_FIELDS - EPA_FIELDS - REST_FIELDS
)


def _as_float(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def compare_cell_maps(
    rebuilt: dict[tuple[str, str], dict[str, Any]],
    prior: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Full-field compare. All 27 contract fields are asserted.

    Contract-bound slack only:
      index |Δ| < 1e-6; listed 5g EPA/success |Δ| < 1e-9; rest_* |Δ| < 1e-9.
    Any other numeric difference (pass-rate, pressure, RZ,
    matchup_diff_def_epa_allowed_5g) is unauthorized and fails.
    Text identity fields must match exactly. Do not loosen.
    """
    fails: list[dict[str, Any]] = []
    counts = {
        "index": 0,
        "epa": 0,
        "rest": 0,
        "exact_numeric": 0,
        "text": 0,
        "missing_status": 0,
    }
    max_delta = {
        "index": 0.0,
        "epa": 0.0,
        "rest": 0.0,
        "exact_numeric": 0.0,
    }
    asserted: set[str] = set()

    if set(rebuilt) != set(prior):
        fails.append(
            {
                "reason": "keyset",
                "n_rebuilt": len(rebuilt),
                "n_prior": len(prior),
                "only_rebuilt": sorted(set(rebuilt) - set(prior))[:8],
                "only_prior": sorted(set(prior) - set(rebuilt))[:8],
            }
        )

    games = {gid for gid, _ in prior} | {gid for gid, _ in rebuilt}
    for gid in sorted(games):
        have = {field for g, field in rebuilt if g == gid}
        missing = [field for field in CONTRACT_27 if field not in have]
        extra = sorted(have - set(CONTRACT_27))
        if missing:
            fails.append({"reason": "missing_fields", "game_id": gid, "fields": missing})
        if extra:
            fails.append({"reason": "unknown_fields", "game_id": gid, "fields": extra})

    for key in sorted(set(rebuilt) & set(prior)):
        gid, field = key
        asserted.add(field)
        new = rebuilt[key]
        old = prior[key]
        if new.get("status") != old.get("status"):
            fails.append(
                {
                    "key": list(key),
                    "reason": "status",
                    "new": new.get("status"),
                    "old": old.get("status"),
                }
            )
            continue
        if new.get("status") == "MISSING_RECORD":
            counts["missing_status"] += 1
            continue
        if field not in CONTRACT_27:
            fails.append({"key": list(key), "reason": "unknown_field"})
            continue
        if field in TEXT_FIELDS:
            counts["text"] += 1
            if str(new.get("reconstructed_value", "")) != str(
                old.get("reconstructed_value", "")
            ):
                fails.append({"key": list(key), "reason": "text"})
            continue
        nv = _as_float(new.get("reconstructed_value"))
        ov = _as_float(old.get("reconstructed_value"))
        if nv is None or ov is None:
            if new.get("reconstructed_value") != old.get("reconstructed_value"):
                fails.append({"key": list(key), "reason": "value_text"})
            continue
        delta = abs(nv - ov)
        if field in INDEX_FIELDS:
            counts["index"] += 1
            max_delta["index"] = max(max_delta["index"], delta)
            if delta >= TOL_INDEX:
                fails.append({"key": list(key), "reason": "index", "delta": delta})
        elif field in EPA_FIELDS:
            counts["epa"] += 1
            max_delta["epa"] = max(max_delta["epa"], delta)
            if delta >= TOL_EPA:
                fails.append({"key": list(key), "reason": "epa", "delta": delta})
        elif field in REST_FIELDS:
            counts["rest"] += 1
            max_delta["rest"] = max(max_delta["rest"], delta)
            if delta >= TOL_REST:
                fails.append({"key": list(key), "reason": "rest", "delta": delta})
        elif field in EXACT_NUMERIC_FIELDS:
            counts["exact_numeric"] += 1
            max_delta["exact_numeric"] = max(max_delta["exact_numeric"], delta)
            if delta != 0.0 or str(new.get("reconstructed_value")) != str(
                old.get("reconstructed_value")
            ):
                fails.append(
                    {
                        "key": list(key),
                        "reason": "exact_numeric",
                        "field": field,
                        "delta": delta,
                    }
                )
        else:
            fails.append({"key": list(key), "reason": "unclassified_field"})

    unasserted = [field for field in CONTRACT_27 if field not in asserted]
    if unasserted and not any(f.get("reason") == "keyset" for f in fails):
        fails.append({"reason": "fields_not_compared", "fields": unasserted})

    return {
        "n_cells": len(rebuilt),
        "n_index_compared": counts["index"],
        "n_epa_compared": counts["epa"],
        "n_rest_compared": counts["rest"],
        "n_exact_numeric_compared": counts["exact_numeric"],
        "n_text_compared": counts["text"],
        "max_abs_delta_index": max_delta["index"],
        "max_abs_delta_epa_success": max_delta["epa"],
        "max_abs_delta_rest": max_delta["rest"],
        "max_abs_delta_exact_numeric": max_delta["exact_numeric"],
        "asserted_fields": list(CONTRACT_27),
        "exact_numeric_fields": sorted(EXACT_NUMERIC_FIELDS),
        "n_fails": len(fails),
        "fails": fails,
        "pass": not fails,
        "tolerances": {
            "index": TOL_INDEX,
            "epa_success": TOL_EPA,
            "rest": TOL_REST,
            "pass_rate_pressure_rz_def_epa_diff": 0.0,
        },
    }


def _finite(value: object) -> bool:
    return value is not None and isinstance(value, (int, float)) and math.isfinite(
        float(value)
    )
