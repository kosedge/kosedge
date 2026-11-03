"""NTBB-K SYNTHETIC kernel tests. CERT=0. REPORTED_ONLY."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.services.nfl_ntbb_k_v1.cases import run_root_nine
from src.services.nfl_ntbb_k_v1.constants import (
    ORACLE_MAX_ENUMERATED_TOTAL,
    PIN_JSONL_143_PROJECTION_SHA256,
    SCIPY_FITTING_ALGORITHM,
    SCIPY_STATUS,
    SPEC_SHA256,
)
from src.services.nfl_ntbb_k_v1.law import log_joint_pmf
from src.services.nfl_ntbb_k_v1.produce import produce_kernel, verify_spec_blob
from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse
from src.services.nfl_ntbb_k_v1.table import (
    choose_tail_n,
    enumerate_joint,
    refuse_unknown_settlement,
    summarize_spread,
    summarize_total,
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for path in (here, *here.parents):
        if (path / ".git").exists():
            return path
    raise AssertionError("git root not found")


def test_spec_sha256_match() -> None:
    spec = verify_spec_blob(_repo_root())
    assert spec["sha256"] == SPEC_SHA256
    assert spec["sha256_match"] is True


def test_root_nine_stdlib_oracle() -> None:
    nine = run_root_nine()
    assert nine["status"] == "PASS"
    assert nine["n_cases"] == 9
    assert nine["max_enumerated_total"] <= ORACLE_MAX_ENUMERATED_TOTAL == 183
    for row in nine["results"]:
        assert row["status"] == "PASS"
        assert row["residuals"]["normalization"] <= 1e-10
        assert row["residuals"]["total_marginal"] <= 1e-8
        assert row["residuals"]["tail_moment"] <= 1e-8


def test_conditional_normalizer_and_transpose() -> None:
    params = {"mu": 8.0, "r": 20.0, "p": 0.35, "c": 12.0, "k0": 0.2, "k3": 0.1, "k7": 0.05}
    swapped = dict(params)
    swapped["p"] = 0.65
    assert abs(log_joint_pmf(7, 3, **params) - log_joint_pmf(3, 7, **swapped)) < 1e-10


def test_tail_cap_refusal() -> None:
    with pytest.raises(NtbbKRefuse, match="NUMERICAL_TAIL_LIMIT"):
        choose_tail_n(r=2.0, mu=400.0)


def test_bad_types_refuse() -> None:
    with pytest.raises(NtbbKRefuse):
        log_joint_pmf(True, 0, mu=4.0, r=20.0, p=0.5, c=12.0)
    with pytest.raises(NtbbKRefuse):
        log_joint_pmf(-1, 0, mu=4.0, r=20.0, p=0.5, c=12.0)


def test_spread_total_push_and_unknown_settlement() -> None:
    table = enumerate_joint(mu=8.0, r=20.0, p=0.5, c=12.0)
    spr = summarize_spread(table, "-3")
    tot = summarize_total(table, "44.5")
    assert spr["win"] + spr["push"] + spr["loss"] == pytest.approx(table["enumerated_mass"])
    assert tot["over"] + tot["push"] + tot["under"] == pytest.approx(table["enumerated_mass"])
    with pytest.raises(NtbbKRefuse, match="settlement"):
        refuse_unknown_settlement(period=None)


def test_produce_atomic_and_market_clocks_unverified(tmp_path: Path) -> None:
    out = produce_kernel(repo_root=_repo_root())
    doc = out["document"]
    assert doc["kernel_implemented"] is True
    assert doc["scipy_status"] == SCIPY_STATUS
    assert doc["fitting_algorithm"] == SCIPY_FITTING_ALGORITHM
    assert doc["clocks_143"] == "SOURCE_VALUE_MATCH_NOT_VERIFIED"
    assert doc["market_partial_preserved"]["clock_semantics_verified_any"] is False
    assert doc["owned_completion_claimed"] is False
    raw = (_repo_root() / "data/ops/nfl_owned_market_v1/codex_staged/JSONL_SELECTED_143_SOURCE_VALUE_PROJECTION.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PIN_JSONL_143_PROJECTION_SHA256
    assert "scipy" not in {m.split(".")[0] for m in __import__("sys").modules}


def test_no_scipy_dependency_held() -> None:
    import importlib

    assert importlib.util.find_spec("scipy") is None
    assert SCIPY_STATUS == "ABSENT_NOT_EVALUABLE"
    assert SCIPY_FITTING_ALGORITHM == "UNEXECUTED_DEPENDENCY_HELD"
