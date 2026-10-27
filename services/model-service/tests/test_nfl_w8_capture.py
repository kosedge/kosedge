"""Synthetic-only tests for W8 prospective capture (t4445u RD-7).

No Odds API network. No keys. No seal-ack.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.services.nfl_w8_capture.fixture_load import (
    cells_from_odds_shaped_event,
    load_json_fixture,
)
from src.services.nfl_w8_capture.books import (
    OPTIONAL_SECONDARY_BOOKS,
    PRIMARY_BOOKS,
    build_w8_odds_request_params,
    classify_book_role,
)
from src.services.nfl_w8_capture.alerts import deliver_alert
from src.services.nfl_w8_capture.archive import archive_forecasts
from src.services.nfl_w8_capture.cadence import (
    F8_CUTOFF,
    F8CutoffError,
    GameKickoff,
    assert_slate_join_before_f8,
    close_window_guaranteed,
    due_sample_windows,
    f8_cutoff_utc,
    past_f8_cutoff,
    plan_pre_kickoff_samples,
    review_sample_coverage,
)
from src.services.nfl_w8_capture.carveouts import (
    explicit_carve_outs,
    require_explicit_carve_out,
)
from src.services.nfl_w8_capture.credits import (
    CREDIT_CEILING,
    CreditCeilingError,
    CreditEstimateError,
    CreditHeaderError,
    CreditPurchaseError,
    CreditReconcileError,
    estimate_request_credits,
    ledger_closed,
    ledger_overrun,
    pre_call_check,
    read_cumulative,
    record_credit_use,
    refuse_credit_purchase,
)
from src.services.nfl_w8_capture.fetch import (
    OddsFetchError,
    OddsTransportResult,
    fetch_odds_with_provenance,
    raw_body_sha256,
)
from src.services.nfl_w8_capture.seal import SealWindowError, produce_seal
from src.services.nfl_w8_capture.close import (
    BookMarketCell,
    evaluate_game_market_close,
)
from src.services.nfl_w8_capture.evidence import (
    EvidenceChainError,
    append_evidence_entry,
    verify_evidence_chain,
)
from src.services.nfl_w8_capture.hold import (
    H1_AUTH_CITE,
    OddsApiHoldError,
    odds_api_hold_is_on,
    refuse_odds_fetch,
)
from src.services.nfl_w8_capture.imv_package import prove_hard_stops, write_imv_package
from src.services.nfl_w8_capture.pin import (
    UNSET_SHA,
    build_pin_manifest,
    validate_pin_manifest,
)
from src.services.nfl_w8_capture.redact import redact_secrets
from src.services.nfl_w8_capture.restore import PEvidenceRestoreError, restore_p_evidence
from src.services.nfl_w8_capture.snapshots import append_snapshot, snapshot_content_sha
from src.services.nfl_w8_capture.store import BundleStore, StoreImmutabilityError
from src.services.nfl_w8_capture.tick import run_capture_tick
from src.services.nfl_w8_capture.streams import (
    STREAM_IND,
    STREAM_MKT,
    ForbiddenInputError,
    check_s_ind_forbidden_inputs,
    refuse_seal,
    scaffold_streams,
)

KICKOFF = datetime(2026, 10, 29, 23, 15, tzinfo=timezone.utc)


def _cell(
    book: str,
    *,
    last_update: str | None,
    provider_ts: str | None,
    received: str = "2026-10-29T23:14:50Z",
    line: float = -3.0,
) -> BookMarketCell:
    return BookMarketCell(
        book=book,
        market="spreads",
        game_id="2026-W08-MIN@LAC",
        line=line,
        price=-110,
        market_last_update=last_update,
        provider_server_ts=provider_ts,
        client_received_at=received,
    )


def _fresh(book: str, *, minutes: int = 6, line: float = -3.0) -> BookMarketCell:
    ts = (KICKOFF - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")
    return _cell(book, last_update=ts, provider_ts=ts, line=line)


def test_part_b_primary_books_exact_and_request_includes_circa() -> None:
    assert PRIMARY_BOOKS == (
        "draftkings",
        "fanduel",
        "betmgm",
        "fanatics",
        "circa",
    )
    assert OPTIONAL_SECONDARY_BOOKS == ("ballybet",)
    params = build_w8_odds_request_params()
    books = params["bookmakers"].split(",")
    assert books == list(PRIMARY_BOOKS)
    assert "circa" in books
    assert "ballybet" not in books
    with_secondary = build_w8_odds_request_params(include_secondary=True)
    assert "ballybet" in with_secondary["bookmakers"].split(",")
    assert classify_book_role("circa") == "primary"
    assert classify_book_role("ballybet") == "secondary"


def test_carried_list_without_circa_is_rejected() -> None:
    carried_without_circa = [
        "draftkings",
        "fanduel",
        "betmgm",
        "betrivers",
        "hardrockbet",
        "fanatics",
        "bovada",
        "williamhill_us",
        "betonlineag",
    ]
    with pytest.raises(ValueError, match="circa"):
        build_w8_odds_request_params(bookmakers=carried_without_circa)


def test_dr7_missing_last_update_is_unknown_not_close() -> None:
    cells = [
        _fresh("draftkings"),
        _fresh("fanduel"),
        _cell("betmgm", last_update=None, provider_ts="2026-10-29T23:08:00Z"),
        _fresh("fanatics"),
        _fresh("circa"),
    ]
    # betmgm UNKNOWN does not count; still k=4 fresh => CLOSE, but UNKNOWN cell
    result = evaluate_game_market_close(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        kickoff_utc=KICKOFF,
        cells=cells,
    )
    betmgm = next(v for v in result.books if v.book == "betmgm")
    assert betmgm.cell_status == "UNKNOWN"
    assert betmgm.reason == "missing_last_update_not_a_close"

    only_unknown = [
        _cell(book, last_update=None, provider_ts="2026-10-29T23:08:00Z")
        for book in PRIMARY_BOOKS
    ]
    missing_close = evaluate_game_market_close(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        kickoff_utc=KICKOFF,
        cells=only_unknown,
    )
    assert missing_close.status == "UNKNOWN"
    assert missing_close.selected is None


def test_dr8_client_receive_alone_is_not_a_close() -> None:
    cells = [
        _cell("draftkings", last_update="2026-10-29T23:08:00Z", provider_ts=None),
        _fresh("fanduel"),
        _fresh("betmgm"),
        _fresh("fanatics"),
        _fresh("circa"),
    ]
    result = evaluate_game_market_close(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        kickoff_utc=KICKOFF,
        cells=cells,
    )
    dk = next(v for v in result.books if v.book == "draftkings")
    assert dk.cell_status == "NOT_CLOSE"
    assert dk.reason == "client_receive_alone_is_not_a_close"
    assert result.status == "CLOSE"
    assert result.primary_fresh_count == 4


def test_dr9_k_lt_3_close_missing() -> None:
    cells = [
        _fresh("draftkings"),
        _fresh("fanduel"),
        # betmgm / fanatics / circa absent
    ]
    result = evaluate_game_market_close(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        kickoff_utc=KICKOFF,
        cells=cells,
    )
    assert result.status == "MISSING"
    assert result.reason == "k_lt_3_primary_present_non_stale"
    assert result.primary_fresh_count == 2
    assert result.selected is None


def test_dr10_missing_circa_never_imputed() -> None:
    cells = [
        _fresh("draftkings", line=-3.0),
        _fresh("fanduel", line=-3.5),
        _fresh("betmgm", line=-3.0),
        _fresh("fanatics", line=-2.5),
        _fresh("ballybet", line=-7.0),  # secondary must not fill circa
    ]
    result = evaluate_game_market_close(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        kickoff_utc=KICKOFF,
        cells=cells,
    )
    circa = next(v for v in result.books if v.book == "circa")
    assert circa.cell_status == "MISSING"
    assert circa.reason == "missing_cell_never_impute"
    assert result.status == "CLOSE"  # k=4 without circa
    assert result.selected is not None
    assert result.selected.book != "circa"
    assert result.selected.line != -7.0


def test_ra5_stale_age_over_10_min_not_a_close_contributor() -> None:
    stale_ts = (KICKOFF - timedelta(minutes=25)).isoformat().replace("+00:00", "Z")
    cells = [
        _cell("draftkings", last_update=stale_ts, provider_ts=stale_ts),
        _cell("fanduel", last_update=stale_ts, provider_ts=stale_ts),
        _cell("betmgm", last_update=stale_ts, provider_ts=stale_ts),
        _cell("fanatics", last_update=stale_ts, provider_ts=stale_ts),
        _cell("circa", last_update=stale_ts, provider_ts=stale_ts),
    ]
    result = evaluate_game_market_close(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        kickoff_utc=KICKOFF,
        cells=cells,
    )
    assert result.status == "MISSING"
    assert all(v.cell_status == "STALE" for v in result.books if v.role == "primary")
    assert result.primary_fresh_count == 0


def test_close_selects_last_fresh_provider_ts() -> None:
    cells = [
        _fresh("draftkings", minutes=9, line=-2.5),
        _fresh("fanduel", minutes=4, line=-3.0),
        _fresh("betmgm", minutes=7, line=-3.0),
        _fresh("fanatics", minutes=8, line=-3.5),
        _fresh("circa", minutes=5, line=-3.0),
    ]
    result = evaluate_game_market_close(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        kickoff_utc=KICKOFF,
        cells=cells,
    )
    assert result.status == "CLOSE"
    assert result.selected is not None
    assert result.selected.book == "fanduel"
    assert result.selected.line == -3.0


def test_post_kickoff_provider_ts_rejected() -> None:
    late = (KICKOFF + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    cells = [
        _cell("draftkings", last_update=late, provider_ts=late),
        _fresh("fanduel"),
        _fresh("betmgm"),
        _fresh("fanatics"),
        _fresh("circa"),
    ]
    result = evaluate_game_market_close(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        kickoff_utc=KICKOFF,
        cells=cells,
    )
    dk = next(v for v in result.books if v.book == "draftkings")
    assert dk.cell_status == "NOT_CLOSE"


def test_hold_blocks_any_odds_fetch_even_if_env_tries_to_lift() -> None:
    with pytest.raises(OddsApiHoldError, match="H-1a/H-1c"):
        refuse_odds_fetch(
            params=build_w8_odds_request_params(),
            env={"NFL_W8_ODDS_API_HOLD": "0", "ODDS_API_HOLD": "false"},
        )


def test_hash_chain_and_tamper_fail_closed(tmp_path: Path) -> None:
    first = append_evidence_entry(
        tmp_path, actor="cursor", artifact_sha="a" * 64, note="snap-1"
    )
    append_evidence_entry(
        tmp_path, actor="cursor", artifact_sha="b" * 64, note="snap-2"
    )
    verified = verify_evidence_chain(tmp_path)
    assert verified["ok"] is True
    assert verified["entries"] == 2
    assert first["prev_entry_sha"] == "0" * 64

    log_path = tmp_path / "evidence.jsonl"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["note"] = "edited-after-write"
    lines[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(EvidenceChainError, match="entry_sha mismatch"):
        verify_evidence_chain(tmp_path)


def test_hash_chain_delete_line_breaks(tmp_path: Path) -> None:
    append_evidence_entry(tmp_path, actor="cursor", artifact_sha="a" * 64)
    append_evidence_entry(tmp_path, actor="cursor", artifact_sha="b" * 64)
    append_evidence_entry(tmp_path, actor="cursor", artifact_sha="c" * 64)
    log_path = tmp_path / "evidence.jsonl"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    log_path.write_text(lines[0] + "\n" + lines[2] + "\n", encoding="utf-8")
    with pytest.raises(EvidenceChainError, match="prev_entry_sha break"):
        verify_evidence_chain(tmp_path)


def test_snapshots_append_only_and_redact_secrets(tmp_path: Path) -> None:
    record = append_snapshot(
        tmp_path,
        {
            "game_id": "2026-W08-MIN@LAC",
            "bookmakers": "draftkings,fanduel,betmgm,fanatics,circa",
            "apiKey": "should-never-land",
            "ODDS_API_KEY": "also-secret",
            "provider_server_ts": "2026-10-29T23:08:00Z",
            "markets": [{"key": "spreads", "last_update": "2026-10-29T23:08:00Z"}],
        },
        captured_at=datetime(2026, 10, 29, 23, 8, tzinfo=timezone.utc),
    )
    assert record["payload"]["apiKey"] == "[REDACTED]"
    assert record["payload"]["ODDS_API_KEY"] == "[REDACTED]"
    assert "should-never-land" not in json.dumps(record)
    text = (tmp_path / "snapshots.jsonl").read_text(encoding="utf-8")
    assert text.count("\n") == 1
    first_line = json.loads(text.splitlines()[0])
    assert first_line["prev_entry_sha"] == "0" * 64
    assert first_line["entry_sha"]
    append_snapshot(tmp_path, {"game_id": "2026-W08-MIN@LAC", "n": 2})
    assert (tmp_path / "snapshots.jsonl").read_text(encoding="utf-8").count("\n") == 2
    assert len(snapshot_content_sha(record["payload"])) == 64
    assert (tmp_path / "SHA256SUMS").is_file()
    assert (tmp_path / "evidence.jsonl").is_file()
    store = BundleStore(tmp_path)
    assert store.verify()["entries"] >= 2


def test_s_ind_forbidden_input_fail_closed() -> None:
    check_s_ind_forbidden_inputs({"epa_prior": 0.1, "rest_days": 7})
    with pytest.raises(ForbiddenInputError, match="blend"):
        check_s_ind_forbidden_inputs({"epa_prior": 0.1, "blend_weight": 0.3})
    with pytest.raises(ForbiddenInputError, match="close"):
        check_s_ind_forbidden_inputs({"market_close_spread": -3.0})
    bundles = scaffold_streams(
        "2026-W08-MIN@LAC",
        s_mkt_features={"blend_weight": UNSET_SHA},
        s_ind_features={"epa_prior": 0.1},
    )
    assert STREAM_MKT in bundles and STREAM_IND in bundles
    assert bundles[STREAM_MKT].path.endswith(".s_mkt.json")
    assert bundles[STREAM_IND].path.endswith(".s_ind.json")
    assert bundles[STREAM_IND].sealed is False
    assert bundles[STREAM_IND].sha256 == ""
    with pytest.raises(ForbiddenInputError):
        scaffold_streams("g", s_ind_features={"odds": -110})
    with pytest.raises(PermissionError, match="AC-12"):
        refuse_seal(bundles.values())


def test_pin_manifest_shape_no_fake_shas() -> None:
    manifest = build_pin_manifest()
    assert validate_pin_manifest(manifest) == []
    assert manifest["spec_sha8"] == "08808adf"
    assert manifest["odds_api_hold"] is True
    assert manifest["nfl_no_go"] is True
    assert manifest["seal_ack"] == "CURSOR_CANNOT_SEAL_ACK"
    assert manifest["code_commit_sha"] == UNSET_SHA
    assert set(manifest["input_shas"]) == {
        "pbp",
        "schedule",
        "injury",
        "weather",
        "odds_vintage",
    }
    with pytest.raises(ValueError, match="fake"):
        build_pin_manifest(code_commit_sha="fake1234")
    bad = dict(manifest)
    bad["odds_api_hold"] = False
    assert "odds_api_hold_must_remain_true" in validate_pin_manifest(bad)


def test_beat_entry_wires_planner_to_celery_tick() -> None:
    beat_src = (
        Path(__file__).resolve().parents[1] / "src" / "celerybeat_schedule.py"
    ).read_text(encoding="utf-8")
    tasks_src = (Path(__file__).resolve().parents[1] / "src" / "tasks.py").read_text(
        encoding="utf-8"
    )
    app_src = (Path(__file__).resolve().parents[1] / "src" / "celery_app.py").read_text(
        encoding="utf-8"
    )
    ci_src = (
        Path(__file__).resolve().parents[3] / ".github" / "workflows" / "pr-check.yml"
    ).read_text(encoding="utf-8")
    assert 'TASK_NFL_W8_CAPTURE_TICK = os.getenv(' in beat_src
    assert '"nfl-w8-capture-pre-kickoff-tick"' in beat_src
    assert "src.tasks.run_nfl_w8_capture_tick" in beat_src
    assert 'NFL_W8_CAPTURE_TICK_MINUTE", "*/2"' in beat_src
    assert '"queue": NFL_MARKET_QUEUE' in beat_src
    assert '@celery_app.task(name="src.tasks.run_nfl_w8_capture_tick")' in tasks_src
    assert "src.services.nfl_w8_capture.tick import run_capture_tick" in tasks_src
    assert '"src.tasks.run_nfl_w8_capture_tick"' in app_src
    assert "tests/test_nfl_w8_capture.py" in ci_src
    assert "W8 prospective capture unit tests" in ci_src


def test_cadence_guarantees_sub_10_min_sample_and_alerts() -> None:
    games = [
        GameKickoff("2026-W08-MIN@LAC", KICKOFF, "REG"),
        GameKickoff("2026-W08-PRE-X", KICKOFF, "PRE"),
    ]
    plan = plan_pre_kickoff_samples(games)
    assert close_window_guaranteed(plan, "2026-W08-MIN@LAC")
    assert "2026-W08-PRE-X" in plan.skipped_non_reg
    close_slots = [w for w in plan.windows if w.in_close_window]
    assert close_slots
    assert all(KICKOFF - w.sample_at <= timedelta(minutes=10) for w in close_slots)

    missing = review_sample_coverage(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        book_statuses=[(b, "MISSING") for b in PRIMARY_BOOKS],
    )
    assert missing.kind == "missing"
    stale = review_sample_coverage(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        book_statuses=[(b, "STALE") for b in PRIMARY_BOOKS],
    )
    assert stale.kind == "stale"
    partial = review_sample_coverage(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        book_statuses=[
            ("draftkings", "PRESENT"),
            ("fanduel", "PRESENT"),
            ("betmgm", "MISSING"),
            ("fanatics", "STALE"),
            ("circa", "MISSING"),
        ],
    )
    assert partial.kind == "partial"

    close_at = next(w.sample_at for w in plan.windows if w.in_close_window)
    due = due_sample_windows(plan, now_utc=close_at, slack=timedelta(minutes=2))
    assert due
    assert all(w.in_close_window for w in due)


def test_alert_delivery_file_sink_hold_blocks_webhook(tmp_path: Path) -> None:
    store = BundleStore(tmp_path)
    alert = review_sample_coverage(
        game_id="2026-W08-MIN@LAC",
        market="spreads",
        book_statuses=[(b, "MISSING") for b in PRIMARY_BOOKS],
    )
    disabled = deliver_alert(alert, store, env={})
    assert disabled.status == "disabled"
    assert (tmp_path / "alerts.jsonl").is_file()
    hold = deliver_alert(
        alert,
        store,
        env={
            "NFL_W8_ALERTS_ENABLED": "1",
            "NFL_W8_ALERT_WEBHOOK_URL": "https://example.invalid/hook",
        },
    )
    assert hold.status == "hold_blocked"
    assert hold.webhook_attempted is False
    store.verify()


def test_forecast_archiver_writes_unset_predictions(tmp_path: Path) -> None:
    store = BundleStore(tmp_path)
    written = archive_forecasts(
        store,
        game_id="2026-W08-MIN@LAC",
        s_mkt_features={"epa_prior": 0.1},
        s_ind_features={"epa_prior": 0.1, "rest_days": 7},
    )
    assert set(written) == {STREAM_MKT, STREAM_IND}
    mkt = json.loads(
        (tmp_path / "forecasts" / "s_mkt" / "2026-W08-MIN@LAC.s_mkt.json").read_text(
            encoding="utf-8"
        )
    )
    ind = json.loads(
        (tmp_path / "forecasts" / "s_ind" / "2026-W08-MIN@LAC.s_ind.json").read_text(
            encoding="utf-8"
        )
    )
    assert mkt["prediction"] == "UNSET"
    assert ind["prediction"] == "UNSET"
    assert mkt["sealed"] is False
    assert ind["seal_ack"] == "CURSOR_CANNOT_SEAL_ACK"
    with pytest.raises(ForbiddenInputError):
        archive_forecasts(store, game_id="g2", s_ind_features={"blend_weight": 0.3})
    store.verify()


def test_restore_p_evidence_read_only_no_eval(tmp_path: Path) -> None:
    source = tmp_path / "prior_deposit"
    prior = BundleStore(source)
    append_snapshot(source, {"game_id": "prior", "n": 1})
    dest = BundleStore(tmp_path / "live")
    restored = restore_p_evidence(source, dest, deposit_id="paper-2a9164bc")
    assert restored["eval"] == "not_run"
    assert restored["deposit_id"] == "paper-2a9164bc"
    copied = tmp_path / "live" / "p_evidence" / "paper-2a9164bc" / "snapshots.jsonl"
    assert copied.is_file()
    assert oct(copied.stat().st_mode)[-3:] == "444"
    with pytest.raises(PEvidenceRestoreError):
        restore_p_evidence(tmp_path / "missing", dest)
    dest.verify()


def test_store_refuses_overwrite_and_detects_tamper(tmp_path: Path) -> None:
    store = BundleStore(tmp_path)
    store.write_new_file("forecasts/s_mkt/one.json", {"prediction": "UNSET"}, actor="t", note="a")
    with pytest.raises(StoreImmutabilityError, match="overwrite"):
        store.write_new_file("forecasts/s_mkt/one.json", {"prediction": "UNSET"}, actor="t", note="b")
    snap = tmp_path / "snapshots.jsonl"
    append_snapshot(tmp_path, {"n": 1})
    append_snapshot(tmp_path, {"n": 2})
    lines = snap.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["record"]["payload"]["n"] = 99
    lines[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
    snap.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(StoreImmutabilityError, match="entry_sha mismatch"):
        store.verify()


def test_tick_schedules_due_close_window_without_odds_fetch(tmp_path: Path) -> None:
    games = [GameKickoff("2026-W08-MIN@LAC", KICKOFF, "REG")]
    plan = plan_pre_kickoff_samples(games)
    close_at = next(w.sample_at for w in plan.windows if w.in_close_window)
    result = run_capture_tick(
        now_utc=close_at,
        bundle_dir=tmp_path,
        kickoffs=games,
        env={"NFL_W8_ALERTS_ENABLED": "0"},
    )
    assert result["due_windows"] >= 1
    assert result["close_window_due"] >= 1
    assert result["odds_fetch"] == "blocked_hold"
    assert (tmp_path / "alerts.jsonl").is_file()
    with pytest.raises(OddsApiHoldError):
        run_capture_tick(
            now_utc=close_at,
            bundle_dir=tmp_path,
            kickoffs=games,
            attempt_fetch=True,
        )


def test_imv_package_proves_hard_stops_and_is_not_a_seal(tmp_path: Path) -> None:
    proof = prove_hard_stops()
    assert proof["refuse_odds_fetch"] == "OddsApiHoldError"
    assert proof["refuse_seal"] == "PermissionError"
    repo = Path(__file__).resolve().parents[3]
    out = write_imv_package(repo, tmp_path / "imv", tip_sha="")
    assert out["seal_ack"] == "CURSOR_CANNOT_SEAL_ACK"
    assert (tmp_path / "imv" / "FILELIST.txt").is_file()
    assert (tmp_path / "imv" / "INVENTORY.SHA256SUMS").is_file()
    assert (tmp_path / "imv" / "HARD_STOPS.json").is_file()
    hard = json.loads((tmp_path / "imv" / "HARD_STOPS.json").read_text(encoding="utf-8"))
    assert hard["odds_api_hold"] is True
    assert hard["nfl_no_go"] is True
    assert hard["coming_soon"] is True
    BundleStore(tmp_path / "imv").verify()


def test_redact_nested_secret_keys() -> None:
    cleaned = redact_secrets({"outer": {"token": "abc", "line": -3}})
    assert cleaned["outer"]["token"] == "[REDACTED]"
    assert cleaned["outer"]["line"] == -3


def test_synthetic_fixture_file_yields_part_b_close() -> None:
    event = load_json_fixture()
    assert event["season_type"] == "REG"
    assert {b["key"] for b in event["bookmakers"]} == set(PRIMARY_BOOKS)
    cells = cells_from_odds_shaped_event(event, market="spreads")
    result = evaluate_game_market_close(
        game_id=event["game_id"],
        market="spreads",
        kickoff_utc=event["kickoff_utc"],
        cells=cells,
    )
    assert result.status == "CLOSE"
    assert result.primary_fresh_count == 5
    assert result.selected is not None
    assert result.selected.book in PRIMARY_BOOKS


def _lift_env(**extra: str) -> dict[str, str]:
    env = {
        "NFL_W8_H1_AUTH_CITE": H1_AUTH_CITE,
        "NFL_W8_PR_ROTATE_CONFIRM": "1",
    }
    env.update(extra)
    return env


def test_hold_lift_requires_cite_and_rotate_confirm(tmp_path: Path) -> None:
    assert odds_api_hold_is_on({}) is True
    assert odds_api_hold_is_on({"NFL_W8_ODDS_API_HOLD": "0"}) is True
    assert odds_api_hold_is_on({"NFL_W8_H1_AUTH_CITE": H1_AUTH_CITE}) is True
    assert odds_api_hold_is_on({"NFL_W8_PR_ROTATE_CONFIRM": "1"}) is True
    assert odds_api_hold_is_on(_lift_env()) is False

    store = BundleStore(tmp_path)
    with pytest.raises(OddsApiHoldError, match="89fdd45f"):
        fetch_odds_with_provenance(
            store=store,
            env={"NFL_W8_H1_AUTH_CITE": H1_AUTH_CITE, "ODDS_API_KEY": "unit-test-not-live"},
        )
    with pytest.raises(OddsApiHoldError):
        fetch_odds_with_provenance(
            store=store,
            env={"NFL_W8_PR_ROTATE_CONFIRM": "1", "ODDS_API_KEY": "unit-test-not-live"},
        )
    alerts = (tmp_path / "alerts.jsonl").read_text(encoding="utf-8")
    assert '"kind":"hold"' in alerts
    assert "unit-test-not-live" not in alerts
    with pytest.raises(OddsApiHoldError, match="H-1a/H-1c"):
        refuse_odds_fetch(env={"NFL_W8_ODDS_API_HOLD": "0"})
    refuse_odds_fetch(env=_lift_env())  # lifted: refuse path no longer raises


def test_credit_ledger_edges_2999_3000_3001(tmp_path: Path) -> None:
    store = BundleStore(tmp_path)
    assert CREDIT_CEILING == 3000
    pre_call_check(2999, 1)
    with pytest.raises(CreditCeilingError):
        pre_call_check(3000, 1)
    with pytest.raises(CreditCeilingError):
        pre_call_check(3001, 1)
    first = record_credit_use(
        store,
        {
            "x-requests-last": "2999",
            "x-requests-used": "2999",
            "x-requests-remaining": "1",
        },
    )
    assert first["cumulative"] == 2999
    second = record_credit_use(
        store,
        {
            "x-requests-last": "1",
            "x-requests-used": "3000",
            "x-requests-remaining": "0",
        },
    )
    assert second["cumulative"] == 3000
    assert read_cumulative(store) == 3000
    with pytest.raises(CreditCeilingError):
        record_credit_use(
            store,
            {
                "x-requests-last": "1",
                "x-requests-used": "3001",
                "x-requests-remaining": "0",
            },
        )
    assert read_cumulative(store) == 3001
    assert ledger_overrun(store) is True
    assert ledger_closed(store) is True
    with pytest.raises(CreditCeilingError):
        pre_call_check(read_cumulative(store), 1, overrun=True)
    with pytest.raises(CreditHeaderError, match="missing"):
        record_credit_use(store, {"x-requests-used": "10"})
    with pytest.raises(CreditPurchaseError, match="not authorized"):
        refuse_credit_purchase()
    store.verify()


def test_credit_ledger_2990_plus_real_cost_30_records_then_blocks(tmp_path: Path) -> None:
    params = build_w8_odds_request_params()
    cost = estimate_request_credits(params)
    assert cost == 30
    assert cost == 5 * 3 * 2
    with pytest.raises(CreditEstimateError, match="never default 1"):
        estimate_request_credits({"bookmakers": "", "markets": "", "regions": ""})
    with pytest.raises(CreditEstimateError):
        pre_call_check(0, 0)

    store = BundleStore(tmp_path)
    seed = record_credit_use(
        store,
        {
            "x-requests-last": "2990",
            "x-requests-used": "2990",
            "x-requests-remaining": "100",
        },
    )
    assert seed["cumulative"] == 2990
    with pytest.raises(CreditCeilingError):
        record_credit_use(
            store,
            {
                "x-requests-last": "30",
                "x-requests-used": "3020",
                "x-requests-remaining": "0",
            },
        )
    assert read_cumulative(store) == 3020
    assert ledger_overrun(store) is True
    assert ledger_closed(store) is True
    with pytest.raises(CreditCeilingError):
        pre_call_check(3020, cost, overrun=True)

    called = {"n": 0}

    def transport(*, endpoint: str, params: object, headers: object) -> OddsTransportResult:
        called["n"] += 1
        raise AssertionError("closed ledger must not call transport")

    with pytest.raises(CreditCeilingError, match="ledger closed"):
        fetch_odds_with_provenance(
            store=store,
            env=_lift_env(ODDS_API_KEY="unit-test-not-live"),
            transport=transport,
        )
    assert called["n"] == 0
    store.verify()


def test_used_header_mismatch_fail_closed(tmp_path: Path) -> None:
    store = BundleStore(tmp_path)
    record_credit_use(
        store,
        {
            "x-requests-last": "100",
            "x-requests-used": "100",
            "x-requests-remaining": "50",
        },
    )
    with pytest.raises(CreditReconcileError, match="mismatch"):
        record_credit_use(
            store,
            {
                "x-requests-last": "30",
                "x-requests-used": "110",
                "x-requests-remaining": "40",
            },
        )
    assert read_cumulative(store) == 130
    assert ledger_closed(store) is True
    store.verify()


def test_fetch_provenance_envelope_redacts_key_no_live_http(tmp_path: Path) -> None:
    store = BundleStore(tmp_path)
    body = b'{"ok":true,"bookmakers":[]}'

    def transport(*, endpoint: str, params: object, headers: object) -> OddsTransportResult:
        assert "apiKey" not in dict(params)  # type: ignore[arg-type]
        assert dict(headers)["x-api-key"] == "unit-test-not-live"
        return OddsTransportResult(
            status_code=200,
            headers={
                "x-requests-last": "30",
                "x-requests-used": "30",
                "x-requests-remaining": "999",
                "Date": "Wed, 28 Oct 2026 22:00:00 GMT",
            },
            body=body,
            provider_server_ts="2026-10-28T22:00:00Z",
        )

    result = fetch_odds_with_provenance(
        store=store,
        env=_lift_env(ODDS_API_KEY="unit-test-not-live"),
        transport=transport,
        game_id="2026-W08-MIN@LAC",
    )
    envelope = result["envelope"]
    assert envelope["raw_body_sha256"] == raw_body_sha256(body)
    assert envelope["request_headers"]["x-api-key"] == "[REDACTED]"
    assert "unit-test-not-live" not in json.dumps(result)
    assert (tmp_path / "provenance.jsonl").is_file()
    with pytest.raises(OddsFetchError, match="no transport"):
        fetch_odds_with_provenance(
            store=store,
            env=_lift_env(ODDS_API_KEY="unit-test-not-live"),
        )
    store.verify()


def test_produce_seal_ac1_ac2_and_refuse_seal_ack(tmp_path: Path) -> None:
    store = BundleStore(tmp_path)
    ok = produce_seal(
        store,
        game_id="2026-W08-MIN@LAC",
        kickoff_utc=KICKOFF,
        now_utc=KICKOFF - timedelta(minutes=61),
        artifact_shas={"snapshot": "a" * 64},
    )
    assert ok["ac_1"] is True
    assert ok["custodian_receipt"]["slot"] == "AC-2"
    assert ok["custodian_receipt"]["receipt_id"] == "UNSET"
    assert ok["seal_ack"] == "CURSOR_CANNOT_SEAL_ACK"
    with pytest.raises(SealWindowError, match="60"):
        produce_seal(
            store,
            game_id="2026-W08-LATE",
            kickoff_utc=KICKOFF,
            now_utc=KICKOFF - timedelta(minutes=59),
        )
    with pytest.raises(PermissionError, match="AC-12"):
        refuse_seal([])
    store.verify()


def test_f8_90m_cutoff_encoded() -> None:
    assert F8_CUTOFF == timedelta(minutes=90)
    cutoff = f8_cutoff_utc(KICKOFF)
    assert cutoff == KICKOFF - timedelta(minutes=90)
    assert past_f8_cutoff(KICKOFF - timedelta(minutes=90), KICKOFF) is False
    assert past_f8_cutoff(KICKOFF - timedelta(minutes=89), KICKOFF) is True
    assert_slate_join_before_f8(KICKOFF - timedelta(minutes=90), KICKOFF)
    with pytest.raises(F8CutoffError):
        assert_slate_join_before_f8(KICKOFF - timedelta(minutes=89), KICKOFF)
    plan = plan_pre_kickoff_samples([GameKickoff("2026-W08-MIN@LAC", KICKOFF, "REG")])
    offsets = {KICKOFF - w.sample_at for w in plan.windows}
    assert timedelta(minutes=90) in offsets
    assert close_window_guaranteed(plan, "2026-W08-MIN@LAC")


def test_ac8_ac10_are_explicit_carve_outs() -> None:
    ids = {item["id"]: item for item in explicit_carve_outs()}
    assert ids["AC-8"]["status"] == "EXPLICIT_CARVE_OUT"
    assert ids["AC-10"]["status"] == "EXPLICIT_CARVE_OUT"
    assert require_explicit_carve_out("AC-8")["status"] == "EXPLICIT_CARVE_OUT"
    assert "invent" not in ids["AC-8"]["reason"].lower() or "not" in ids["AC-8"]["reason"].lower()


def test_control_alerts_ceiling_hold_fetch_fail(tmp_path: Path) -> None:
    from src.services.nfl_w8_capture.alerts import control_alert, deliver_alert

    store = BundleStore(tmp_path)
    for kind in ("ceiling", "hold", "fetch_fail"):
        delivery = deliver_alert(
            control_alert(kind=kind, detail=f"{kind} test", market=kind),
            store,
            env={},
        )
        assert delivery.status == "disabled"
    text = (tmp_path / "alerts.jsonl").read_text(encoding="utf-8")
    assert "ceiling" in text and "hold" in text and "fetch_fail" in text
    store.verify()
