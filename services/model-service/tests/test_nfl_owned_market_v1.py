"""Isolated nfl_owned_market_v1 tests. CERT=0. RETURN 47318."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.services.nfl_owned_market_v1.arithmetic import (
    RISK1_U,
    american_profit,
    grade_spread_ats,
    line_clv,
    portfolio_roi,
    settle_ticket,
)
from src.services.nfl_owned_market_v1.constants import (
    CERT,
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
    ROLE_FICTIONAL_ECONOMIC,
    ROLE_OWNED_READINESS,
)
from src.services.nfl_owned_market_v1.hashing import require_sha256_hex
from src.services.nfl_owned_market_v1.produce import (
    build_events_document,
    build_trace_document,
    produce_artifacts,
)
from src.services.nfl_owned_market_v1.profiles import handoff_interface
from src.services.nfl_owned_market_v1.refuse import OwnedMarketRefuse
from src.services.nfl_owned_market_v1.schema import schema_hash
from src.services.nfl_owned_market_v1.validate import (
    validate_join,
    validate_owned_market_trace,
    validate_synthetic_market_economic_events,
)


def test_american_profit_risk1_exact() -> None:
    assert american_profit(risk1_u=RISK1_U, juice=-110, won=True) == pytest.approx(100.0 / 110.0)
    assert american_profit(risk1_u=RISK1_U, juice=-110, won=False) == -1.0
    assert american_profit(risk1_u=RISK1_U, juice=150, won=True) == 1.5


def test_ats_win_push_loss() -> None:
    assert grade_spread_ats(side="home", line=-3.0, home_score=24, away_score=20) == "win"
    assert grade_spread_ats(side="home", line=-3.0, home_score=23, away_score=20) == "push"
    assert grade_spread_ats(side="home", line=-3.0, home_score=20, away_score=20) == "loss"


def test_missing_line_refuses() -> None:
    with pytest.raises(OwnedMarketRefuse, match="line required"):
        grade_spread_ats(side="home", line=None, home_score=24, away_score=20)


def test_missing_juice_refuses_roi() -> None:
    ticket = {
        "market": "spread",
        "side": "home",
        "line": -3.0,
        "open_line": -3.0,
        "close_line": -4.0,
        "open_price": -110,
        "close_price": -115,
        "home_score": 24,
        "away_score": 20,
        "juice": None,
        "juice_status": "DATA_GAP",
        "settlement_status": "final",
    }
    with pytest.raises(OwnedMarketRefuse, match="DATA_GAP"):
        settle_ticket(ticket)


def test_no_invent_minus_110() -> None:
    with pytest.raises(OwnedMarketRefuse, match="flat -110"):
        settle_ticket(
            {
                "market": "spread",
                "side": "home",
                "line": -3.0,
                "open_line": -3.0,
                "close_line": -3.0,
                "open_price": -110,
                "close_price": -110,
                "home_score": 24,
                "away_score": 20,
                "juice": None,
                "settlement_status": "final",
            }
        )


def test_line_clv_spread_home() -> None:
    assert line_clv(
        market="spread",
        side="home",
        open_line=-3.0,
        close_line=-4.5,
        open_price=None,
        close_price=None,
    ) == pytest.approx(1.5)


def test_void_excluded_from_roi() -> None:
    settled = [
        {"ats_result": "win", "profit_u": 100.0 / 110.0, "risked_u": 1.0, "roi_eligible": True},
        {"ats_result": "void", "profit_u": 0.0, "risked_u": 0.0, "roi_eligible": False},
        {"ats_result": "push", "profit_u": 0.0, "risked_u": 0.0, "roi_eligible": False},
    ]
    roi = portfolio_roi(settled)
    assert roi["status"] == "ok"
    assert roi["risked_u"] == 1.0
    assert roi["ats"]["v"] == 1
    assert roi["ats"]["p"] == 1


def test_produce_and_separate_profiles(tmp_path: Path) -> None:
    artifacts = produce_artifacts(repo_root=tmp_path)
    assert artifacts["trace_report"]["profile_role"] == ROLE_OWNED_READINESS
    assert artifacts["events_report"]["profile_role"] == ROLE_FICTIONAL_ECONOMIC
    assert artifacts["trace_report"]["owned_completion_claimed"] is False
    assert artifacts["trace"]["data_label"] == "OWNED_SOURCE_UNAVAILABLE"
    assert "observations" not in artifacts["trace"]
    assert artifacts["join_report"]["profiles_separate"] is True
    assert artifacts["join_report"]["joined"] is False
    assert artifacts["events_report"]["n_tickets"] == 5
    assert artifacts["events"]["roi"]["status"] == "ok"


def test_handoff_names_roles(tmp_path: Path) -> None:
    artifacts = produce_artifacts(repo_root=tmp_path)
    interface = handoff_interface(artifacts)
    assert interface["worker"] == "B"
    assert interface["cert"] == CERT
    assert interface["profile_roles"][PROFILE_OWNED_MARKET_TRACE] == ROLE_OWNED_READINESS
    assert (
        interface["profile_roles"][PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS]
        == ROLE_FICTIONAL_ECONOMIC
    )
    assert interface["preserves"]["prior_handoff_sha256"].startswith("5b7ee2e4")
    require_sha256_hex(
        interface["profiles"][PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS]["fixture_sha256"],
        name="econ_fixture",
    )
    assert interface["profiles"][PROFILE_OWNED_MARKET_TRACE]["schema_hash"] == schema_hash(
        PROFILE_OWNED_MARKET_TRACE
    )


def test_owned_refuses_fictional_observations() -> None:
    doc = build_trace_document(repo_root=Path.cwd())
    doc["observations"] = [{"seq": 1}]
    with pytest.raises(OwnedMarketRefuse, match="fictional observations"):
        validate_owned_market_trace(doc)


def test_in_memory_builders_validate(tmp_path: Path) -> None:
    trace = build_trace_document(repo_root=tmp_path)
    events = build_events_document()
    assert validate_owned_market_trace(trace)["validated"] is True
    assert validate_synthetic_market_economic_events(events)["validated"] is True
    assert validate_join(trace, events)["profiles_separate"] is True


def test_schema_hashes_stable() -> None:
    a = schema_hash(PROFILE_OWNED_MARKET_TRACE)
    b = schema_hash(PROFILE_OWNED_MARKET_TRACE)
    c = schema_hash(PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS)
    require_sha256_hex(a, name="schema_trace")
    require_sha256_hex(c, name="schema_events")
    assert a == b
    assert a != c
