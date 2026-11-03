"""t5289u R7_CORRECTNESS_V1 tests. CERT=0. SYNTHETIC only."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
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
from src.services.nfl_r7_correctness_v1.calendar import CalendarHold, CalendarRefuse, bind_rest_from_et_calendar
from src.services.nfl_r7_correctness_v1.consume_b import HANDOFF_SHA256, consume_b_handoff
from src.services.nfl_r7_correctness_v1.franchise import (
    FranchiseRefuse,
    canonical_carry_prior,
    franchise_bind,
    franchise_key,
    key_packet_and_history_for_q2,
)
from src.services.nfl_r7_correctness_v1.q2_canonical import produce_q2_margin_canonical
from src.services.nfl_r7_correctness_v1.packets import (
    R7PacketRefuse,
    build_synthetic_r7_demo,
    build_typed_synthetic_input,
    require_typed_synthetic_input,
)
from src.services.nfl_r7_correctness_v1.pins import CALENDAR_ID, FW_SHA256, IF_TIP, OPS_REL, SIM_SHA256
from src.services.nfl_r7_correctness_v1.produce import (
    NUMERICAL_ENV_PREFIXES,
    R7ProduceRefuse,
    ambient_numerical_env_hits,
    consume_effective_config,
    produce_r7_point_margin,
    refuse_ambient_numerical_env,
)
from src.services.nfl_t5208u.caller import model_spy_counts, produce_q2_margin, reset_model_spy
from src.services.nfl_t5208u.if_tree import preflight_if_tree
from src.services.nfl_t5208u.packets import PacketRefuse, RealModeRefuse, history_games_for_q2

REPO = Path(__file__).resolve().parents[3]


def _stamp(kickoff_utc: str, *, hours: int) -> str:
    text = kickoff_utc[:-1] + "+00:00" if kickoff_utc.endswith("Z") else kickoff_utc
    dt = datetime.fromisoformat(text).astimezone(timezone.utc)
    return (dt + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _phys(
    home: str,
    away: str,
    kickoff_utc: str,
    *,
    season: int = 2018,
    week: int = 5,
    game_id: str | None = None,
    **extra: object,
) -> dict:
    row = {
        "game_id": game_id or f"SYNTHETIC_{home}_{away}_{kickoff_utc}",
        "season": season,
        "week": week,
        "season_type": "REG",
        "home_team": home,
        "away_team": away,
        "kickoff_utc": kickoff_utc,
        "actual_kickoff_utc": kickoff_utc,
        "scheduled_kickoff_utc": kickoff_utc,
        "status": "PLAYED",
        "kickoff_kind": "ACTUAL_KICKOFF",
        "source": "SYNTHETIC_PHYSICAL_SCHEDULE_t5289u",
        "available_at": _stamp(kickoff_utc, hours=4),
        "observed_at": _stamp(kickoff_utc, hours=5),
    }
    row.update(extra)
    return row


def setup_function() -> None:
    reset_registry_for_tests()


def test_preflight_if_pins_match() -> None:
    pre = preflight_if_tree()
    assert pre["status"] == "PRESENT_PIN_MATCH"
    assert pre["sim_sha256"] == SIM_SHA256
    assert pre["fw_sha256"] == FW_SHA256
    assert pre["if_tip"] == IF_TIP


def test_et_calendar_tnf_differs_from_utc_date_delta() -> None:
    rest = bind_rest_from_et_calendar(
        home_team="LAC",
        away_team="LAR",
        kickoff_utc="2018-10-12T00:20:00Z",
        target_season=2018,
        physical_schedule=[
            _phys("SD", "KC", "2018-10-07T17:00:00Z", week=5, game_id="SYNTHETIC_2018_W05_SD_KC"),
            _phys("STL", "NE", "2018-10-07T20:25:00Z", week=5, game_id="SYNTHETIC_2018_W05_STL_NE"),
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
    assert rest["home_prev_availability"] == "BEFORE_SEAL"
    assert rest["home_prev_available_at"] < rest["cutoff_utc"]


def test_franchise_relocation_aliases() -> None:
    assert franchise_key("SD") == "LAC"
    assert franchise_key("STL") == "LAR"
    assert franchise_key("OAK") == "LV"
    assert franchise_key("WSH") == "WAS"
    assert franchise_key("WAS") == "WAS"
    assert franchise_key("LA", source="RAMS") == "LAR"
    assert franchise_key("LA", source="CHARGERS") == "LAC"
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
    assert receipt["exit_source"] == "SUBPROCESS_RETURNCODE"
    assert receipt["log_source"] == "SUBPROCESS_STDOUT"
    assert receipt["log_hash"]
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
    keyed = produce_q2_margin_canonical(keyed_packet, keyed_history)
    assert raw["q2_margin"] == pytest.approx(2.4320498873107033)
    assert keyed["q2_margin"] == pytest.approx(1.93920745003233)
    assert raw["q2_margin"] != keyed["q2_margin"]
    assert keyed_history[0]["home_team"] == "LAC"
    assert keyed_history[1]["home_team"] == "LAR"


def test_physical_same_week_sets_rest_q2_history_stays_prior() -> None:
    physical = [
        _phys("LAC", "KC", "2018-10-12T00:20:00Z", week=6, game_id="SYNTHETIC_2018_W06_TNF_LAC_KC"),
        _phys("LAR", "NE", "2018-10-12T00:20:00Z", week=6, game_id="SYNTHETIC_2018_W06_TNF_LAR_NE"),
    ]
    rest = bind_rest_from_et_calendar(
        home_team="LAC",
        away_team="LAR",
        kickoff_utc="2018-10-14T17:00:00Z",
        target_season=2018,
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
            target_season=2018,
            physical_schedule=demo["physical_schedule"],
            history=demo["history"],
        )
    with pytest.raises(CalendarRefuse, match="non-outcome"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            target_season=2018,
            physical_schedule=demo["history"],
        )


def test_calendar_predecessor_bound_to_cutoff_not_ko() -> None:
    between_cutoff_and_ko = _phys(
        "LAC", "BUF", "2018-10-11T23:30:00Z", week=6, game_id="SYNTHETIC_BETWEEN_CUTOFF_KO"
    )
    prior = _phys("LAC", "KC", "2018-10-07T17:00:00Z", week=5, game_id="SYNTHETIC_2018_W05_LAC_KC")
    away_prior = _phys("LAR", "NE", "2018-10-07T20:25:00Z", week=5, game_id="SYNTHETIC_2018_W05_LAR_NE")
    rest = bind_rest_from_et_calendar(
        home_team="LAC",
        away_team="LAR",
        kickoff_utc="2018-10-12T00:20:00Z",
        target_season=2018,
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


def test_b2_exit_not_literal_zero_in_runner() -> None:
    text = (
        REPO / "services/model-service/src/services/nfl_r7_correctness_v1/run.py"
    ).read_text(encoding="utf-8")
    assert "exit_code = 0" not in text
    assert "EXIT_SOURCE = \"SUBPROCESS_RETURNCODE\"" in text


def test_b2_exit_mismatch_refused_at_direct_api(tmp_path: Path) -> None:
    from dataclasses import replace

    from src.services.nfl_ops_v1_evidence.gate import gate_before_final_receipt
    from src.services.nfl_ops_v1_evidence.hashes import sha256_text
    from src.services.nfl_ops_v1_evidence.validate import utc_now
    from src.services.nfl_r7_correctness_v1.run import build_r7_direct_pre_consume
    from src.services.nfl_t5208u.hashing import sha256_file

    dest = tmp_path / "gate"
    dest.mkdir()
    out = dest / "demo_result.json"
    out.write_text("{}\n", encoding="utf-8")
    bundle = build_r7_direct_pre_consume(root=REPO, dest=dest)
    log_text = "observed-stdout\n"
    manifest = bundle["manifest"]
    manifest["exit"] = 0
    manifest["end_utc"] = utc_now()
    manifest["log_hash"] = sha256_text(log_text)
    manifest["output_paths"] = [out.as_posix()]
    manifest["output_hashes"] = {out.as_posix(): sha256_file(out)}
    manifest["failures"] = []
    manifest["numerical_output"] = {
        "n": 1,
        "game_id": "SYNTHETIC_2018_W06_LAC_LAR",
        "if_margin": 1.0,
        "q2_margin": 1.0,
        "c_margin": 1.0,
    }
    trace = dict(manifest["producer_consumer_trace"])
    trace["consumer_digest"] = trace["producer_digest"]
    manifest["producer_consumer_trace"] = trace
    ctx = replace(
        bundle["verification"],
        actual_exit=1,
        log_bytes=log_text.encode("utf-8"),
        output_bytes={out.as_posix(): out.read_bytes()},
    )
    spy = OutcomeReadSpy()
    with pytest.raises(EvidenceGateRefuse) as exc:
        gate_before_final_receipt(
            manifest,
            chain_payload=bundle["payload"],
            root=REPO,
            command=manifest["command"],
            cwd=manifest["cwd"],
            exit_code=1,
            output_paths=[out],
            log_text=log_text,
            outcome_spy=spy,
            verification=ctx,
        )
    assert exc.value.refuse_class == RefuseClass.EXIT
    assert spy.reads == 0


def test_unknown_franchise_token_refused() -> None:
    with pytest.raises(FranchiseRefuse, match="unknown franchise token"):
        franchise_key("XYZ")


def test_source_unqualified_la_refused() -> None:
    with pytest.raises(FranchiseRefuse, match="source-unqualified LA"):
        franchise_key("LA")
    with pytest.raises(FranchiseRefuse, match="source-unqualified LA"):
        franchise_key("LA", source="NFL")


def test_canonical_carry_prior_one_slot_refuses_legacy_duplicate() -> None:
    out = canonical_carry_prior({"LAC": 2.0, "LAR": 4.0})
    assert set(out) == {"LAC", "LAR"}
    assert "SD" not in out and "STL" not in out
    with pytest.raises(FranchiseRefuse, match="duplicate legacy-slot"):
        canonical_carry_prior({"SD": 1.0, "LAC": 1.0})


def test_calendar_same_season_excludes_prior_season_rows() -> None:
    rest = bind_rest_from_et_calendar(
        home_team="LAC",
        away_team="LAR",
        kickoff_utc="2018-10-12T00:20:00Z",
        target_season=2018,
        physical_schedule=[
            _phys("SD", "BUF", "2017-10-29T17:00:00Z", season=2017, week=8, game_id="SYNTHETIC_2017_W08_NE_SD"),
            _phys("STL", "MIA", "2017-11-26T18:00:00Z", season=2017, week=12, game_id="SYNTHETIC_2017_W12_MIA_STL"),
            _phys("SD", "KC", "2018-10-07T17:00:00Z", week=5, game_id="SYNTHETIC_2018_W05_SD_KC"),
            _phys("STL", "NE", "2018-10-07T20:25:00Z", week=5, game_id="SYNTHETIC_2018_W05_STL_NE"),
        ],
    )
    assert rest["rest_days_home"] == 4.0
    assert rest["rest_days_away"] == 4.0
    assert rest["home_prev_game_id"] == "SYNTHETIC_2018_W05_SD_KC"
    assert rest["home_prev_status"] == "PLAYED"
    assert rest["home_prev_kickoff_kind"] == "ACTUAL_KICKOFF"
    assert rest["actual_versus_scheduled_proof"] is True


def test_calendar_refuses_unsupported_and_ambiguous_predecessors() -> None:
    priors = [
        _phys("SD", "KC", "2018-10-07T17:00:00Z", week=5, game_id="SYNTHETIC_2018_W05_SD_KC"),
        _phys("STL", "NE", "2018-10-07T20:25:00Z", week=5, game_id="SYNTHETIC_2018_W05_STL_NE"),
    ]
    with pytest.raises(CalendarRefuse, match="REG required"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            target_season=2018,
            physical_schedule=priors + [
                _phys("LAC", "BUF", "2018-10-08T17:00:00Z", week=5, season_type="POST", game_id="SYNTHETIC_POST")
            ],
        )
    with pytest.raises(CalendarRefuse, match="not PLAYED"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            target_season=2018,
            physical_schedule=priors + [
                _phys("LAC", "BUF", "2018-10-08T17:00:00Z", week=5, status="SCHEDULED", game_id="SYNTHETIC_SCHED")
            ],
        )
    with pytest.raises(CalendarRefuse, match="missing"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            target_season=2018,
            physical_schedule=priors + [
                _phys("LAC", "BUF", "2018-10-08T17:00:00Z", week=5, source="", game_id="SYNTHETIC_NOSRC")
            ],
        )
    with pytest.raises(CalendarRefuse, match="duplicate-identity"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            target_season=2018,
            physical_schedule=priors + [
                _phys("LAC", "BUF", "2018-10-08T17:00:00Z", week=5, game_id="SYNTHETIC_2018_W05_SD_KC")
            ],
        )
    with pytest.raises(CalendarRefuse, match="ambiguous predecessor"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            target_season=2018,
            physical_schedule=priors + [
                _phys("LAC", "BUF", "2018-10-07T17:00:00Z", week=5, game_id="SYNTHETIC_DUP_TIME")
            ],
        )


def test_calendar_source_availability_unknown_is_hold() -> None:
    priors = [
        _phys("SD", "KC", "2018-10-07T17:00:00Z", week=5, game_id="SYNTHETIC_2018_W05_SD_KC"),
        _phys("STL", "NE", "2018-10-07T20:25:00Z", week=5, game_id="SYNTHETIC_2018_W05_STL_NE"),
    ]
    with pytest.raises(CalendarHold, match="source-availability HOLD"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            target_season=2018,
            physical_schedule=[
                {**priors[0], "available_at": "unknown", "observed_at": "unknown"},
                priors[1],
            ],
        )
    with pytest.raises(CalendarHold, match="not strictly before seal"):
        bind_rest_from_et_calendar(
            home_team="LAC",
            away_team="LAR",
            kickoff_utc="2018-10-12T00:20:00Z",
            target_season=2018,
            physical_schedule=[
                {**priors[0], "available_at": "2018-10-11T23:20:00Z", "observed_at": "2018-10-11T23:20:00Z"},
                priors[1],
            ],
        )


def test_consumed_effective_config_bound_and_ambient_env_refused() -> None:
    cfg = consume_effective_config()
    assert cfg["meta"]["consumed"] is True
    assert cfg["meta"]["ambient_env_reread"] is False
    assert cfg["simulator"]["simulations"] == 4000
    assert cfg["simulator"]["market_blend"] == 0
    assert cfg["helper"]["c_formula"] == "C=0.5*IF+0.5*Q2"
    assert cfg["helper"]["candidate_weight"] == 0.5
    assert cfg["framework"]["settings"]["prior_total_points"] == 45.3
    assert cfg["simulator"]["settings"]["pass_rate_weight"] == 3.2
    assert NUMERICAL_ENV_PREFIXES == ("NFL_FRAMEWORK_", "NFL_TOTALS_")
    hits = ambient_numerical_env_hits(
        (
            "PATH",
            "NFL_FRAMEWORK_PRIOR_TOTAL_POINTS",
            "NFL_TOTALS_PASS_RATE_WEIGHT",
            "HOME",
            "SIMULATIONS",
        )
    )
    assert hits == (
        "NFL_FRAMEWORK_PRIOR_TOTAL_POINTS",
        "NFL_TOTALS_PASS_RATE_WEIGHT",
        "SIMULATIONS",
    )
    with pytest.raises(R7ProduceRefuse, match="ambient numerical env"):
        refuse_ambient_numerical_env(("NFL_FRAMEWORK_HOME_FIELD_POINTS",))
    with pytest.raises(R7ProduceRefuse, match="ambient numerical env"):
        refuse_ambient_numerical_env(("NFL_TOTALS_MAX_ADJUSTMENT_POINTS",))
    caller_src = (
        REPO / "services/model-service/src/services/nfl_t5208u/caller.py"
    ).read_text(encoding="utf-8")
    assert "effective_config" in caller_src
    assert "os.getenv" not in caller_src
    assert "os.environ" not in caller_src
    franchise_src = (
        REPO / "services/model-service/src/services/nfl_r7_correctness_v1/franchise.py"
    ).read_text(encoding="utf-8")
    assert "canonical_q2_carry" not in franchise_src
    assert "q2_mod.carry_prior" not in franchise_src


def test_generic_typed_synthetic_input_caller_allows_et_eq_utc() -> None:
    sunday = build_typed_synthetic_input(
        envelope={
            "game_id": "SYNTHETIC_2018_W06_SUN_LAC_LAR",
            "season": 2018,
            "week": 6,
            "season_type": "REG",
            "home_team": "LAC",
            "away_team": "LAR",
            "kickoff_utc": "2018-10-14T17:00:00Z",
            "venue_id": "SYNTHETIC_VENUE_SUN",
            "identity_kind": "SYNTHETIC_REG",
        },
        physical_schedule=[
            _phys("SD", "KC", "2018-10-07T17:00:00Z", week=5, game_id="SYNTHETIC_2018_W05_SD_KC"),
            _phys("STL", "NE", "2018-10-07T20:25:00Z", week=5, game_id="SYNTHETIC_2018_W05_STL_NE"),
        ],
    )
    rest = sunday["rest_calendar"]
    assert rest["rest_days_home"] == rest["utc_date_delta_home"]
    produced = produce_r7_point_margin(synthetic_input=sunday)
    assert produced["game_id"] == "SYNTHETIC_2018_W06_SUN_LAC_LAR"
    assert produced["effective_config"]["meta"]["consumed"] is True
    assert produced["q2_canonical_state_slots"] is True
    assert produced["c_formula"] == "C=0.5*IF+0.5*Q2"
    assert produced["r6_point_margin"]["effective_config_bound"] is True
    assert produced["r6_point_margin"]["simulations"] == 4000
    assert produced["r6_point_margin"]["q2"].get("parameter_label")
    with pytest.raises(R7PacketRefuse, match="missing"):
        require_typed_synthetic_input({"packet": sunday["packet"]})
