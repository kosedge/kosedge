"""t5157u R5-HISTORY-ID proofs. CERT=0. No EVAL. No Phase2 score."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.services.nfl_t5107u.builder import challenger_margin
from src.services.nfl_t5107u.cohort_enforcement import (
    DEV_IF437_IDENTITY_SHA256,
    REG496_IDENTITY_SHA256,
)
from src.services.nfl_t5107u.market_arm_freeze import (
    INTERSECTION_BYTES_SHA256,
    INTERSECTION_IDENTITY_SHA256,
)
from src.services.nfl_t5107u.q2 import A_Q2, B_Q2, Game
from src.services.nfl_t5107u.r5_496_freeze import (
    CANDIDATE_WEIGHT,
    R3_STOP,
    R5FreezeRefuse,
    r5_history_for_target,
    refuse_week_le_18_proxy,
)
from src.services.nfl_t5107u.r5_history_id import (
    COS_ORDER_A,
    HOLD_DIR,
    IDENTITY_COLS,
    IF_FORECASTS_SHA256,
    OUT_DIR,
    R5_HISTORY_ID,
    TargetScoringRefuse,
    existing_alias_closure,
    join_identities,
    parse_manifest_sha256,
    project_identities_from_pbp,
    refuse_phase2_score,
    refuse_target_scoring,
    snapshot_hold_hashes,
    teams_alias_match,
    verify_pbp_file_shas,
)

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / OUT_DIR


def test_existing_team_map_composes_without_invention():
    assert teams_alias_match("LA", "LAR")
    assert teams_alias_match("LA", "STL")
    assert teams_alias_match("WAS", "WSH")
    assert teams_alias_match("LV", "OAK")
    assert teams_alias_match("SD", "LAC")
    assert not teams_alias_match("KC", "NE")
    assert "LAR" in existing_alias_closure("STL")
    assert "WSH" in existing_alias_closure("WAS")


def test_week_le_18_proxy_refused():
    with pytest.raises(R5FreezeRefuse, match="week<=18"):
        refuse_week_le_18_proxy(claimed_reg=True, used_week_le_18=True)


def test_forbidden_2020_26_pbp_refused(tmp_path: Path):
    with pytest.raises(Exception, match="2020–26|2013–2019"):
        verify_pbp_file_shas(tmp_path, years=(2024, 2025, 2026))


def test_identity_projection_fixture_dedup_and_explicit_type(tmp_path: Path):
    header = ",".join(IDENTITY_COLS) + ",epa,play_type,home_score\n"
    rows = [
        "2013_01_ARI_STL,2013090810,2013,REG,LA,ARI,1,2013-09-08,t1,0.1,pass,27\n",
        "2013_01_ARI_STL,2013090810,2013,REG,LA,ARI,1,2013-09-08,t1,0.2,run,27\n",
        "2013_18_KC_IND,2014010411,2013,POST,IND,KC,18,2014-01-04,t2,0.0,pass,45\n",
    ]
    (tmp_path / "play_by_play_2013.csv").write_text(header + "".join(rows), encoding="utf-8")
    file_shas = {"files": {"2013": {"sha256": "fixture"}}}
    out = project_identities_from_pbp(tmp_path, years=(2013,), file_shas=file_shas)
    assert out["n_games"] == 2
    assert out["n_reg"] == 1
    assert out["n_post"] == 1
    assert out["week_le_18_proxy"] is False
    assert out["play_values_used"] is False
    assert out["games"][0]["game_id"] == "2013_01_ARI_STL"
    assert set(out["games"][0]) == set(IDENTITY_COLS)
    assert "epa" not in json.dumps(out["games"])


def test_identity_refuses_invented_season_type(tmp_path: Path):
    header = ",".join(IDENTITY_COLS) + "\n"
    (tmp_path / "play_by_play_2013.csv").write_text(
        header + "2013_01_AAA_BBB,1,2013,,AAA,BBB,1,2013-09-08,t\n",
        encoding="utf-8",
    )
    with pytest.raises(Exception, match="invented season_type|not explicit"):
        project_identities_from_pbp(
            tmp_path,
            years=(2013,),
            file_shas={"files": {"2013": {"sha256": "x"}}},
        )


def test_join_bijective_and_unmatched_examples():
    identities = [
        {
            "game_id": "2013_01_ARI_STL",
            "season": "2013",
            "week": "1",
            "season_type": "REG",
            "home_team": "LA",
            "away_team": "ARI",
        },
        {
            "game_id": "2013_18_KC_IND",
            "season": "2013",
            "week": "18",
            "season_type": "POST",
            "home_team": "IND",
            "away_team": "KC",
        },
    ]
    games = [
        {
            "game_id": "2013_01_ARI_STL",
            "season": "2013",
            "week": "1",
            "home": "STL",
            "away": "ARI",
            "kickoff_utc": "2013-09-08T17:00:00Z",
        },
        {
            "game_id": "2013_18_KC_IND",
            "season": "2013",
            "week": "18",
            "home": "IND",
            "away": "KC",
            "kickoff_utc": "2014-01-04T21:00:00Z",
        },
    ]
    outcomes = [
        {
            "season": "2013",
            "week": "1",
            "home": "STL",
            "away": "ARI",
            "home_score": "27",
            "away_score": "24",
        },
        {
            "season": "2013",
            "week": "18",
            "home": "IND",
            "away": "KC",
            "home_score": "45",
            "away_score": "44",
        },
    ]
    joined = join_identities(
        identities,
        games,
        outcomes,
        identity_source="fixture",
        require_complete_season=True,
    )
    assert joined["n_reg"] == 1
    assert joined["n_post"] == 1
    assert joined["n_unmatched"] == 0
    assert joined["n_conflict"] == 0
    assert joined["n_post_week_le_18"] == 1
    assert joined["reg_rows"][0]["home"] == "STL"
    assert joined["reg_rows"][0]["join"] == "canonical_game_id"

    missing = join_identities(
        identities,
        games[:1],
        outcomes[:1],
        identity_source="fixture",
    )
    assert missing["n_unmatched"] == 1
    assert missing["unmatched_examples"][0]["game_id"] == "2013_18_KC_IND"


def test_r5_history_rule_unchanged_excludes_same_week_own_later_ko60():
    target = Game(
        season=2020,
        week=3,
        game_id="2020_03_AAA_BBB",
        home="BBB",
        away="AAA",
        kickoff_utc=datetime(2020, 9, 27, 17, 0, tzinfo=timezone.utc),
    )
    same_week = Game(
        season=2020,
        week=3,
        game_id="2020_03_CCC_DDD",
        home="DDD",
        away="CCC",
        kickoff_utc=datetime(2020, 9, 27, 14, 0, tzinfo=timezone.utc),
        home_score=20,
        away_score=10,
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
        [same_week, prior_week, prior_year],
        target,
        proven_reg_ids=["2020_02_GGG_HHH", "2019_17_III_JJJ"],
        proven_reg_years=(2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021),
    )
    assert [g.game_id for g in allowed] == ["2019_17_III_JJJ", "2020_02_GGG_HHH"]


def test_candidate_half_if_half_q2_r3_stopped():
    assert CANDIDATE_WEIGHT == 0.5
    assert R3_STOP == "81b6c0fc"
    assert challenger_margin(10.0, -4.0) == 3.0
    with pytest.raises(Exception, match="0.5|weight"):
        challenger_margin(10.0, -4.0, w=0.75)


def test_phase2_score_refused():
    result = refuse_phase2_score()
    assert result["refused"] is True
    assert result["phase2_score"] is False
    assert result["outcome_loader_reads"] == 0
    with pytest.raises(TargetScoringRefuse):
        refuse_target_scoring()


def test_if_and_hold_pins_untouched():
    hashes = snapshot_hold_hashes(ROOT)
    assert hashes["FORECASTS_DEV_R5_496.json"] == IF_FORECASTS_SHA256


def test_q2_coeffs_frozen():
    assert A_Q2 == 2.5637441292077354
    assert B_Q2 == 1.660624056183471


def test_manifest_parser_reads_local_sha_column():
    text = (
        "| 2013 | `play_by_play_2013.csv` | url | 1 | t | t | 9 | "
        "`33f96de712a82cc772cfb882fcb5016b985c68647fdb7e78f642de2f9c7f9b22` | "
        "`PUBLISHER_DIGEST_ABSENT` | PUBLISHER_DIGEST_ABSENT+size_ok |\n"
    )
    parsed = parse_manifest_sha256(text)
    assert parsed[2013].startswith("33f96de7")


@pytest.mark.skipif(not (ART / "FREEZE_MANIFEST.json").is_file(), reason="freeze not written yet")
def test_committed_history_id_freeze():
    manifest = json.loads((ART / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    from src.services.nfl_t5107u.recon_driver import sha256_file

    assert manifest["r5_history_id"] == R5_HISTORY_ID
    assert manifest["stop"] == "STOP_FOR_COS_B"
    assert manifest["if_forecasts_sha256"] == IF_FORECASTS_SHA256
    assert manifest["eval"] is None
    assert manifest["scoring"] is None
    for name, digest in manifest["files"].items():
        path = ART / f"{name}.json"
        assert path.is_file(), name
        assert sha256_file(path) == digest, name

    ident = json.loads((ART / "IDENTITY_FREEZE.json").read_text(encoding="utf-8"))
    assert ident["n_reg"] == 1792
    assert ident["n_post"] == 77
    assert ident["week_le_18_proxy"] is False
    assert ident["play_values_used"] is False

    prov = json.loads((ART / "JOIN_PROVENANCE.json").read_text(encoding="utf-8"))
    assert prov["pbp_2013_2019"]["n_reg"] == 1792
    assert prov["pbp_2013_2019"]["n_post"] == 77
    assert prov["pbp_2013_2019"]["n_unmatched"] == 0
    assert prov["pbp_2013_2019"]["n_conflict"] == 0
    assert prov["schedule_2020_2021_reg"]["n_reg"] == 528
    assert prov["n_unmatched"] == 0
    assert prov["week_le_18_proxy"] is False
    assert prov["pbp_2013_2019"]["n_post_week_le_18"] == 28

    splits = json.loads((ART / "SPLIT_SCAFFOLDING.json").read_text(encoding="utf-8"))
    assert splits["full496"]["n"] == 496
    assert splits["old437"]["n"] == 437
    assert splits["new59"]["n"] == 59
    assert splits["full496"]["identity_sha256"] == REG496_IDENTITY_SHA256
    assert splits["old437"]["identity_sha256"] == DEV_IF437_IDENTITY_SHA256
    assert splits["from_frozen_identities"] is True
    assert splits["labels"] == ["RECONSTRUCTED", "RETRO_FIT"]

    pins = json.loads((ART / "SOURCE_PINS.json").read_text(encoding="utf-8"))
    assert pins["pins"]["market_intersection_bytes"] == INTERSECTION_BYTES_SHA256
    assert pins["pins"]["market_intersection_identity"] == INTERSECTION_IDENTITY_SHA256
    assert pins["pins"]["if_forecasts"] == IF_FORECASTS_SHA256
    assert pins["holds"]["Q2_2017"] == "CLOSED"
    assert pins["holds"]["Phase2_score"] is False

    stop = json.loads((ART / "STOP_FOR_COS_B.json").read_text(encoding="utf-8"))
    assert stop["stop"] == "STOP_FOR_COS_B"
    assert stop["cos_order_a"] == COS_ORDER_A
    assert stop["cert_candidate"] == 0
    assert stop["green"] is False
    assert stop["hash6"] is False
    assert stop["q2_2017_eval"] == "CLOSED"

    forecasts = json.loads(
        (ART / "FORECASTS_DEV_R5_496_Q2_COMPLETED.json").read_text(encoding="utf-8")
    )
    if forecasts.get("hold_q2"):
        assert forecasts.get("n_candidate_finite") == 0
        return
    assert forecasts["n_forecasts"] == 496
    assert forecasts["n_if_finite"] == 496
    assert forecasts["n_q2_finite"] == 496
    assert forecasts["n_candidate_finite"] == 496
    assert forecasts["if_regenerated"] is False
    assert forecasts["if_forecasts_sha256"] == IF_FORECASTS_SHA256
    assert forecasts["initial_prior_2013"] is None
    assert forecasts["candidate"] == "0.5*IF+0.5*Q2"
    assert forecasts["q2_2017_eval"] == "CLOSED"
    pinned = json.loads(
        (ROOT / HOLD_DIR / "FORECASTS_DEV_R5_496.json").read_text(encoding="utf-8")
    )
    pinned_if = {r["game_id"]: r["m_if"] for r in pinned["forecasts"]}
    for row in forecasts["forecasts"]:
        assert row["m_if"] == pinned_if[row["game_id"]]
        assert row["m_q2"] is not None
        assert row["m_candidate"] == pytest.approx(0.5 * row["m_if"] + 0.5 * row["m_q2"])
        assert row["fit_label"] == "RETRO_FIT"
        assert row["history_ids_sha256"]
    hist = json.loads((ART / "HISTORY_IDS_FREEZE.json").read_text(encoding="utf-8"))
    assert hist["choice_frozen"] is True
    assert hist["n_targets"] == 496
    assert hist["history_rule"]["disclose_not_old_kickoff_only_asof"] is True
    assert hist["history_rule"]["initial_prior_2013"] is None
    first = hist["targets"][0]
    assert first["n_history"] > 0
    assert len(first["history_ids"]) == first["n_history"]
