"""H-HL-1 L1 capture schema (protocol §5). Interfaces only — no acquisition.

Immutable event identity, source provenance, capture timestamps, kickoff
cutoff, expected starter state, missingness, and rejection reasons.

uncertainty is unused and MUST be null (protocol §5.2).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Tuple


class Hhl1RejectCode(str, Enum):
    """Closed set of plumbing rejection reasons. No silent default."""

    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    PROVENANCE_INCOMPLETE = "PROVENANCE_INCOMPLETE"
    LATE = "LATE"
    STALE = "STALE"
    AS_OF_VIOLATION = "AS_OF_VIOLATION"
    CUTOFF_MISMATCH = "CUTOFF_MISMATCH"
    AMBIGUOUS = "AMBIGUOUS"
    DUPLICATE = "DUPLICATE"
    NOWCAST_OFF = "NOWCAST_OFF"
    MARKET_IN_L1 = "MARKET_IN_L1"
    UNSUPPORTED_SOURCE = "UNSUPPORTED_SOURCE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    UNCERTAINTY_NOT_NULL = "UNCERTAINTY_NOT_NULL"
    RATING_WINDOW_UNRESOLVED = "RATING_WINDOW_UNRESOLVED"


class Hhl1Reject(ValueError):
    """Fail-closed capture-plumbing reject. Callers must not impute."""

    def __init__(self, code: Hhl1RejectCode, message: str) -> None:
        self.code = code
        super().__init__(f"HHL1 REJECT [{code.value}] {message}")


@dataclass(frozen=True)
class CaptureTimestamps:
    """Protocol capture_ts triple + kickoff used to verify the −90m cutoff.

    Rule: source_published_at ≤ captured_at ≤ decision_ts < kickoff_ts.
    decision_ts MUST equal kickoff_ts − 90 minutes (provisional R3).
    All instants are UTC.
    """

    source_published_at: str
    captured_at: str
    decision_ts: str
    kickoff_ts: str


@dataclass(frozen=True)
class SourceProvenance:
    """Source provenance required on every candidate L1 row."""

    source_id: str
    source_url: str
    source_snapshot_id: str  # sha256 of raw bytes (hex)
    parser_version: str
    protocol_sha: str
    table_sha: Optional[str] = None  # 73cad579 pin when weights are recorded


@dataclass(frozen=True)
class BaselinePersonnelRef:
    """Hashed expected-starter list over the rating window.

    snap_share_threshold is the provisional ≥50% rule (R3).
    rating_window MUST be the literal UNRESOLVED — do not invent a window.
    player_ids are synthetic-or-gsis identifiers supplied by the caller;
    this plumbing does not build the list from snap counts.
    """

    team: str
    player_ids: Tuple[str, ...]
    snap_share_threshold: float
    rating_window: str
    source_id: str
    as_of_completed_week: str
    ref_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team,
            "player_ids": list(self.player_ids),
            "snap_share_threshold": self.snap_share_threshold,
            "rating_window": self.rating_window,
            "source_id": self.source_id,
            "as_of_completed_week": self.as_of_completed_week,
            "ref_sha256": self.ref_sha256,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "BaselinePersonnelRef":
        ids = raw.get("player_ids")
        if not isinstance(ids, (list, tuple)):
            raise Hhl1Reject(
                Hhl1RejectCode.SCHEMA_MISMATCH,
                "baseline_personnel_ref.player_ids must be a list (no impute)",
            )
        return cls(
            team=str(raw.get("team") or ""),
            player_ids=tuple(str(x) for x in ids),
            snap_share_threshold=raw.get("snap_share_threshold"),  # type: ignore[arg-type]
            rating_window=str(raw.get("rating_window") or ""),
            source_id=str(raw.get("source_id") or ""),
            as_of_completed_week=str(raw.get("as_of_completed_week") or ""),
            ref_sha256=str(raw.get("ref_sha256") or ""),
        )


@dataclass(frozen=True)
class ExpectedStarter:
    player_id: str
    position: str

    def to_dict(self) -> Dict[str, str]:
        return {"player_id": self.player_id, "position": self.position}


@dataclass(frozen=True)
class DeltaPlayer:
    """Delta-source fields (protocol §5.1). Weights are recorded, not computed.

    player_impact / weight fields may be present on a future authorized write.
    This plumbing does not calculate them and does not call nowcast.
    """

    player_id: str
    position: str
    report_status: str
    practice_status: Optional[str] = None
    injury: Optional[str] = None
    status_weight: Optional[float] = None
    practice_weight: Optional[float] = None
    position_weight_offense: Optional[float] = None
    position_weight_defense: Optional[float] = None
    injury_weight: Optional[float] = None
    player_impact: Optional[float] = None
    table_sha: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DeltaPlayer":
        return cls(
            player_id=str(raw.get("player_id") or ""),
            position=str(raw.get("position") or ""),
            report_status=str(raw.get("report_status") or ""),
            practice_status=_opt_str(raw.get("practice_status")),
            injury=_opt_str(raw.get("injury")),
            status_weight=_opt_float(raw.get("status_weight")),
            practice_weight=_opt_float(raw.get("practice_weight")),
            position_weight_offense=_opt_float(raw.get("position_weight_offense")),
            position_weight_defense=_opt_float(raw.get("position_weight_defense")),
            injury_weight=_opt_float(raw.get("injury_weight")),
            player_impact=_opt_float(raw.get("player_impact")),
            table_sha=_opt_str(raw.get("table_sha")),
        )


@dataclass(frozen=True)
class L1AvailabilityRow:
    """Protocol §5.2 L1 availability row. Append-only candidate; not written live."""

    capture_id: str
    game_id: str
    team: str
    factor: str
    as_of_ts: str
    timestamps: CaptureTimestamps
    baseline_personnel_ref: BaselinePersonnelRef
    expected_starters_asof: Tuple[ExpectedStarter, ...]
    registry_id: str
    provenance: SourceProvenance
    offense_raw: float
    defense_raw: float
    offense_multiplier: float
    defense_multiplier: float
    delta_players: Tuple[DeltaPlayer, ...]
    missing_enum: str
    supersedes_capture_id: Optional[str] = None
    uncertainty: Any = None  # must remain null
    schema_version: str = "hhl1-capture-plumbing-v0"

    @property
    def decision_ts(self) -> str:
        return self.timestamps.decision_ts

    @property
    def source_snapshot_id(self) -> str:
        return self.provenance.source_snapshot_id

    @property
    def baseline_ref(self) -> str:
        return self.baseline_personnel_ref.ref_sha256

    def identity_payload(self) -> Dict[str, Any]:
        """Canonical payload used (with provenance stamps) to derive capture_id."""
        return {
            "game_id": self.game_id,
            "team": self.team,
            "factor": self.factor,
            "as_of_ts": self.as_of_ts,
            "decision_ts": self.timestamps.decision_ts,
            "kickoff_ts": self.timestamps.kickoff_ts,
            "baseline_personnel_ref": self.baseline_personnel_ref.to_dict(),
            "expected_starters_asof": [s.to_dict() for s in self.expected_starters_asof],
            "registry_id": self.registry_id,
            "source_snapshot_id": self.provenance.source_snapshot_id,
            "offense_raw": self.offense_raw,
            "defense_raw": self.defense_raw,
            "offense_multiplier": self.offense_multiplier,
            "defense_multiplier": self.defense_multiplier,
            "delta_players": [p.to_dict() for p in self.delta_players],
            "missing_enum": self.missing_enum,
            "supersedes_capture_id": self.supersedes_capture_id,
            "uncertainty": self.uncertainty,
            "schema_version": self.schema_version,
        }

    def to_dict(self) -> Dict[str, Any]:
        payload = self.identity_payload()
        payload["capture_id"] = self.capture_id
        payload["source_published_at"] = self.timestamps.source_published_at
        payload["captured_at"] = self.timestamps.captured_at
        payload["provenance"] = asdict(self.provenance)
        return payload


@dataclass(frozen=True)
class ExclusionRecord:
    """Game/team excluded because no admissible L1 can be produced.

    Protocol §4.3: missing=true, counted and reported, never imputed.
    This CLEAR does not score; HF:=IF is recorded as a future-eval note only.
    """

    game_id: str
    team: str
    missing_enum: str
    reject_code: Hhl1RejectCode
    reason: str
    missing: bool = True
    hf_equals_if_note: str = "future-eval only; scoring NOT authorized"


@dataclass
class CaptureBatchIndex:
    """In-memory identity index for one validation batch. Not a store."""

    capture_ids: Dict[str, str] = field(default_factory=dict)
    business_keys: Dict[Tuple[str, str, str, str], str] = field(default_factory=dict)


def _opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _opt_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Hhl1Reject(
            Hhl1RejectCode.SCHEMA_MISMATCH,
            f"numeric field has non-numeric value {value!r} (no impute)",
        )
    return float(value)


# L1 required fields — protocol §4.4(iii) plus §5 identity/provenance.
L1_REQUIRED_FIELDS: Tuple[str, ...] = (
    "capture_id",
    "game_id",
    "team",
    "factor",
    "as_of_ts",
    "source_published_at",
    "captured_at",
    "decision_ts",
    "kickoff_ts",
    "baseline_personnel_ref",
    "expected_starters_asof",
    "registry_id",
    "source_snapshot_id",
    "offense_raw",
    "defense_raw",
    "offense_multiplier",
    "defense_multiplier",
    "delta_players",
    "missing_enum",
    "provenance",
)

PROVENANCE_REQUIRED_FIELDS: Tuple[str, ...] = (
    "source_id",
    "source_url",
    "source_snapshot_id",
    "parser_version",
    "protocol_sha",
)
