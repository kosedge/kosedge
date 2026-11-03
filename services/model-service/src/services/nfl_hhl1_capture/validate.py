"""Deterministic H-HL-1 capture validation.

Rejects stale, late, ambiguous, duplicated, or provenance-incomplete inputs.
No imputation. No nowcast. No market fields. No live I/O.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from src.services.nfl_hhl1_capture.constants import (
    ADMITTED_SOURCE_ID,
    BASELINE_INPUT_SOURCE_ID,
    CALIBRATION_2013_2025_CLAIM,
    FACTOR_AVAILABILITY,
    MARKET_FIELD_NAMES,
    MISSINGNESS_ENUM,
    MISSINGNESS_OBSERVED,
    NOWCAST_TABLE_SHA256,
    NOWCAST_TABLE_SHA8,
    PARSER_VERSION_PLUMBING,
    PROTOCOL_SHA256,
    QUESTIONABLE_KEPT,
    QUESTIONABLE_STATUS,
    RATING_WINDOW_DEFINITION,
    SCHEMA_VERSION,
    SNAP_SHARE_THRESHOLD,
    STARTER_REMOVING_STATUSES,
)
from src.services.nfl_hhl1_capture.gates import (
    assert_activation_locked,
    assert_nowcast_off,
    collect_nowcast_markers,
    reject_nowcast_fields,
    select_admitted_source,
)
from src.services.nfl_hhl1_capture.identity import (
    canonicalize_utc,
    expected_decision_ts,
    is_sha256_hex,
    is_team_code,
    make_baseline_ref_sha,
    make_capture_id,
    parse_utc,
    require_protocol_sha,
)
from src.services.nfl_hhl1_capture.schema import (
    L1_REQUIRED_FIELDS,
    PROVENANCE_REQUIRED_FIELDS,
    BaselinePersonnelRef,
    CaptureBatchIndex,
    CaptureTimestamps,
    DeltaPlayer,
    ExpectedStarter,
    Hhl1Reject,
    Hhl1RejectCode,
    L1AvailabilityRow,
    SourceProvenance,
)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _as_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"{name} must be an object (no impute)",
        )
    return value


def _nested(row: Mapping[str, Any], name: str) -> Any:
    if name in row and _present(row.get(name)):
        return row.get(name)
    provenance = row.get("provenance")
    if isinstance(provenance, Mapping) and name in provenance and _present(provenance.get(name)):
        return provenance.get(name)
    timestamps = row.get("timestamps")
    if isinstance(timestamps, Mapping) and name in timestamps and _present(timestamps.get(name)):
        return timestamps.get(name)
    return None


def _conflict(row: Mapping[str, Any], left: str, right: Any, *, field: str) -> None:
    if field not in row or not _present(row.get(field)) or not _present(right):
        return
    if field.endswith("_ts") or field.endswith("_at"):
        if canonicalize_utc(row.get(field), field=field) != canonicalize_utc(right, field=field):
            raise Hhl1Reject(
                Hhl1RejectCode.AMBIGUOUS,
                f"top-level {field} conflicts with nested value (no precedence)",
            )
        return
    if row.get(field) != right:
        raise Hhl1Reject(
            Hhl1RejectCode.AMBIGUOUS,
            f"top-level {field} conflicts with nested value (no precedence)",
        )


def reject_market_fields(row: Mapping[str, Any]) -> None:
    keys = set(row.keys())
    provenance = row.get("provenance")
    if isinstance(provenance, Mapping):
        keys.update(provenance.keys())
    hit = sorted(k for k in keys if k in MARKET_FIELD_NAMES or k.startswith("market_"))
    if hit:
        raise Hhl1Reject(
            Hhl1RejectCode.MARKET_IN_L1,
            f"L1 contains market fields {hit} (O-c; reject test vii)",
        )


def _require_fields(row: Mapping[str, Any], names: Sequence[str], *, code: Hhl1RejectCode) -> None:
    missing = [name for name in names if not _present(_nested(row, name))]
    if missing:
        raise Hhl1Reject(code, f"missing required fields {missing} (no impute)")


def _parse_baseline(raw: Any, *, team: str) -> BaselinePersonnelRef:
    mapping = _as_mapping(raw, name="baseline_personnel_ref")
    ref = BaselinePersonnelRef.from_mapping(mapping)
    if not is_team_code(ref.team):
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"baseline_personnel_ref.team invalid: {ref.team!r}",
        )
    if ref.team != team:
        raise Hhl1Reject(
            Hhl1RejectCode.AMBIGUOUS,
            f"baseline team {ref.team!r} != row team {team!r}",
        )
    if ref.source_id != BASELINE_INPUT_SOURCE_ID:
        raise Hhl1Reject(
            Hhl1RejectCode.UNSUPPORTED_SOURCE,
            f"baseline source_id must be {BASELINE_INPUT_SOURCE_ID} (got {ref.source_id!r})",
        )
    if not _present(ref.as_of_completed_week):
        raise Hhl1Reject(
            Hhl1RejectCode.PROVENANCE_INCOMPLETE,
            "baseline as_of_completed_week missing (no impute)",
        )
    if ref.rating_window != RATING_WINDOW_DEFINITION:
        raise Hhl1Reject(
            Hhl1RejectCode.RATING_WINDOW_UNRESOLVED,
            "rating_window must be the literal UNRESOLVED; do not invent a window (R3)",
        )
    if not isinstance(ref.snap_share_threshold, (int, float)) or isinstance(
        ref.snap_share_threshold, bool
    ):
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            "snap_share_threshold must be numeric (no impute)",
        )
    if float(ref.snap_share_threshold) != SNAP_SHARE_THRESHOLD:
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"snap_share_threshold must be {SNAP_SHARE_THRESHOLD} (provisional R3)",
        )
    if not ref.player_ids or any(not str(p).strip() for p in ref.player_ids):
        raise Hhl1Reject(
            Hhl1RejectCode.PROVENANCE_INCOMPLETE,
            "baseline player_ids missing/empty (no impute)",
        )
    expected_sha = make_baseline_ref_sha(ref.player_ids, team=ref.team)
    if not is_sha256_hex(ref.ref_sha256):
        raise Hhl1Reject(
            Hhl1RejectCode.PROVENANCE_INCOMPLETE,
            "baseline ref_sha256 must be sha256 hex",
        )
    if ref.ref_sha256 != expected_sha:
        raise Hhl1Reject(
            Hhl1RejectCode.IDENTITY_MISMATCH,
            "baseline ref_sha256 does not match hashed player_ids",
        )
    return ref


def _parse_starters(raw: Any) -> Tuple[ExpectedStarter, ...]:
    if not isinstance(raw, list):
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            "expected_starters_asof must be a list (no impute)",
        )
    starters: List[ExpectedStarter] = []
    seen: set[str] = set()
    for item in raw:
        mapping = _as_mapping(item, name="expected_starter")
        player_id = str(mapping.get("player_id") or "").strip()
        position = str(mapping.get("position") or "").strip()
        if not player_id or not position:
            raise Hhl1Reject(
                Hhl1RejectCode.PROVENANCE_INCOMPLETE,
                "expected starter missing player_id/position (no impute)",
            )
        if player_id in seen:
            raise Hhl1Reject(
                Hhl1RejectCode.DUPLICATE,
                f"duplicate expected starter {player_id}",
            )
        seen.add(player_id)
        starters.append(ExpectedStarter(player_id=player_id, position=position))
    if not starters:
        raise Hhl1Reject(
            Hhl1RejectCode.PROVENANCE_INCOMPLETE,
            "expected_starters_asof empty (no impute)",
        )
    return tuple(starters)


def _parse_delta_players(raw: Any) -> Tuple[DeltaPlayer, ...]:
    if not isinstance(raw, list):
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            "delta_players must be a list (no impute)",
        )
    players: List[DeltaPlayer] = []
    seen: Dict[str, str] = {}
    qb_count = 0
    for item in raw:
        mapping = _as_mapping(item, name="delta_player")
        player = DeltaPlayer.from_mapping(mapping)
        if not player.player_id or not player.position or not player.report_status:
            raise Hhl1Reject(
                Hhl1RejectCode.PROVENANCE_INCOMPLETE,
                "delta player missing player_id/position/report_status (no impute)",
            )
        status_key = player.report_status.strip().lower()
        prior = seen.get(player.player_id)
        if prior is not None and prior != status_key:
            raise Hhl1Reject(
                Hhl1RejectCode.AMBIGUOUS,
                f"player {player.player_id} has conflicting report_status {prior!r} vs {status_key!r}",
            )
        if prior is not None:
            raise Hhl1Reject(
                Hhl1RejectCode.DUPLICATE,
                f"duplicate delta player {player.player_id}",
            )
        seen[player.player_id] = status_key
        if player.position.strip().upper() == "QB":
            qb_count += 1
        if player.table_sha is not None:
            digest = player.table_sha.strip().lower()
            if digest not in {NOWCAST_TABLE_SHA256, NOWCAST_TABLE_SHA8}:
                raise Hhl1Reject(
                    Hhl1RejectCode.IDENTITY_MISMATCH,
                    f"delta table_sha must pin {NOWCAST_TABLE_SHA8} (got {player.table_sha!r})",
                )
            # R2: pin is opaque. Calibration claim stays UNVERIFIED.
            if CALIBRATION_2013_2025_CLAIM != "UNVERIFIED":
                raise Hhl1Reject(
                    Hhl1RejectCode.NOT_AUTHORIZED,
                    "calibration claim must remain UNVERIFIED (R2)",
                )
        weight_present = any(
            value is not None
            for value in (
                player.status_weight,
                player.practice_weight,
                player.position_weight_offense,
                player.position_weight_defense,
                player.injury_weight,
                player.player_impact,
            )
        )
        if weight_present and player.table_sha is None:
            raise Hhl1Reject(
                Hhl1RejectCode.PROVENANCE_INCOMPLETE,
                "recorded weights require table_sha=73cad579 (opaque pin; no nowcast)",
            )
        players.append(player)
    if qb_count > 1:
        raise Hhl1Reject(
            Hhl1RejectCode.AMBIGUOUS,
            "QB excluded from cluster double-application (single registry row)",
        )
    return tuple(players)


def _parse_provenance(row: Mapping[str, Any]) -> SourceProvenance:
    raw = row.get("provenance")
    mapping = _as_mapping(raw, name="provenance") if _present(raw) else row
    _require_fields(mapping, PROVENANCE_REQUIRED_FIELDS, code=Hhl1RejectCode.PROVENANCE_INCOMPLETE)
    source_id = select_admitted_source(mapping.get("source_id"))
    source_url = str(mapping.get("source_url")).strip()
    if not source_url:
        raise Hhl1Reject(Hhl1RejectCode.PROVENANCE_INCOMPLETE, "source_url missing (no impute)")
    nowcast_hits = collect_nowcast_markers(
        [source_id, source_url, str(mapping.get("parser_version") or "")]
    )
    if nowcast_hits:
        raise Hhl1Reject(
            Hhl1RejectCode.NOWCAST_OFF,
            f"nowcast markers in provenance {nowcast_hits} (R4)",
        )
    snapshot = str(mapping.get("source_snapshot_id")).strip().lower()
    if not is_sha256_hex(snapshot):
        raise Hhl1Reject(
            Hhl1RejectCode.PROVENANCE_INCOMPLETE,
            "source_snapshot_id must be sha256 hex of raw bytes",
        )
    parser_version = str(mapping.get("parser_version")).strip()
    if parser_version != PARSER_VERSION_PLUMBING:
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"parser_version must be {PARSER_VERSION_PLUMBING} until a parser CLEAR",
        )
    protocol_sha = require_protocol_sha(mapping.get("protocol_sha"))
    table_sha = mapping.get("table_sha")
    normalized_table: Optional[str] = None
    if _present(table_sha):
        digest = str(table_sha).strip().lower()
        if digest not in {NOWCAST_TABLE_SHA256, NOWCAST_TABLE_SHA8}:
            raise Hhl1Reject(
                Hhl1RejectCode.IDENTITY_MISMATCH,
                f"table_sha must pin {NOWCAST_TABLE_SHA8} (got {table_sha!r})",
            )
        normalized_table = NOWCAST_TABLE_SHA256
    top_snapshot = _nested(row, "source_snapshot_id")
    if _present(top_snapshot) and str(top_snapshot).strip().lower() != snapshot:
        raise Hhl1Reject(
            Hhl1RejectCode.AMBIGUOUS,
            "source_snapshot_id conflicts between row and provenance",
        )
    return SourceProvenance(
        source_id=source_id,
        source_url=source_url,
        source_snapshot_id=snapshot,
        parser_version=parser_version,
        protocol_sha=protocol_sha,
        table_sha=normalized_table,
    )


def _parse_timestamps(row: Mapping[str, Any]) -> CaptureTimestamps:
    source_published_at = canonicalize_utc(
        _nested(row, "source_published_at"), field="source_published_at"
    )
    captured_at = canonicalize_utc(_nested(row, "captured_at"), field="captured_at")
    decision_ts = canonicalize_utc(_nested(row, "decision_ts"), field="decision_ts")
    kickoff_ts = canonicalize_utc(_nested(row, "kickoff_ts"), field="kickoff_ts")

    published = parse_utc(source_published_at, field="source_published_at")
    captured = parse_utc(captured_at, field="captured_at")
    decision = parse_utc(decision_ts, field="decision_ts")
    kickoff = parse_utc(kickoff_ts, field="kickoff_ts")

    expected = expected_decision_ts(kickoff_ts)
    if decision_ts != expected:
        raise Hhl1Reject(
            Hhl1RejectCode.CUTOFF_MISMATCH,
            f"decision_ts must be kickoff − 90m ({expected}); got {decision_ts} (R3 provisional)",
        )
    if captured > kickoff or published > kickoff:
        raise Hhl1Reject(
            Hhl1RejectCode.STALE,
            "source_published_at/captured_at after kickoff (post-kickoff / stale)",
        )
    if captured > decision or published > decision:
        raise Hhl1Reject(
            Hhl1RejectCode.LATE,
            "source_published_at/captured_at after decision_ts (late vs kickoff−90m)",
        )
    if not (published <= captured <= decision):
        raise Hhl1Reject(
            Hhl1RejectCode.AS_OF_VIOLATION,
            "require source_published_at ≤ captured_at ≤ decision_ts",
        )
    return CaptureTimestamps(
        source_published_at=source_published_at,
        captured_at=captured_at,
        decision_ts=decision_ts,
        kickoff_ts=kickoff_ts,
    )


def _check_starter_consistency(
    baseline: BaselinePersonnelRef,
    starters: Sequence[ExpectedStarter],
    delta_players: Sequence[DeltaPlayer],
) -> None:
    baseline_ids = set(baseline.player_ids)
    starter_ids = {s.player_id for s in starters}
    extra = starter_ids - baseline_ids
    if extra:
        raise Hhl1Reject(
            Hhl1RejectCode.AMBIGUOUS,
            f"expected_starters_asof not subset of baseline: {sorted(extra)}",
        )
    removed = {
        p.player_id
        for p in delta_players
        if p.report_status.strip().lower() in STARTER_REMOVING_STATUSES
    }
    still_starting = starter_ids & removed
    if still_starting:
        raise Hhl1Reject(
            Hhl1RejectCode.AMBIGUOUS,
            f"Out/Doubtful/IR still listed as expected starters: {sorted(still_starting)}",
        )
    # R3: Questionable is kept at the provisional status weight. Weight is
    # not applied here (no scoring). Q players may remain in expected_starters.
    if QUESTIONABLE_KEPT:
        _ = QUESTIONABLE_STATUS


def _require_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"{name} must be numeric (no impute)",
        )
    return float(value)


def validate_l1_candidate(
    row: Mapping[str, Any],
    *,
    index: Optional[CaptureBatchIndex] = None,
) -> L1AvailabilityRow:
    """Validate one synthetic/candidate L1 row. Does not persist or acquire."""
    assert_activation_locked()
    assert_nowcast_off()
    if not isinstance(row, Mapping):
        raise Hhl1Reject(Hhl1RejectCode.SCHEMA_MISMATCH, "row must be an object")

    reject_nowcast_fields(row)
    reject_market_fields(row)
    _require_fields(row, L1_REQUIRED_FIELDS, code=Hhl1RejectCode.MISSING_REQUIRED_FIELD)

    if row.get("uncertainty") is not None:
        raise Hhl1Reject(
            Hhl1RejectCode.UNCERTAINTY_NOT_NULL,
            "uncertainty must be null (not used)",
        )

    factor = str(row.get("factor") or "").strip()
    if factor != FACTOR_AVAILABILITY:
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"factor must be {FACTOR_AVAILABILITY!r} (got {factor!r})",
        )

    missing_enum = str(row.get("missing_enum") or "").strip()
    if missing_enum not in MISSINGNESS_ENUM:
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"missing_enum {missing_enum!r} not in {sorted(MISSINGNESS_ENUM)}",
        )
    if missing_enum != MISSINGNESS_OBSERVED:
        raise Hhl1Reject(
            Hhl1RejectCode.UNAVAILABLE,
            f"missing_enum={missing_enum} is not an admitted OBSERVED L1 row",
        )

    team = str(row.get("team") or "").strip()
    if not is_team_code(team):
        raise Hhl1Reject(Hhl1RejectCode.SCHEMA_MISMATCH, f"team invalid: {team!r}")
    game_id = str(row.get("game_id") or "").strip()
    if not game_id:
        raise Hhl1Reject(Hhl1RejectCode.MISSING_REQUIRED_FIELD, "game_id missing")

    schema_version = str(row.get("schema_version") or SCHEMA_VERSION).strip()
    if schema_version != SCHEMA_VERSION:
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"schema_version must be {SCHEMA_VERSION} (got {schema_version!r})",
        )

    timestamps = _parse_timestamps(row)
    as_of_ts = canonicalize_utc(row.get("as_of_ts"), field="as_of_ts")
    if as_of_ts != timestamps.captured_at:
        raise Hhl1Reject(
            Hhl1RejectCode.AS_OF_VIOLATION,
            "as_of_ts must equal captured_at for an admitted L1 row",
        )

    provenance = _parse_provenance(row)
    baseline = _parse_baseline(row.get("baseline_personnel_ref"), team=team)
    starters = _parse_starters(row.get("expected_starters_asof"))
    delta_players = _parse_delta_players(row.get("delta_players"))
    _check_starter_consistency(baseline, starters, delta_players)

    offense_raw = _require_number(row.get("offense_raw"), "offense_raw")
    defense_raw = _require_number(row.get("defense_raw"), "defense_raw")
    offense_multiplier = _require_number(row.get("offense_multiplier"), "offense_multiplier")
    defense_multiplier = _require_number(row.get("defense_multiplier"), "defense_multiplier")
    # Magnitudes are accepted as caller-supplied numbers for schema completeness.
    # This CLEAR does not compute, fit, or score them.

    registry_id = str(row.get("registry_id") or "").strip()
    if not registry_id:
        raise Hhl1Reject(Hhl1RejectCode.MISSING_REQUIRED_FIELD, "registry_id missing")

    supersedes = row.get("supersedes_capture_id")
    supersedes_id = str(supersedes).strip() if _present(supersedes) else None

    candidate = L1AvailabilityRow(
        capture_id="pending",
        game_id=game_id,
        team=team,
        factor=FACTOR_AVAILABILITY,
        as_of_ts=as_of_ts,
        timestamps=timestamps,
        baseline_personnel_ref=baseline,
        expected_starters_asof=starters,
        registry_id=registry_id,
        provenance=provenance,
        offense_raw=offense_raw,
        defense_raw=defense_raw,
        offense_multiplier=offense_multiplier,
        defense_multiplier=defense_multiplier,
        delta_players=delta_players,
        missing_enum=MISSINGNESS_OBSERVED,
        supersedes_capture_id=supersedes_id,
        uncertainty=None,
        schema_version=SCHEMA_VERSION,
    )
    derived = make_capture_id(
        payload=candidate.identity_payload(),
        source_id=provenance.source_id,
        source_published_at=timestamps.source_published_at,
        captured_at=timestamps.captured_at,
    )
    supplied = str(row.get("capture_id") or "").strip().lower()
    if supplied != derived:
        raise Hhl1Reject(
            Hhl1RejectCode.IDENTITY_MISMATCH,
            "capture_id does not match sha256(canonical_json(payload)‖source_id‖"
            "source_published_at‖captured_at)",
        )
    if supersedes_id and supersedes_id == derived:
        raise Hhl1Reject(
            Hhl1RejectCode.AMBIGUOUS,
            "supersedes_capture_id must not equal capture_id",
        )

    sealed = L1AvailabilityRow(
        capture_id=derived,
        game_id=candidate.game_id,
        team=candidate.team,
        factor=candidate.factor,
        as_of_ts=candidate.as_of_ts,
        timestamps=candidate.timestamps,
        baseline_personnel_ref=candidate.baseline_personnel_ref,
        expected_starters_asof=candidate.expected_starters_asof,
        registry_id=candidate.registry_id,
        provenance=candidate.provenance,
        offense_raw=candidate.offense_raw,
        defense_raw=candidate.defense_raw,
        offense_multiplier=candidate.offense_multiplier,
        defense_multiplier=candidate.defense_multiplier,
        delta_players=candidate.delta_players,
        missing_enum=candidate.missing_enum,
        supersedes_capture_id=candidate.supersedes_capture_id,
        uncertainty=None,
        schema_version=candidate.schema_version,
    )

    if index is not None:
        _index_or_duplicate(index, sealed)
    return sealed


def _index_or_duplicate(index: CaptureBatchIndex, row: L1AvailabilityRow) -> None:
    biz = (row.game_id, row.team, row.factor, row.provenance.source_snapshot_id)
    prior = index.capture_ids.get(row.capture_id)
    if prior is not None:
        raise Hhl1Reject(
            Hhl1RejectCode.DUPLICATE,
            f"duplicate capture_id {row.capture_id}",
        )
    prior_biz = index.business_keys.get(biz)
    if prior_biz is not None:
        raise Hhl1Reject(
            Hhl1RejectCode.DUPLICATE,
            f"duplicate business identity {biz} (prior capture_id {prior_biz})",
        )
    index.capture_ids[row.capture_id] = row.game_id
    index.business_keys[biz] = row.capture_id


def validate_l1_batch(rows: Iterable[Mapping[str, Any]]) -> List[L1AvailabilityRow]:
    """Validate a batch atomically. Any reject ⇒ no admitted rows returned."""
    assert_activation_locked()
    index = CaptureBatchIndex()
    prepared: List[L1AvailabilityRow] = []
    raw_list = list(rows)
    for raw in raw_list:
        prepared.append(validate_l1_candidate(raw, index=index))
    return prepared


def admitted_source_id() -> str:
    return ADMITTED_SOURCE_ID


def protocol_sha() -> str:
    return PROTOCOL_SHA256
