"""A producer→capability/gate for isolated NTBB-K. CERT=0.

Cos ACCEPT B tip 12c41587 (RETURN 58427 + ADDITIVE 80649).
Verifies the checked-out kernel; does not call produce_kernel (no rewrite).
Not an R7 model arm. Not a package close from B alone. Clocks not promoted.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from src.services.nfl_ntbb_k_v1.cases import run_root_nine
from src.services.nfl_ntbb_k_v1.constants import (
    ADDITIVE_ID,
    ORACLE_MAX_ENUMERATED_TOTAL,
    PROFILE,
    RETURN_ID,
    ROOT_EXPECTED_N,
    SCIPY_FITTING_ALGORITHM,
    SCIPY_STATUS,
    UNDER_RETURN_ID,
)
from src.services.nfl_ntbb_k_v1.law import conditional_log_mass, log_joint_pmf
from src.services.nfl_ntbb_k_v1.produce import (
    verify_clarifications_blob,
    verify_market_partial_preserved,
    verify_spec_blob,
)
from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse
from src.services.nfl_ntbb_k_v1.special import remaining_series_tail
from src.services.nfl_ops_v1_evidence.profiles import (
    PROFILE_NTBB_K_SYNTHETIC,
    get_profile,
)
from src.services.nfl_r7_correctness_v1.followthrough_preflight import (
    ADDITIVE_NTBBK,
    B_NTBBK_KERNEL_SHA256,
    B_NTBBK_TIP_INTEGRATED,
    B_NTBBK_TIP_REFUSED,
    B_NTBBK_TIP_SUPERSEDED,
    RETURN_NTBBK,
    RETURN_UNFREEZE,
)
from src.services.nfl_r7_correctness_v1.produce import repo_root
from src.services.nfl_r7_record_date_retro_c1.grant import (
    ROOT_APPROVED_AUTH_DIGEST,
    refuse_real_without_root_grant,
)
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroHold, RetroRefuse
from src.services.nfl_t5208u.hashing import sha256_file

KERNEL_REL = "data/ops/nfl_ntbb_k_v1/KERNEL_SYNTHETIC_92861.json"
CSV44_REL = "data/ops/nfl_owned_market_v1/codex_staged/CSV_SELECTED_44_RAW_VALUE_PROJECTION.json"
ORDINARY_LOG_JOINT_00 = -23.263016196113618


def _must_refuse(fn, *, label: str) -> str:
    try:
        fn()
    except NtbbKRefuse as exc:
        return f"REFUSE:{exc}"
    raise RetroRefuse(f"{label} accepted — must REFUSE")


def _producer_root_nine() -> dict[str, Any]:
    nine = run_root_nine()
    if nine["status"] != "PASS":
        raise RetroRefuse(f"root-nine status {nine['status']}")
    if nine["n_cases"] != 9:
        raise RetroRefuse("root-nine n_cases != 9")
    if nine["max_enumerated_total"] != ORACLE_MAX_ENUMERATED_TOTAL:
        raise RetroRefuse("root-nine max N drifted")
    by_family: dict[str, set[int]] = {}
    for row in nine["results"]:
        if row["status"] != "PASS" or row["N"] != row["expected_N"]:
            raise RetroRefuse(f"root-nine row failed {row.get('name')}")
        by_family.setdefault(row["family"], set()).add(row["N"])
    expect = {name: {n} for name, n in ROOT_EXPECTED_N.items()}
    if by_family != expect:
        raise RetroRefuse(f"root-nine N {by_family} != {expect}")
    return {
        "status": nine["status"],
        "n_cases": nine["n_cases"],
        "max_enumerated_total": nine["max_enumerated_total"],
        "n_by_family": {name: next(iter(vals)) for name, vals in by_family.items()},
        "fixture_kind": nine["fixture_kind"],
        "rewrote_kernel": False,
    }


def _refusal_consumer() -> dict[str, Any]:
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
        "log_joint_extreme": log_joint,
        "ordinary_log_joint_00": ordinary,
        "bb_extreme": bb,
        "nb_tail_max_q_rho": {
            "rho": tail["rho"],
            "rho_bound": tail["rho_bound"],
            "q": 0.5,
        },
    }


def _capability(*, root: Path) -> dict[str, Any]:
    if importlib.util.find_spec("scipy") is not None:
        raise RetroRefuse("SciPy present — install forbidden")
    if ROOT_APPROVED_AUTH_DIGEST is not None:
        raise RetroRefuse("ROOT_APPROVED_AUTH_DIGEST must stay None")
    try:
        refuse_real_without_root_grant()
    except RetroHold:
        real_denied = True
    else:
        raise RetroRefuse("REAL must deny without Root auth digest")
    if (root / CSV44_REL).exists():
        raise RetroRefuse("CSV_SELECTED_44 present — clocks/market not promoted")
    market = verify_market_partial_preserved(root)
    if market["clock_semantics_verified_any"]:
        raise RetroRefuse("143 clocks must remain SOURCE_VALUE_MATCH ≠ verified")
    if market["clocks_status"] != "SOURCE_VALUE_MATCH_NOT_VERIFIED":
        raise RetroRefuse("143 clocks status drifted")
    profile = get_profile(PROFILE_NTBB_K_SYNTHETIC)
    if profile.b_tip != B_NTBBK_TIP_INTEGRATED:
        raise RetroRefuse(f"profile b_tip {profile.b_tip} != {B_NTBBK_TIP_INTEGRATED}")
    if profile.status == "ACTIVE":
        raise RetroRefuse("NTBB-K must not be an ACTIVE R7 model arm")
    return {
        "scipy_status": SCIPY_STATUS,
        "fitting_algorithm": SCIPY_FITTING_ALGORITHM,
        "scipy_present": False,
        "real_denied": real_denied,
        "root_approved_auth_digest": ROOT_APPROVED_AUTH_DIGEST,
        "b_clocks_promoted": False,
        "csv44_present": False,
        "clocks_143": market["clocks_status"],
        "profile_id": profile.profile_id,
        "profile_status": profile.status,
        "profile_b_tip": profile.b_tip,
        "r7_model_arm": False,
    }


def run_ntbbk_integrate_gate(*, root: Path | None = None) -> dict[str, Any]:
    """Producer (verify + root-nine) → capability → shared-gate bind. No kernel rewrite."""
    repo = repo_root() if root is None else Path(root)
    if B_NTBBK_TIP_INTEGRATED == B_NTBBK_TIP_REFUSED:
        raise RetroRefuse("integrated and refused tips must differ")
    if B_NTBBK_TIP_INTEGRATED == B_NTBBK_TIP_SUPERSEDED:
        raise RetroRefuse("12c41587 must not equal superseded a807af22")
    if B_NTBBK_TIP_SUPERSEDED == B_NTBBK_TIP_REFUSED:
        raise RetroRefuse("superseded and refused tips must differ")
    spec = verify_spec_blob(repo)
    clar = verify_clarifications_blob(repo)
    kernel = repo / KERNEL_REL
    if not kernel.is_file():
        raise RetroRefuse(f"missing kernel {KERNEL_REL}")
    before = sha256_file(kernel)
    if before != B_NTBBK_KERNEL_SHA256:
        raise RetroRefuse(f"kernel sha {before} != pin {B_NTBBK_KERNEL_SHA256}")
    producer = _producer_root_nine()
    refusals = _refusal_consumer()
    capability = _capability(root=repo)
    after = sha256_file(kernel)
    if after != before:
        raise RetroRefuse("gate rewrote the kernel — forbidden")
    return {
        "ok": True,
        "cert": 0,
        "profile": PROFILE,
        "integrated": True,
        "integrated_once": True,
        "integrated_tip": B_NTBBK_TIP_INTEGRATED,
        "frozen_tip": B_NTBBK_TIP_INTEGRATED,
        "frozen_as_final": False,
        "superseded_tip": B_NTBBK_TIP_SUPERSEDED,
        "refused_tip": B_NTBBK_TIP_REFUSED,
        "held_tip": None,
        "kernel_sha256": after,
        "kernel_sha256_locked": True,
        "kernel_role": "INTEGRATED_FROM_12C41587",
        "kernel_rewritten": False,
        "produce_kernel_called": False,
        "r7_model_arm": False,
        "package_accepted": False,
        "package_closed_from_b_alone": False,
        "direct_paths_open": True,
        "return_order": RETURN_NTBBK,
        "return_unfreeze": RETURN_UNFREEZE,
        "additive_id": ADDITIVE_NTBBK,
        "b_return_id": RETURN_ID,
        "b_under_return_id": UNDER_RETURN_ID,
        "b_additive_id": ADDITIVE_ID,
        "spec_sha256_match": spec["sha256_match"],
        "clarifications_sha256_match": clar["sha256_match"],
        "producer": producer,
        "refusal_consumer": refusals,
        "capability": capability,
        "b_clocks_promoted": False,
        "scipy_status": SCIPY_STATUS,
        "fitting_algorithm": SCIPY_FITTING_ALGORITHM,
        "real_exec": False,
        "science_hold": True,
        "producer_capability_gate": {
            "owner": "A",
            "status": "INTEGRATED_ONCE_PRODUCER_GATE",
            "reexecuted_this_turn": True,
            "real_science": False,
            "produce_kernel_rewrote": False,
        },
    }
