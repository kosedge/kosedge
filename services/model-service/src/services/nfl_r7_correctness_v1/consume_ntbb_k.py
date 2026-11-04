"""A-side NTBB-K staged consume. CERT=0.

RETURN 58427: a807af22 is held, not final. d0bb6bef remains refused.
Integrate the corrected B log-PMF/tail revision once when posted.
Not a real R7 model arm. Package not accepted while direct paths open.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.services.nfl_ntbb_k_v1.constants import PROFILE, SCIPY_FITTING_ALGORITHM, SCIPY_STATUS
from src.services.nfl_ntbb_k_v1.produce import verify_clarifications_blob, verify_spec_blob
from src.services.nfl_r7_correctness_v1.followthrough_preflight import (
    B_NTBBK_KERNEL_SHA256,
    B_NTBBK_TIP_FROZEN,
    B_NTBBK_TIP_HELD,
    B_NTBBK_TIP_REFUSED,
    RETURN_UNFREEZE,
)
from src.services.nfl_r7_correctness_v1.produce import repo_root
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroRefuse
from src.services.nfl_t5208u.hashing import sha256_file

KERNEL_REL = "data/ops/nfl_ntbb_k_v1/KERNEL_SYNTHETIC_92861.json"


def consume_ntbb_k(*, root: Path | None = None) -> dict[str, Any]:
    repo = repo_root() if root is None else Path(root)
    if B_NTBBK_TIP_HELD == B_NTBBK_TIP_REFUSED:
        raise RetroRefuse("held and refused tips must differ")
    if B_NTBBK_TIP_FROZEN is not None:
        raise RetroRefuse("RETURN 58427 forbids a final frozen NTBB-K tip")
    spec = verify_spec_blob(repo)
    clar = verify_clarifications_blob(repo)
    kernel = repo / KERNEL_REL
    if not kernel.is_file():
        raise RetroRefuse(f"missing staged kernel {KERNEL_REL}")
    digest = sha256_file(kernel)
    if digest != B_NTBBK_KERNEL_SHA256:
        raise RetroRefuse(f"staged kernel sha {digest} != held {B_NTBBK_KERNEL_SHA256}")
    return {
        "ok": True,
        "cert": 0,
        "profile": PROFILE,
        "held_tip": B_NTBBK_TIP_HELD,
        "frozen_tip": None,
        "frozen_as_final": False,
        "refused_tip": B_NTBBK_TIP_REFUSED,
        "kernel_sha256": digest,
        "kernel_role": "STAGED_NOT_FINAL_FROM_a807af22",
        "r7_model_arm": False,
        "package_accepted": False,
        "package_closed_from_b_alone": False,
        "direct_paths_open": True,
        "return_unfreeze": RETURN_UNFREEZE,
        "waiting_for": "B direct log-PMF/tail proof delta under 36205",
        "producer_capability_gate": "A_OBLIGATION",
        "b_clocks_promoted": False,
        "scipy_status": SCIPY_STATUS,
        "fitting_algorithm": SCIPY_FITTING_ALGORITHM,
        "spec_sha256_match": spec["sha256_match"],
        "clarifications_sha256_match": clar["sha256_match"],
        "real_exec": False,
    }
