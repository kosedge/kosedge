"""A NTBB-K producer→capability/gate. CERT=0. Synthetic only."""

from __future__ import annotations

from pathlib import Path

from src.services.nfl_ops_v1_evidence.profiles import (
    PROFILE_NTBB_K_SYNTHETIC,
    get_profile,
)
from src.services.nfl_r7_correctness_v1.consume_ntbb_k import consume_ntbb_k
from src.services.nfl_r7_correctness_v1.followthrough_preflight import (
    B_NTBBK_KERNEL_SHA256,
    B_NTBBK_TIP_INTEGRATED,
    B_NTBBK_TIP_REFUSED,
    B_NTBBK_TIP_SUPERSEDED,
)
from src.services.nfl_r7_correctness_v1.ntbbk_gate import run_ntbbk_integrate_gate
from src.services.nfl_t5208u.hashing import sha256_file

REPO = Path(__file__).resolve().parents[3]
KERNEL = REPO / "data/ops/nfl_ntbb_k_v1/KERNEL_SYNTHETIC_92861.json"


def test_gate_verifies_12c41587_without_rewrite() -> None:
    before = sha256_file(KERNEL)
    bound = run_ntbbk_integrate_gate(root=REPO)
    after = sha256_file(KERNEL)
    assert before == after == B_NTBBK_KERNEL_SHA256
    assert bound["ok"] is True
    assert bound["cert"] == 0
    assert bound["integrated_tip"] == B_NTBBK_TIP_INTEGRATED
    assert bound["superseded_tip"] == B_NTBBK_TIP_SUPERSEDED
    assert bound["refused_tip"] == B_NTBBK_TIP_REFUSED
    assert bound["frozen_as_final"] is False
    assert bound["package_closed_from_b_alone"] is False
    assert bound["package_accepted"] is False
    assert bound["r7_model_arm"] is False
    assert bound["produce_kernel_called"] is False
    assert bound["kernel_rewritten"] is False
    assert bound["producer"]["n_by_family"] == {
        "MU44_R20": 175,
        "MU36_R12": 183,
        "MU52_R30": 174,
    }
    assert bound["refusal_consumer"]["ordinary_log_joint_00"] == -23.263016196113618
    assert bound["refusal_consumer"]["nb_tail_max_q_rho"]["rho_bound"] == 0.5
    assert bound["capability"]["consumed"] is True
    assert bound["capability"]["from_producer"] is True
    assert bound["capability"]["hand_built"] is False
    assert bound["capability"]["self_reported_integrated_proof"] is False
    assert bound["capability"]["clocks_143"] == "SOURCE_VALUE_MATCH_NOT_VERIFIED"
    assert bound["self_reported_integrated_proof"] is False
    assert bound["consumer_invoked"] is True
    assert bound["shared_gate_invoked"] is True
    assert bound["shared_gate_ok"] is True
    assert bound["csv44_role"] in {"ABSENT", "EVIDENCE_ONLY_NOT_PROMOTED"}


def test_consume_is_the_gate() -> None:
    bound = consume_ntbb_k(root=REPO)
    assert bound["producer_capability_gate"]["status"] == "JOINT_CONSUMER_SHARED_GATE"
    profile = get_profile(PROFILE_NTBB_K_SYNTHETIC)
    assert profile.b_tip == B_NTBBK_TIP_INTEGRATED
    assert profile.status == "REGISTERED"
    assert profile.cos_accept == B_NTBBK_TIP_INTEGRATED


def test_csv44_not_promoted() -> None:
    assert not (
        REPO / "data/ops/nfl_owned_market_v1/codex_staged/CSV_SELECTED_44_RAW_VALUE_PROJECTION.json"
    ).exists()
