"""t5289u R7_CORRECTNESS_V1 tests. CERT=0. SYNTHETIC only."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.services.nfl_ops_v1_evidence.profiles import (
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_EVENTS,
    WORKER_A_ID,
    WORKER_B_ID,
    get_profile,
    list_profiles,
    register_b_profile,
    require_active_profile,
    reset_registry_for_tests,
)
from src.services.nfl_ops_v1_evidence.refuse import EvidenceGateRefuse, RefuseClass
from src.services.nfl_r7_correctness_v1.calendar import bind_rest_from_et_calendar
from src.services.nfl_r7_correctness_v1.consume_b import HANDOFF_SHA256, consume_b_handoff
from src.services.nfl_r7_correctness_v1.franchise import franchise_bind, franchise_key
from src.services.nfl_r7_correctness_v1.packets import build_synthetic_r7_demo
from src.services.nfl_r7_correctness_v1.pins import CALENDAR_ID, FW_SHA256, IF_TIP, SIM_SHA256
from src.services.nfl_t5208u.if_tree import preflight_if_tree
from src.services.nfl_t5208u.packets import RealModeRefuse

REPO = Path(__file__).resolve().parents[3]


def setup_function() -> None:
    reset_registry_for_tests()


def test_preflight_if_pins_match() -> None:
    pre = preflight_if_tree()
    assert pre["status"] == "PRESENT_PIN_MATCH"
    assert pre["sim_sha256"] == SIM_SHA256
    assert pre["fw_sha256"] == FW_SHA256
    assert pre["if_tip"] == IF_TIP


def test_et_calendar_tnf_differs_from_utc_date_delta() -> None:
    history = [
        {
            "home_team": "SD",
            "away_team": "KC",
            "kickoff_utc": "2018-10-07T17:00:00Z",
        },
        {
            "home_team": "STL",
            "away_team": "NE",
            "kickoff_utc": "2018-10-07T20:25:00Z",
        },
    ]
    rest = bind_rest_from_et_calendar(
        home_team="LAC",
        away_team="LAR",
        kickoff_utc="2018-10-12T00:20:00Z",
        history=history,
    )
    assert rest["calendar_id"] == CALENDAR_ID
    assert rest["rest_days_home"] == 4.0
    assert rest["rest_days_away"] == 4.0
    assert rest["utc_date_delta_home"] == 5
    assert rest["used_production_rest_days_from_schedule"] is False
    assert rest["kickoff_et_date"] == "2018-10-11"


def test_franchise_relocation_aliases() -> None:
    assert franchise_key("SD") == "LAC"
    assert franchise_key("STL") == "LAR"
    assert franchise_key("OAK") == "LV"
    bind = franchise_bind("LAC", "LAR")
    assert bind["franchise_key_home"] == "LAC"
    assert bind["franchise_key_away"] == "LAR"


def test_synthetic_demo_binds_et_rest_and_franchise() -> None:
    demo = build_synthetic_r7_demo()
    rest = demo["rest_calendar"]
    packet = demo["packet"]
    assert packet["real_mode_usable"] is False
    assert rest["rest_days_home"] == 4.0
    assert rest["utc_date_delta_home"] == 5
    assert packet["contract_27"]["rest_days_home"]["reconstructed_value"] == 4.0
    assert demo["franchise_bind"]["franchise_key_home"] == "LAC"


def test_real_mode_refused() -> None:
    with pytest.raises(RealModeRefuse):
        build_synthetic_r7_demo(mode="REAL")


def test_b_cannot_self_register() -> None:
    with pytest.raises(EvidenceGateRefuse) as exc:
        register_b_profile(
            PROFILE_OWNED_MARKET_TRACE,
            registered_by=WORKER_B_ID,
            handoff={"handoff_sha256": "a" * 64, "worker": "B", "profile_id": PROFILE_OWNED_MARKET_TRACE},
        )
    assert exc.value.refuse_class == RefuseClass.B_SELF_REGISTER
    assert get_profile(PROFILE_OWNED_MARKET_TRACE).status == "PENDING_HANDOFF"


def test_pending_b_profile_not_active() -> None:
    with pytest.raises(EvidenceGateRefuse) as exc:
        require_active_profile(PROFILE_SYNTHETIC_MARKET_EVENTS)
    assert exc.value.refuse_class == RefuseClass.PENDING_HANDOFF


def test_consume_b_handoff_registers_both_profiles() -> None:
    result = consume_b_handoff(root=REPO, registered_by=WORKER_A_ID)
    assert result["ok"] is True
    assert result["copied_validators"] is False
    assert result["handoff_sha256"] == HANDOFF_SHA256
    assert result["cos_accept"] == "5c86d228"
    assert result["status"][PROFILE_OWNED_MARKET_TRACE] == "REGISTERED"
    assert result["status"][PROFILE_SYNTHETIC_MARKET_EVENTS] == "REGISTERED"
    trace = get_profile(PROFILE_OWNED_MARKET_TRACE)
    events = get_profile(PROFILE_SYNTHETIC_MARKET_EVENTS)
    assert trace.schema_hash == "cd564061cb12a45b0cf813d3e23b6e1166e3fefb77d6b3525e6a997a819dfc57"
    assert trace.document_hash == "dda58e0bccc509784cb32326f679463c58db8f203c104a1d635c2ceb7f460d59"
    assert trace.fixture_sha256 == "7e412d1f701929ae963ff0d50d2ee11af93a9b928f14d770e46b310e20da9a4b"
    assert events.schema_hash == "326c18108d90ce4b2de5cbbfdb499274abe2aca37baf7a2046a91aa24e3ac021"
    assert events.document_hash == "ab6e0f4ec87a109dee07024ae186c252e6a6643b09fa9ec3538858e283341efd"
    assert events.fixture_sha256 == "37b21de21c6bb68493b87b8ac908c89f2cf0ebe03ec996d867646386957eb87f"
    assert result["join"]["joined"] is True


def test_does_not_import_production_rest_helper() -> None:
    import src.services.nfl_r7_correctness_v1.calendar as calendar
    import src.services.nfl_r7_correctness_v1.produce as produce

    assert "rest_days_from_schedule" not in calendar.__dict__
    assert "rest_days_from_schedule" not in produce.__dict__


def test_handoff_file_sha_matches_pin() -> None:
    path = REPO / "data/ops/nfl_owned_market_v1/HANDOFF_INTERFACE.json"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == HANDOFF_SHA256


def test_r7_integrated_produce_gate_pair() -> None:
    from src.services.nfl_r7_correctness_v1.run import run_r7_integrated

    receipt = run_r7_integrated(root=REPO)
    assert receipt["ok"] is True
    assert receipt["cert"] == 0
    assert receipt["ready_for_review"] is False
    assert receipt["produce"]["replay_ok"] is True
    assert receipt["produce"]["game_id"] == "SYNTHETIC_2018_W06_LAC_LAR"
    assert receipt["rest_calendar"]["rest_days_home"] == 4.0
    assert receipt["rest_calendar"]["utc_date_delta_home"] == 5
    assert receipt["pair"]["paired"] is True
    assert receipt["b_consume"]["status"][PROFILE_OWNED_MARKET_TRACE] == "REGISTERED"
    catalog = list_profiles()
    assert catalog["R7_CORRECTNESS_V1"]["status"] == "ACTIVE"
    assert catalog[PROFILE_OWNED_MARKET_TRACE]["status"] == "REGISTERED"
