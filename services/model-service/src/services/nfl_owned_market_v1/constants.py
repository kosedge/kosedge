"""Isolated nfl_owned_market_v1 pins. CERT=0. Synthetic only.

Worker B package. Worker A (R7_CORRECTNESS_V1) is the sole shared-gate
registrar. This module does not register profiles.
"""

from __future__ import annotations

from typing import FrozenSet, Tuple

PACKAGE = "nfl_owned_market_v1"
CERT = 0
DATA_LABEL = "SYNTHETIC"
CHANNEL = "SYNTHETIC"
OWNER_CLEAR = "86257"
TICKET = "t5289u"
SCOPE_ID = "chief-nflgreen-model-day-20261103-1700"
PLAN_FINGERPRINT = "b15d6cec143212067b896057a048cd51071981d6ea1b3561c08db89cb6355358"
WORKER = "B"
ROLE = "NARROW_PATCH"

PROFILE_OWNED_MARKET_TRACE = "OWNED_MARKET_TRACE_V1"
PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS = "SYNTHETIC_MARKET_ECONOMIC_EVENTS_V1"
PROFILES: Tuple[str, ...] = (
    PROFILE_OWNED_MARKET_TRACE,
    PROFILE_SYNTHETIC_MARKET_ECONOMIC_EVENTS,
)

SCHEMA_OWNED_MARKET_TRACE = "owned-market-trace-v1"
SCHEMA_SYNTHETIC_MARKET_ECONOMIC_EVENTS = "synthetic-market-economic-events-v1"

KO_MINUS_MINUTES = 60
SEAL_EQUALS_CUTOFF = True

PIN_R6_A = "54b08a301cf824c79ee3203180a51e2d832bb6f9"
PIN_R6_B = "afb13301b5c7e3b8780a8dd1f85145e91bebef55"
PIN_713_TIP = "679dbdaf8c9044edffb34ffca1543c33eea77db7"
PIN_714_PARTIAL = "5558890b5f8a66c16c658fce2971f0a7e2f2c7de"
PIN_BASE = "f5e3bb58ccbe5a8892fed2a01f347c2308394a2f"
PIN_714_IS_BASE = False

SYNTHETIC_TOKEN = "SYNTHETIC"
IDENTITY_KIND = "SYNTHETIC_OWNED_MARKET"
BOOK_ID = "OWNED_SYNTH_BOOK"
VENUE_ID = "SYNTHETIC_VENUE_99"

# Fictional week-99 envelope. Not EVAL. Not a 2024-26 reopen.
PINNED_GAME_ID = "SYNTHETIC_2026_99_AAA_ZZZ"
PINNED_SEASON = 2026
PINNED_WEEK = 99
PINNED_SEASON_TYPE = "REG"
PINNED_HOME = "ZZZ"
PINNED_AWAY = "AAA"
PINNED_KICKOFF_UTC = "2026-12-06T18:00:00Z"
PINNED_CUTOFF_UTC = "2026-12-06T17:00:00Z"
PINNED_SEAL_UTC = PINNED_CUTOFF_UTC
PINNED_TRACE_ID = "SYNTHETIC_TRACE_OWNED_MARKET_V1"
PINNED_BATCH_ID = "SYNTHETIC_EVT_BATCH_OWNED_MARKET_V1"

MARKETS: FrozenSet[str] = frozenset({"spread", "total", "ml"})
SIDES: FrozenSet[str] = frozenset({"home", "away", "over", "under"})
EVENT_TYPES: FrozenSet[str] = frozenset(
    {
        "INJURY_STATUS",
        "WEATHER_SHIFT",
        "LINEUP_CONFIRM",
        "REST_SHOCK",
        "LIQUIDITY_SHOCK",
        "NEWS_VOID",
    }
)
EFFECT_CHANNELS: FrozenSet[str] = frozenset(
    {"SPREAD", "TOTAL", "ML", "USAGE", "VIG", "VOID"}
)
TEAMS: FrozenSet[str] = frozenset({PINNED_HOME, PINNED_AWAY, "NEUTRAL"})
PLAYER_SLOTS: FrozenSet[str] = frozenset({"QB1", "RB1", "WR1", "TE1", "NONE"})
OBS_STATUS = "DERIVED_PREGAME"
OBS_SOURCE = "SYNTHETIC_OWNED_QUOTE"
EVT_SOURCE = "SYNTHETIC_OWNED_EVENT"

FORBIDDEN_OUTPUT_KEYS: FrozenSet[str] = frozenset(
    {
        "play",
        "lean",
        "stake",
        "units",
        "clv",
        "edge",
        "kei",
        "bet",
        "wager",
        "ticket_stake",
    }
)
FORBIDDEN_BOOK_IDS: FrozenSet[str] = frozenset(
    {
        "draftkings",
        "fanduel",
        "pinnacle",
        "betmgm",
        "caesars",
        "bovada",
        "pointsbet",
        "bet365",
        "circa",
        "bookmaker",
        "betonline",
        "heritage",
        "circasports",
        "dk",
        "fd",
        "mgm",
    }
)

ENVELOPE_FIELDS: Tuple[str, ...] = (
    "game_id",
    "season",
    "week",
    "season_type",
    "home_team",
    "away_team",
    "kickoff_utc",
    "venue_id",
    "identity_kind",
    "book_id",
)
TIMING_FIELDS: Tuple[str, ...] = (
    "kickoff_utc",
    "cutoff_utc",
    "seal_utc",
    "ko_minus_minutes",
)
OBS_FIELDS: Tuple[str, ...] = (
    "seq",
    "market",
    "side",
    "line",
    "price",
    "available_at",
    "observed_at",
    "source",
    "status",
    "caused_by_event_id",
    "source_byte_hash",
)
EVENT_FIELDS: Tuple[str, ...] = (
    "event_id",
    "event_type",
    "effect_channel",
    "team",
    "player_slot",
    "magnitude",
    "available_at",
    "observed_at",
    "payload",
    "source",
    "source_byte_hash",
)

CODE_BIND_FILES: Tuple[str, ...] = (
    "constants.py",
    "hashing.py",
    "refuse.py",
    "schema.py",
    "validate.py",
    "produce.py",
    "pins.py",
    "profiles.py",
    "run.py",
    "__init__.py",
)
