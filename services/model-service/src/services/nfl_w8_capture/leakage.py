"""RA-1 leak locks for the frozen W8 model.

Anything UNVERIFIABLE is FAIL. Evidence is this package's source plus
per-feature as-of proofs — not week-number matching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from src.services.nfl_w8_capture.frozen_model import (
    W8_HOME_FIELD_POINTS,
    W8_MARKET_BLEND_WEIGHT,
    W8_PRIOR_TOTAL_POINTS,
)
from src.services.nfl_w8_capture.streams import validate_input_proof


LK2 = "LK-2"
LK7 = "LK-7"
LK8 = "LK-8"
LK9 = "LK-9"
LK10 = "LK-10"
LK1 = "LK-1"
LK4 = "LK-4"

CONTAMINATED_HFA = 1.05
CONTAMINATED_PRIOR_TOTAL = 45.3
CONTAMINATED_BLEND = 0.30


def _read(name: str) -> str:
    return (Path(__file__).resolve().parent / name).read_text(encoding="utf-8")


def verify_code_locks() -> list[dict[str, Any]]:
    """Inspect frozen W8 code. UNVERIFIABLE / contaminated constants → FAIL."""
    failures: list[dict[str, Any]] = []
    src = _read("frozen_model.py")
    if W8_HOME_FIELD_POINTS == CONTAMINATED_HFA:
        failures.append({"lk": LK8, "reason": "hfa_is_2023_25_tuned_1_05"})
    if W8_PRIOR_TOTAL_POINTS == CONTAMINATED_PRIOR_TOTAL:
        failures.append({"lk": LK8, "reason": "prior_total_is_2023_25_tuned_45_3"})
    if W8_MARKET_BLEND_WEIGHT != 0.0 or W8_MARKET_BLEND_WEIGHT == CONTAMINATED_BLEND:
        failures.append({"lk": LK1, "reason": "blend_weight_not_resolved"})
    if "holdout_fraction" in src or "0.16" in src:
        failures.append({"lk": LK7, "reason": "sixteen_percent_cut_present"})
    if "simulate_nfl_game" in src or "nfl_simulator" in src:
        failures.append({"lk": LK1, "reason": "production_sim_blend_imported"})
    if "CURRENT ROW" in src or "h.week = s.week" in src:
        failures.append({"lk": LK2, "reason": "same_week_epa_join_present"})
    if "prefer_packaged_epa" in src and "FORBIDDEN" not in src:
        failures.append({"lk": LK10, "reason": "season_epa_not_locked"})
    if "fit_nfl_supervised" in src:
        failures.append({"lk": LK7, "reason": "supervised_16pct_fit_present"})
    return failures


def verify_proofs(
    proofs: Iterable[Mapping[str, Any]],
    *,
    required_inputs: Sequence[str],
    min_lead_minutes: int,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for proof in proofs:
        reason = validate_input_proof(proof, min_lead_minutes=min_lead_minutes)
        gid = str(proof.get("game_id") or "")
        name = str(proof.get("input_name") or "")
        if reason:
            failures.append(
                {
                    "game_id": gid,
                    "input_name": name,
                    "reason": reason,
                    "unverifiable": True,
                    "stays_in_n": True,
                }
            )
            continue
        seen.add((gid, name))
    games = {str(p.get("game_id") or "") for p in proofs if p.get("game_id")}
    for gid in games:
        for name in required_inputs:
            if (gid, name) not in seen:
                failures.append(
                    {
                        "game_id": gid,
                        "input_name": name,
                        "reason": "unverifiable_missing_asof_proof",
                        "unverifiable": True,
                        "stays_in_n": True,
                    }
                )
    return failures


def ra1_status(
    *,
    proofs: Sequence[Mapping[str, Any]],
    required_inputs: Sequence[str],
    min_lead_minutes: int,
) -> dict[str, Any]:
    failures = verify_code_locks() + verify_proofs(
        proofs, required_inputs=required_inputs, min_lead_minutes=min_lead_minutes
    )
    return {
        "check": "RA-1",
        "status": "FAIL" if failures else "PASS",
        "failures": failures,
        "locks": {
            LK2: "feature_week < game_week; per-feature as-of required",
            LK7: "no 16% chronological cut / no supervised overlay",
            LK8: "HFA and prior total are not the 2023-25 tuned pair",
            LK9: "rest and injury must be observed",
            LK10: "2026 season-level EPA inputs forbidden",
            LK1: "blend weight 0.0 on both streams",
            LK4: "independent stream forbids close/market features",
        },
    }
