"""Synthetic fixture builders. Transport-only inputs — no live rows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional

from src.services.nfl_fixture_assembly.contract import (
    CapabilityRecord,
    FixtureEnvelope,
    FixturePeriod,
    ForecastCapability,
    ForecastRecord,
    ProvenanceRecord,
    QuoteSide,
    RequestedOutput,
    SyntheticQuoteSpec,
    expected_quote_line,
)
from src.services.nfl_hhl1_capture.constants import (
    ADMITTED_SOURCE_ID,
    DECISION_OFFSET_BEFORE_KICKOFF_MINUTES,
    PARSER_VERSION_PLUMBING,
    PROTOCOL_SHA256,
    RATING_WINDOW_DEFINITION,
    SCHEMA_VERSION,
    SNAP_SHARE_THRESHOLD,
)
from src.services.nfl_hhl1_capture.identity import (
    canonical_json,
    make_baseline_ref_sha,
    make_capture_id,
    make_source_snapshot_id,
    sha256_hex,
)
from src.services.nfl_hhl1_capture.schema import (
    BaselinePersonnelRef,
    CaptureTimestamps,
    DeltaPlayer,
    ExpectedStarter,
    L1AvailabilityRow,
    SourceProvenance,
)

KICKOFF = datetime(2026, 11, 8, 18, 0, tzinfo=timezone.utc)
DECISION = KICKOFF - timedelta(minutes=DECISION_OFFSET_BEFORE_KICKOFF_MINUTES)
CAPTURED = DECISION - timedelta(minutes=15)
PUBLISHED = CAPTURED - timedelta(minutes=10)

SYNTH_BOOK = "SYNTH-BOOK-T5178U"
SYNTH_GAME_ID = "2026_99_TST_SYN"
SYNTH_SOURCE_BYTES = b"synthetic-official-report-bytes-t5178u-v0"


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_forecast_id(*, game_id: str, period: str, side: str, point_margin: float) -> str:
    blob = canonical_json(
        {
            "game_id": game_id,
            "period": period,
            "point_margin": float(point_margin),
            "side": side,
        }
    )
    return sha256_hex(blob.encode("utf-8"))


def _baseline(team: str = "SYN") -> BaselinePersonnelRef:
    ids = tuple(f"00-SYNTH-{s}" for s in ("QB1", "WR1", "RB1", "TE1", "OL1"))
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


def synthetic_l1_row(
    *,
    team: str = "SYN",
    game_id: str = SYNTH_GAME_ID,
    offense_raw: float = 0.12,
    defense_raw: float = -0.08,
    offense_multiplier: float = 0.97,
    defense_multiplier: float = 1.03,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    timestamps = CaptureTimestamps(
        source_published_at=iso(PUBLISHED),
        captured_at=iso(CAPTURED),
        decision_ts=iso(DECISION),
        kickoff_ts=iso(KICKOFF),
    )
    provenance = SourceProvenance(
        source_id=ADMITTED_SOURCE_ID,
        source_url="https://example.test/synth/official-nfl-injury-report",
        source_snapshot_id=make_source_snapshot_id(SYNTH_SOURCE_BYTES),
        parser_version=PARSER_VERSION_PLUMBING,
        protocol_sha=PROTOCOL_SHA256,
    )
    pending = L1AvailabilityRow(
        capture_id="pending",
        game_id=game_id,
        team=team,
        factor="availability",
        as_of_ts=timestamps.captured_at,
        timestamps=timestamps,
        baseline_personnel_ref=_baseline(team),
        expected_starters_asof=_starters(),
        registry_id="hhl1-synth-registry-t5178u",
        provenance=provenance,
        offense_raw=offense_raw,
        defense_raw=defense_raw,
        offense_multiplier=offense_multiplier,
        defense_multiplier=defense_multiplier,
        delta_players=(
            DeltaPlayer(
                player_id="00-SYNTH-WR2",
                position="WR",
                report_status="Out",
            ),
        ),
        missing_enum="OBSERVED",
        supersedes_capture_id=None,
        uncertainty=None,
        schema_version=SCHEMA_VERSION,
    )
    capture_id = make_capture_id(
        payload=pending.identity_payload(),
        source_id=pending.provenance.source_id,
        source_published_at=pending.timestamps.source_published_at,
        captured_at=pending.timestamps.captured_at,
    )
    sealed = L1AvailabilityRow(
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
    row = sealed.to_dict()
    if extra:
        row.update(dict(extra))
    return row


def synthetic_envelope(**overrides: Any) -> FixtureEnvelope:
    point_margin = float(overrides.pop("point_margin", 3.0))
    side = overrides.pop("side", QuoteSide.HOME)
    if isinstance(side, str):
        side = QuoteSide(side)
    period = overrides.pop("period", FixturePeriod.FULL_GAME)
    if isinstance(period, str):
        period = FixturePeriod(period)
    game_id = str(overrides.pop("game_id", SYNTH_GAME_ID))
    overrides.pop("team_ignored", None)
    l1 = overrides.pop("l1_candidate", None) or synthetic_l1_row(game_id=game_id)
    captured_at = str(l1.get("captured_at") or iso(CAPTURED))
    forecast_id = str(
        overrides.pop(
            "forecast_id",
            make_forecast_id(
                game_id=game_id,
                period=period.value,
                side=side.value,
                point_margin=point_margin,
            ),
        )
    )
    quote_line = overrides.pop("quote_line", expected_quote_line(point_margin=point_margin, side=side))
    quote_spec = overrides.pop("quote_spec", None) or SyntheticQuoteSpec(
        book=str(overrides.pop("book", SYNTH_BOOK)),
        event_id=str(overrides.pop("event_id", game_id)),
        side=side,
        period=period,
        line=float(quote_line),
        price=int(overrides.pop("price", -110)),
        time=str(overrides.pop("quote_time", captured_at)),
    )
    provenance = overrides.pop("provenance", None) or ProvenanceRecord(
        source_id=str(l1["provenance"]["source_id"]),
        source_url=str(l1["provenance"]["source_url"]),
        source_snapshot_id=str(l1["provenance"]["source_snapshot_id"]),
        parser_version=str(l1["provenance"]["parser_version"]),
        protocol_sha=str(l1["provenance"]["protocol_sha"]),
        schema_version=str(l1.get("schema_version") or SCHEMA_VERSION),
        source_published_at=str(l1["source_published_at"]),
        captured_at=captured_at,
        decision_ts=str(l1["decision_ts"]),
        kickoff_ts=str(l1["kickoff_ts"]),
        as_of_ts=str(l1["as_of_ts"]),
    )
    bits = overrides.pop("capability_bits", None) or frozenset({ForecastCapability.POINT_MARGIN})
    capability = overrides.pop("capability", None) or CapabilityRecord(bits=frozenset(bits))
    forecast = overrides.pop("forecast", None) or ForecastRecord(
        forecast_id=forecast_id,
        game_id=game_id,
        period=period,
        side=side,
        point_margin=point_margin,
    )
    return FixtureEnvelope(
        forecast=forecast,
        provenance=provenance,
        capability=capability,
        l1_candidate=l1,
        quote_spec=quote_spec,
        requested_output=overrides.pop("requested_output", RequestedOutput.POINT_MARGIN_SPREAD),
        channel=str(overrides.pop("channel", "FIXTURE")),
        fixture=bool(overrides.pop("fixture", True)),
        production_mode=bool(overrides.pop("production_mode", False)),
        honor_env_bypass=bool(overrides.pop("honor_env_bypass", False)),
        cacheable=bool(overrides.pop("cacheable", False)),
    )
