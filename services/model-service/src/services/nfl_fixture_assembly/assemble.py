"""OPT-IN INTERNAL FIXTURE-ONLY assembly.

typed envelope → #664 validate_l1_* / reject_market_fields →
synthetic exact quote → ONE eligibility result.

No simulator, produce_mu, forecast loader, outcome loader, network, DB, or jobs.
"""

from __future__ import annotations

import os
from typing import Any, Iterable, List, Mapping, Sequence

from src.services.nfl_fixture_assembly.contract import (
    FIXTURE_CHANNEL,
    FIXTURE_ENV_BYPASS_KEYS,
    OUTPUT_REFUSE,
    SYNTHETIC_ADJUSTMENT_POLICY,
    AssemblyResult,
    EligibilityDecision,
    FixtureEligibilityResult,
    FixtureEnvelope,
    FixtureHardRefuse,
    FixturePeriod,
    ForecastCapability,
    RequestedOutput,
    SyntheticQuote,
    expected_quote_line,
)
from src.services.nfl_fixture_assembly.synth import make_forecast_id
from src.services.nfl_hhl1_capture.identity import expected_decision_ts, is_sha256_hex
from src.services.nfl_hhl1_capture.schema import Hhl1Reject, Hhl1RejectCode
from src.services.nfl_hhl1_capture.validate import (
    reject_market_fields,
    validate_l1_batch,
    validate_l1_candidate,
)

_TRUTHY = frozenset({"1", "true", "yes", "y", "on"})

_HHL1_TO_FIXTURE = {
    Hhl1RejectCode.IDENTITY_MISMATCH: FixtureEligibilityResult.REFUSE_IDENTITY,
    Hhl1RejectCode.STALE: FixtureEligibilityResult.REFUSE_STALE,
    Hhl1RejectCode.LATE: FixtureEligibilityResult.REFUSE_TIME,
    Hhl1RejectCode.AS_OF_VIOLATION: FixtureEligibilityResult.REFUSE_TIME,
    Hhl1RejectCode.CUTOFF_MISMATCH: FixtureEligibilityResult.REFUSE_CUTOFF,
    Hhl1RejectCode.MISSING_REQUIRED_FIELD: FixtureEligibilityResult.REFUSE_MISSING,
    Hhl1RejectCode.PROVENANCE_INCOMPLETE: FixtureEligibilityResult.REFUSE_MISSING,
    Hhl1RejectCode.UNAVAILABLE: FixtureEligibilityResult.REFUSE_MISSING,
    Hhl1RejectCode.MARKET_IN_L1: FixtureEligibilityResult.REFUSE_MARKET_FIELDS,
    Hhl1RejectCode.AMBIGUOUS: FixtureEligibilityResult.REFUSE_PARTIAL,
    Hhl1RejectCode.DUPLICATE: FixtureEligibilityResult.REFUSE_PARTIAL,
    Hhl1RejectCode.SCHEMA_MISMATCH: FixtureEligibilityResult.REFUSE_VERSION,
    Hhl1RejectCode.NOT_AUTHORIZED: FixtureEligibilityResult.REFUSE_QUALIFICATION,
    Hhl1RejectCode.NOWCAST_OFF: FixtureEligibilityResult.REFUSE_QUALIFICATION,
    Hhl1RejectCode.UNSUPPORTED_SOURCE: FixtureEligibilityResult.REFUSE_QUALIFICATION,
    Hhl1RejectCode.RATING_WINDOW_UNRESOLVED: FixtureEligibilityResult.REFUSE_QUALIFICATION,
    Hhl1RejectCode.UNCERTAINTY_NOT_NULL: FixtureEligibilityResult.REFUSE_VALIDATION,
}

NON_FIXTURE_CONSUMERS = frozenset(
    {
        "subscriber",
        "betting",
        "production",
        "fair_lines_api",
        "honesty_board",
        "props_eligibility",
    }
)


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUTHY


def _refuse(result: FixtureEligibilityResult, reason: str) -> None:
    raise FixtureHardRefuse(result, reason)


def _map_hhl1(exc: Hhl1Reject) -> FixtureHardRefuse:
    mapped = _HHL1_TO_FIXTURE.get(exc.code, FixtureEligibilityResult.REFUSE_VALIDATION)
    return FixtureHardRefuse(mapped, str(exc))


def _finite_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _refuse(FixtureEligibilityResult.REFUSE_LINE, f"{field} is not a finite number")
    out = float(value)
    if out != out:  # NaN
        _refuse(FixtureEligibilityResult.REFUSE_LINE, f"{field} is NaN")
    return out


def _channel_gates(envelope: FixtureEnvelope) -> None:
    if envelope.production_mode:
        _refuse(
            FixtureEligibilityResult.REFUSE_PRODUCTION_CHANNEL,
            "production_mode=true is not a fixture allow (Alex X1)",
        )
    if envelope.channel != FIXTURE_CHANNEL:
        _refuse(
            FixtureEligibilityResult.REFUSE_PRODUCTION_CHANNEL,
            f"channel={envelope.channel!r} is not {FIXTURE_CHANNEL}",
        )
    if envelope.honor_env_bypass:
        _refuse(
            FixtureEligibilityResult.REFUSE_ENV_BYPASS,
            "honor_env_bypass cannot upgrade ALLOW_FIXTURE (Alex X1)",
        )
    if envelope.cacheable:
        _refuse(
            FixtureEligibilityResult.REFUSE_CACHE,
            "fixture assembly is private,no-store; cacheable=true refused",
        )
    if not envelope.fixture:
        _refuse(
            FixtureEligibilityResult.REFUSE_QUALIFICATION,
            "envelope.fixture must be true for fixture-channel qualification",
        )


def _capability_gates(envelope: FixtureEnvelope) -> None:
    bits = envelope.capability.bits
    requested = envelope.requested_output
    if not bits:
        _refuse(
            FixtureEligibilityResult.REFUSE_PARTIAL,
            "capability.bits empty (no silent default)",
        )
    if requested is RequestedOutput.POINT_MARGIN_SPREAD:
        if ForecastCapability.POINT_MARGIN not in bits:
            _refuse(
                FixtureEligibilityResult.REFUSE_CAPABILITY,
                "POINT_MARGIN_SPREAD requires POINT_MARGIN capability bit",
            )
        return
    if ForecastCapability.JOINT_SCORE in bits:
        _refuse(
            FixtureEligibilityResult.REFUSE_QUALIFICATION,
            "JOINT_SCORE bit is declared only; totals/ML/prob production is not authorized",
        )
    mapped = OUTPUT_REFUSE.get(requested)
    if mapped is not None:
        _refuse(mapped, f"point-margin input hard-refuses {requested.value} (no partial object)")
    _refuse(
        FixtureEligibilityResult.REFUSE_CAPABILITY,
        f"unsupported requested_output {requested.value}",
    )


def _cross_checks(envelope: FixtureEnvelope) -> None:
    forecast = envelope.forecast
    provenance = envelope.provenance
    quote = envelope.quote_spec
    l1 = envelope.l1_candidate
    if not isinstance(l1, Mapping):
        _refuse(FixtureEligibilityResult.REFUSE_PARTIAL, "l1_candidate must be an object")

    if forecast.period is not FixturePeriod.FULL_GAME or quote.period is not FixturePeriod.FULL_GAME:
        _refuse(FixtureEligibilityResult.REFUSE_PERIOD, "period must be full_game")
    if quote.period is not forecast.period:
        _refuse(FixtureEligibilityResult.REFUSE_PERIOD, "quote.period != forecast.period")

    l1_game = str(l1.get("game_id") or "")
    if not forecast.game_id or forecast.game_id != l1_game or quote.event_id != forecast.game_id:
        _refuse(
            FixtureEligibilityResult.REFUSE_GAME,
            "forecast.game_id / l1.game_id / quote.event_id identity mismatch",
        )
    if quote.side is not forecast.side:
        _refuse(FixtureEligibilityResult.REFUSE_SIGN, "quote.side != forecast.side")

    if not is_sha256_hex(forecast.forecast_id):
        _refuse(FixtureEligibilityResult.REFUSE_HASH, "forecast_id must be sha256 hex")
    derived_fid = make_forecast_id(
        game_id=forecast.game_id,
        period=forecast.period.value,
        side=forecast.side.value,
        point_margin=forecast.point_margin,
    )
    if forecast.forecast_id != derived_fid:
        _refuse(FixtureEligibilityResult.REFUSE_HASH, "forecast_id does not match canonical digest")

    if not is_sha256_hex(provenance.source_snapshot_id):
        _refuse(FixtureEligibilityResult.REFUSE_HASH, "source_snapshot_id must be sha256 hex")
    l1_snap = str((l1.get("provenance") or {}).get("source_snapshot_id") or l1.get("source_snapshot_id") or "")
    if provenance.source_snapshot_id != l1_snap:
        _refuse(FixtureEligibilityResult.REFUSE_HASH, "provenance.source_snapshot_id != l1 snapshot")

    l1_version = str(l1.get("schema_version") or "")
    if provenance.schema_version != l1_version:
        _refuse(FixtureEligibilityResult.REFUSE_VERSION, "schema_version mismatch vs L1")

    point_margin = _finite_number(forecast.point_margin, field="forecast.point_margin")
    line = _finite_number(quote.line, field="quote.line")
    expected_line = expected_quote_line(point_margin=point_margin, side=forecast.side)
    if line != expected_line:
        _refuse(
            FixtureEligibilityResult.REFUSE_SIGN
            if line == -expected_line
            else FixtureEligibilityResult.REFUSE_LINE,
            f"quote.line {line} != expected {expected_line} for {forecast.side.value}",
        )
    if not isinstance(quote.price, int) or isinstance(quote.price, bool):
        _refuse(FixtureEligibilityResult.REFUSE_LINE, "quote.price must be an int American price")
    if not str(quote.book or "").strip():
        _refuse(FixtureEligibilityResult.REFUSE_MISSING, "quote.book missing")

    if quote.time != provenance.captured_at or quote.time != provenance.as_of_ts:
        _refuse(FixtureEligibilityResult.REFUSE_TIME, "quote.time must equal captured_at/as_of_ts")
    try:
        expected_cut = expected_decision_ts(provenance.kickoff_ts)
    except Hhl1Reject as exc:
        raise _map_hhl1(exc) from exc
    if provenance.decision_ts != expected_cut:
        _refuse(
            FixtureEligibilityResult.REFUSE_CUTOFF,
            f"decision_ts must be kickoff−90m ({expected_cut})",
        )


def consume_eligibility(decision: EligibilityDecision, *, consumer: str) -> EligibilityDecision:
    """Alex X1: ALLOW_FIXTURE cannot be consumed by subscriber/betting/production."""
    token = str(consumer or "").strip().lower()
    if token in NON_FIXTURE_CONSUMERS:
        _refuse(
            FixtureEligibilityResult.REFUSE_PRODUCTION_CHANNEL,
            f"consumer={token!r} cannot consume ALLOW_FIXTURE (fixture-channel-only)",
        )
    if token != "fixture":
        _refuse(
            FixtureEligibilityResult.REFUSE_QUALIFICATION,
            f"unknown consumer {consumer!r}; only consumer='fixture' is qualified",
        )
    if decision.result is not FixtureEligibilityResult.ALLOW_FIXTURE:
        _refuse(decision.result, "eligibility is not ALLOW_FIXTURE")
    if (
        decision.subscriber_consumable
        or decision.betting_consumable
        or decision.production_consumable
        or decision.env_bypass_honored
        or decision.cacheable
    ):
        _refuse(
            FixtureEligibilityResult.REFUSE_PRODUCTION_CHANNEL,
            "ALLOW_FIXTURE payload illegally set a production/cache consumable bit",
        )
    bypass_hit = [name for name in FIXTURE_ENV_BYPASS_KEYS if _env_truthy(name)]
    if bypass_hit and decision.env_bypass_honored:
        _refuse(
            FixtureEligibilityResult.REFUSE_ENV_BYPASS,
            f"env {bypass_hit} must not be honored for ALLOW_FIXTURE",
        )
    return decision


def assemble_fixture_only(envelope: FixtureEnvelope) -> AssemblyResult:
    """Positive fixture path or typed hard refuse. Never a partial object."""
    if not isinstance(envelope, FixtureEnvelope):
        _refuse(FixtureEligibilityResult.REFUSE_PARTIAL, "envelope must be FixtureEnvelope")
    _channel_gates(envelope)
    _capability_gates(envelope)
    _cross_checks(envelope)

    try:
        reject_market_fields(envelope.l1_candidate)
        admitted = validate_l1_candidate(envelope.l1_candidate)
    except Hhl1Reject as exc:
        raise _map_hhl1(exc) from exc

    quote = SyntheticQuote(
        book=envelope.quote_spec.book,
        event_id=envelope.quote_spec.event_id,
        side=envelope.quote_spec.side.value,
        period=envelope.quote_spec.period.value,
        line=float(envelope.quote_spec.line),
        price=int(envelope.quote_spec.price),
        time=envelope.quote_spec.time,
    )
    eligibility = EligibilityDecision(
        result=FixtureEligibilityResult.ALLOW_FIXTURE,
        reason="fixture-channel transport admitted; not a production/betting allow",
    )
    consume_eligibility(eligibility, consumer="fixture")
    return AssemblyResult(
        eligibility=eligibility,
        quote=quote,
        admitted_capture_id=admitted.capture_id,
        admitted_game_id=admitted.game_id,
        offense_raw=admitted.offense_raw,
        defense_raw=admitted.defense_raw,
        offense_multiplier=admitted.offense_multiplier,
        defense_multiplier=admitted.defense_multiplier,
        adjustment_policy=SYNTHETIC_ADJUSTMENT_POLICY,
        capability_bits=tuple(sorted(bit.value for bit in envelope.capability.bits)),
    )


def assemble_fixture_batch(envelopes: Sequence[FixtureEnvelope]) -> List[AssemblyResult]:
    """Atomic batch: any refuse ⇒ no assembled rows returned."""
    prepared: List[Mapping[str, Any]] = []
    for envelope in envelopes:
        if not isinstance(envelope, FixtureEnvelope):
            _refuse(FixtureEligibilityResult.REFUSE_PARTIAL, "batch row is not FixtureEnvelope")
        _channel_gates(envelope)
        _capability_gates(envelope)
        _cross_checks(envelope)
        prepared.append(envelope.l1_candidate)
    try:
        validate_l1_batch(prepared)
    except Hhl1Reject as exc:
        raise _map_hhl1(exc) from exc
    return [assemble_fixture_only(envelope) for envelope in envelopes]


def forbidden_import_names() -> frozenset[str]:
    return frozenset(
        {
            "src.services.nfl_simulator",
            "src.services.nfl_injury_nowcast",
            "src.services.nfl_injury_report_scan",
            "src.services.nfl_props_eligibility",
            "src.tasks",
            "requests",
            "httpx",
            "sqlalchemy",
            "psycopg",
            "celery",
        }
    )


def forbidden_name_tokens() -> frozenset[str]:
    return frozenset(
        {
            "produce_mu",
            "result_loader",
            "fetch_nowcast",
            "acquire_odds",
        }
    )


def iter_package_paths() -> Iterable[Any]:
    from pathlib import Path

    return Path(__file__).resolve().parent.glob("*.py")
