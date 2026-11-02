"""t5194u / t5201u consume of a serialized FixtureChainRecord.

Reuses A's assemble identity/hash, cutoff, and American-price semantics.
Does not treat a hash-shaped string, equality of two corrupted fields, or a
self-declared recomputed digest as proof. CERT=0. Fixture-channel only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from src.services.nfl_fixture_assembly.assemble import (
    _american_price,
    _finite_number,
    consume_fixture_eligibility,
)
from src.services.nfl_fixture_assembly.contract import (
    CHAIN_CONTRACT_ID,
    CHAIN_SCHEMA_VERSION,
    CONTRACT_ID,
    CONTRACT_SCHEMA_VERSION,
    FIXTURE_CHANNEL,
    FixtureEligibilityResult,
    FixtureHardRefuse,
    QuoteSide,
)
from src.services.nfl_fixture_assembly.synth import make_forecast_id
from src.services.nfl_hhl1_capture.identity import (
    canonicalize_utc,
    expected_decision_ts,
    is_sha256_hex,
    parse_utc,
)
from src.services.nfl_hhl1_capture.schema import Hhl1Reject

HANDOFF_KEYS = (
    "eligibility",
    "quote",
    "forecast",
    "provenance",
    "cutoff",
    "capability",
    "l1_candidate",
    "game_id",
    "admitted_capture_id",
)

_TIME_FIELDS = (
    "source_published_at",
    "captured_at",
    "decision_ts",
    "kickoff_ts",
    "as_of_ts",
)


def _refuse(result: FixtureEligibilityResult, reason: str) -> None:
    raise FixtureHardRefuse(result, reason)


def _as_record(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _refuse(FixtureEligibilityResult.REFUSE_PARTIAL, f"{label} must be an object")
    return value


def _parse_required_utc(
    value: Any,
    *,
    field: str,
    result: FixtureEligibilityResult,
) -> datetime:
    if value is None or (isinstance(value, str) and not value.strip()):
        _refuse(result, f"{field} missing (no impute)")
    try:
        return parse_utc(value, field=field)
    except Hhl1Reject as exc:
        raise FixtureHardRefuse(result, f"{field} is not a valid UTC timestamp: {exc}") from exc


def _canon_utc(value: Any, *, field: str, result: FixtureEligibilityResult) -> str:
    dt = _parse_required_utc(value, field=field, result=result)
    return canonicalize_utc(dt.strftime("%Y-%m-%dT%H:%M:%SZ"), field=field)


def consume_fixture_chain(raw: Any, *, consumer: str = "fixture") -> dict[str, Any]:
    """Validate a serialized A chain against trusted identity context.

    forecast_id must equal make_forecast_id(game_id, period, side, point_margin).
    decision_ts must parse as UTC and equal kickoff − 90 minutes on both
    cutoff and provenance. quote.price must be a valid American integer.
    """
    payload = _as_record(raw, "chain")
    if payload.get("chain_contract_id") != CHAIN_CONTRACT_ID:
        _refuse(
            FixtureEligibilityResult.REFUSE_VERSION,
            f"chain_contract_id {payload.get('chain_contract_id')!r} != {CHAIN_CONTRACT_ID}",
        )
    if payload.get("chain_schema_version") != CHAIN_SCHEMA_VERSION:
        _refuse(
            FixtureEligibilityResult.REFUSE_VERSION,
            f"chain_schema_version {payload.get('chain_schema_version')!r} != {CHAIN_SCHEMA_VERSION}",
        )
    if payload.get("base_contract_id") != CONTRACT_ID:
        _refuse(FixtureEligibilityResult.REFUSE_VERSION, "base_contract_id mismatch (not rewritten)")
    if payload.get("base_schema_version") != CONTRACT_SCHEMA_VERSION:
        _refuse(FixtureEligibilityResult.REFUSE_VERSION, "base_schema_version mismatch")
    if payload.get("channel") != FIXTURE_CHANNEL:
        _refuse(FixtureEligibilityResult.REFUSE_PRODUCTION_CHANNEL, "chain channel is not FIXTURE")
    if payload.get("fixture") is not True:
        _refuse(FixtureEligibilityResult.REFUSE_QUALIFICATION, "chain.fixture=false cannot be rewritten")
    if payload.get("production_mode") is not False:
        _refuse(FixtureEligibilityResult.REFUSE_PRODUCTION_CHANNEL, "production_mode must be false")
    if payload.get("cacheable") is not False:
        _refuse(FixtureEligibilityResult.REFUSE_CACHE, "chain.cacheable must be false")
    if payload.get("honor_env_bypass") is not False:
        _refuse(FixtureEligibilityResult.REFUSE_ENV_BYPASS, "honor_env_bypass must be false")

    missing = [key for key in HANDOFF_KEYS if key not in payload]
    if missing:
        _refuse(FixtureEligibilityResult.REFUSE_PARTIAL, f"chain missing {missing}")

    consume_fixture_eligibility(payload["eligibility"], consumer=consumer)

    forecast = _as_record(payload["forecast"], "forecast")
    quote = _as_record(payload["quote"], "quote")
    provenance = _as_record(payload["provenance"], "provenance")
    cutoff = _as_record(payload["cutoff"], "cutoff")
    capability = _as_record(payload["capability"], "capability")
    candidate = _as_record(payload["l1_candidate"], "l1_candidate")

    game_id = payload.get("game_id")
    if (
        not isinstance(game_id, str)
        or not game_id
        or game_id != forecast.get("game_id")
        or game_id != quote.get("event_id")
        or game_id != candidate.get("game_id")
    ):
        _refuse(
            FixtureEligibilityResult.REFUSE_GAME,
            "game_id / forecast / quote / candidate identity mismatch",
        )
    if payload.get("admitted_capture_id") != candidate.get("capture_id"):
        _refuse(FixtureEligibilityResult.REFUSE_IDENTITY, "admitted_capture_id != l1_candidate.capture_id")

    period = forecast.get("period")
    side = forecast.get("side")
    if period != "full_game" or quote.get("period") != "full_game":
        _refuse(FixtureEligibilityResult.REFUSE_PERIOD, "period must be full_game")
    if side not in {QuoteSide.HOME.value, QuoteSide.AWAY.value}:
        _refuse(FixtureEligibilityResult.REFUSE_SIGN, "forecast.side must be HOME or AWAY")
    if quote.get("side") != side:
        _refuse(FixtureEligibilityResult.REFUSE_SIGN, "quote.side != forecast.side")
    if quote.get("side") not in {QuoteSide.HOME.value, QuoteSide.AWAY.value}:
        _refuse(FixtureEligibilityResult.REFUSE_SIGN, "quote.side must be HOME or AWAY")

    point_margin = _finite_number(forecast.get("point_margin"), field="forecast.point_margin")
    line = _finite_number(quote.get("line"), field="quote.line")
    expected_line = -point_margin if side == QuoteSide.HOME.value else point_margin
    if line != expected_line:
        _refuse(
            FixtureEligibilityResult.REFUSE_SIGN
            if line == -expected_line
            else FixtureEligibilityResult.REFUSE_LINE,
            f"quote.line {line} != expected {expected_line}",
        )
    _american_price(quote.get("price"))

    declared_id = forecast.get("forecast_id")
    if not is_sha256_hex(declared_id):
        _refuse(FixtureEligibilityResult.REFUSE_HASH, "forecast_id must be sha256 hex")
    # Trusted context is the identity fields, not a self-declared digest field.
    derived_id = make_forecast_id(
        game_id=str(game_id),
        period=str(period),
        side=str(side),
        point_margin=point_margin,
    )
    if declared_id != derived_id:
        _refuse(
            FixtureEligibilityResult.REFUSE_HASH,
            "forecast_id does not match canonical digest of trusted identity fields",
        )

    for field in _TIME_FIELDS:
        if field not in cutoff or cutoff.get(field) in (None, ""):
            result = (
                FixtureEligibilityResult.REFUSE_CUTOFF
                if field in {"decision_ts", "kickoff_ts"}
                else FixtureEligibilityResult.REFUSE_TIME
            )
            _refuse(result, f"cutoff.{field} missing")
        if field not in provenance or provenance.get(field) in (None, ""):
            result = (
                FixtureEligibilityResult.REFUSE_CUTOFF
                if field in {"decision_ts", "kickoff_ts"}
                else FixtureEligibilityResult.REFUSE_TIME
            )
            _refuse(result, f"provenance.{field} missing")

    kickoff_cut = _canon_utc(
        cutoff.get("kickoff_ts"), field="cutoff.kickoff_ts", result=FixtureEligibilityResult.REFUSE_CUTOFF
    )
    kickoff_prov = _canon_utc(
        provenance.get("kickoff_ts"),
        field="provenance.kickoff_ts",
        result=FixtureEligibilityResult.REFUSE_CUTOFF,
    )
    if kickoff_cut != kickoff_prov:
        _refuse(FixtureEligibilityResult.REFUSE_CUTOFF, "cutoff.kickoff_ts != provenance.kickoff_ts")

    try:
        expected_cut = expected_decision_ts(kickoff_prov)
    except Hhl1Reject as exc:
        raise FixtureHardRefuse(
            FixtureEligibilityResult.REFUSE_CUTOFF,
            f"kickoff_ts is not a valid UTC timestamp: {exc}",
        ) from exc

    decision_cut = _canon_utc(
        cutoff.get("decision_ts"),
        field="cutoff.decision_ts",
        result=FixtureEligibilityResult.REFUSE_CUTOFF,
    )
    decision_prov = _canon_utc(
        provenance.get("decision_ts"),
        field="provenance.decision_ts",
        result=FixtureEligibilityResult.REFUSE_CUTOFF,
    )
    if decision_cut != decision_prov:
        _refuse(FixtureEligibilityResult.REFUSE_CUTOFF, "cutoff.decision_ts != provenance.decision_ts")
    if decision_cut != expected_cut or decision_prov != expected_cut:
        _refuse(
            FixtureEligibilityResult.REFUSE_CUTOFF,
            f"decision_ts must be kickoff−90m ({expected_cut})",
        )

    captured_cut = _canon_utc(
        cutoff.get("captured_at"), field="cutoff.captured_at", result=FixtureEligibilityResult.REFUSE_TIME
    )
    captured_prov = _canon_utc(
        provenance.get("captured_at"),
        field="provenance.captured_at",
        result=FixtureEligibilityResult.REFUSE_TIME,
    )
    quote_time = _canon_utc(quote.get("time"), field="quote.time", result=FixtureEligibilityResult.REFUSE_TIME)
    if quote_time != captured_cut or quote_time != captured_prov:
        _refuse(FixtureEligibilityResult.REFUSE_TIME, "quote.time must equal captured_at")

    as_of_cut = _parse_required_utc(
        cutoff.get("as_of_ts"), field="cutoff.as_of_ts", result=FixtureEligibilityResult.REFUSE_TIME
    )
    as_of_prov = _parse_required_utc(
        provenance.get("as_of_ts"),
        field="provenance.as_of_ts",
        result=FixtureEligibilityResult.REFUSE_TIME,
    )
    kickoff_dt = _parse_required_utc(
        kickoff_prov, field="kickoff_ts", result=FixtureEligibilityResult.REFUSE_CUTOFF
    )
    if as_of_cut > kickoff_dt or as_of_prov > kickoff_dt:
        _refuse(FixtureEligibilityResult.REFUSE_STALE, "as_of_ts after kickoff_ts")
    if as_of_cut != as_of_prov:
        _refuse(FixtureEligibilityResult.REFUSE_TIME, "cutoff.as_of_ts != provenance.as_of_ts")

    bits = capability.get("bits")
    if not isinstance(bits, list) or "POINT_MARGIN" not in bits:
        _refuse(FixtureEligibilityResult.REFUSE_CAPABILITY, "POINT_MARGIN capability bit required")

    return payload
