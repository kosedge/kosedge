"""Snap-share `_5g` exposure ledger types.

DEVELOPMENT_ONLY. Answers one question: which players, and how much of
their participation, are represented in each team's Independent Fair
`_5g` historical rating window. Does not estimate player point value.

Authority: DECISION d48d15bc · ORDER 4f5811dc · contract 0614bdcc ·
IF window 205f33e0 (5G_ONLY) · RATIFY d4acc170 · as-of 312d4c65.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Optional, Tuple

from src.services.nfl_pregame_asof import IF_5G_SQL_FRAME, IF_MATCHUP_ASOF_CONTRACT


LEDGER_SCHEMA_VERSION = "snap-share-exposure-ledger-v0-t4822u"
WINDOW_LABEL_5G = "5g"
WINDOW_SIZE_5G = 5
STARTER_LABEL_THRESHOLD = 0.50

# ingest.py @1b39f4e9 materialize_matchup_features_from_usage — the IF `_5g`
# row is the unweighted mean over this exact SQL frame. Game IDs are NOT
# persisted on nfl_dp_team_rolling_features_weekly; they must be reconstructed
# from the same situational grain + schedule join. Do not substitute
# "latest five completed games from the schedule."
#
# t4822u: the frame still includes CURRENT ROW at rating_week (completed-data
# week). The matchup / ledger join is pregame: rating_week = target_week - 1.
# Pin 1b39f4e9 L1497-1501 joined rolling.week to schedule.week (same-week).
IF_5G_WINDOW_CONTRACT = f"{IF_5G_SQL_FRAME}; {IF_MATCHUP_ASOF_CONTRACT}"
IF_5G_WINDOW_CONTRACT_CITE = (
    "services/model-service/data_platform_nfl/ingest.py@1b39f4e9 L1305-1314 "
    "(frame) + t4822u pregame join rating_week = target_week - 1"
)

# Contract 0614bdcc §2 + snap_depth_ingest source label. Synthetic is tests only.
SOURCE_NFLVERSE_SNAP_COUNTS = "nflverse_snap_counts"
SOURCE_SYNTH_SNAP_COUNTS = "synth_snap_counts"
ALLOWED_SNAP_SOURCE_IDS = frozenset(
    {SOURCE_NFLVERSE_SNAP_COUNTS, SOURCE_SYNTH_SNAP_COUNTS}
)

ParticipationCompleteness = Literal["complete", "incomplete", "missing"]
SideName = Literal["offense", "defense"]
ParticipationStatus = Literal["measured", "verified_zero"]

# Fail-closed codes. Verified 0 and UNKNOWN are not interchangeable.
REJECT_WINDOW_INCOMPLETE = "WINDOW_INCOMPLETE"
REJECT_WINDOW_SHORT = "WINDOW_SHORT"
REJECT_WINDOW_MISMATCH = "WINDOW_MISMATCH"
REJECT_RATING_WEEK_UNRESOLVED = "RATING_WEEK_UNRESOLVED"
REJECT_TARGET_WEEK_INVALID = "TARGET_WEEK_INVALID"
REJECT_RATING_WEEK_NOT_LAGGED = "RATING_WEEK_NOT_LAGGED"
REJECT_RATING_WEEK_STALE = "RATING_WEEK_STALE"
REJECT_FUTURE_GAME_IN_WINDOW = "FUTURE_GAME_IN_WINDOW"
REJECT_GRAIN_MISMATCH = "GRAIN_MISMATCH"
REJECT_SCHEDULE_UNRESOLVED = "SCHEDULE_UNRESOLVED"
REJECT_GAME_NOT_COMPLETED = "GAME_NOT_COMPLETED"
REJECT_SNAPS_MISSING = "SNAPS_MISSING"
REJECT_SNAPS_INCOMPLETE = "SNAPS_INCOMPLETE"
REJECT_SOURCE_UNSUPPORTED = "SOURCE_UNSUPPORTED"
REJECT_ID_UNMAPPED = "ID_UNMAPPED"
REJECT_IDENTITY_COLLISION = "IDENTITY_COLLISION"
REJECT_INVALID_SNAP_DENOMINATOR = "INVALID_SNAP_DENOMINATOR"
REJECT_POSITION_UNKNOWN = "POSITION_UNKNOWN"
REJECT_POSITION_SIDE_UNSUPPORTED = "POSITION_SIDE_UNSUPPORTED"
REJECT_AS_OF_VIOLATION = "AS_OF_VIOLATION"
REJECT_TIMESTAMP_INVALID = "TIMESTAMP_INVALID"
REJECT_INPUT_INVALID = "INPUT_INVALID"

# Positions that select offense_pct vs defense_pct (contract §1).
# ST-only and unmapped tokens fail closed — they are not guessed.
OFFENSE_POSITIONS = frozenset(
    {
        "QB",
        "RB",
        "FB",
        "HB",
        "WR",
        "TE",
        "T",
        "G",
        "C",
        "OT",
        "OG",
        "OL",
        "LT",
        "RT",
        "LG",
        "RG",
    }
)
DEFENSE_POSITIONS = frozenset(
    {
        "DE",
        "DT",
        "NT",
        "DL",
        "EDGE",
        "LB",
        "ILB",
        "OLB",
        "MLB",
        "CB",
        "S",
        "FS",
        "SS",
        "DB",
        "NB",
        "SAF",
    }
)

# Isolation: this package must never import or name-call these live paths.
FORBIDDEN_IMPORT_NAMES = frozenset(
    {
        "nfl_simulator",
        "simulate_nfl_game",
        "simulate_nfl_game_independent_fair",
        "nfl_injury_nowcast",
        "injury_nowcast",
        "nfl_hhl1_capture",
        "src.tasks",
        "src.routes",
        "offense_index",
        "defense_index",
        "data_platform_nfl",
        "nflreadpy",
        "nflverse",
    }
)


class ExposureLedgerReject(Exception):
    """Fail-closed reject. Never impute missing participation as 0."""

    def __init__(self, code: str, message: str) -> None:
        self.code = str(code)
        self.message = str(message)
        super().__init__(f"{self.code}: {self.message}")


@dataclass(frozen=True)
class SituationalWeekRow:
    """One team-week row from the IF `_5g` situational grain (no game_id)."""

    season: int
    week: int
    team: str
    games_played: Optional[int] = None
    source: Optional[str] = None


@dataclass(frozen=True)
class ScheduleGameRow:
    """Schedule join used only to recover game_id for a situational week."""

    season: int
    week: int
    game_id: str
    home_team: str
    away_team: str
    completed: bool = True
    game_date: Optional[str] = None
    kickoff_ts: Optional[str] = None


@dataclass(frozen=True)
class SnapFact:
    """Game-level snap share for one player on one team.

    ``player_pfr_id`` is the snap-source key (nflverse). GSIS is applied
    via an explicit identity map — never guessed from name.
    """

    game_id: str
    team: str
    player_pfr_id: str
    player_name: str
    position: str
    offense_pct: Optional[float]
    defense_pct: Optional[float]
    source_id: str
    as_of_ts: str
    offense_snaps: Optional[float] = None
    defense_snaps: Optional[float] = None


@dataclass(frozen=True)
class GameParticipationBundle:
    """Participation record for one team-game.

    completeness:
      complete — verified full snap list; players absent from facts = 0
      incomplete — source present but not trusted as complete → UNKNOWN
      missing — no source → UNKNOWN
    complete and incomplete are not interchangeable.
    """

    game_id: str
    team: str
    source_id: str
    as_of_ts: str
    completeness: ParticipationCompleteness
    facts: Tuple[SnapFact, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class IdentityLink:
    """Caller-supplied PFR → GSIS link. Missing link ⇒ ID_UNMAPPED."""

    player_pfr_id: str
    player_gsis_id: str


@dataclass(frozen=True)
class ResolvedWindowGame:
    season: int
    week: int
    team: str
    game_id: str
    games_played: Optional[int]


@dataclass(frozen=True)
class ResolvedIf5gWindow:
    season: int
    rating_week: int
    target_week: int
    team: str
    window: str
    contract: str
    games: Tuple[ResolvedWindowGame, ...]
    window_fingerprint: str
    target_game_id: Optional[str] = None

    @property
    def game_ids(self) -> Tuple[str, ...]:
        return tuple(g.game_id for g in self.games)


@dataclass(frozen=True)
class GameExposure:
    game_id: str
    week: int
    snap_pct: float
    participation_status: ParticipationStatus
    position: Optional[str]


@dataclass(frozen=True)
class ExposureLedgerRow:
    window: str
    season: int
    rating_week: int
    target_week: int
    team: str
    player_gsis_id: str
    player_pfr_ids: Tuple[str, ...]
    player_name: str
    position: str
    side: SideName
    game_ids: Tuple[str, ...]
    game_exposures: Tuple[GameExposure, ...]
    embedded_snap_share: float
    starter_label_derived: bool
    source_ids: Tuple[str, ...]
    source_as_of_ts: Tuple[str, ...]
    schema_version: str
    row_fingerprint: str

    def to_public_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass(frozen=True)
class ExposureLedger:
    """Deterministic team-window ledger. No impact weights. No scoring."""

    schema_version: str
    window: str
    season: int
    rating_week: int
    target_week: int
    team: str
    window_contract: str
    window_game_ids: Tuple[str, ...]
    window_fingerprint: str
    input_fingerprint: str
    output_fingerprint: str
    ledger_id: str
    as_of_ts: str
    rows: Tuple[ExposureLedgerRow, ...]
    notes: Tuple[str, ...] = field(default_factory=tuple)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "window": self.window,
            "season": self.season,
            "rating_week": self.rating_week,
            "target_week": self.target_week,
            "team": self.team,
            "window_contract": self.window_contract,
            "window_game_ids": list(self.window_game_ids),
            "window_fingerprint": self.window_fingerprint,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "ledger_id": self.ledger_id,
            "as_of_ts": self.as_of_ts,
            "notes": list(self.notes),
            "rows": [r.to_public_dict() for r in self.rows],
        }


def normalize_team(value: Any) -> str:
    return str(value or "").strip().upper()


def normalize_position(value: Any) -> str:
    return str(value or "").strip().upper()


def side_for_position(position: str) -> SideName:
    pos = normalize_position(position)
    if not pos:
        raise ExposureLedgerReject(
            REJECT_POSITION_UNKNOWN, "position missing (no impute)"
        )
    if pos in OFFENSE_POSITIONS:
        return "offense"
    if pos in DEFENSE_POSITIONS:
        return "defense"
    raise ExposureLedgerReject(
        REJECT_POSITION_SIDE_UNSUPPORTED,
        f"position {pos!r} has no offense/defense snap side (no ST guess)",
    )


def require_nonempty_str(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ExposureLedgerReject(
            REJECT_INPUT_INVALID, f"{field_name} required (no impute)"
        )
    return text
