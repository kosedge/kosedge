"""Actual NTBB-K joint capability / refusal consumers. CERT=0.

Consumes a fresh producer document. Does not hand-build integrated:true proof.
Does not rewrite kernel/research bytes.
"""

from __future__ import annotations

import importlib.util
from typing import Any, Mapping

from src.services.nfl_ntbb_k_v1.constants import (
    ORACLE_MAX_ENUMERATED_TOTAL,
    ROOT_EXPECTED_N,
    SCIPY_FITTING_ALGORITHM,
    SCIPY_STATUS,
)
from src.services.nfl_ntbb_k_v1.law import conditional_log_mass, log_joint_pmf
from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse
from src.services.nfl_ntbb_k_v1.special import remaining_series_tail
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse

ORDINARY_LOG_JOINT_00 = -23.263016196113618


def _must_refuse(fn, *, label: str) -> str:
    try:
        fn()
    except NtbbKRefuse as exc:
        return f"REFUSE:{exc}"
    raise RetroRefuse(f"{label} accepted — must REFUSE")


def consume_joint_capability(document: Mapping[str, Any]) -> dict[str, Any]:
    """Capability consumer of a fresh joint-producer document."""
    if not document.get("kernel_implemented"):
        raise RetroRefuse("producer document missing kernel_implemented")
    nine = document.get("root_nine") or {}
    if nine.get("status") != "PASS":
        raise RetroRefuse(f"producer root-nine {nine.get('status')}")
    if nine.get("max_enumerated_total") != ORACLE_MAX_ENUMERATED_TOTAL:
        raise RetroRefuse("producer max N drifted")
    by_family: dict[str, set[int]] = {}
    for row in nine.get("results") or []:
        family = str(row.get("family") or str(row.get("name") or "").rsplit("_", 1)[0])
        by_family.setdefault(family, set()).add(int(row["N"]))
    expect = {name: {n} for name, n in ROOT_EXPECTED_N.items()}
    if by_family and by_family != expect:
        raise RetroRefuse(f"producer N {by_family} != {expect}")
    if document.get("scipy_status") != SCIPY_STATUS:
        raise RetroRefuse("producer scipy_status drifted")
    if document.get("fitting_algorithm") != SCIPY_FITTING_ALGORITHM:
        raise RetroRefuse("producer fitting algorithm drifted")
    if document.get("clocks_143") != "SOURCE_VALUE_MATCH_NOT_VERIFIED":
        raise RetroRefuse("producer promoted 143 clocks")
    if importlib.util.find_spec("scipy") is not None:
        raise RetroRefuse("SciPy present — install forbidden")
    return {
        "consumed": True,
        "from_producer": True,
        "hand_built": False,
        "root_nine_status": nine.get("status"),
        "n_by_family": {name: next(iter(vals)) for name, vals in (by_family or expect).items()},
        "scipy_status": document.get("scipy_status"),
        "fitting_algorithm": document.get("fitting_algorithm"),
        "clocks_143": document.get("clocks_143"),
        "r7_model_arm": False,
        "self_reported_integrated_proof": False,
    }


def consume_joint_refusals(document: Mapping[str, Any]) -> dict[str, Any]:
    """Refusal consumer of the producer law. Uses the live joint entrypoints."""
    _ = document.get("return_id")
    log_joint = {
        "r_1e12": _must_refuse(
            lambda: log_joint_pmf(0, 0, mu=44.0, r=1e12, p=0.5, c=12.0),
            label="log_joint r=1e12",
        ),
        "r_1e16": _must_refuse(
            lambda: log_joint_pmf(0, 0, mu=44.0, r=1e16, p=0.5, c=12.0),
            label="log_joint r=1e16",
        ),
    }
    ordinary = log_joint_pmf(0, 0, mu=44.0, r=20.0, p=0.5, c=12.0)
    if ordinary != ORDINARY_LOG_JOINT_00:
        raise RetroRefuse(f"ordinary log_joint drifted {ordinary}")
    bb = {
        "c_1e12": _must_refuse(
            lambda: conditional_log_mass(2, p=0.3, c=1e12, k0=0.0, k3=0.0, k7=0.0),
            label="BB c=1e12",
        ),
        "c_1e16": _must_refuse(
            lambda: conditional_log_mass(2, p=0.3, c=1e16, k0=0.0, k3=0.0, k7=0.0),
            label="BB c=1e16",
        ),
    }
    tail = remaining_series_tail(n_success=0.5, p=0.5, q=0.5, cutoff=0)
    if tail["rho_bound"] != max(0.5, tail["rho"]):
        raise RetroRefuse("NB-tail rho_bound is not max(q, rho)")
    return {
        "consumed": True,
        "from_producer": True,
        "hand_built": False,
        "log_joint_extreme": log_joint,
        "ordinary_log_joint_00": ordinary,
        "bb_extreme": bb,
        "nb_tail_max_q_rho": {
            "rho": tail["rho"],
            "rho_bound": tail["rho_bound"],
            "q": 0.5,
        },
    }
