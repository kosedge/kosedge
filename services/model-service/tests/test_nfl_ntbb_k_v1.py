"""NTBB-K SYNTHETIC kernel tests. CERT=0. REPORTED_ONLY.

RETURN 36205 numeric/direct boundary. Not a new pool. Not a fitted-model claim.
Prior DEMO_SMALL_NINE (mu 4–12, maxN 61) is not a reproduction of the root fixtures.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from src.services.nfl_ntbb_k_v1.cases import run_root_nine
from src.services.nfl_ntbb_k_v1.constants import (
    CLARIFICATIONS_SHA256,
    DEMO_SMALL_NINE,
    FUTURE_GRAD_STEP,
    ORACLE_MAX_ENUMERATED_TOTAL,
    PIN_JSONL_143_PROJECTION_SHA256,
    ADDITIVE_ID,
    RETURN_ID,
    UNDER_RETURN_ID,
    ROOT_EXPECTED_N,
    ROOT_NINE,
    SCIPY_FITTING_ALGORITHM,
    SCIPY_STATUS,
    SPEC_SHA256,
)
from src.services.nfl_ntbb_k_v1.law import conditional_log_mass, log_joint_pmf
from src.services.nfl_ntbb_k_v1.produce import (
    produce_kernel,
    verify_clarifications_blob,
    verify_spec_blob,
)
from src.services.nfl_ntbb_k_v1.refuse import NtbbKRefuse
from src.services.nfl_ntbb_k_v1.special import (
    log_betabinom_pmf,
    log_nbinom_pmf,
    nbinom_success_p,
    remaining_series_tail,
)
from src.services.nfl_ntbb_k_v1.table import (
    choose_tail_n,
    enumerate_joint,
    event_interval,
    moment_bound,
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


def test_clarifications_sha256_match() -> None:
    clar = verify_clarifications_blob(_repo_root())
    assert clar["sha256"] == CLARIFICATIONS_SHA256
    assert clar["sha256"] == "dd2fa8d041b652324c07b77aea2f2b589146213342a414b98e8bcc629d5bc3e8"
    assert clar["sha256_match"] is True


def test_root_nine_are_executed_root_fixtures_not_demo_small() -> None:
    assert RETURN_ID == "58427"
    assert UNDER_RETURN_ID == "36205"
    assert ADDITIVE_ID == "80649"
    assert len(ROOT_NINE) == 9
    names = [row[0] for row in ROOT_NINE]
    assert names == [
        "MU44_R20_K0",
        "MU44_R20_KPOS",
        "MU44_R20_KNEG",
        "MU36_R12_K0",
        "MU36_R12_KPOS",
        "MU36_R12_KNEG",
        "MU52_R30_K0",
        "MU52_R30_KPOS",
        "MU52_R30_KNEG",
    ]
    bases = {(row[1], row[2], row[3], row[4]) for row in ROOT_NINE}
    assert bases == {(44.0, 20.0, 0.50, 12.0), (36.0, 12.0, 0.35, 6.0), (52.0, 30.0, 0.70, 25.0)}
    tilts = {(row[5], row[6], row[7]) for row in ROOT_NINE}
    assert tilts == {(0.0, 0.0, 0.0), (0.4, 0.7, 0.6), (-0.5, -0.7, -0.6)}
    assert ROOT_EXPECTED_N == {"MU44_R20": 175, "MU36_R12": 183, "MU52_R30": 174}
    demo_names = {row[0] for row in DEMO_SMALL_NINE}
    assert demo_names.isdisjoint(set(names))
    assert all(row[1] <= 12.0 for row in DEMO_SMALL_NINE)


def test_root_nine_stdlib_oracle() -> None:
    nine = run_root_nine()
    assert nine["status"] == "PASS"
    assert nine["n_cases"] == 9
    assert nine["fixture_kind"] == "RETURN_36205_ROOT_NINE"
    assert nine["not_demo_small_nine"] is True
    assert nine["max_enumerated_total"] == 183
    assert nine["max_enumerated_total"] <= ORACLE_MAX_ENUMERATED_TOTAL == 183
    by_family = {}
    for row in nine["results"]:
        assert row["status"] == "PASS"
        assert row["group"] == "root"
        assert row["N"] == row["expected_N"]
        by_family.setdefault(row["family"], set()).add(row["N"])
        assert row["residuals"]["normalization"] <= 1e-10
        assert row["residuals"]["total_marginal"] <= 1e-8
        assert row["residuals"]["tail_moment"] <= 1e-8
        assert row["enumeration_error"] <= 1e-10
    assert by_family == {
        "MU44_R20": {175},
        "MU36_R12": {183},
        "MU52_R30": {174},
    }


def test_conditional_normalizer_and_transpose() -> None:
    params = {"mu": 8.0, "r": 20.0, "p": 0.35, "c": 12.0, "k0": 0.2, "k3": 0.1, "k7": 0.05}
    swapped = dict(params)
    swapped["p"] = 0.65
    assert abs(log_joint_pmf(7, 3, **params) - log_joint_pmf(3, 7, **swapped)) < 1e-10


def test_conditional_log_mass_refuses_nan_and_bool_before_t0_shortcut() -> None:
    with pytest.raises(NtbbKRefuse):
        conditional_log_mass(0, p=0.5, c=True, k0=float("nan"), k3=0, k7=0)
    with pytest.raises(NtbbKRefuse, match="nonfinite"):
        conditional_log_mass(0, p=0.5, c=12.0, k0=float("nan"), k3=0.0, k7=0.0)
    with pytest.raises(NtbbKRefuse, match="bad type"):
        conditional_log_mass(0, p=0.5, c=True, k0=0.0, k3=0.0, k7=0.0)
    with pytest.raises(NtbbKRefuse, match="nonfinite"):
        conditional_log_mass(0, p=0.5, c=12.0, k0=0.0, k3=float("inf"), k7=0.0)
    assert conditional_log_mass(0, p=0.5, c=12.0, k0=0.0, k3=0.0, k7=0.0) == [0.0]


def test_extreme_r_refuse_accept_matrix() -> None:
    """Direct controls. Extreme r must not accept a silently different law."""
    common = {"mu": 44.0, "p": 0.5, "c": 12.0}
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        nbinom_success_p(r=1e16, mu=44.0)
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        nbinom_success_p(r=1e12, mu=44.0)
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        log_nbinom_pmf(0, r=1e16, mu=44.0)
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        log_nbinom_pmf(0, r=1e12, mu=44.0)
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        enumerate_joint(r=1e16, **common)
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        enumerate_joint(r=1e12, **common)
    accepted = enumerate_joint(r=20.0, **common)
    assert accepted["moments"]["status"] == "OK"
    assert accepted["N"] == 175
    assert abs(accepted["moments"]["total_mean"] - 44.0) <= 1e-8 + accepted["moments"]["moment_bound"]
    assert accepted["enumeration_error"] <= 1e-10


def test_log_joint_pmf_extreme_refuse_ordinary_unchanged() -> None:
    """Shared log-PMF entrypoint. Extremes refuse; ordinary pins stay bit-identical."""
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        log_joint_pmf(0, 0, mu=44.0, r=1e12, p=0.5, c=12.0)
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        log_joint_pmf(0, 0, mu=44.0, r=1e16, p=0.5, c=12.0)
    assert log_joint_pmf(0, 0, mu=44.0, r=20.0, p=0.5, c=12.0) == -23.263016196113618
    assert log_joint_pmf(0, 0, mu=36.0, r=12.0, p=0.35, c=6.0) == -16.635532333438686
    assert log_joint_pmf(0, 0, mu=52.0, r=30.0, p=0.7, c=25.0) == -30.16565596806293


def test_remaining_series_n_lt_1_uses_max_q_rho() -> None:
    """n=0.5, p=q=0.5, cutoff=0: rho is not an upper envelope."""
    from src.services.nfl_ntbb_k_v1.special import log_nbinom_pmf_np

    true_tail = 1.0 - math.sqrt(0.5)
    first = math.exp(log_nbinom_pmf_np(1, n=0.5, p=0.5, q=0.5))
    rho = (0 + 1 + 0.5) / (0 + 2) * 0.5
    assert rho == pytest.approx(0.375)
    invalid = first / (1.0 - rho)
    assert invalid == pytest.approx(0.282842712474619, abs=1e-15)
    assert invalid < true_tail
    tail = remaining_series_tail(n_success=0.5, p=0.5, q=0.5, cutoff=0)
    assert tail["rho"] == pytest.approx(0.375)
    assert tail["rho_bound"] == pytest.approx(0.5)
    assert tail["upper"] == pytest.approx(first / (1.0 - 0.5), abs=1e-15)
    assert tail["upper"] >= true_tail
    assert true_tail == pytest.approx(0.2928932188134524, abs=1e-15)
    mb = moment_bound(mu=0.5, r=0.5, n=20)
    p, _q = nbinom_success_p(r=0.5, mu=0.5)
    assert mb["same_mean"] is False
    assert mb["same_probability"] is True
    assert mb["p"] == p == pytest.approx(0.5)
    assert mb["r_plus_1"] == 1.5
    assert mb["tail"]["rho_bound"] == mb["tail"]["rho"]


def test_event_interval_clips_to_unit() -> None:
    assert event_interval(1.0, 1e-12) == (1.0, 1.0)
    lo, hi = event_interval(0.0, 1e-12)
    assert lo == 0.0
    assert 0.0 <= hi <= 1.0
    lo, hi = event_interval(0.25, 1e-12)
    assert lo == 0.25
    assert hi == pytest.approx(0.25 + 1e-12)
    assert 0.0 <= lo <= hi <= 1.0
    with pytest.raises(NtbbKRefuse):
        event_interval(-0.1, 0.0)


def test_moment_bound_uses_same_p_not_same_mean() -> None:
    mb = moment_bound(mu=44.0, r=20.0, n=175)
    p, _q = nbinom_success_p(r=20.0, mu=44.0)
    assert mb["same_mean"] is False
    assert mb["same_probability"] is True
    assert mb["p"] == p
    assert mb["r_plus_1"] == 21.0
    assert mb["bound"] <= 1e-8


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
    for pair in (*spr["intervals"].values(), *tot["intervals"].values()):
        assert 0.0 <= pair[0] <= pair[1] <= 1.0
    with pytest.raises(NtbbKRefuse, match="settlement"):
        refuse_unknown_settlement(period=None)


def test_produce_atomic_and_market_clocks_unverified(tmp_path: Path) -> None:
    out = produce_kernel(repo_root=_repo_root())
    doc = out["document"]
    assert doc["kernel_implemented"] is True
    assert doc["return_id"] == "58427"
    assert doc["under_return_id"] == "36205"
    assert doc["additive_id"] == "80649"
    assert doc["design"] == "25194"
    assert doc["future_grad_step"] == FUTURE_GRAD_STEP == 5e-6
    assert doc["scipy_status"] == SCIPY_STATUS
    assert doc["fitting_algorithm"] == SCIPY_FITTING_ALGORITHM
    assert doc["clocks_143"] == "SOURCE_VALUE_MATCH_NOT_VERIFIED"
    assert doc["market_partial_preserved"]["clock_semantics_verified_any"] is False
    assert doc["owned_completion_claimed"] is False
    assert doc["clarifications"]["sha256_match"] is True
    assert doc["root_nine"]["fixture_kind"] == "RETURN_36205_ROOT_NINE"
    assert doc["root_nine"]["max_enumerated_total"] == 183
    assert doc["root_nine"]["not_demo_small_nine"] is True
    raw = (_repo_root() / "data/ops/nfl_owned_market_v1/codex_staged/JSONL_SELECTED_143_SOURCE_VALUE_PROJECTION.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PIN_JSONL_143_PROJECTION_SHA256
    assert "scipy" not in {m.split(".")[0] for m in __import__("sys").modules}
    del tmp_path


def test_no_scipy_dependency_held() -> None:
    import importlib

    assert importlib.util.find_spec("scipy") is None
    assert SCIPY_STATUS == "ABSENT_NOT_EVALUABLE"
    assert SCIPY_FITTING_ALGORITHM == "UNEXECUTED_DEPENDENCY_HELD"


def test_future_grad_step_not_promoted() -> None:
    assert FUTURE_GRAD_STEP == 5e-6
    assert math.isfinite(FUTURE_GRAD_STEP)


def test_betabinom_large_c_refuse_ordinary_unchanged() -> None:
    """ADDITIVE 80649: shared BB/conditional. No fabricated corrected probs."""
    ordinary = conditional_log_mass(2, p=0.3, c=12.0, k0=0.0, k3=0.0, k7=0.0)
    probs = [math.exp(x) for x in ordinary]
    mean = sum(h * pr for h, pr in enumerate(probs))
    assert mean == pytest.approx(0.6, abs=1e-15)
    assert probs == pytest.approx(
        [0.5061538461538465, 0.3876923076923073, 0.10615384615384624], abs=1e-15
    )
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        conditional_log_mass(2, p=0.3, c=1e12, k0=0.0, k3=0.0, k7=0.0)
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        conditional_log_mass(2, p=0.3, c=1e16, k0=0.0, k3=0.0, k7=0.0)
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        log_betabinom_pmf(1, 2, alpha=0.3 * 1e16, beta=0.7 * 1e16)
    with pytest.raises(NtbbKRefuse, match="UNSUPPORTED_NUMERIC_DOMAIN"):
        log_joint_pmf(1, 1, mu=44.0, r=20.0, p=0.3, c=1e16)
    # ordinary root conditionals still evaluate
    root = conditional_log_mass(2, p=0.5, c=12.0, k0=0.0, k3=0.0, k7=0.0)
    assert [math.exp(x) for x in root] == pytest.approx(
        [0.2692307692307691, 0.4615384615384619, 0.2692307692307691], abs=1e-15
    )
