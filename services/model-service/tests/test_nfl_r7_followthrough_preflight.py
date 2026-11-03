"""t5335u followthrough metadata preflight tests. CERT=0. No kernel."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_r7_correctness_v1.followthrough_preflight import (
    EXACT_496,
    N_2020,
    N_2021,
    N_NEW_59,
    N_OLD_437,
    N_SAME_96,
    SPEC_SHA256,
    FollowthroughRefuse,
    _scan_forbidden,
    build_candidate,
    require_spec,
    run_direct_boundary_controls,
)

REPO = Path(__file__).resolve().parents[3]


def test_spec_bind_matches_connector() -> None:
    bound = require_spec(REPO)
    assert bound["sha256"] == SPEC_SHA256
    assert bound["kernel_implemented"] is False


def test_candidate_counts_and_unknown_timing() -> None:
    cand = build_candidate(root=REPO)
    assert cand["counts"]["exact496"] == EXACT_496 == N_2020 + N_2021
    assert cand["counts"]["old437"] + cand["counts"]["new59"] == EXACT_496
    assert cand["counts"]["old437"] == N_OLD_437
    assert cand["counts"]["new59"] == N_NEW_59
    assert cand["counts"]["same96"] == N_SAME_96
    assert cand["counts"]["same96_ids_present"] is False
    assert len(cand["game_ids"]) == EXACT_496
    assert len(cand["new_59_ids"]) == N_NEW_59
    assert cand["readiness"] == "NOT_READY"
    assert cand["kernel_implemented"] is False
    assert cand["score_bearing_payload_returned"] is False
    assert cand["packaging_revision"] is None
    assert cand["packaging_revision_claimed_as_executed"] is False
    assert cand["runtime_source_revision"]
    assert cand["missing_n"] >= 1
    assert all(row["actual_versus_scheduled"] == "UNKNOWN" for row in cand["targets"])
    assert all(row["played"] == "UNKNOWN" for row in cand["targets"])
    assert all(row["rest_ready"] is False for row in cand["targets"])
    assert all(row["score_bearing_payload"] is False for row in cand["targets"])
    assert cand["targets"][0]["previous_week_history_pointer_eligible"] is True
    assert cand["spec"]["sha256"] == SPEC_SHA256


def test_score_keys_and_missing_spec_refused() -> None:
    with pytest.raises(FollowthroughRefuse, match="home_score"):
        _scan_forbidden({"home_score": 21}, where="test")
    with pytest.raises(FollowthroughRefuse, match="spec missing"):
        require_spec(Path("/tmp/no-such-r7-root"))
    controls = run_direct_boundary_controls()
    assert controls["spy_positive_control"]["spy_fired"] is True
    assert all(item["refused"] for item in controls["negatives"])
