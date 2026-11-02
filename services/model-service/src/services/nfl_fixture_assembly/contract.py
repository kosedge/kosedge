"""t5178u shared typed contract — fixture-channel only.

Source of truth for Worker A assembly and Worker B projections.
CERT=0. Not a production allow. Not a betting eligibility widen.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet, Literal, Mapping, Optional, Tuple

FIXTURE_CHANNEL: Literal["FIXTURE"] = "FIXTURE"
CONTRACT_ID = "t5178u-nfl-fixture-assembly-v0"
CONTRACT_SCHEMA_VERSION = "nfl-fixture-assembly-v0"

# Synthetic adjusted values prove transport through #664 validation only.
SYNTHETIC_ADJUSTMENT_POLICY = "TRANSPORT_ONLY_NOT_INJURY_POLICY"

# Env names that must not upgrade ALLOW_FIXTURE to production (Alex X1).
FIXTURE_ENV_BYPASS_KEYS: Tuple[str, ...] = (
    "NFL_EDGE_BOARD_INTERNAL",
    "NEXT_PUBLIC_NFL_EDGE_BOARD_INTERNAL",
    "NFL_EDGE_BOARD_PUBLIC_ENABLED",
    "NFL_FAIR_LINES_PUBLIC_SPREAD_ENABLED",
    "NFL_FAIR_LINES_PUBLIC_ML_ENABLED",
    "NFL_FAIR_LINES_PUBLIC_TOTAL_ENABLED",
    "NFL_FIXTURE_ALLOW_PRODUCTION",
    "NFL_FIXTURE_ENV_BYPASS",
    "HHL1_LIVE_CAPTURE",
    "HHL1_NOWCAST_ENABLED",
    "HHL1_SCORING",
    "HHL1_PUBLISH",
)

FORBIDDEN_POINT_MARGIN_OUTPUTS: FrozenSet[str] = frozenset(
    {
        "TOTAL",
        "MONEYLINE",
        "COVER_PROBABILITY",
        "ECONOMIC_ELIGIBILITY",
    }
)


class ForecastCapability(str, Enum):
    """Declared capability bit — not a joint spread/total/ML law."""

    POINT_MARGIN = "POINT_MARGIN"
    JOINT_SCORE = "JOINT_SCORE"


class RequestedOutput(str, Enum):
    POINT_MARGIN_SPREAD = "POINT_MARGIN_SPREAD"
    TOTAL = "TOTAL"
    MONEYLINE = "MONEYLINE"
    COVER_PROBABILITY = "COVER_PROBABILITY"
    ECONOMIC_ELIGIBILITY = "ECONOMIC_ELIGIBILITY"


class QuoteSide(str, Enum):
    HOME = "HOME"
    AWAY = "AWAY"


class FixturePeriod(str, Enum):
    """Only FULL_GAME is authorized. Other values exist so they can be refused."""

    FULL_GAME = "full_game"
    H1 = "h1"


class FixtureEligibilityResult(str, Enum):
    """ONE eligibility/refusal enum. ALLOW_FIXTURE is fixture-channel-only (X1)."""

    ALLOW_FIXTURE = "ALLOW_FIXTURE"
    REFUSE_IDENTITY = "REFUSE_IDENTITY"
    REFUSE_HASH = "REFUSE_HASH"
    REFUSE_VERSION = "REFUSE_VERSION"
    REFUSE_GAME = "REFUSE_GAME"
    REFUSE_PERIOD = "REFUSE_PERIOD"
    REFUSE_LINE = "REFUSE_LINE"
    REFUSE_SIGN = "REFUSE_SIGN"
    REFUSE_TIME = "REFUSE_TIME"
    REFUSE_CUTOFF = "REFUSE_CUTOFF"
    REFUSE_CAPABILITY = "REFUSE_CAPABILITY"
    REFUSE_QUALIFICATION = "REFUSE_QUALIFICATION"
    REFUSE_MISSING = "REFUSE_MISSING"
    REFUSE_STALE = "REFUSE_STALE"
    REFUSE_PARTIAL = "REFUSE_PARTIAL"
    REFUSE_CACHE = "REFUSE_CACHE"
    REFUSE_TOTALS = "REFUSE_TOTALS"
    REFUSE_MONEYLINE = "REFUSE_MONEYLINE"
    REFUSE_COVER_PROBABILITY = "REFUSE_COVER_PROBABILITY"
    REFUSE_ECONOMIC_ELIGIBILITY = "REFUSE_ECONOMIC_ELIGIBILITY"
    REFUSE_PRODUCTION_CHANNEL = "REFUSE_PRODUCTION_CHANNEL"
    REFUSE_ENV_BYPASS = "REFUSE_ENV_BYPASS"
    REFUSE_MARKET_FIELDS = "REFUSE_MARKET_FIELDS"
    REFUSE_VALIDATION = "REFUSE_VALIDATION"


OUTPUT_REFUSE: Mapping[RequestedOutput, FixtureEligibilityResult] = {
    RequestedOutput.TOTAL: FixtureEligibilityResult.REFUSE_TOTALS,
    RequestedOutput.MONEYLINE: FixtureEligibilityResult.REFUSE_MONEYLINE,
    RequestedOutput.COVER_PROBABILITY: FixtureEligibilityResult.REFUSE_COVER_PROBABILITY,
    RequestedOutput.ECONOMIC_ELIGIBILITY: FixtureEligibilityResult.REFUSE_ECONOMIC_ELIGIBILITY,
}


class FixtureHardRefuse(Exception):
    """Typed hard refuse. Callers must not build a partial success object."""

    def __init__(self, result: FixtureEligibilityResult, reason: str) -> None:
        self.result = result
        self.reason = reason
        self.partial = False
        super().__init__(f"FIXTURE HARD REFUSE [{result.value}] {reason}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "reason": self.reason,
            "partial": False,
            "fixture": True,
            "subscriber_consumable": False,
            "betting_consumable": False,
            "production_consumable": False,
            "env_bypass_honored": False,
            "cacheable": False,
            "contract_id": CONTRACT_ID,
        }


@dataclass(frozen=True)
class ForecastRecord:
    forecast_id: str
    game_id: str
    period: FixturePeriod
    side: QuoteSide
    point_margin: float


@dataclass(frozen=True)
class ProvenanceRecord:
    source_id: str
    source_url: str
    source_snapshot_id: str
    parser_version: str
    protocol_sha: str
    schema_version: str
    source_published_at: str
    captured_at: str
    decision_ts: str
    kickoff_ts: str
    as_of_ts: str


@dataclass(frozen=True)
class CapabilityRecord:
    bits: FrozenSet[ForecastCapability]

    @property
    def point_margin(self) -> bool:
        return ForecastCapability.POINT_MARGIN in self.bits

    @property
    def joint_score(self) -> bool:
        return ForecastCapability.JOINT_SCORE in self.bits


@dataclass(frozen=True)
class SyntheticQuoteSpec:
    """Exact-book/event/side/period/line/price/time — synthetic transport only."""

    book: str
    event_id: str
    side: QuoteSide
    period: FixturePeriod
    line: float
    price: int
    time: str


@dataclass(frozen=True)
class SyntheticQuote:
    book: str
    event_id: str
    side: str
    period: str
    line: float
    price: int
    time: str
    fixture: Literal[True] = True
    transport_only: Literal[True] = True
    injury_policy_approved: Literal[False] = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EligibilityDecision:
    result: FixtureEligibilityResult
    reason: str
    fixture: bool = True
    channel: str = FIXTURE_CHANNEL
    subscriber_consumable: Literal[False] = False
    betting_consumable: Literal[False] = False
    production_consumable: Literal[False] = False
    env_bypass_honored: Literal[False] = False
    cacheable: Literal[False] = False
    contract_id: str = CONTRACT_ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "reason": self.reason,
            "fixture": self.fixture,
            "channel": self.channel,
            "subscriber_consumable": False,
            "betting_consumable": False,
            "production_consumable": False,
            "env_bypass_honored": False,
            "cacheable": False,
            "contract_id": self.contract_id,
        }


@dataclass(frozen=True)
class FixtureEnvelope:
    forecast: ForecastRecord
    provenance: ProvenanceRecord
    capability: CapabilityRecord
    l1_candidate: Mapping[str, Any]
    quote_spec: SyntheticQuoteSpec
    requested_output: RequestedOutput = RequestedOutput.POINT_MARGIN_SPREAD
    channel: str = FIXTURE_CHANNEL
    fixture: bool = True
    production_mode: bool = False
    honor_env_bypass: bool = False
    cacheable: bool = False


@dataclass(frozen=True)
class AssemblyResult:
    eligibility: EligibilityDecision
    quote: SyntheticQuote
    admitted_capture_id: str
    admitted_game_id: str
    offense_raw: float
    defense_raw: float
    offense_multiplier: float
    defense_multiplier: float
    adjustment_policy: str = SYNTHETIC_ADJUSTMENT_POLICY
    capability_bits: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eligibility": self.eligibility.to_dict(),
            "quote": self.quote.to_dict(),
            "admitted_capture_id": self.admitted_capture_id,
            "admitted_game_id": self.admitted_game_id,
            "offense_raw": self.offense_raw,
            "defense_raw": self.defense_raw,
            "offense_multiplier": self.offense_multiplier,
            "defense_multiplier": self.defense_multiplier,
            "adjustment_policy": self.adjustment_policy,
            "capability_bits": list(self.capability_bits),
            "contract_id": CONTRACT_ID,
            "schema_version": CONTRACT_SCHEMA_VERSION,
        }


def home_spread_from_point_margin(point_margin: float) -> float:
    """Home spread = −(home − away). Fixture convention only."""
    return -float(point_margin)


def expected_quote_line(*, point_margin: float, side: QuoteSide) -> float:
    home_spread = home_spread_from_point_margin(point_margin)
    if side is QuoteSide.HOME:
        return home_spread
    return float(point_margin)
