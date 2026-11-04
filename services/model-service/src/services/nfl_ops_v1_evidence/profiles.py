"""Shared evidence-gate profile registry. Worker A is the sole registrar.

Worker B must not write this file and must not self-register.
B profiles stay PENDING_HANDOFF until A binds a handoff proof.
CERT=0. Synthetic only.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Optional

from src.services.nfl_ops_v1_evidence.constants import (
    AUTHORITY as WFIX_AUTHORITY,
    CERT,
    JOINT_CONTRACT,
    OWNER as WFIX_OWNER,
    OWNER_CLEAR as WFIX_OWNER_CLEAR,
    PACKAGE,
    PROFILE as WFIX_PROFILE,
    PROTOCOL,
    SCOPE_ID as WFIX_SCOPE_ID,
)
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass


STATUS_ACTIVE = "ACTIVE"
STATUS_PENDING_HANDOFF = "PENDING_HANDOFF"
STATUS_REGISTERED = "REGISTERED"

WORKER_A_ID = "bc-54a966a5-24bf-5d5d-a63c-50f75ad0abb8"
WORKER_A_ROLE = "Worker A"
WORKER_B_ID = "bc-02a716be-429a-56c8-ab0f-5f262aa479df"
WORKER_B_ROLE = "Worker B"

PROFILE_R7 = "R7_CORRECTNESS_V1"
PROFILE_OWNED_MARKET_TRACE = "OWNED_MARKET_TRACE_V1"
PROFILE_SYNTHETIC_MARKET_EVENTS = "SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1"
PROFILE_RECORDED_DATE_RETRO = "RECORDED_DATE_RETRO"
RETRO_ISOLATED_AREA = "services/model-service/src/services/nfl_r7_record_date_retro_c1"
PROFILE_NTBB_K_SYNTHETIC = "NTBB_K_SYNTHETIC_KERNEL_V1"
NTBBK_ISOLATED_AREA = "services/model-service/src/services/nfl_ntbb_k_v1"

R7_AUTHORITY = "t5289u"
R7_OWNER_CLEAR = "86257"
R7_SCOPE_ID = "chief-nflgreen-model-day-20261103-1700"
R7_OWNER = WORKER_A_ROLE

B_ISOLATED_AREA = "services/model-service/src/services/nfl_owned_market_v1"
B_ISOLATED_OPS = "data/ops/nfl_owned_market_v1"


class RefuseClassExt:
    PENDING_HANDOFF = "PENDING_HANDOFF"
    B_SELF_REGISTER = "B_SELF_REGISTER"
    HANDOFF_MISSING = "HANDOFF_MISSING"


if not hasattr(RefuseClass, "PENDING_HANDOFF"):
    RefuseClass.PENDING_HANDOFF = RefuseClassExt.PENDING_HANDOFF  # type: ignore[attr-defined]
if not hasattr(RefuseClass, "B_SELF_REGISTER"):
    RefuseClass.B_SELF_REGISTER = RefuseClassExt.B_SELF_REGISTER  # type: ignore[attr-defined]
if not hasattr(RefuseClass, "HANDOFF_MISSING"):
    RefuseClass.HANDOFF_MISSING = RefuseClassExt.HANDOFF_MISSING  # type: ignore[attr-defined]


@dataclass(frozen=True)
class GateProfile:
    profile_id: str
    owner: str
    authority: str
    owner_clear: str
    scope_id: str
    status: str
    registered_by: Optional[str]
    handoff_sha256: Optional[str]
    isolated_area: Optional[str]
    notes: str
    schema_hash: Optional[str] = None
    document_hash: Optional[str] = None
    fixture_sha256: Optional[str] = None
    validator: Optional[str] = None
    b_tip: Optional[str] = None
    cos_accept: Optional[str] = None


def _seed() -> Dict[str, GateProfile]:
    return {
        WFIX_PROFILE: GateProfile(
            profile_id=WFIX_PROFILE,
            owner=WFIX_OWNER,
            authority=WFIX_AUTHORITY,
            owner_clear=WFIX_OWNER_CLEAR,
            scope_id=WFIX_SCOPE_ID,
            status=STATUS_ACTIVE,
            registered_by="lineage_713_679dbdaf",
            handoff_sha256=None,
            isolated_area=None,
            notes="Narrow reuse of #713 SYNTHETIC_WFIX_AB_CHAIN. Unchanged W-FIX pins.",
        ),
        PROFILE_R7: GateProfile(
            profile_id=PROFILE_R7,
            owner=R7_OWNER,
            authority=R7_AUTHORITY,
            owner_clear=R7_OWNER_CLEAR,
            scope_id=R7_SCOPE_ID,
            status=STATUS_ACTIVE,
            registered_by=WORKER_A_ID,
            handoff_sha256=None,
            isolated_area=None,
            notes="Worker A opt-in synthetic IF/Q2 correctness profile.",
        ),
        PROFILE_OWNED_MARKET_TRACE: GateProfile(
            profile_id=PROFILE_OWNED_MARKET_TRACE,
            owner=WORKER_B_ROLE,
            authority=R7_AUTHORITY,
            owner_clear=R7_OWNER_CLEAR,
            scope_id=R7_SCOPE_ID,
            status=STATUS_PENDING_HANDOFF,
            registered_by=None,
            handoff_sha256=None,
            isolated_area=B_ISOLATED_AREA,
            notes="Worker B isolated. A registers only after B handoff.",
        ),
        PROFILE_SYNTHETIC_MARKET_EVENTS: GateProfile(
            profile_id=PROFILE_SYNTHETIC_MARKET_EVENTS,
            owner=WORKER_B_ROLE,
            authority=R7_AUTHORITY,
            owner_clear=R7_OWNER_CLEAR,
            scope_id=R7_SCOPE_ID,
            status=STATUS_PENDING_HANDOFF,
            registered_by=None,
            handoff_sha256=None,
            isolated_area=B_ISOLATED_AREA,
            notes="Worker B isolated. A registers only after B handoff.",
        ),
        PROFILE_RECORDED_DATE_RETRO: GateProfile(
            profile_id=PROFILE_RECORDED_DATE_RETRO,
            owner=WORKER_A_ROLE,
            authority="t5344u",
            owner_clear="92861",
            scope_id=R7_SCOPE_ID,
            status=STATUS_ACTIVE,
            registered_by=WORKER_A_ID,
            handoff_sha256=None,
            isolated_area=RETRO_ISOLATED_AREA,
            notes=(
                "Isolated RECORDED_DATE_RETRO metadata + synthetic executor. "
                "NOT_EXECUTABLE for real data. Strict live-causal remains DATA_HOLD."
            ),
        ),
        PROFILE_NTBB_K_SYNTHETIC: GateProfile(
            profile_id=PROFILE_NTBB_K_SYNTHETIC,
            owner=WORKER_B_ROLE,
            authority="t5344u",
            owner_clear="92861",
            scope_id=R7_SCOPE_ID,
            status=STATUS_REGISTERED,
            registered_by=WORKER_A_ID,
            handoff_sha256="bc71269fd3191ad08f8f4283dd2325c8da49bb3a2d1dfc5f64836ea08c4a341e",
            isolated_area=NTBBK_ISOLATED_AREA,
            b_tip="12c4158707304d1640158bfe59171237be8aca2c",
            cos_accept="12c4158707304d1640158bfe59171237be8aca2c",
            notes=(
                "Cos ACCEPT 12c41587: isolated NTBB-K SYNTHETIC kernel integrated once "
                "(RETURN 58427 + ADDITIVE 80649). a807af22 SUPERSEDED. d0bb6bef refused. "
                "Not a real R7 model arm. B 143 clocks not promoted. Package not closed "
                "from B alone."
            ),
        ),
    }


_REGISTRY: Dict[str, GateProfile] = _seed()


def reset_registry_for_tests() -> None:
    """Test helper. Not a production reset. Does not touch R5/protected seasons."""
    _REGISTRY.clear()
    _REGISTRY.update(_seed())


def list_profiles() -> Dict[str, dict[str, Any]]:
    return {
        key: {
            "profile_id": row.profile_id,
            "owner": row.owner,
            "authority": row.authority,
            "owner_clear": row.owner_clear,
            "scope_id": row.scope_id,
            "status": row.status,
            "registered_by": row.registered_by,
            "handoff_sha256": row.handoff_sha256,
            "isolated_area": row.isolated_area,
            "notes": row.notes,
            "schema_hash": row.schema_hash,
            "document_hash": row.document_hash,
            "fixture_sha256": row.fixture_sha256,
            "validator": row.validator,
            "b_tip": row.b_tip,
            "cos_accept": row.cos_accept,
            "package": PACKAGE,
            "protocol": PROTOCOL,
            "joint_contract": JOINT_CONTRACT,
            "cert": CERT,
        }
        for key, row in sorted(_REGISTRY.items())
    }


def get_profile(profile_id: Any) -> GateProfile:
    if not isinstance(profile_id, str) or not profile_id:
        raise EvidenceGateRefuse(
            f"profile missing/invalid: {profile_id!r}",
            refuse_class=RefuseClass.WRONG_PROFILE_IDENTITY,
        )
    row = _REGISTRY.get(profile_id)
    if row is None:
        raise EvidenceGateRefuse(
            f"profile {profile_id!r} is not registered in the shared gate",
            refuse_class=RefuseClass.WRONG_PROFILE_IDENTITY,
        )
    return row


def require_active_profile(profile_id: Any) -> GateProfile:
    row = get_profile(profile_id)
    if row.status != STATUS_ACTIVE:
        raise EvidenceGateRefuse(
            f"profile {row.profile_id} status={row.status} (not ACTIVE)",
            refuse_class=RefuseClass.PENDING_HANDOFF,
            detail={"profile": row.profile_id, "status": row.status},
        )
    return row


def register_b_profile(
    profile_id: str,
    *,
    registered_by: str,
    handoff: Mapping[str, Any],
) -> GateProfile:
    """Worker A only. Requires B handoff proof. B cannot self-register."""
    if registered_by != WORKER_A_ID:
        raise EvidenceGateRefuse(
            f"B self-register refused (registered_by={registered_by!r})",
            refuse_class=RefuseClass.B_SELF_REGISTER,
            detail={"registered_by": registered_by, "required": WORKER_A_ID},
        )
    if profile_id not in {PROFILE_OWNED_MARKET_TRACE, PROFILE_SYNTHETIC_MARKET_EVENTS}:
        raise EvidenceGateRefuse(
            f"not a Worker B profile: {profile_id!r}",
            refuse_class=RefuseClass.WRONG_PROFILE_IDENTITY,
        )
    row = get_profile(profile_id)
    proof = str(handoff.get("handoff_sha256") or "").strip().lower()
    if len(proof) != 64 or any(ch not in "0123456789abcdef" for ch in proof):
        raise EvidenceGateRefuse(
            "B handoff_sha256 missing or not sha256 hex",
            refuse_class=RefuseClass.HANDOFF_MISSING,
        )
    worker_ok = str(handoff.get("worker_id") or "") == WORKER_B_ID or str(handoff.get("worker") or "") == "B"
    if not worker_ok:
        raise EvidenceGateRefuse(
            "handoff worker is not today's Worker B",
            refuse_class=RefuseClass.HANDOFF_MISSING,
            detail={"got": handoff.get("worker_id") or handoff.get("worker"), "expected": WORKER_B_ID},
        )
    if str(handoff.get("profile_id") or "") not in {"", profile_id} and str(handoff.get("profile_id")) != profile_id:
        raise EvidenceGateRefuse(
            "handoff profile_id does not match registration target",
            refuse_class=RefuseClass.HANDOFF_MISSING,
        )
    isolated = str(handoff.get("isolated_area") or "")
    if isolated and B_ISOLATED_AREA not in isolated and B_ISOLATED_OPS not in isolated:
        raise EvidenceGateRefuse(
            "handoff is not from the isolated nfl_owned_market_v1 area",
            refuse_class=RefuseClass.HANDOFF_MISSING,
            detail={"isolated_area": isolated},
        )
    schema_hash = str(handoff.get("schema_hash") or "") or None
    document_hash = str(handoff.get("document_hash") or "") or None
    fixture_sha256 = str(handoff.get("fixture_sha256") or "") or None
    updated = replace(
        row,
        status=STATUS_REGISTERED,
        registered_by=WORKER_A_ID,
        handoff_sha256=proof,
        isolated_area=isolated or B_ISOLATED_OPS,
        schema_hash=schema_hash,
        document_hash=document_hash,
        fixture_sha256=fixture_sha256,
        validator=str(handoff.get("validator") or "") or None,
        b_tip=str(handoff.get("b_tip") or "") or None,
        cos_accept=str(handoff.get("cos_accept") or "") or None,
        notes=f"Registered by Worker A after Cos ACCEPT {handoff.get('cos_accept') or 'handoff'} {proof[:12]}",
    )
    _REGISTRY[profile_id] = updated
    return updated
