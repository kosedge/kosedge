"""H-HL-1 capture plumbing tests (t4791u). Synthetic fixtures only.

No real injury reports, odds, holdouts, or live acquisition.
Does not import nowcast or the simulator.
"""

from __future__ import annotations

import ast
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.services.nfl_hhl1_capture import (
    ADMITTED_SOURCE_ID,
    CALIBRATION_2013_2025_CLAIM,
    DECISION_OFFSET_BEFORE_KICKOFF_MINUTES,
    HHL1_LIVE_CAPTURE_AUTHORIZED,
    HHL1_NOWCAST_AUTHORIZED,
    HHL1_PUBLICATION_AUTHORIZED,
    HHL1_SCORING_AUTHORIZED,
    MISSINGNESS_NOT_PUBLISHED,
    MISSINGNESS_SOURCE_DOWN,
    PARENT_PAPER_SHA8,
    PROTOCOL_SHA256,
    RATING_WINDOW_DEFINITION,
    SIMULATOR_EXECUTABLE_IDENTITY,
    SIMULATOR_SHA_PROTOCOL_PIN,
    SIMULATOR_SHA_TIP_BYTES,
    SNAP_SHARE_THRESHOLD,
    BaselinePersonnelRef,
    CaptureTimestamps,
    DeltaPlayer,
    ExpectedStarter,
    Hhl1Reject,
    Hhl1RejectCode,
    L1AvailabilityRow,
    SourceProvenance,
    acquire_odds,
    acquire_official_report,
    assert_no_delta_constant_overrides,
    build_baseline_personnel_ref,
    expected_decision_ts,
    fetch_nowcast,
    forbidden_import_names,
    handle_unavailable,
    make_baseline_ref_sha,
    make_capture_id,
    make_source_snapshot_id,
    publish,
    reconstruct_historical,
    score_l1,
    select_admitted_source,
    validate_l1_batch,
    validate_l1_candidate,
    verify_plumbing_inert,
)
from src.services.nfl_hhl1_capture.constants import (
    COS_ACCEPT_SHA256,
    DECISION_SHA256,
    NOWCAST_TABLE_SHA256,
    ORDER_SHA256,
    PARSER_VERSION_PLUMBING,
    PASS_PROTOCOL_SHA256,
    SCHEMA_VERSION,
)

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "services" / "nfl_hhl1_capture"

KICKOFF = datetime(2026, 11, 8, 18, 0, tzinfo=timezone.utc)
DECISION = KICKOFF - timedelta(minutes=DECISION_OFFSET_BEFORE_KICKOFF_MINUTES)
CAPTURED = DECISION - timedelta(minutes=15)
PUBLISHED = CAPTURED - timedelta(minutes=10)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _synth_ids(*suffixes: str) -> tuple[str, ...]:
    return tuple(f"00-SYNTH-{s}" for s in suffixes)


def _baseline(team: str = "SYN") -> BaselinePersonnelRef:
    ids = _synth_ids("QB1", "WR1", "RB1", "TE1", "OL1")
    return BaselinePersonnelRef(
        team=team,
        player_ids=ids,
        snap_share_threshold=SNAP_SHARE_THRESHOLD,
        rating_window=RATING_WINDOW_DEFINITION,
        source_id="nflverse_snap_counts",
        as_of_completed_week="2026-W99-SYNTH",
        ref_sha256=make_baseline_ref_sha(ids, team=team),
    )


def _starters() -> tuple[ExpectedStarter, ...]:
    return (
        ExpectedStarter("00-SYNTH-QB1", "QB"),
        ExpectedStarter("00-SYNTH-WR1", "WR"),
        ExpectedStarter("00-SYNTH-RB1", "RB"),
        ExpectedStarter("00-SYNTH-TE1", "TE"),
        ExpectedStarter("00-SYNTH-OL1", "OL"),
    )


def _row_parts(**overrides: object) -> L1AvailabilityRow:
    team = str(overrides.get("team") or "SYN")
    baseline = overrides.get("baseline_personnel_ref") or _baseline(team)
    starters = overrides.get("expected_starters_asof") or _starters()
    delta = overrides.get("delta_players")
    if delta is None:
        delta = (
            DeltaPlayer(
                player_id="00-SYNTH-WR2",
                position="WR",
                report_status="Out",
            ),
        )
    timestamps = overrides.get("timestamps") or CaptureTimestamps(
        source_published_at=_iso(PUBLISHED),
        captured_at=_iso(CAPTURED),
        decision_ts=_iso(DECISION),
        kickoff_ts=_iso(KICKOFF),
    )
    provenance = overrides.get("provenance") or SourceProvenance(
        source_id=ADMITTED_SOURCE_ID,
        source_url="https://example.test/synth/official-nfl-injury-report",
        source_snapshot_id=make_source_snapshot_id(b"synthetic-official-report-bytes-v0"),
        parser_version=PARSER_VERSION_PLUMBING,
        protocol_sha=PROTOCOL_SHA256,
    )
    pending = L1AvailabilityRow(
        capture_id="pending",
        game_id=str(overrides.get("game_id") or "2026_99_TST_SYN"),
        team=team,
        factor="availability",
        as_of_ts=timestamps.captured_at,
        timestamps=timestamps,
        baseline_personnel_ref=baseline,  # type: ignore[arg-type]
        expected_starters_asof=starters,  # type: ignore[arg-type]
        registry_id=str(overrides.get("registry_id") or "hhl1-synth-registry"),
        provenance=provenance,  # type: ignore[arg-type]
        offense_raw=float(overrides.get("offense_raw") or 0.0),
        defense_raw=float(overrides.get("defense_raw") or 0.0),
        offense_multiplier=float(overrides.get("offense_multiplier") or 1.0),
        defense_multiplier=float(overrides.get("defense_multiplier") or 1.0),
        delta_players=delta,  # type: ignore[arg-type]
        missing_enum=str(overrides.get("missing_enum") or "OBSERVED"),
        supersedes_capture_id=overrides.get("supersedes_capture_id"),  # type: ignore[arg-type]
        uncertainty=overrides.get("uncertainty", None),
        schema_version=str(overrides.get("schema_version") or SCHEMA_VERSION),
    )
    capture_id = make_capture_id(
        payload=pending.identity_payload(),
        source_id=pending.provenance.source_id,
        source_published_at=pending.timestamps.source_published_at,
        captured_at=pending.timestamps.captured_at,
    )
    return L1AvailabilityRow(
        capture_id=capture_id,
        game_id=pending.game_id,
        team=pending.team,
        factor=pending.factor,
        as_of_ts=pending.as_of_ts,
        timestamps=pending.timestamps,
        baseline_personnel_ref=pending.baseline_personnel_ref,
        expected_starters_asof=pending.expected_starters_asof,
        registry_id=pending.registry_id,
        provenance=pending.provenance,
        offense_raw=pending.offense_raw,
        defense_raw=pending.defense_raw,
        offense_multiplier=pending.offense_multiplier,
        defense_multiplier=pending.defense_multiplier,
        delta_players=pending.delta_players,
        missing_enum=pending.missing_enum,
        supersedes_capture_id=pending.supersedes_capture_id,
        uncertainty=pending.uncertainty,
        schema_version=pending.schema_version,
    )


def synthetic_row(**overrides: object) -> dict:
    return _row_parts(**overrides).to_dict()


# --- schema / happy path -------------------------------------------------


def test_valid_synthetic_row_accepts() -> None:
    admitted = validate_l1_candidate(synthetic_row())
    assert admitted.factor == "availability"
    assert admitted.missing_enum == "OBSERVED"
    assert admitted.uncertainty is None
    assert admitted.provenance.source_id == ADMITTED_SOURCE_ID
    assert admitted.baseline_personnel_ref.rating_window == "UNRESOLVED"
    assert admitted.baseline_personnel_ref.snap_share_threshold == 0.50
    assert expected_decision_ts(admitted.timestamps.kickoff_ts) == admitted.decision_ts


def test_batch_accepts_two_teams() -> None:
    home = synthetic_row(team="SYN", game_id="2026_99_TST_SYN")
    away_parts = _row_parts(team="TST", game_id="2026_99_TST_SYN")
    away = away_parts.to_dict()
    rows = validate_l1_batch([home, away])
    assert {r.team for r in rows} == {"SYN", "TST"}


def test_authority_pins_match_clear() -> None:
    assert DECISION_SHA256.startswith("2806545b")
    assert ORDER_SHA256.startswith("e0159e65")
    assert PROTOCOL_SHA256.startswith("a9f1c28f")
    assert PASS_PROTOCOL_SHA256.startswith("d359ce54")
    assert COS_ACCEPT_SHA256.startswith("3d80968f")
    assert PARENT_PAPER_SHA8 == "7b4d70ac"
    assert SIMULATOR_SHA_PROTOCOL_PIN == "9b61c5c3"
    assert SIMULATOR_SHA_TIP_BYTES == "52d9e909"
    assert SIMULATOR_SHA_PROTOCOL_PIN != SIMULATOR_SHA_TIP_BYTES
    assert "UNRESOLVED" in SIMULATOR_EXECUTABLE_IDENTITY
    assert CALIBRATION_2013_2025_CLAIM == "UNVERIFIED"
    assert RATING_WINDOW_DEFINITION == "UNRESOLVED"
    assert NOWCAST_TABLE_SHA256.startswith("73cad579")


# --- required fields / provenance ----------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "capture_id",
        "game_id",
        "team",
        "source_published_at",
        "captured_at",
        "decision_ts",
        "kickoff_ts",
        "baseline_personnel_ref",
        "source_snapshot_id",
        "registry_id",
        "provenance",
    ],
)
def test_missing_required_field_rejects(field: str) -> None:
    row = synthetic_row()
    if field == "source_snapshot_id":
        row.pop(field, None)
        row["provenance"] = dict(row["provenance"])
        row["provenance"].pop("source_snapshot_id", None)
    else:
        row.pop(field, None)
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(row)
    assert exc.value.code in {
        Hhl1RejectCode.MISSING_REQUIRED_FIELD,
        Hhl1RejectCode.PROVENANCE_INCOMPLETE,
        Hhl1RejectCode.SCHEMA_MISMATCH,
    }


def test_naive_timestamp_rejects() -> None:
    row = synthetic_row()
    row["captured_at"] = "2026-11-08T16:15:00"
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(row)
    assert exc.value.code in {Hhl1RejectCode.SCHEMA_MISMATCH, Hhl1RejectCode.PROVENANCE_INCOMPLETE}


def test_wrong_protocol_sha_rejects() -> None:
    prov = SourceProvenance(
        source_id=ADMITTED_SOURCE_ID,
        source_url="https://example.test/synth/official-nfl-injury-report",
        source_snapshot_id=make_source_snapshot_id(b"synthetic-official-report-bytes-v0"),
        parser_version=PARSER_VERSION_PLUMBING,
        protocol_sha="deadbeef" * 8,
    )
    row = _row_parts(provenance=prov).to_dict()
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(row)
    assert exc.value.code == Hhl1RejectCode.PROVENANCE_INCOMPLETE


def test_non_hex_snapshot_rejects() -> None:
    row = synthetic_row()
    row["source_snapshot_id"] = "not-a-sha"
    row["provenance"] = dict(row["provenance"], source_snapshot_id="not-a-sha")
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(row)
    assert exc.value.code == Hhl1RejectCode.PROVENANCE_INCOMPLETE


# --- stale / late / as-of / cutoff ---------------------------------------


def test_late_captured_after_decision_rejects() -> None:
    late_cap = DECISION + timedelta(minutes=1)
    ts = CaptureTimestamps(
        source_published_at=_iso(PUBLISHED),
        captured_at=_iso(late_cap),
        decision_ts=_iso(DECISION),
        kickoff_ts=_iso(KICKOFF),
    )
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(timestamps=ts).to_dict())
    assert exc.value.code == Hhl1RejectCode.LATE


def test_stale_captured_after_kickoff_rejects() -> None:
    post = KICKOFF + timedelta(minutes=5)
    ts = CaptureTimestamps(
        source_published_at=_iso(PUBLISHED),
        captured_at=_iso(post),
        decision_ts=_iso(DECISION),
        kickoff_ts=_iso(KICKOFF),
    )
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(timestamps=ts).to_dict())
    assert exc.value.code == Hhl1RejectCode.STALE


def test_as_of_published_after_captured_rejects() -> None:
    ts = CaptureTimestamps(
        source_published_at=_iso(CAPTURED + timedelta(minutes=1)),
        captured_at=_iso(CAPTURED),
        decision_ts=_iso(DECISION),
        kickoff_ts=_iso(KICKOFF),
    )
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(timestamps=ts).to_dict())
    assert exc.value.code == Hhl1RejectCode.AS_OF_VIOLATION


def test_cutoff_not_90m_rejects() -> None:
    ts = CaptureTimestamps(
        source_published_at=_iso(PUBLISHED),
        captured_at=_iso(CAPTURED),
        decision_ts=_iso(KICKOFF - timedelta(minutes=60)),
        kickoff_ts=_iso(KICKOFF),
    )
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(timestamps=ts).to_dict())
    assert exc.value.code == Hhl1RejectCode.CUTOFF_MISMATCH


def test_as_of_ts_must_equal_captured_at() -> None:
    row = synthetic_row()
    row["as_of_ts"] = _iso(PUBLISHED)
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(row)
    assert exc.value.code == Hhl1RejectCode.AS_OF_VIOLATION


# --- ambiguous / duplicate -----------------------------------------------


def test_conflicting_player_status_rejects() -> None:
    delta = (
        DeltaPlayer(player_id="00-SYNTH-WR2", position="WR", report_status="Out"),
        DeltaPlayer(player_id="00-SYNTH-WR2", position="WR", report_status="Questionable"),
    )
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(delta_players=delta).to_dict())
    assert exc.value.code == Hhl1RejectCode.AMBIGUOUS


def test_out_player_still_starting_rejects() -> None:
    delta = (DeltaPlayer(player_id="00-SYNTH-WR1", position="WR", report_status="Out"),)
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(delta_players=delta).to_dict())
    assert exc.value.code == Hhl1RejectCode.AMBIGUOUS


def test_questionable_may_remain_starter() -> None:
    delta = (DeltaPlayer(player_id="00-SYNTH-WR1", position="WR", report_status="Questionable"),)
    admitted = validate_l1_candidate(_row_parts(delta_players=delta).to_dict())
    assert any(p.report_status == "Questionable" for p in admitted.delta_players)
    assert any(s.player_id == "00-SYNTH-WR1" for s in admitted.expected_starters_asof)


def test_two_qb_delta_rows_reject() -> None:
    delta = (
        DeltaPlayer(player_id="00-SYNTH-QB1", position="QB", report_status="Out"),
        DeltaPlayer(player_id="00-SYNTH-QB2", position="QB", report_status="Doubtful"),
    )
    starters = tuple(s for s in _starters() if s.player_id != "00-SYNTH-QB1")
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(delta_players=delta, expected_starters_asof=starters).to_dict())
    assert exc.value.code == Hhl1RejectCode.AMBIGUOUS


def test_duplicate_capture_id_in_batch_rejects() -> None:
    row = synthetic_row()
    clone = copy.deepcopy(row)
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_batch([row, clone])
    assert exc.value.code == Hhl1RejectCode.DUPLICATE


def test_duplicate_business_identity_rejects() -> None:
    first = synthetic_row()
    # Different capture stamps → different capture_id, same snapshot/game/team.
    later = CAPTURED + timedelta(minutes=1)
    ts = CaptureTimestamps(
        source_published_at=_iso(PUBLISHED),
        captured_at=_iso(later),
        decision_ts=_iso(DECISION),
        kickoff_ts=_iso(KICKOFF),
    )
    second = _row_parts(timestamps=ts).to_dict()
    assert first["capture_id"] != second["capture_id"]
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_batch([first, second])
    assert exc.value.code == Hhl1RejectCode.DUPLICATE


def test_tampered_capture_id_rejects() -> None:
    row = synthetic_row()
    row["capture_id"] = "0" * 64
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(row)
    assert exc.value.code == Hhl1RejectCode.IDENTITY_MISMATCH


# --- nowcast OFF / market / unsupported source ---------------------------


def test_nowcast_source_id_rejects() -> None:
    with pytest.raises(Hhl1Reject) as exc:
        select_admitted_source("nfl_injury_nowcast")
    assert exc.value.code == Hhl1RejectCode.NOWCAST_OFF


def test_nowcast_field_name_on_l1_rejects() -> None:
    row = synthetic_row()
    row["injury_nowcast_offense_multiplier"] = 0.91
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(row)
    assert exc.value.code == Hhl1RejectCode.NOWCAST_OFF
    assert "R4" in str(exc.value)


def test_nowcast_url_rejects() -> None:
    prov = SourceProvenance(
        source_id=ADMITTED_SOURCE_ID,
        source_url="https://example.test/nowcast-surface",
        source_snapshot_id=make_source_snapshot_id(b"synthetic-official-report-bytes-v0"),
        parser_version=PARSER_VERSION_PLUMBING,
        protocol_sha=PROTOCOL_SHA256,
    )
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(provenance=prov).to_dict())
    assert exc.value.code == Hhl1RejectCode.NOWCAST_OFF


def test_postgres_injury_source_rejects() -> None:
    with pytest.raises(Hhl1Reject) as exc:
        select_admitted_source("postgres_injuries")
    assert exc.value.code == Hhl1RejectCode.NOWCAST_OFF


def test_news_feed_source_rejects() -> None:
    with pytest.raises(Hhl1Reject) as exc:
        select_admitted_source("news_feed")
    assert exc.value.code == Hhl1RejectCode.UNSUPPORTED_SOURCE


def test_market_field_on_l1_rejects() -> None:
    row = synthetic_row()
    row["market_line"] = -3.5
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(row)
    assert exc.value.code == Hhl1RejectCode.MARKET_IN_L1


def test_weights_without_table_sha_reject() -> None:
    delta = (
        DeltaPlayer(
            player_id="00-SYNTH-WR2",
            position="WR",
            report_status="Out",
            status_weight=1.0,
        ),
    )
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(delta_players=delta).to_dict())
    assert exc.value.code == Hhl1RejectCode.PROVENANCE_INCOMPLETE


def test_weights_with_opaque_table_pin_accept() -> None:
    delta = (
        DeltaPlayer(
            player_id="00-SYNTH-WR2",
            position="WR",
            report_status="Out",
            status_weight=1.0,
            table_sha=NOWCAST_TABLE_SHA256,
        ),
    )
    admitted = validate_l1_candidate(_row_parts(delta_players=delta).to_dict())
    assert admitted.delta_players[0].table_sha == NOWCAST_TABLE_SHA256
    assert CALIBRATION_2013_2025_CLAIM == "UNVERIFIED"


def test_invented_rating_window_rejects() -> None:
    ids = _synth_ids("QB1", "WR1", "RB1", "TE1", "OL1")
    baseline = BaselinePersonnelRef(
        team="SYN",
        player_ids=ids,
        snap_share_threshold=SNAP_SHARE_THRESHOLD,
        rating_window="last_4_games",
        source_id="nflverse_snap_counts",
        as_of_completed_week="2026-W99-SYNTH",
        ref_sha256=make_baseline_ref_sha(ids, team="SYN"),
    )
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(baseline_personnel_ref=baseline).to_dict())
    assert exc.value.code == Hhl1RejectCode.RATING_WINDOW_UNRESOLVED


def test_uncertainty_not_null_rejects() -> None:
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(_row_parts(uncertainty=0.0).to_dict())
    assert exc.value.code == Hhl1RejectCode.UNCERTAINTY_NOT_NULL


# --- fail-closed unavailable + disabled paths ----------------------------


def test_source_down_is_exclusion_not_imputed_row() -> None:
    excluded = handle_unavailable(
        game_id="2026_99_TST_SYN",
        team="SYN",
        missing_enum=MISSINGNESS_SOURCE_DOWN,
        reason="synthetic source down",
    )
    assert excluded.missing is True
    assert excluded.missing_enum == MISSINGNESS_SOURCE_DOWN
    assert excluded.reject_code == Hhl1RejectCode.UNAVAILABLE
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(synthetic_row(missing_enum=MISSINGNESS_SOURCE_DOWN))
    assert exc.value.code == Hhl1RejectCode.UNAVAILABLE


def test_not_published_is_exclusion() -> None:
    excluded = handle_unavailable(
        game_id="2026_99_TST_SYN",
        team="TST",
        missing_enum=MISSINGNESS_NOT_PUBLISHED,
        reason="synthetic report not published",
    )
    assert excluded.missing_enum == MISSINGNESS_NOT_PUBLISHED


@pytest.mark.parametrize(
    "fn,code",
    [
        (acquire_official_report, Hhl1RejectCode.NOT_AUTHORIZED),
        (fetch_nowcast, Hhl1RejectCode.NOWCAST_OFF),
        (acquire_odds, Hhl1RejectCode.NOT_AUTHORIZED),
        (score_l1, Hhl1RejectCode.NOT_AUTHORIZED),
        (publish, Hhl1RejectCode.NOT_AUTHORIZED),
        (build_baseline_personnel_ref, Hhl1RejectCode.RATING_WINDOW_UNRESOLVED),
        (reconstruct_historical, Hhl1RejectCode.NOT_AUTHORIZED),
    ],
)
def test_live_paths_fail_closed(fn, code: Hhl1RejectCode) -> None:
    with pytest.raises(Hhl1Reject) as exc:
        fn()
    assert exc.value.code == code


def test_env_cannot_enable_live_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HHL1_LIVE_CAPTURE", "true")
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(synthetic_row())
    assert exc.value.code == Hhl1RejectCode.NOT_AUTHORIZED


def test_env_cannot_enable_nowcast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HHL1_NOWCAST_ENABLED", "1")
    with pytest.raises(Hhl1Reject) as exc:
        validate_l1_candidate(synthetic_row())
    assert exc.value.code == Hhl1RejectCode.NOT_AUTHORIZED


def test_delta_constant_overrides_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NFL_INJURY_IMPACT_SCALE", "0.50")
    with pytest.raises(Hhl1Reject) as exc:
        assert_no_delta_constant_overrides()
    assert exc.value.code == Hhl1RejectCode.NOT_AUTHORIZED


def test_verify_plumbing_inert() -> None:
    report = verify_plumbing_inert()
    assert report["inert"] is True
    assert report["live_capture"] is False
    assert report["nowcast"] is False
    assert report["scoring"] is False
    assert report["publication"] is False
    assert HHL1_LIVE_CAPTURE_AUTHORIZED is False
    assert HHL1_NOWCAST_AUTHORIZED is False
    assert HHL1_SCORING_AUTHORIZED is False
    assert HHL1_PUBLICATION_AUTHORIZED is False
    assert SIMULATOR_EXECUTABLE_IDENTITY == "UNRESOLVED_CONFLICT_9b61c5c3_vs_52d9e909"


def test_package_does_not_import_acquisition_or_scoring() -> None:
    forbidden = forbidden_import_names()
    for path in PACKAGE_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.add(node.module.split(".")[0])
        overlap = imported & forbidden
        assert not overlap, f"{path.name} imports forbidden {overlap}"


def test_plumbing_not_wired_to_live_callers() -> None:
    src_root = PACKAGE_DIR.parents[1]
    hits: list[str] = []
    for path in src_root.rglob("*.py"):
        if PACKAGE_DIR in path.parents or path.parent == PACKAGE_DIR:
            continue
        text = path.read_text(encoding="utf-8")
        if "nfl_hhl1_capture" in text:
            hits.append(str(path.relative_to(src_root)))
    assert hits == []


def test_package_does_not_mention_real_holdout_or_odds_calls() -> None:
    for path in PACKAGE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "the-odds-api.com" not in text.lower()
        assert "holdout/" not in text
        assert "predictions.csv" not in text
