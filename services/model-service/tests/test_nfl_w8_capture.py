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
from src.services.nfl_w8_capture.cadence import (
    GameKickoff,
    close_window_guaranteed,
    plan_pre_kickoff_samples,
    review_sample_coverage,
)
from src.services.nfl_w8_capture.close import (
    BookMarketCell,
    evaluate_game_market_close,
)
from src.services.nfl_w8_capture.evidence import (
    EvidenceChainError,
    append_evidence_entry,
    verify_evidence_chain,
    write_sha256sums,
)
from src.services.nfl_w8_capture.hold import (
    OddsApiHoldError,
    refuse_odds_fetch,
)
from src.services.nfl_w8_capture.pin import (
    UNSET_SHA,
    build_pin_manifest,
    validate_pin_manifest,
)
from src.services.nfl_w8_capture.redact import redact_secrets
from src.services.nfl_w8_capture.snapshots import append_snapshot, snapshot_content_sha
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
    append_snapshot(tmp_path, {"game_id": "2026-W08-MIN@LAC", "n": 2})
    assert (tmp_path / "snapshots.jsonl").read_text(encoding="utf-8").count("\n") == 2
    assert len(snapshot_content_sha(record["payload"])) == 64
    write_sha256sums(tmp_path, [(record["content_sha256"], "snapshots.jsonl")])
    assert (tmp_path / "SHA256SUMS").is_file()


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
