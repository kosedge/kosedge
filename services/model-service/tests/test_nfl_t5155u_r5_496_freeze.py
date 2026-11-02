"""t5155u DEV_R5_496 Phase 1 FREEZE proofs. CERT=0. No EVAL. No target scores."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.services.nfl_t5107u.cohort_enforcement import (
    FEATURE_RECON_REG496_ARTIFACT_SHA256,
    REG496_IDENTITY_SHA256,
    OutcomeReadSpy,
)
from src.services.nfl_t5107u.if_produce import SIMULATIONS, seed_for
from src.services.nfl_t5107u.last_played_cohort import WILDCARD_2020_W18
from src.services.nfl_t5107u.q2 import A_Q2, B_Q2, Game
from src.services.nfl_t5107u.r5_496_freeze import (
    CANDIDATE_WEIGHT,
    FEATURE_RECON_REG496_ARTIFACT_PATH,
    PATH_ID,
    PROFILE_FEATURE_RECON_REG496,
    R3_STOP,
    R3_WEIGHT_STOPPED,
    R5FreezeRefuse,
    TargetScoringRefuse,
    assemble_forecasts,
    compare_437_if,
    freeze_identities,
    freeze_q2_history_sources,
    load_feature_matrix,
    packets_from_matrix,
    phase2_positive_path,
    produce_if_forecasts,
    q2_margin_or_hold,
    r5_history_for_target,
    refuse_target_scoring,
    refuse_week_le_18_proxy,
    replay_ok,
    run_phase1_freeze,
    split_scaffolding,
    validate_27_inputs,
)

ROOT = Path(__file__).resolve().parents[3]


def test_identity_freeze_496_keeps_w18_refuses_wildcard():
    ident = freeze_identities(ROOT)
    assert ident["n"] == 496
    assert ident["n_by_season"] == {"2020": 240, "2021": 256}
    assert ident["identity_sha256"] == REG496_IDENTITY_SHA256
    assert ident["artifact_sha256"] == FEATURE_RECON_REG496_ARTIFACT_SHA256
    assert ident["schedule_order_first"] == "2020_02_ATL_DAL"
    assert ident["artifact_order_first"] == "2020_02_CIN_CLE"
    assert ident["week_le_18_proxy"] is False
    assert len(ident["reg_week18_2021_retained"]) == 16
    assert ident["wildcard_2020_refused"] == list(WILDCARD_2020_W18)
    assert not (set(WILDCARD_2020_W18) & set(ident["game_ids"]))
    assert ident["eval"] is None
    assert ident["scoring"] is None
    assert ident["labels"] == ["RECONSTRUCTED", "RETRO_FIT"]


def test_split_scaffolding_full496_old437_new59():
    ident = freeze_identities(ROOT)
    from src.services.nfl_t5107u.cohort_enforcement import (
        PROFILE_DEV_IF437,
        expected_profile_ids,
    )

    splits = split_scaffolding(ident["game_ids"], expected_profile_ids(PROFILE_DEV_IF437, ROOT))
    assert splits["full496"]["n"] == 496
    assert splits["old437"]["n"] == 437
    assert splits["new59"]["n"] == 59
    assert splits["from_outcomes"] is False
    assert splits["from_frozen_identities"] is True
    assert set(splits["old437"]["game_ids"]).issubset(set(splits["full496"]["game_ids"]))
    assert not (set(splits["new59"]["game_ids"]) & set(splits["old437"]["game_ids"]))
    assert set(splits["full496"]["game_ids"]) == set(splits["old437"]["game_ids"]) | set(
        splits["new59"]["game_ids"]
    )


def test_validate_all_27_inputs_on_frozen_matrix():
    ident = freeze_identities(ROOT)
    artifact = __import__("json").loads(
        (ROOT / FEATURE_RECON_REG496_ARTIFACT_PATH).read_text(encoding="utf-8")
    )
    rows = load_feature_matrix(ROOT)
    result = validate_27_inputs(
        rows,
        expected_ids=ident["artifact_game_ids"],
        identities=artifact["identities"],
    )
    assert result["n_complete_27"] == 496
    assert result["n_partial"] == 0
    assert result["n_fails"] == 0
    packets = packets_from_matrix(rows)
    assert len(packets) == 496
    first = packets["2020_02_CIN_CLE"]
    assert first["game_id"]["status"] == "DERIVED_PREGAME"
    assert first["game_id"]["label"] == "RECONSTRUCTED"
    assert first["game_id"]["fit_label"] == "RETRO_FIT"
    assert first["rest_days_home"]["source_sha256"]


def test_q2_hold_when_earlier_year_reg_unproven():
    hist = freeze_q2_history_sources(ROOT)
    assert hist["hold_q2"] is True
    assert hist["q2_leg"] == "HOLD"
    assert hist["week_le_18_proxy"] is False
    assert hist["invented_history"] is False
    assert hist["a_q2"] == A_Q2
    assert hist["b_q2"] == B_Q2
    assert hist["ridge"] == 20.0
    assert hist["prior_reg"] == 0.5
    assert hist["refit"] is False
    assert "2013" in hist["hold_reason"]
    assert hist["reg_membership"]["2013"]["reg_membership"] == "UNPROVEN"
    assert hist["reg_membership"]["2020"]["status"] == "PROVEN"
    assert hist["reg_membership"]["2021"]["status"] == "PROVEN"
    assert hist["history_rule"]["disclose_not_old_kickoff_only_asof"] is True
    target = Game(
        season=2020,
        week=2,
        game_id="2020_02_CIN_CLE",
        home="CLE",
        away="CIN",
        kickoff_utc=datetime(2020, 9, 18, 0, 20, tzinfo=timezone.utc),
    )
    held = q2_margin_or_hold(target, [], history_freeze=hist)
    assert held["q2_status"] == "HOLD"
    assert held["m_q2"] is None
    assert held["history_ids"] == []


def test_week_le_18_proxy_refused():
    with pytest.raises(R5FreezeRefuse, match="week<=18"):
        refuse_week_le_18_proxy(claimed_reg=True, used_week_le_18=True)


def test_r5_history_excludes_same_week_own_target_later_and_ko60():
    target = Game(
        season=2020,
        week=3,
        game_id="2020_03_AAA_BBB",
        home="BBB",
        away="AAA",
        kickoff_utc=datetime(2020, 9, 27, 17, 0, tzinfo=timezone.utc),
    )
    same_week_earlier_ko = Game(
        season=2020,
        week=3,
        game_id="2020_03_CCC_DDD",
        home="DDD",
        away="CCC",
        kickoff_utc=datetime(2020, 9, 27, 14, 0, tzinfo=timezone.utc),
        home_score=20,
        away_score=10,
    )
    own = Game(
        season=2020,
        week=3,
        game_id="2020_03_AAA_BBB",
        home="BBB",
        away="AAA",
        kickoff_utc=datetime(2020, 9, 27, 17, 0, tzinfo=timezone.utc),
        home_score=1,
        away_score=0,
    )
    later = Game(
        season=2020,
        week=4,
        game_id="2020_04_EEE_FFF",
        home="FFF",
        away="EEE",
        kickoff_utc=datetime(2020, 10, 4, 17, 0, tzinfo=timezone.utc),
        home_score=3,
        away_score=0,
    )
    inside_60 = Game(
        season=2020,
        week=2,
        game_id="2020_02_INSIDE_KO",
        home="KO",
        away="IN",
        kickoff_utc=datetime(2020, 9, 27, 16, 30, tzinfo=timezone.utc),
        home_score=7,
        away_score=0,
    )
    prior_week = Game(
        season=2020,
        week=2,
        game_id="2020_02_GGG_HHH",
        home="HHH",
        away="GGG",
        kickoff_utc=datetime(2020, 9, 20, 17, 0, tzinfo=timezone.utc),
        home_score=14,
        away_score=7,
    )
    prior_year = Game(
        season=2019,
        week=17,
        game_id="2019_17_III_JJJ",
        home="JJJ",
        away="III",
        kickoff_utc=datetime(2019, 12, 29, 18, 0, tzinfo=timezone.utc),
        home_score=21,
        away_score=10,
    )
    allowed = r5_history_for_target(
        [same_week_earlier_ko, own, later, inside_60, prior_week, prior_year],
        target,
        proven_reg_ids=["2020_02_GGG_HHH", "2020_02_INSIDE_KO", "2020_03_CCC_DDD"],
        proven_reg_years=(2020,),
    )
    assert [g.game_id for g in allowed] == ["2020_02_GGG_HHH"]


def test_candidate_is_half_if_half_q2_r3_075_stopped():
    assert CANDIDATE_WEIGHT == 0.5
    assert R3_WEIGHT_STOPPED == 0.75
    assert R3_STOP == "81b6c0fc"
    from src.services.nfl_t5107u.builder import challenger_margin

    assert challenger_margin(10.0, -4.0) == 3.0
    with pytest.raises(Exception, match="0.5|weight"):
        challenger_margin(10.0, -4.0, w=0.75)


def test_replay_tolerance_and_blocker():
    assert replay_ok(2.0, 2.0)
    assert replay_ok(2.0 + 1e-12, 2.0)
    assert not replay_ok(2.0 + 1e-6, 2.0)
    forecasts = [
        {
            "game_id": "2020_02_CIN_CLE",
            "m_if": 1.0,
            "seed": seed_for("2020_02_CIN_CLE"),
        }
    ]
    old = {
        "forecasts": [
            {"game_id": "2020_02_CIN_CLE", "m_if": 1.0},
        ]
    }
    ok = compare_437_if(
        forecasts,
        old,
        input_compare={"identical_game_ids": ["2020_02_CIN_CLE"], "discrepancies": []},
    )
    assert ok["n_replayed_within_tol"] == 1
    assert ok["n_blocker"] == 0
    with pytest.raises(R5FreezeRefuse, match="IF replay BLOCKER"):
        compare_437_if(
            [{"game_id": "2020_02_CIN_CLE", "m_if": 9.0, "seed": seed_for("2020_02_CIN_CLE")}],
            old,
            input_compare={"identical_game_ids": ["2020_02_CIN_CLE"], "discrepancies": []},
        )


def test_scoring_refuse_spy_zero_target_labels():
    ident = freeze_identities(ROOT)
    spy = OutcomeReadSpy(lambda: {"2020_02_ATL_DAL": {"home_score": 40, "away_score": 0}})
    result = refuse_target_scoring(
        candidate_ids=ident["game_ids"],
        root=ROOT,
        outcome_loader=spy,
        coverage_blocked=True,
    )
    assert result["refused"] is True
    assert result["outcome_loader_reads"] == 0
    assert result["target_labels_loaded"] == 0
    assert spy.reads == 0
    assert spy.ids_returned == []
    assert result["stop"] == "AWAITING_ALEX_PREFLIGHT_AND_COS_BIND"


def test_phase2_path_documented_not_executed():
    path = phase2_positive_path()
    assert path["executed"] is False
    assert path["phase"] == 2
    assert any("Alex" in step or "Alex" in req for req in path["requires"] for step in [req])
    assert path["scoring"] is None


def _fake_produce(packet):
    gid = str(packet["game_id"]["reconstructed_value"])
    return {
        "game_id": gid,
        "if_margin_mu": 1.25,
        "seed": seed_for(gid),
        "simulations": SIMULATIONS,
        "if_tip": "6ca03716fe52930332d5ffba302c312a651980cc",
        "source": "reconstructed_if_produce",
    }


def test_stubbed_phase1_holds_q2_finishes_if_no_scores(tmp_path: Path):
    bundle = run_phase1_freeze(
        root=ROOT,
        produce=_fake_produce,
        write=False,
        compare_old_if=False,
    )
    forecasts = bundle["FORECASTS_DEV_R5_496"]
    assert forecasts["n_forecasts"] == 496
    assert forecasts["n_if_finite"] == 496
    assert forecasts["n_q2_hold"] == 496
    assert forecasts["n_candidate_finite"] == 0
    assert forecasts["path_id"] == PATH_ID
    assert forecasts["eval"] is None
    assert forecasts["scoring"] is None
    blob = __import__("json").dumps(forecasts)
    assert "home_score" not in blob
    assert "actual_margin" not in blob
    assert bundle["SCORING_REFUSE"]["outcome_loader_reads"] == 0
    assert bundle["Q2_HISTORY_FREEZE"]["hold_q2"] is True
    one = forecasts["forecasts"][0]
    assert one["seed"] == seed_for(one["game_id"])
    assert one["m_if"] == 1.25
    assert one["m_q2"] is None
    assert one["m_candidate"] is None


def test_committed_freeze_hashes_stable():
    manifest = __import__("json").loads(
        (ROOT / "data/ops/nfl-t5155u-r5-496-freeze/FREEZE_MANIFEST.json").read_text(
            encoding="utf-8"
        )
    )
    from src.services.nfl_t5107u.recon_driver import sha256_file

    assert manifest["n_forecasts"] == 496
    assert manifest["n_if_finite"] == 496
    assert manifest["n_q2_hold"] == 496
    assert manifest["n_candidate_finite"] == 0
    assert manifest["stop"] == "AWAITING_ALEX_PREFLIGHT_AND_COS_BIND"
    for name, digest in manifest["files"].items():
        path = ROOT / "data/ops/nfl-t5155u-r5-496-freeze" / f"{name}.json"
        assert sha256_file(path) == digest, name


def test_produce_one_real_if_packet():
    rows = load_feature_matrix(ROOT)
    packets = packets_from_matrix(rows)
    gid = "2020_02_CIN_CLE"
    produced = produce_if_forecasts(
        {gid: packets[gid]},
        [
            {
                "game_id": gid,
                "season": 2020,
                "week": 2,
                "home": "CLE",
                "away": "CIN",
                "kickoff_utc": "2020-09-18T00:20:00Z",
            }
        ],
    )
    assert produced[gid]["simulations"] == 4000
    assert produced[gid]["seed"] == seed_for(gid)
    assert isinstance(produced[gid]["if_margin_mu"], float)
    assembled = assemble_forecasts(
        [
            {
                "game_id": gid,
                "season": 2020,
                "week": 2,
                "home": "CLE",
                "away": "CIN",
                "kickoff_utc": "2020-09-18T00:20:00Z",
            }
        ],
        if_rows=produced,
        q2_rows={
            gid: {
                "m_q2": None,
                "q2_status": "HOLD",
                "hold_reason": "test",
                "history_ids": [],
                "n_history": 0,
            }
        },
        history_freeze={"hold_q2": True, "hold_reason": "test", "history_rule": {}},
        code_hashes={},
    )
    assert assembled["n_if_finite"] == 1
    assert assembled["n_q2_hold"] == 1
    assert assembled["forecasts"][0]["m_candidate"] is None
