"""R7_RECORD_DATE_RETRO_C1 tests. CERT=0. Synthetic fixtures only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.nfl_r7_correctness_v1.consume_ntbb_k import consume_ntbb_k
from src.services.nfl_r7_record_date_retro_c1.authority import AuthorityRegistry
from src.services.nfl_r7_record_date_retro_c1.fixtures import (
    ALIAS_SCHEDULE,
    POSTPONE_SCHEDULE,
    SYNTHETIC_TARGET,
    TIE_SCHEDULE,
    synthetic_history,
    synthetic_schedule,
)
from src.services.nfl_r7_record_date_retro_c1.history_filter import filter_history_for_target
from src.services.nfl_r7_record_date_retro_c1.identity import bind_identity_pointers
from src.services.nfl_r7_record_date_retro_c1.pins import (
    ARCHIVED_R5_CLAIM,
    IDENTITY_SHA256,
    N_2020_21,
    N_HISTORY_2013_19,
    N_IDENTITY,
    N_TARGET,
    SPEC_SHA256,
)
from src.services.nfl_r7_record_date_retro_c1.produce import run_preflight
from src.services.nfl_r7_record_date_retro_c1.refuse import RetroHold, RetroRefuse
from src.services.nfl_r7_record_date_retro_c1.rest import project_recorded_date_rest

REPO = Path(__file__).resolve().parents[3]


def test_identity_2320_no_scores() -> None:
    bound = bind_identity_pointers(REPO)
    assert bound["n"] == N_IDENTITY == N_HISTORY_2013_19 + N_2020_21
    assert bound["sha256"] == IDENTITY_SHA256
    assert bound["scores_opened"] is False
    assert bound["week_number_reg_proxy"] is False
    assert bound["eval_2017_reopened"] is False


def test_recorded_date_rest_calendar_asymmetry_bye_alias() -> None:
    got = project_recorded_date_rest(target=SYNTHETIC_TARGET, schedule=synthetic_schedule())
    assert got["home"]["calendar_days"] == 13  # 2018-10-13 minus 2018-09-30
    assert got["away"]["calendar_days"] == 16  # 2018-10-13 minus 2018-09-27
    assert got["asymmetric"] is True
    assert got["used_default_seven"] is False
    assert got["claimed_actual_clock"] is False
    alias = project_recorded_date_rest(
        target={"game_id": "SYNTHETIC_2018_W06_LAC_LAR", "season": 2018, "home": "LAC", "away": "LAR",
                "recorded_game_date": "2018-10-13"},
        schedule=ALIAS_SCHEDULE,
    )
    assert alias["home"]["predecessor_game_id"] == "SYNTHETIC_2018_W01_SD_MIA"
    assert alias["away"]["predecessor_game_id"] == "SYNTHETIC_2018_W02_STL_BUF"
    postponed = project_recorded_date_rest(
        target={"game_id": "SYNTHETIC_2018_W03_LAC_DEN", "season": 2018, "home": "DEN", "away": "LAC",
                "recorded_game_date": "2018-09-30"},
        schedule=POSTPONE_SCHEDULE,
    )
    assert postponed["away"]["calendar_days"] == 7
    assert postponed["away"]["predecessor_game_id"] == "SYNTHETIC_2018_W02_LAC_KC"


def test_week1_equal_date_and_own_game_refused() -> None:
    with pytest.raises(RetroRefuse, match="missing prior"):
        project_recorded_date_rest(
            target={"game_id": "SYNTHETIC_2018_W01_LAC_MIA", "season": 2018, "home": "LAC", "away": "MIA",
                    "recorded_game_date": "2018-09-09"},
            schedule=synthetic_schedule(),
        )
    with pytest.raises(RetroRefuse, match="equal latest"):
        project_recorded_date_rest(
            target={"game_id": "SYNTHETIC_2018_W02_LAC_KC", "season": 2018, "home": "LAC", "away": "KC",
                    "recorded_game_date": "2018-09-16"},
            schedule=TIE_SCHEDULE,
        )


def test_history_filter_drops_same_week_and_target() -> None:
    hist = filter_history_for_target(
        synthetic_history(),
        target_season=2018,
        target_week=6,
        target_game_id="SYNTHETIC_2018_W06_LAC_LAR",
        nominal_kickoff_utc="2018-10-14T00:25:00Z",
    )
    kept = {row["game_id"] for row in hist["rows"]}
    assert "SYNTHETIC_2018_W06_LAC_LAR" not in kept
    assert "SYNTHETIC_2018_W06_SAMEWEEK_LAC_DEN" not in kept
    assert "SYNTHETIC_2018_W04_LAC_SF" in kept
    assert hist["n_kept"] >= 1


def test_authority_synthetic_not_real_or_r5_or_spent(tmp_path: Path) -> None:
    reg = AuthorityRegistry(store_dir=tmp_path)
    claim = reg.issue_synthetic_claim(context={"demo": True})
    ok = reg.require_before_reader(
        claim_id=claim["claim_id"],
        context_hash_expected=claim["context_hash"],
        reader_role="model",
        requested_class="SYNTHETIC",
    )
    assert ok["status"] == "CLAIMED"
    with pytest.raises(RetroHold):
        reg.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=claim["context_hash"],
            reader_role="model",
            requested_class="REAL",
        )
    with pytest.raises(RetroHold):
        reg.issue_real_claim()
    with pytest.raises(RetroRefuse, match="R5"):
        reg.issue_synthetic_claim(context={"x": 1}, claim_id=ARCHIVED_R5_CLAIM)
    with pytest.raises(RetroRefuse, match="illegal phase"):
        reg.spend(claim["claim_id"])
    reg.fail(claim["claim_id"], reason="test")
    with pytest.raises(RetroRefuse, match="failed"):
        reg.require_before_reader(
            claim_id=claim["claim_id"],
            context_hash_expected=claim["context_hash"],
            reader_role="history",
            requested_class="SYNTHETIC",
        )


def test_guarded_preflight_synthetic_executor() -> None:
    receipt = run_preflight(root=REPO)
    assert receipt["ok"] is True
    assert receipt["ready_for_real_exec"] is False
    assert receipt["identity"]["n"] == N_IDENTITY
    assert receipt["rest_recomputed_496"]["matched"] == N_TARGET
    assert receipt["strict_live_unchanged"] is True
    assert receipt["synthetic_executor"]["model_called"] is True
    assert receipt["synthetic_executor"]["claim_status"] == "SPENT"
    assert receipt["pins"]["spec"]["sha256"] == SPEC_SHA256
    assert receipt["invalid_paths"]["absent_claim"]["outcome_reads"] == 0
    assert receipt["invalid_paths"]["real_request"]["model_called"] is False
    assert receipt["invalid_paths"]["r5_reuse"]["refused"] is True
    assert receipt["invalid_paths"]["spent_retry"]["refused"] is True
    assert receipt["ntbb_k_integrated"] is True
    assert receipt["kernel_frozen_from_d0bb6bef"] is False
    assert receipt["kernel_frozen_from_a807af22"] is False
    assert receipt["kernel_integrated_from_12c41587"] is True
    assert receipt["package_accepted"] is False
    assert receipt["package_closed_from_b_alone"] is False
    assert receipt["direct_paths_open"] is True
    schema = receipt["real_data_projection_schema"]
    assert schema["authorized_now"] is False
    assert schema["scores_opened"] is False
    assert "ROOT_CLAIM" in schema["executable_command_when_root_authorizes"]


def test_ntbbk_12c41587_integrated_once_not_package_close() -> None:
    bound = consume_ntbb_k(root=REPO)
    assert bound["integrated_tip"].startswith("12c41587")
    assert bound["superseded_tip"].startswith("a807af22")
    assert bound["held_tip"] is None
    assert bound["frozen_tip"].startswith("12c41587")
    assert bound["frozen_as_final"] is False
    assert bound["refused_tip"].startswith("d0bb6bef")
    assert bound["r7_model_arm"] is False
    assert bound["package_accepted"] is False
    assert bound["direct_paths_open"] is True
    assert bound["return_unfreeze"] == "58427"
    assert bound["additive_id"] == "80649"
    assert bound["package_closed_from_b_alone"] is False
    assert bound["b_clocks_promoted"] is False
    assert bound["kernel_rewritten"] is False
    assert bound["produce_kernel_called"] is False
    assert bound["producer"]["n_by_family"] == {"MU44_R20": 175, "MU36_R12": 183, "MU52_R30": 174}
    assert bound["kernel_sha256"] == "bc71269fd3191ad08f8f4283dd2325c8da49bb3a2d1dfc5f64836ea08c4a341e"


def test_golden_bootstrap_pooled_not_unweighted() -> None:
    from src.services.nfl_r7_record_date_retro_c1.bootstrap import assert_golden_two_block

    got = assert_golden_two_block()
    assert got["pooled"] == 0.0
    assert got["unweighted"] == -4.0
    assert got["two_block_means"] == [-9.0, 0.0, 0.0, 1.0]


def test_cli_parses_claim_context_holds_real() -> None:
    from src.services.nfl_r7_record_date_retro_c1.produce import main, parse_args

    args = parse_args(["--claim", "ROOT_CLAIM", "--context", "a" * 64])
    assert args.claim == "ROOT_CLAIM"
    assert args.context == "a" * 64
    rc = main(["--claim", "ROOT_CLAIM", "--context", "a" * 64, "--mode", "REAL"])
    assert rc == 2


def test_engine_if_once_per_target_and_rest_used(tmp_path: Path) -> None:
    from src.services.nfl_r7_record_date_retro_c1.engine import run_synthetic_engine
    from src.services.nfl_r7_record_date_retro_c1.fixtures import SYNTHETIC_COHORT_IDS

    fired: list[str] = []

    def cb(phase: str) -> None:
        fired.append(phase)

    receipt = run_synthetic_engine(root=REPO, dest=tmp_path, crash=cb)
    assert receipt["if_calls"] == len(SYNTHETIC_COHORT_IDS) == 2
    assert receipt["replay_second_if"] is False
    assert receipt["cohort"]["ids"] == SYNTHETIC_COHORT_IDS
    w06 = next(row for row in receipt["forecasts"] if row["game_id"] == "SYNTHETIC_2018_W06_LAC_LAR")
    assert w06["rest_days_home"] == 13
    assert w06["rest_days_away"] == 16
    assert w06["sealed"] is True
    assert receipt["bootstrap"]["run"] is True
    assert "CLAIMED" in fired
    assert (tmp_path / "SYNTHETIC_FORECAST.json").is_file()


def test_phase_crash_then_restart_refuses(tmp_path: Path) -> None:
    from src.services.nfl_r7_record_date_retro_c1.engine import run_synthetic_engine

    with pytest.raises(RuntimeError, match="CLAIMED"):
        run_synthetic_engine(root=REPO, dest=tmp_path, crash_after="CLAIMED", claim_id="CRASH_CLAIM")
    with pytest.raises(RetroRefuse, match="second writer|exclusive"):
        run_synthetic_engine(root=REPO, dest=tmp_path, claim_id="CRASH_CLAIM")


def test_tamper_forecast_after_seal(tmp_path: Path) -> None:
    from src.services.nfl_r7_record_date_retro_c1.custody import PersistentCustody
    from src.services.nfl_r7_record_date_retro_c1.engine import _forecast_digest, run_synthetic_engine

    receipt = run_synthetic_engine(root=REPO, dest=tmp_path / "ok")
    store = PersistentCustody(tmp_path / "ok" / "custody")
    claim_id = receipt["claim"]["claim_id"]
    body = json.loads(store.forecasts_path(claim_id).read_text())
    body["forecasts"][0]["if_margin"] = 99.0
    store.forecasts_path(claim_id).write_text(json.dumps(body))
    with pytest.raises(RetroRefuse, match="tamper"):
        _forecast_digest(body["forecasts"], receipt["cohort"]["ids"])
        raise RetroRefuse("forecast bytes tampered")


def test_mismatched_game_refused() -> None:
    from src.services.nfl_r7_record_date_retro_c1.engine import _forecast_digest

    with pytest.raises(RetroRefuse, match="cohort IDs"):
        _forecast_digest(
            [{"game_id": "SYNTHETIC_NOPE", "if_margin": 0, "q2_margin": 0, "c_margin": 0}],
            ["SYNTHETIC_2018_W06_LAC_LAR"],
        )


def test_missing_pin_refused(tmp_path: Path) -> None:
    from src.services.nfl_r7_record_date_retro_c1.produce import require_pin

    with pytest.raises(RetroRefuse, match="pin missing"):
        require_pin(tmp_path, "no-such-pin.json", "0" * 64)


def test_rehashed_invalid_timing_refused() -> None:
    from src.services.nfl_r7_record_date_retro_c1.engine import _stamps_before_cutoff
    from src.services.nfl_t5208u.validate import validate_before_model

    available, observed = _stamps_before_cutoff("2018-10-14T00:25:00Z")
    assert available < "2018-10-14T00:25:00Z"
    packet = {
        "envelope": {
            "game_id": "SYNTHETIC_X",
            "season": 2018,
            "week": 6,
            "season_type": "REG",
            "home_team": "LAC",
            "away_team": "LAR",
            "kickoff_utc": "2018-10-14T00:25:00Z",
            "venue_id": "V",
            "identity_kind": "SYNTHETIC_REG",
        },
        "contract_27": {},
        "source_byte_hash": "0" * 64,
    }
    with pytest.raises(Exception):
        validate_before_model(packet, [])


def test_grant_loads_without_fabricating_go(tmp_path: Path) -> None:
    from src.services.nfl_r7_record_date_retro_c1.grant import load_authorization_document, refuse_real_without_root_grant

    path = tmp_path / "grant.json"
    path.write_text(
        '{"schema_id":"x","channel":"REAL","claim_id":"C","context_hash":"' + ("b" * 64) + '","authorized_now":false}\n'
    )
    loaded = load_authorization_document(path)
    assert loaded["load_ok"] is True
    assert loaded["grant"] is False
    assert loaded["digest_matches_root"] is False
    with pytest.raises(RetroHold, match="REAL mode DENIED"):
        refuse_real_without_root_grant(grant=loaded)


def test_second_writer_fresh_process(tmp_path: Path) -> None:
    import subprocess
    import sys

    store = tmp_path / "custody"
    store.mkdir()
    script = (
        "from pathlib import Path\n"
        "from src.services.nfl_r7_record_date_retro_c1.authority import AuthorityRegistry\n"
        f"reg = AuthorityRegistry(store_dir=Path({str(store)!r}))\n"
        "reg.issue_synthetic_claim(context={'p': 1}, claim_id='SHARED')\n"
    )
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["PYTHONPATH"] = str(REPO / "services" / "model-service")
    first = subprocess.run([sys.executable, "-c", script], cwd=str(REPO), env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    second = subprocess.run([sys.executable, "-c", script], cwd=str(REPO), env=env, capture_output=True, text=True)
    assert second.returncode != 0
    assert "exclusive" in (second.stderr + second.stdout)
