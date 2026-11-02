"""t5194u P14 RETURN_DELTA — real chain guard (import + socket)."""

from __future__ import annotations

import importlib
import socket
import sys
from pathlib import Path

import pytest

from src.services.nfl_fixture_assembly.assemble import FORBIDDEN_CALL_ATTEMPTS
from src.services.nfl_fixture_assembly.contract import FixtureEligibilityResult, FixtureHardRefuse
from src.services.nfl_fixture_assembly.guard import (
    chain_guard,
    guard_active,
    last_guard_report,
    run_under_chain_guard,
)
from src.services.nfl_fixture_assembly.produce_chain import produce_fixture_chain
from src.services.nfl_fixture_assembly.synth import synthetic_envelope


def test_produce_chain_reports_guard_active_true() -> None:
    FORBIDDEN_CALL_ATTEMPTS.clear()
    payload = produce_fixture_chain()
    report = last_guard_report()
    assert report["guard_active"] is True
    assert report["forbidden_call_attempts"] == 0
    assert payload["forecast"]["game_id"]
    assert guard_active() is False


def test_chain_path_refuses_real_forbidden_import_and_socket_connect() -> None:
    FORBIDDEN_CALL_ATTEMPTS.clear()
    sys.modules.pop("src.services.nfl_simulator", None)

    def probe() -> None:
        assert guard_active() is True
        with pytest.raises(FixtureHardRefuse) as import_exc:
            importlib.import_module("src.services.nfl_simulator")
        assert import_exc.value.result is FixtureEligibilityResult.REFUSE_QUALIFICATION
        with pytest.raises(FixtureHardRefuse) as sock_exc:
            socket.socket().connect(("203.0.113.1", 9))
        assert sock_exc.value.result is FixtureEligibilityResult.REFUSE_QUALIFICATION
        with pytest.raises(FixtureHardRefuse) as dns_exc:
            socket.getaddrinfo("example.test", 80)
        assert dns_exc.value.result is FixtureEligibilityResult.REFUSE_QUALIFICATION
        if len(FORBIDDEN_CALL_ATTEMPTS) < 2:
            raise AssertionError(f"expected import+socket attempts, got {FORBIDDEN_CALL_ATTEMPTS}")
        raise FixtureHardRefuse(
            FixtureEligibilityResult.REFUSE_QUALIFICATION,
            "chain path observed forbidden import and socket",
        )

    with pytest.raises(FixtureHardRefuse) as exc:
        run_under_chain_guard(probe)
    assert exc.value.result is FixtureEligibilityResult.REFUSE_QUALIFICATION
    assert len(FORBIDDEN_CALL_ATTEMPTS) > 0
    assert any(item.startswith("import:") for item in FORBIDDEN_CALL_ATTEMPTS)
    assert any(item.startswith("socket.") for item in FORBIDDEN_CALL_ATTEMPTS)
    assert "src.services.nfl_simulator" not in sys.modules
    report = last_guard_report()
    assert report["guard_active"] is True
    assert report["forbidden_call_attempts"] > 0


def test_produce_chain_refuses_when_probe_hits_guard(tmp_path: Path) -> None:
    """Forbidden import under an active produce/assemble guard refuses the run."""
    FORBIDDEN_CALL_ATTEMPTS.clear()
    dest = tmp_path / "chain.json"
    dest.write_text("ORIGINAL\n", encoding="utf-8")
    sys.modules.pop("requests", None)

    def hijacked_assemble(envelope):  # type: ignore[no-untyped-def]
        importlib.import_module("requests")
        raise AssertionError("import should have refused")

    import src.services.nfl_fixture_assembly.produce_chain as pc

    original = pc.assemble_fixture_only
    pc.assemble_fixture_only = hijacked_assemble  # type: ignore[assignment]
    try:
        with pytest.raises(FixtureHardRefuse) as exc:
            produce_fixture_chain(dest=dest, envelope=synthetic_envelope())
        assert exc.value.result is FixtureEligibilityResult.REFUSE_QUALIFICATION
        assert dest.read_text(encoding="utf-8") == "ORIGINAL\n"
        assert len(FORBIDDEN_CALL_ATTEMPTS) > 0
    finally:
        pc.assemble_fixture_only = original


def test_chain_guard_context_marks_active() -> None:
    assert guard_active() is False
    with chain_guard() as state:
        assert state.active is True
        assert guard_active() is True
    assert guard_active() is False
