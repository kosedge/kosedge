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
from src.services.nfl_ops_v1_evidence.gate import gate_before_consume
from src.services.nfl_ops_v1_evidence.spy import ForbiddenSurfaceSpy, OutcomeReadSpy
from src.services.nfl_ops_v1_evidence.validate_r7 import dest_is_actually_temp, readback_and_rehash
from src.services.nfl_r7_correctness_v1.calendar import CalendarRefuse, bind_rest_from_et_calendar
from src.services.nfl_r7_correctness_v1.consume_b import HANDOFF_SHA256, consume_b_handoff
from src.services.nfl_r7_correctness_v1.franchise import (
    franchise_bind,
    franchise_key,
    key_packet_and_history_for_q2,
)
from src.services.nfl_r7_correctness_v1.packets import build_synthetic_r7_demo
from src.services.nfl_r7_correctness_v1.pins import CALENDAR_ID, FW_SHA256, IF_TIP, OPS_REL, SIM_SHA256
from src.services.nfl_t5208u.caller import model_spy_counts, produce_q2_margin, reset_model_spy
from src.services.nfl_t5208u.if_tree import preflight_if_tree
from src.services.nfl_t5208u.packets import PacketRefuse, RealModeRefuse, history_games_for_q2

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
        physical_schedule=[
            {
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "kickoff_utc": row["kickoff_utc"],
            }
            for row in history
        ],
    )
    assert rest["calendar_id"] == CALENDAR_ID
    assert rest["rest_days_home"] == 4.0
    assert rest["rest_days_away"] == 4.0
    assert rest["utc_date_delta_home"] == 5
    assert rest["used_production_rest_days_from_schedule"] is False
    assert rest["kickoff_et_date"] == "2018-10-11"
    assert rest["predecessor_bound_to"] == "KO_MINUS_60_CUTOFF"
    assert rest["cutoff_utc"] == "2018-10-11T23:20:00Z"
    assert rest["q2_history_used_for_rest"] is False


def test_franchise_relocation_aliases() -> None:
    assert franchise_key("SD") == "LAC"
    assert franchise_key("STL") == "LAR"
    assert franchise_key("OAK") == "LV"
    assert franchise_key("WSH") == "WAS"
    assert franchise_key("WAS") == "WAS"
    assert franchise_key("LA") == "LAR"
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


def test_r7_integrated_produce_gate_pair(tmp_path: Path) -> None:
    from src.services.nfl_r7_correctness_v1.run import run_r7_integrated
    from src.services.nfl_ops_v1_evidence.verify import git_tip

    receipt = run_r7_integrated(root=REPO, dest=tmp_path / "out")
    assert receipt["ok"] is True
    assert receipt["cert"] == 0
    assert receipt["ready_for_review"] is False
    assert receipt["produce"]["replay_ok"] is True
    assert receipt["produce"]["game_id"] == "SYNTHETIC_2018_W06_LAC_LAR"
    assert receipt["rest_calendar"]["rest_days_home"] == 4.0
    assert receipt["rest_calendar"]["utc_date_delta_home"] == 5
    assert receipt["pair"]["paired"] is True
    assert receipt["exit"] == 0
    assert receipt["git_tip"] == git_tip(REPO)
    assert receipt["git_head"] == git_tip(REPO)
    assert receipt["head"] == git_tip(REPO)
    assert receipt["immutable_input_proof"]["dest_is_temp"] is True
    assert dest_is_actually_temp(receipt["immutable_input_proof"]["dest"]) is True
    assert receipt["rehashed_faults"]["refused"] is True
    assert receipt["spy_positive_control"]["spy_fired"] is True
    assert receipt["b_consume"]["status"][PROFILE_OWNED_MARKET_TRACE] == "REGISTERED"
    catalog = list_profiles()
    assert catalog["R7_CORRECTNESS_V1"]["status"] == "ACTIVE"
    assert catalog[PROFILE_OWNED_MARKET_TRACE]["status"] == "REGISTERED"


def test_keyed_q2_differs_from_raw_on_synthetic_slate() -> None:
    demo = build_synthetic_r7_demo()
    raw = produce_q2_margin(demo["packet"], demo["history"])
    keyed_packet, keyed_history = key_packet_and_history_for_q2(demo["packet"], demo["history"])
    keyed = produce_q2_margin(keyed_packet, keyed_history)
    assert raw["q2_margin"] == pytest.approx(2.4320498873107033)
    assert keyed["q2_margin"] == pytest.approx(1.93921, abs=1e-5)
    assert raw["q2_margin"] != keyed["q2_margin"]
    assert keyed_history[0]["home_team"] == "LAC"
    assert keyed_history[1]["home_team"] == "LAR"


def test_physical_same_week_sets_rest_q2_history_stays_prior() -> None:
    physical = [
        {"home_team": "LAC", "away_team": "KC", "kickoff_utc": "2018-10-12T00:20:00Z"},
        {"home_team": "LAR", "away_team": "NE", "kickoff_utc": "2018-10-12T00:20:00Z"},
    ]
    rest = bind_rest_from_et_calendar(
        home_team="LAC",
        away_team="LAR",
        kickoff_utc="2018-10-14T17:00:00Z",
        physical_schedule=physical,
    )
    assert rest["rest_days_home"] == 3.0
    assert rest["rest_days_away"] == 3.0
    assert rest["q2_history_used_for_rest"] is False
    sunday = build_synthetic_r7_demo()
    sunday_packet = sunday["packet"]
    sunday_packet = {
        **sunday_packet,
        "envelope": {
            **sunday_packet["envelope"],
            "game_id": "SYNTHETIC_2018_W06_SUN_LAC_LAR",
            "kickoff_utc": "2018-10-14T17:00:00Z",
            "week": 6,
        },
    }
    same_week_scored = {
        "channel": "SYNTHETIC",
        "game_id": "SYNTHETIC_2018_W06_TNF_LAC_KC",
        "season": 2018,
        "week": 6,
        "season_type": "REG",
        "home_team": "LAC",
        "away_team": "KC",
        "kickoff_utc": "2018-10-12T00:20:00Z",
        "home_score": 20.0,
        "away_score": 17.0,
    }
    with pytest.raises(PacketRefuse, match="same-week"):
        history_games_for_q2(sunday_packet, sunday["history"] + [same_week_scored])
    target, hist = history_games_for_q2(sunday_packet, sunday["history"])
    assert all(row.week < 6 or row.season < 2018 for row in hist)
    assert target.week == 6


def test_q2_history_cannot_set_physical_rest() -> None:
    demo = build_synthetic_r7_demo()
    with pytest.raises(CalendarRefuse, match="physical_schedule"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            physical_schedule=demo["physical_schedule"],
            history=demo["history"],
        )
    with pytest.raises(CalendarRefuse, match="non-outcome"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            physical_schedule=demo["history"],
        )


def test_calendar_predecessor_bound_to_cutoff_not_ko() -> None:
    between_cutoff_and_ko = {
        "home_team": "LAC",
        "away_team": "BUF",
        "kickoff_utc": "2018-10-11T23:30:00Z",
    }
    prior = {
        "home_team": "LAC",
        "away_team": "KC",
        "kickoff_utc": "2018-10-07T17:00:00Z",
    }
    away_prior = {
        "home_team": "LAR",
        "away_team": "NE",
        "kickoff_utc": "2018-10-07T20:25:00Z",
    }
    rest = bind_rest_from_et_calendar(
        home_team="LAC",
        away_team="LAR",
        kickoff_utc="2018-10-12T00:20:00Z",
        physical_schedule=[prior, away_prior, between_cutoff_and_ko],
    )
    assert rest["home_prev_kickoff_utc"] == "2018-10-07T17:00:00Z"
    assert rest["predecessor_bound_to"] == "KO_MINUS_60_CUTOFF"
    assert rest["cutoff_utc"] == "2018-10-11T23:20:00Z"


def test_invalid_a_refuses_before_model_zero_solver_calls() -> None:
    from src.services.nfl_r7_correctness_v1.run import run_r7_invalid_a

    reset_model_spy()
    spy = OutcomeReadSpy()
    surface = ForbiddenSurfaceSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        run_r7_invalid_a(root=REPO, outcome_spy=spy, surface=surface)
    assert exc.value.refuse_class in {RefuseClass.CHANNEL, RefuseClass.REAL_MODE}
    assert model_spy_counts() == {"produce_if_mu": 0, "asof_for_targets": 0}
    assert spy.reads == 0
    assert surface.count == 0


def test_b4_rehashed_false_refused_at_direct_api(tmp_path: Path) -> None:
    from src.services.nfl_r7_correctness_v1.run import build_r7_direct_pre_consume

    bundle = build_r7_direct_pre_consume(
        root=REPO,
        dest=tmp_path,
        rehashed={"ran": True, "refused": False, "gate_invoked": 1, "instrumentation_control": {"fired": True}},
    )
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(
            bundle["manifest"],
            chain_payload=bundle["payload"],
            root=REPO,
            command=bundle["manifest"]["command"],
            cwd=bundle["manifest"]["cwd"],
            outcome_spy=spy,
            verification=bundle["verification"],
        )
    assert exc.value.refuse_class == RefuseClass.INCOMPLETE
    assert spy.reads == 0


def test_b4_handmade_allow_refused_at_direct_api(tmp_path: Path) -> None:
    from src.services.nfl_r7_correctness_v1.run import build_r7_direct_pre_consume

    bundle = build_r7_direct_pre_consume(root=REPO, dest=tmp_path)
    bundle["manifest"]["ready_for_review"] = True
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(
            bundle["manifest"],
            chain_payload=bundle["payload"],
            root=REPO,
            command=bundle["manifest"]["command"],
            cwd=bundle["manifest"]["cwd"],
            outcome_spy=spy,
            verification=bundle["verification"],
        )
    assert exc.value.refuse_class == RefuseClass.READY_FOR_REVIEW
    assert spy.reads == 0


def test_b4_stale_refused_at_direct_api(tmp_path: Path) -> None:
    from src.services.nfl_r7_correctness_v1.run import build_r7_direct_pre_consume

    bundle = build_r7_direct_pre_consume(root=REPO, dest=tmp_path)
    bundle["manifest"]["head"] = {"kind": "git_commit", "value": "a" * 40}
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(
            bundle["manifest"],
            chain_payload=bundle["payload"],
            root=REPO,
            command=bundle["manifest"]["command"],
            cwd=bundle["manifest"]["cwd"],
            outcome_spy=spy,
            verification=bundle["verification"],
        )
    assert exc.value.refuse_class == RefuseClass.STALE
    assert spy.reads == 0


def test_b4_tamper_refused_at_direct_api(tmp_path: Path) -> None:
    from src.services.nfl_r7_correctness_v1.run import build_r7_direct_pre_consume

    bundle = build_r7_direct_pre_consume(root=REPO, dest=tmp_path)
    mutated = dict(bundle["payload"])
    mutated["channel"] = "TAMPERED"
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_consume(
            bundle["manifest"],
            chain_payload=mutated,
            root=REPO,
            command=bundle["manifest"]["command"],
            cwd=bundle["manifest"]["cwd"],
            outcome_spy=spy,
            verification=bundle["verification"],
        )
    assert exc.value.refuse_class in {RefuseClass.HASH_MUTATED, RefuseClass.CHANNEL}
    assert spy.reads == 0


def test_b4_partial_write_and_dest_lie_refused_at_direct_api(tmp_path: Path) -> None:
    from src.services.nfl_r7_correctness_v1.run import build_r7_direct_pre_consume

    partial = tmp_path / "partial.json"
    partial.write_text("{partial", encoding="utf-8")
    with pytest.raises(EvidenceGateRefuse) as exc:
        readback_and_rehash(partial, "a" * 64)
    assert exc.value.refuse_class == RefuseClass.WRITE_TAMPER

    bundle = build_r7_direct_pre_consume(root=REPO, dest=tmp_path)
    ops = REPO / OPS_REL
    bundle["manifest"]["immutable_input_proof"] = {
        "dest_is_temp": True,
        "dest": ops.as_posix(),
        "pinned_originals_unwritten": True,
    }
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc2:
        gate_before_consume(
            bundle["manifest"],
            chain_payload=bundle["payload"],
            root=REPO,
            command=bundle["manifest"]["command"],
            cwd=bundle["manifest"]["cwd"],
            outcome_spy=spy,
            verification=bundle["verification"],
        )
    assert exc2.value.refuse_class == RefuseClass.WRITE_TAMPER
    assert spy.reads == 0
